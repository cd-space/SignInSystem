from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional,List
from app.db.connection import get_connection
import logging
import uuid

logger = logging.getLogger()
router = APIRouter()


class ClassCreate(BaseModel):
    name: str
    owner: str
    studentlist: List[str]


@router.post("/api/addclass", response_model=dict, status_code=200)
def create_class(req: ClassCreate):
    """
    新建班级并加入学生（使用 uuid4.hex 前 12 位作为 id）
    请求示例:
    {
        "name": "汗建国",
        "owner": "exercitation Excepteur fugiat ea",
        "studentlist": ["5515sdad25s5", "sdcd51525c2v"]
    }
    返回:
    {
        "code": 0,
        "id": "generated_id"
    }
    """
    if not req.name or not req.owner:
        raise HTTPException(status_code=400, detail="需要提供 name 和 owner")

    conn = None
    cursor = None
    try:
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败")
        cursor = conn.cursor()

        # 若已存在相同 name + owner 的班级，复用之（避免重复插入）
        cursor.execute("SELECT id FROM class WHERE `name` = %s AND `owner` = %s LIMIT 1", (req.name, req.owner))
        row = cursor.fetchone()
        if row:
            class_id = row[0]
        else:
            # 生成 12 位 id 并插入 class 表，冲突重试最多 5 次
            class_id = None
            for _ in range(5):
                candidate = uuid.uuid4().hex[:12]
                try:
                    cursor.execute("INSERT INTO class (id, `name`, `owner`) VALUES (%s, %s, %s)", (candidate, req.name, req.owner))
                    conn.commit()
                    class_id = candidate
                    break
                except Exception as e:
                    conn.rollback()
                    msg = str(e).lower()
                    if "duplicate" in msg or "unique" in msg or "1062" in msg:
                        continue
                    raise HTTPException(status_code=500, detail=f"插入班级失败: {e}")

            if class_id is None:
                raise HTTPException(status_code=500, detail="生成班级ID失败，请重试")

        # 插入 student_class 映射表 (student_id, class_id)，先校验 student 存在并避免重复映射
        if req.studentlist:
            for student_id in req.studentlist:
                # 验证 student_id 在 user_info 表中存在（student_id 对应 user_info.id）
                cursor.execute("SELECT id FROM user_info WHERE id = %s LIMIT 1", (student_id,))
                if not cursor.fetchone():
                    logger.warning(f"学生不存在，跳过映射: {student_id}")
                    continue

                # 避免重复映射
                cursor.execute("SELECT 1 FROM student_class WHERE student_id = %s AND class_id = %s LIMIT 1", (student_id, class_id))
                if cursor.fetchone():
                    continue

                cursor.execute("INSERT INTO student_class (student_id, class_id) VALUES (%s, %s)", (student_id, class_id))

            conn.commit()

        logger.info(f"新增/复用班级成功: ID={class_id}, 数据={req.dict()}")
        return {"code": 200, "id": class_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"新增班级失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {e}")
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass



@router.get("/api/searchclass", response_model=dict, status_code=200)
def get_all_classes():
    """
    返回 class 表中所有班级的 id 和 name
    无需请求体，直接调用
    返回: {"code":200, "data": {"classes": [{"id":"...", "name":"..."}]}}
    """
    try:
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败")

        cursor = conn.cursor()
        cursor.execute("SELECT id, `name` FROM class")
        rows = cursor.fetchall()
        classes = [{"id": r[0], "name": r[1]} for r in rows] if rows else []

        cursor.close()
        conn.close()

        return {"code": 200, "data": {"classes": classes}}

    except Exception as e:
        logger.error(f"查询所有班级失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {e}")


class DeleteClassReq(BaseModel):
    class_id: str


@router.post("/api/deleteclass", response_model=dict, status_code=200)
def delete_class(req: DeleteClassReq):
    class_id = req.class_id
    """
    删除班级及其 student_class 映射
    请求示例: /api/deleteclass?class_id=abcdef123456
    返回: {"code":200}
    """
    if not class_id:
        raise HTTPException(status_code=400, detail="需要提供 class_id")

    conn = None
    cursor = None
    try:
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败")
        cursor = conn.cursor()

        # 检查班级是否存在
        cursor.execute("SELECT id FROM class WHERE id = %s LIMIT 1", (class_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="班级不存在")

        # 删除 student_class 中的映射
        cursor.execute("DELETE FROM student_class WHERE class_id = %s", (class_id,))

        # 删除 class 表中的记录
        cursor.execute("DELETE FROM class WHERE id = %s", (class_id,))

        conn.commit()
        logger.info(f"删除班级成功: ID={class_id}")
        return {"code": 200}

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.error(f"删除班级失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {e}")
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass