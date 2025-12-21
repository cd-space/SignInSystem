from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from pydantic import BaseModel
from typing import Optional, List
from app.db.connection import get_connection
import logging
import uuid
import os
from pathlib import Path
from app.services.FaceRecognitionService import FaceRecognitionService
from app.utils.FeatureBinaryConver import feature_to_bytes, bytes_to_feature
from PIL import Image
import io

logger = logging.getLogger()
router = APIRouter()

# 初始化人脸识别服务
face_service = FaceRecognitionService()


@router.post("/api/upload_face")
async def upload_face(
    user_id: str = Form(..., description="用户ID"),
    face_image: UploadFile = File(..., description="人脸照片文件")
):
    """
    上传用户人脸照片并提取特征向量
    """
    logger.info(f"收到上传请求: user_id={user_id}, filename={face_image.filename}, content_type={face_image.content_type}")
    
    if not user_id or user_id.strip() == "":
        raise HTTPException(status_code=400, detail="需要提供 user_id")
    
    if not face_image or not face_image.filename:
        raise HTTPException(status_code=400, detail="需要上传人脸照片")
    
    # 验证文件类型
    allowed_extensions = {".jpg", ".jpeg", ".png", ".bmp"}
    file_ext = os.path.splitext(face_image.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="仅支持 jpg, jpeg, png, bmp 格式")

    conn = None
    cursor = None
    file_path = None
    
    try:
        # 验证用户是否存在
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败")
        
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM user_info WHERE id = %s LIMIT 1", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="用户不存在")

        # 读取文件内容
        content = await face_image.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="上传的文件为空")
        
        # 创建保存目录
        base_dir = Path("app/static/faces")
        base_dir.mkdir(parents=True, exist_ok=True)

        # 生成唯一文件名
        unique_filename = f"{user_id}_{uuid.uuid4().hex[:8]}{file_ext}"
        file_path = base_dir / unique_filename
        
        # 保存文件到磁盘
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"文件已保存: {file_path}")
        
        # 使用 PIL 打开图片
        try:
            # ✅ 从内存中打开图片（而不是从文件路径）
            pil_image = Image.open(io.BytesIO(content))
            
            # 如果是 RGBA 模式，转换为 RGB
            if pil_image.mode == 'RGBA':
                pil_image = pil_image.convert('RGB')
            
            logger.info(f"图片尺寸: {pil_image.size}, 模式: {pil_image.mode}")
            
        except Exception as img_error:
            # 删除已保存的文件
            if file_path and file_path.exists():
                os.remove(file_path)
            logger.error(f"图片格式错误: {img_error}")
            raise HTTPException(status_code=400, detail="图片格式错误，无法解析")
        
        # 检测人脸并提取特征向量
        try:
            # ✅ 使用 detect_and_extract 方法（一步完成）
            features_list, boxes = face_service.detect_and_extract(pil_image)
            
            if len(features_list) == 0 or len(boxes) == 0:
                # 未检测到人脸，删除文件
                if file_path and file_path.exists():
                    os.remove(file_path)
                logger.warning(f"未检测到人脸: user_id={user_id}")
                raise HTTPException(status_code=400, detail="未检测到人脸，请上传清晰的正面照片")
            
            # 如果检测到多个人脸，选择第一个（也可以选择面积最大的）
            if len(features_list) > 1:
                logger.warning(f"检测到 {len(features_list)} 个人脸，使用第一个")
            
            # 获取第一个人脸的特征向量（numpy array, shape=(512,)）
            face_features = features_list[0]
            face_box = boxes[0]
            
            logger.info(f"提取到人脸特征: shape={face_features.shape}, dtype={face_features.dtype}")
            logger.info(f"人脸位置: x1={face_box[0]:.0f}, y1={face_box[1]:.0f}, x2={face_box[2]:.0f}, y2={face_box[3]:.0f}")
            
            # 将特征向量转换为二进制
            feature_bytes = feature_to_bytes(face_features)
            logger.info(f"特征向量转换为二进制: size={len(feature_bytes)} bytes")
            
        except HTTPException:
            raise
        except Exception as face_error:
            # 人脸识别失败，删除文件
            if file_path and file_path.exists():
                os.remove(file_path)
            logger.error(f"人脸特征提取失败: {face_error}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"人脸特征提取失败: {str(face_error)}")
        finally:
            # 关闭 PIL Image 对象
            if 'pil_image' in locals():
                pil_image.close()
        
        # 相对路径
        relative_path = f"faces/{unique_filename}"
        
        # 更新数据库（同时保存路径和特征向量）
        cursor.execute(
            "UPDATE user_info SET face_path = %s, face_feature = %s WHERE id = %s",
            (relative_path, feature_bytes, user_id)
        )
        
        if cursor.rowcount == 0:
            # 删除已保存的文件
            if file_path and file_path.exists():
                os.remove(file_path)
            raise HTTPException(status_code=500, detail="更新数据库失败")
        
        conn.commit()
        
        logger.info(f"上传成功: user_id={user_id}, path={relative_path}, feature_size={len(feature_bytes)}")
        return {
            "code": 200,
            "message": "上传成功，人脸特征已提取",
            "face_path": relative_path,
            "feature_dimension": len(face_features),
            "face_count": len(features_list)  # 告诉前端检测到几个人脸
        }

    except HTTPException:
        raise
    except Exception as e:
        # 出错时删除已保存的文件
        if file_path and file_path.exists():
            try:
                os.remove(file_path)
            except Exception:
                pass
        
        logger.error(f"上传人脸照片失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass

