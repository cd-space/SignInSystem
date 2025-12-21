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

logger = logging.getLogger()
router = APIRouter()


@router.post("/api/upload_face", response_model=dict, status_code=200)
async def upload_face(
    user_id: str = Form(..., description="用户ID"),
    face_image: UploadFile = File(..., description="人脸照片文件")
):
    """
    上传用户人脸照片
    请求参数:
    - user_id: 用户ID (必填)
    - face_image: 人脸照片文件 (必填)
    
    返回:
    {
      "code": 200,
      "message": "上传成功",
      "face_path": "faces/user_id_xxx.jpg"
    }
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

        # 创建保存目录
        base_dir = Path("app/static/faces")
        base_dir.mkdir(parents=True, exist_ok=True)

        # 生成唯一文件名（用户ID + UUID + 原扩展名）
        unique_filename = f"{user_id}_{uuid.uuid4().hex[:8]}{file_ext}"
        file_path = base_dir / unique_filename
        
        # 保存文件
        with open(file_path, "wb") as f:
            content = await face_image.read()
            if len(content) == 0:
                raise HTTPException(status_code=400, detail="上传的文件为空")
            f.write(content)
        
        # 相对路径（用于存储到数据库）
        relative_path = f"faces/{unique_filename}"
        
        # 更新数据库
        cursor.execute(
            "UPDATE user_info SET face_path = %s WHERE id = %s",
            (relative_path, user_id)
        )
        
        if cursor.rowcount == 0:
            # 删除已保存的文件
            if file_path and file_path.exists():
                os.remove(file_path)
            raise HTTPException(status_code=500, detail="更新数据库失败")
        
        conn.commit()
        
        logger.info(f"上传人脸照片成功: user_id={user_id}, path={relative_path}")
        return {
            "code": 200,
            "message": "上传成功",
            "face_path": relative_path
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
        
        logger.error(f"上传人脸照片失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {e}")
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass

