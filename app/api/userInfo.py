import logging
from fastapi import HTTPException
from pydantic import BaseModel
from app.db.connection import get_connection
from typing import Optional
from fastapi import APIRouter

logger = logging.getLogger()
router = APIRouter()


class StudentCreate(BaseModel):
    name: str
    photo_url: str = ""

class StudentResponse(BaseModel):
    id: int
    name: str
    photo_url: str

class UserCreate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    student_id: Optional[str] = None
    face_feature: Optional[str] = None
    role: Optional[str] = None


@router.post("/api/addusers", response_model=dict, status_code=200)
def create_user(user: UserCreate):
    """
    新增用户接口
    请求示例:
    {
        "name": "string",
        "phone": "string",
        "student_id": "string",
        "face_feature": "string",
        "role": "string"
    }
    返回:
    {
        "code": 200,
        "user_id": 1
    }
    """
    try:
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败")

        cursor = conn.cursor()
        sql = """
            INSERT INTO user_info (name, phone, student_id, face_feature, role)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (user.name, user.phone, user.student_id, user.face_feature, user.role))
        conn.commit()
        user_id = cursor.lastrowid

        logger.info(f"新增用户成功: ID={user_id}, 数据={user.dict()}")

        cursor.close()
        conn.close()

        return {"code": 200, "user_id": user_id}

    except Exception as e:
        logger.error(f"新增用户失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {e}")
    