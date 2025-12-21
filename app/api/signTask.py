from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.db.connection import get_connection
import logging
import uuid

logger = logging.getLogger()
router = APIRouter()


class PublishSignReq(BaseModel):
    classlist: List[str]
    initiator: str

@router.post("/api/publish_sign_task", response_model=dict, status_code=200)
def publish_sign_task(req: PublishSignReq):
    """
    发布签到任务：
    请求 Body:
    {
      "classlist": ["classid1", "classid2"],
      "initiator": "teacher_name"
    }
    为本次发布生成一个统一的 task_id（12位），每个班级生成独立的 sign_task.id（12位）且写入相同的 task_id。
    然后查询 student_class 表拿到该班级的所有 student_id，并将生成的 task_id 与 student_id 写入 sign_record 表。
    """
    if not req.classlist or not req.initiator:
        raise HTTPException(status_code=400, detail="需要提供 classlist 和 initiator")

    conn = None
    cursor = None
    try:
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败")

        cursor = conn.cursor()
        created = []

        # 统一 task_id（12 位）
        task_id = uuid.uuid4().hex[:12]

        for class_id in req.classlist:
            # 为每个班级生成独立的 sign_task.id（12位），并写入共同的 task_id
            sign_task_id = None
            for _ in range(5):
                candidate = uuid.uuid4().hex[:12]
                try:
                    cursor.execute(
                        "INSERT INTO sign_task (id, task_id, class_id, initiator, status) VALUES (%s, %s, %s, %s, %s)",
                        (candidate, task_id, class_id, req.initiator, 1)
                    )
                    conn.commit()
                    sign_task_id = candidate
                    break
                except Exception as e:
                    conn.rollback()
                    msg = str(e).lower()
                    if "duplicate" in msg or "unique" in msg or "1062" in msg:
                        continue
                    raise HTTPException(status_code=500, detail=f"插入 sign_task 失败: {e}")

            if sign_task_id is None:
                raise HTTPException(status_code=500, detail="生成 sign_task id 失败，请重试")

            # 查询该班级所有学生
            cursor.execute("SELECT student_id FROM student_class WHERE class_id = %s", (class_id,))
            rows = cursor.fetchall()

            # 将 task_id 与 student_id 存入 sign_record（每条记录生成独立 id）
            if rows:
                for r in rows:
                    student_id = r[0]
                    record_id = None
                    for _ in range(5):
                        rid = uuid.uuid4().hex[:12]
                        try:
                            # 存入统一的 task_id（而非单条 sign_task.id）
                            cursor.execute(
                                "INSERT INTO sign_record (id, sign_task_id, student_id) VALUES (%s, %s, %s)",
                                (rid, sign_task_id, student_id)
                            )
                            conn.commit()
                            record_id = rid
                            break
                        except Exception as e:
                            conn.rollback()
                            msg = str(e).lower()
                            if "duplicate" in msg or "unique" in msg or "1062" in msg:
                                break
                            raise HTTPException(status_code=500, detail=f"插入 sign_record 失败: {e}")

            created.append({"class_id": class_id, "sign_task_id": sign_task_id})

        logger.info(f"发布签到任务成功: initiator={req.initiator}, task_id={task_id}, tasks={created}")
        return {"code": 200, "task_id": task_id, "tasks": created}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发布签到失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {e}")
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass


class StudentSignReq(BaseModel):
    student_id: str

@router.post("/api/query_student_sign", response_model=dict, status_code=200)
def query_student_sign(req: StudentSignReq):
    """
    查询学生的进行中签到：
    请求 Body: { "student_id": "stu123" }
    若存在 sign_task.status = 1 的记录，返回列表每项包含:
      sign_task_id, sign_status, initiator, created_at
    否则返回 {"code":200, "message":"没有进行中的签到"}
    """
    if not req.student_id:
        raise HTTPException(status_code=400, detail="需要提供 student_id")

    conn = None
    cursor = None
    try:
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败")

        cursor = conn.cursor()
        # 查询 student 的所有 sign_record 并关联 sign_task，只选取 sign_task.status = 1 的进行中签到
        cursor.execute(
            """
            SELECT sr.sign_task_id, sr.sign_status, st.initiator, st.created_at
            FROM sign_record sr
            JOIN sign_task st ON sr.sign_task_id = st.id
            WHERE sr.student_id = %s AND st.status = 1
            """,
            (req.student_id,)
        )
        rows = cursor.fetchall()

        if not rows:
            return {"code": 200, "message": "没有进行中的签到"}

        results = []
        for r in rows:
            results.append({
                "sign_task_id": r[0],
                "sign_status": r[1],
                "initiator": r[2],
                "created_at": r[3],
            })

        return {"code": 200, "data": results}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询学生签到失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {e}")
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass


class CloseSignReq(BaseModel):
    sign_task_id: List[str]

@router.post("/api/close_sign_task", response_model=dict, status_code=200)
def close_sign_task(req: CloseSignReq):
    """
    关闭签到任务：
    请求 Body: { "sign_task_id": ["task1","task2"] }
    将 sign_task 表中对应记录的 status 更新为 2，支持批量关闭
    """
    if not req.sign_task_id or not isinstance(req.sign_task_id, list):
        raise HTTPException(status_code=400, detail="需要提供 sign_task_id（非空数组）")

    conn = None
    cursor = None
    try:
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败")

        cursor = conn.cursor()
        # 构建 IN 子句并执行批量更新
        ids = req.sign_task_id
        placeholders = ",".join(["%s"] * len(ids))
        sql = f"UPDATE sign_task SET status = %s WHERE id IN ({placeholders})"
        params = [2] + ids
        cursor.execute(sql, tuple(params))
        if getattr(cursor, "rowcount", None) == 0:
            conn.rollback()
            return {"code": 404, "message": "未找到要关闭的 sign_task"}
        conn.commit()
        return {"code": 200, "updated": getattr(cursor, "rowcount", 0), "message": "签到已关闭"}

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.error(f"关闭签到失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {e}")
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass

class UpdateRecordReq(BaseModel):
    sign_task_id: str
    student_id: str
    new_status: int  # 0 未签到, 1 已签到, 2 请假, 3 迟到

@router.post("/api/update_sign_status", response_model=dict, status_code=200)
def update_sign_record(req: UpdateRecordReq):
    """
    更新 sign_record 中的 sign_status
    请求 Body 示例:
    {
      "sign_task_id": "task123",
      "student_id": "stu123",
      "new_status": 1
    }
    返回: {"code": 200} 或 {"code":404, "message":"记录未找到"}
    """
    if not req.sign_task_id or not req.student_id:
        raise HTTPException(status_code=400, detail="需要提供 sign_task_id 和 student_id")
    if req.new_status not in (0, 1, 2, 3):
        raise HTTPException(status_code=400, detail="new_status 必须为 0,1,2 或 3")

    conn = None
    cursor = None
    try:
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败")

        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sign_record SET sign_status = %s WHERE sign_task_id = %s AND student_id = %s",
            (req.new_status, req.sign_task_id, req.student_id)
        )
        if getattr(cursor, "rowcount", None) == 0:
            conn.rollback()
            return {"code": 404, "message": "记录未找到"}
        conn.commit()
        return {"code": 200}

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.error(f"更新签到记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {e}")
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass