from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.db.connection import get_connection
import logging

logger = logging.getLogger()
router = APIRouter()

class UserCreate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    student_id: Optional[str] = None
    face_feature: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None


class LoginReq(BaseModel):
    phone: Optional[str] = None
    student_id: Optional[str] = None
    password: str


@router.post("/api/addusers", response_model=dict, status_code=200)
def create_user(user: UserCreate):
    try:
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败")

        cursor = conn.cursor()
        sql = """
            INSERT INTO user_info (name, phone, student_id, face_feature, role, password)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (user.name, user.phone, user.student_id, user.face_feature, user.role, user.password))
        conn.commit()
        user_id = cursor.lastrowid

        logger.info(f"新增用户成功: ID={user_id}, 数据={user.dict()}")

        cursor.close()
        conn.close()

        return {"code": 200, "user_id": user_id}

    except Exception as e:
        logger.error(f"新增用户失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {e}")


@router.post("/api/login", response_model=dict, status_code=200)
def login(req: LoginReq):
    """
    登录接口（支持 phone+password 或 student_id+password）
    优先使用 phone，如未提供则使用 student_id
    """
    if not req.phone and not req.student_id:
        raise HTTPException(status_code=400, detail="需要提供 phone 或 student_id")

    try:
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败")

        cursor = conn.cursor()
        if req.phone:
            sql = "SELECT id, name, phone, role FROM user_info WHERE phone = %s AND password = %s LIMIT 1"
            params = (req.phone, req.password)
        else:
            sql = "SELECT id, name, phone, role FROM user_info WHERE student_id = %s AND password = %s LIMIT 1"
            params = (req.student_id, req.password)

        cursor.execute(sql, params)
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            return {"code": 401, "message": "账号或密码错误"}

        return {"code": 200}

    except Exception as e:
        logger.error(f"登录失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {e}")