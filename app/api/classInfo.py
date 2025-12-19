from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.db.connection import get_connection
import logging
import uuid

logger = logging.getLogger()
router = APIRouter()


class ClassCreate(BaseModel):
    name: Optional[str] = None
    owner: Optional[str] = None


@router.post("/api/addclass", response_model=dict, status_code=200)
def create_class(req: ClassCreate):
    """
    新建班级
    Body 示例:
    {
        "name": "string",
        "owner": "string"
    }
    返回:
    {
        "code": 200,
        "id": 0
    }
    """
    try:
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败")

        cursor = conn.cursor()
        # 使用 uuid4 生成 8 位 hex 字符串作为 id，若冲突重试最多 5 次
        class_id = None
        for _ in range(5):
            candidate = uuid.uuid4().hex[:12]
            try:
                sql = "INSERT INTO class (id, `name`, `owner`) VALUES (%s, %s, %s)"
                cursor.execute(sql, (candidate, req.name, req.owner))
                conn.commit()
                class_id = candidate
                break
            except Exception as e:
                conn.rollback()
                msg = str(e).lower()
                # 检查是否为唯一键冲突，若是则重试，否则抛出
                if "duplicate" in msg or "unique" in msg or "1062" in msg:
                    continue
                cursor.close()
                conn.close()
                raise

        cursor.close()
        conn.close()

        logger.info(f"新增班级成功: ID={class_id}, 数据={req.dict()}")
        return {"code": 200, "id": class_id}

    except Exception as e:
        logger.error(f"新增班级失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {e}")
