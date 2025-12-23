import logging
from fastapi import HTTPException
from pydantic import BaseModel
from app.db.connection import get_connection
from typing import Optional
from fastapi import APIRouter

logger = logging.getLogger()
router = APIRouter()

class DeleteUserReq(BaseModel):
    user_id: str

@router.post("/api/deleteusers", response_model=dict, status_code=200)
def delete_user(req: DeleteUserReq):
    user_id = req.user_id
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

@router.post("/api/updateusers", response_model=dict, status_code=200)
def update_user(req: UpdateUserReq):
    """
    通过 id 锁定用户，上传哪些值就更新哪些值
    请求示例:
    {
        "id": 1,
        "name": "new name",
        "phone": "123",
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
    

class PasswordChangeReq(BaseModel):
        id: str
        old_password: str
        new_password: str

@router.post("/api/update_password", response_model=dict, status_code=200)
def change_password(req: PasswordChangeReq):
    """
    通过 id 锁定用户，使用旧密码比对后更新为新密码
    请求 Body:
    {
        "id": "string",
        "old_password": "string",
        "new_password": "string"
    }
    返回:
    {
        "code": 200,
        "message": "密码修改成功"
    }
    不成功时返回 code 为 404(用户不存在) 或 401(原密码错误)
    """

    # 解析并验证请求体
    try:
        if isinstance(req, PasswordChangeReq):
            data = req
        else:
            data = PasswordChangeReq(**(req.dict() if hasattr(req, "dict") else {}))
    except Exception:
        raise HTTPException(status_code=400, detail="请求参数错误，需包含 id、old_password、new_password")

    if not data.id or not data.old_password or not data.new_password:
        raise HTTPException(status_code=400, detail="需要提供 id、old_password 和 new_password")

    try:
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败")

        cursor = conn.cursor()
        cursor.execute("SELECT password FROM user_info WHERE id = %s LIMIT 1", (data.id,))
        row = cursor.fetchone()
        if not row:
            cursor.close()
            conn.close()
            return {"code": 404, "message": "用户不存在"}

        current_password = row[0]
        if current_password != data.old_password:
            cursor.close()
            conn.close()
            return {"code": 401, "message": "原密码错误"}

        cursor.execute("UPDATE user_info SET password = %s WHERE id = %s", (data.new_password, data.id))
        conn.commit()

        cursor.close()
        conn.close()

        logger.info(f"用户 {data.id} 修改密码成功")
        return {"code": 200, "message": "密码修改成功"}

    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {e}")
    

class RoleSearchReq(BaseModel):
    role: str  # "all" / "teacher" / "student"

@router.post("/api/search_by_role", response_model=dict, status_code=200)
def search_by_role(req: RoleSearchReq):
    """
    根据 role 返回用户信息
    role = "all" 返回所有用户
    role = "teacher" 返回 role 字段为 teacher 的用户
    role = "student" 返回 role 字段为 student 的用户
    返回 data 包含 users 列表，每项含 id,name,phone,student_id,role,created_time,update_time
    """
    role = (req.role or "").lower()
    if role not in ("all", "teacher", "student"):
        raise HTTPException(status_code=400, detail="role 必须为 all/teacher/student")

    try:
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败")

        cursor = conn.cursor()
        # 增加 face_feature, face_path 两列用于判断是否采集过人脸数据
        if role == "all":
            sql = "SELECT id, name, phone, student_id, role, created_at, updated_at, face_feature, face_path FROM user_info"
            params = ()
        else:
            sql = "SELECT id, name, phone, student_id, role, created_at, updated_at, face_feature, face_path FROM user_info WHERE role = %s"
            params = (role,)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        users = []
        if rows:
            for r in rows:
                # r indices: 0:id,1:name,2:phone,3:student_id,4:role,5:created_at,6:updated_at,7:face_feature,8:face_path
                face_collected = bool(r[7]) and bool(r[8])
                users.append({
                    "id": r[0],
                    "name": r[1],
                    "phone": r[2],
                    "student_id": r[3],
                    "role": r[4],
                    "created_time": r[5],
                    "update_time": r[6],
                    "face_collected": face_collected
                })



        cursor.close()
        conn.close()

        return {"code": 200, "data": {"users": users}}

    except Exception as e:
        logger.error(f"按 role 查询用户失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {e}")