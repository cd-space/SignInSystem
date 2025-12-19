import logging
from fastapi import HTTPException
from pydantic import BaseModel
from app.db.connection import get_connection
from typing import Optional
from fastapi import APIRouter

logger = logging.getLogger()
router = APIRouter()
    
@router.delete("/api/deleteusers", response_model=dict, status_code=200)
def delete_user(user_id: str):
    """
    删除用户接口
    请求参数:
    - user_id: 用户ID
    返回:
    {
        "code": 200,
        "message": "用户删除成功"
    }
    """
    try:
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败")

        cursor = conn.cursor()
        sql = "DELETE FROM user_info WHERE id = %s"
        cursor.execute(sql, (user_id,))
        conn.commit()

        logger.info(f"删除用户成功: ID={user_id}")

        cursor.close()
        conn.close()

        return {"code": 200, "message": "用户删除成功"}

    except Exception as e:
        logger.error(f"删除用户失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {e}")
    
class UserSearchReq(BaseModel):
    id: Optional[str] = None
    phone: Optional[str] = None
    student_id: Optional[str] = None

@router.post("/api/searchusers", response_model=dict, status_code=200)
def search_users(req: UserSearchReq):
    id = req.id
    phone = req.phone
    student_id = req.student_id
    """
    通过 id / phone / student_id 中的任意一个查询用户信息，优先级：id -> phone -> student_id
    返回示例:
    {
        "code": 0,
        "id": 0,
        "phone": "string",
        "role": "string",
        "name": "string"
        student_id": "string"
    }
    """
    if id is None and not phone and not student_id:
        raise HTTPException(status_code=400, detail="需要提供 id 或 phone 或 student_id 任一参数")

    try:
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败")

        cursor = conn.cursor()
        if id is not None:
            sql = "SELECT id, phone, role, name, student_id FROM user_info WHERE id = %s LIMIT 1"
            params = (id,)
        elif phone:
            sql = "SELECT id, phone, role, name, student_id FROM user_info WHERE phone = %s LIMIT 1"
            params = (phone,)
        else:
            sql = "SELECT id, phone, role, name, student_id FROM user_info WHERE student_id = %s LIMIT 1"
            params = (student_id,)

        cursor.execute(sql, params)
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            return {"code": 404, "message": "用户未找到"}

        uid, phone_v, role_v, name_v, student_id_v = row
        return {
            "code": 200,
            "data": {
                "id": uid,
                "phone": phone_v,
                "role": role_v,
                "name": name_v,
                "student_id": student_id_v
            }
        }

    except Exception as e:
        logger.error(f"查询用户失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {e}")

class UpdateUserReq(BaseModel):
    id: str
    name: Optional[str] = None
    phone: Optional[str] = None
    student_id: Optional[str] = None
    face_feature: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None

@router.post("/api/updateusers", response_model=dict, status_code=200)
def update_user(req: UpdateUserReq):
    """
    通过 id 锁定用户，上传哪些值就更新哪些值
    请求示例:
    {
        "id": 1,
        "name": "new name",
        "phone": "123",
        "password": "newpass"
    }
    返回:
    {
        "code": 200,
        "message": "用户更新成功"
    }
    """
    if not req.id:
        raise HTTPException(status_code=400, detail="需要提供 id")

    try:
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败")

        cursor = conn.cursor()

        # ① 先检查用户是否存在（关键）
        cursor.execute("SELECT 1 FROM user_info WHERE id = %s", (req.id,))
        if cursor.fetchone() is None:
            cursor.close()
            conn.close()
            return {"code": 404, "message": "用户不存在"}

        # ② 再拼接更新字段
        updates = []
        params = []

        if req.name is not None:
            updates.append("name = %s")
            params.append(req.name)
        if req.phone is not None:
            updates.append("phone = %s")
            params.append(req.phone)
        if req.student_id is not None:
            updates.append("student_id = %s")
            params.append(req.student_id)
        if req.face_feature is not None:
            updates.append("face_feature = %s")
            params.append(req.face_feature)
        if req.role is not None:
            updates.append("role = %s")
            params.append(req.role)
        if req.password is not None:
            updates.append("password = %s")
            params.append(req.password)

        # ③ 用户存在，但没有任何更新字段
        if not updates:
            cursor.close()
            conn.close()
            return {"code": 400, "message": "没有要更新的字段"}

        # ④ 执行更新
        sql = "UPDATE user_info SET " + ", ".join(updates) + " WHERE id = %s"
        params.append(req.id)
        cursor.execute(sql, tuple(params))
        conn.commit()

        logger.info(f"更新用户成功: ID={req.id}, 更新字段={updates}")

        cursor.close()
        conn.close()

        return {"code": 200, "message": "用户更新成功"}

    except Exception as e:
        logger.error(f"更新用户失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {e}")