import uuid
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.db.connection import get_connection

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
    
    逻辑说明：
    1. 为本次发布生成一个统一的 sign_task_id（12位）
    2. 为每个班级生成独立的 sign_task.id（12位）
    3. 所有 sign_task 记录共享同一个 sign_task_id
    4. sign_record.sign_task_id 关联到 sign_task.sign_task_id
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
        created_tasks = []

        # 生成统一的 sign_task_id（12位UUID），所有班级共享
        unified_sign_task_id = uuid.uuid4().hex[:12]

        for class_id in req.classlist:
            # 验证班级是否存在
            cursor.execute("SELECT id FROM class WHERE id = %s LIMIT 1", (class_id,))
            if not cursor.fetchone():
                logger.warning(f"班级不存在，跳过: {class_id}")
                continue

            # 为每个班级生成独立的 sign_task.id（数据库主键）
            task_primary_id = None
            for attempt in range(5):
                candidate_id = uuid.uuid4().hex[:12]
                try:
                    cursor.execute(
                        """
                        INSERT INTO sign_task (id, sign_task_id, class_id, initiator, status) 
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (candidate_id, unified_sign_task_id, class_id, req.initiator, 1)
                    )
                    conn.commit()
                    task_primary_id = candidate_id
                    logger.info(f"创建签到任务成功: id={candidate_id}, sign_task_id={unified_sign_task_id}, class_id={class_id}")
                    break
                except Exception as e:
                    conn.rollback()
                    error_msg = str(e).lower()
                    # 检查是否为唯一键冲突（id主键冲突）
                    if "duplicate" in error_msg or "unique" in error_msg or "1062" in error_msg:
                        logger.warning(f"ID冲突，重试: attempt={attempt + 1}")
                        continue
                    # 其他错误直接抛出
                    logger.error(f"插入 sign_task 失败: {e}")
                    raise HTTPException(status_code=500, detail=f"插入 sign_task 失败: {e}")

            if task_primary_id is None:
                logger.error(f"生成 sign_task id 失败，班级: {class_id}")
                raise HTTPException(status_code=500, detail=f"生成签到任务ID失败，班级: {class_id}")

            # 查询该班级的所有学生
            cursor.execute(
                "SELECT student_id FROM student_class WHERE class_id = %s", 
                (class_id,)
            )
            students = cursor.fetchall()

            if not students:
                logger.warning(f"班级无学生，跳过创建记录: class_id={class_id}")
                created_tasks.append({
                    "class_id": class_id, 
                    "task_id": task_primary_id,
                    "student_count": 0
                })
                continue

            # 批量插入 sign_record（使用统一的 sign_task_id）
            success_count = 0
            for student_row in students:
                student_id = student_row[0]
                
                # 为每条记录生成独立的 id
                for attempt in range(5):
                    record_id = uuid.uuid4().hex[:12]
                    try:
                        cursor.execute(
                            """
                            INSERT INTO sign_record (id, sign_task_id, student_id, sign_status) 
                            VALUES (%s, %s, %s, %s)
                            """,
                            (record_id, unified_sign_task_id, student_id, 0)
                        )
                        conn.commit()
                        success_count += 1
                        break
                    except Exception as e:
                        conn.rollback()
                        error_msg = str(e).lower()
                        # 唯一键冲突（同一学生同一任务重复插入）
                        if "duplicate" in error_msg or "unique" in error_msg or "1062" in error_msg:
                            logger.warning(f"签到记录已存在: sign_task_id={unified_sign_task_id}, student_id={student_id}")
                            success_count += 1  # 记录已存在也算成功
                            break
                        # 其他错误重试
                        if attempt < 4:
                            continue
                        logger.error(f"插入 sign_record 失败: {e}")
                        raise HTTPException(status_code=500, detail=f"插入 sign_record 失败: {e}")

            created_tasks.append({
                "class_id": class_id,
                "task_id": task_primary_id,
                "student_count": success_count
            })

        logger.info(f"发布签到任务成功: initiator={req.initiator}, sign_task_id={unified_sign_task_id}, tasks={created_tasks}")
        return {
            "code": 200,
            "message": "签到任务发布成功",
            "sign_task_id": unified_sign_task_id,
            "tasks": created_tasks
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发布签到任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {e}")
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception as close_error:
            logger.error(f"关闭数据库连接失败: {close_error}")


class StudentSignReq(BaseModel):
    student_id: str

@router.post("/api/query_student_sign", response_model=dict, status_code=200)
def query_student_sign(req: StudentSignReq):
    """
    查询学生的进行中签到：
    请求 Body: { "student_id": "stu123" }
    返回该学生所有进行中的签到记录
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
        # 查询学生的签到记录，关联 sign_task 获取进行中的任务（status=1）
        cursor.execute(
            """
            SELECT sr.sign_task_id, sr.sign_status, st.initiator, st.created_at, st.class_id
            FROM sign_record sr
            JOIN sign_task st ON sr.sign_task_id = st.sign_task_id
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
                "created_at": r[3].strftime("%Y-%m-%d %H:%M:%S") if r[3] else None,
                "class_id": r[4]
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
    sign_task_id: str  # 现在是统一的业务ID

@router.post("/api/close_sign_task", response_model=dict, status_code=200)
def close_sign_task(req: CloseSignReq):
    """
    关闭签到任务：
    请求 Body: { "sign_task_id": "task123" }
    将该 sign_task_id 对应的所有班级任务的 status 更新为 2
    """
    if not req.sign_task_id:
        raise HTTPException(status_code=400, detail="需要提供 sign_task_id")

    conn = None
    cursor = None
    try:
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败")

        cursor = conn.cursor()
        # 批量更新所有相同 sign_task_id 的记录
        cursor.execute(
            "UPDATE sign_task SET status = %s WHERE sign_task_id = %s",
            (2, req.sign_task_id)
        )
        affected_rows = cursor.rowcount
        if affected_rows == 0:
            conn.rollback()
            return {"code": 404, "message": "未找到要关闭的签到任务"}
        
        conn.commit()
        logger.info(f"关闭签到任务成功: sign_task_id={req.sign_task_id}, affected_rows={affected_rows}")
        return {
            "code": 200, 
            "updated": affected_rows, 
            "message": f"成功关闭 {affected_rows} 个班级的签到任务"
        }

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
    face_score: float = None  # 可选：人脸相似度得分

@router.post("/api/update_sign_status", response_model=dict, status_code=200)
def update_sign_record(req: UpdateRecordReq):
    """
    更新 sign_record 中的 sign_status
    请求 Body 示例:
    {
      "sign_task_id": "task123",
      "student_id": "stu123",
      "new_status": 1,
      "face_score": 0.95  // 可选
    }
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
        
        # 根据是否提供 face_score 决定更新字段
        if req.face_score is not None:
            cursor.execute(
                """
                UPDATE sign_record 
                SET sign_status = %s, face_score = %s 
                WHERE sign_task_id = %s AND student_id = %s
                """,
                (req.new_status, req.face_score, req.sign_task_id, req.student_id)
            )
        else:
            cursor.execute(
                """
                UPDATE sign_record 
                SET sign_status = %s 
                WHERE sign_task_id = %s AND student_id = %s
                """,
                (req.new_status, req.sign_task_id, req.student_id)
            )
        
        if cursor.rowcount == 0:
            conn.rollback()
            return {"code": 404, "message": "记录未找到"}
        
        conn.commit()
        logger.info(f"更新签到状态成功: sign_task_id={req.sign_task_id}, student_id={req.student_id}, status={req.new_status}")
        return {"code": 200, "message": "更新成功"}

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

class TeacherQueryReq(BaseModel):
    initiator: str

@router.post("/api/query_teacher_sign", response_model=dict, status_code=200)
def query_teacher_sign(req: TeacherQueryReq):
    """
    老师查询进行中的签到：
    请求 Body: { "initiator": "teacher_name" }
    若存在 status=1 的 sign_task，返回第一个 sign_task_id；否则返回 message 表示没有进行中的签到
    """
    if not req.initiator:
        raise HTTPException(status_code=400, detail="需要提供 initiator")

    conn = None
    cursor = None
    try:
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败")

        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT sign_task_id FROM sign_task WHERE initiator = %s AND status = %s LIMIT 1",
            (req.initiator, 1)
        )
        row = cursor.fetchone()
        if not row:
            return {"code": 200, "message": "没有进行中的签到"}

        return {"code": 200, "sign_task_id": row[0]}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询老师签到失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {e}")
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass


class SignTaskStudentsReq(BaseModel):
    sign_task_id: str

@router.post("/api/query_sign_task_students", response_model=dict, status_code=200)
def query_sign_task_students(req: SignTaskStudentsReq):
    """
    查询应签到学生名单：
    请求 Body: { "sign_task_id": "task123" }
    返回: {"code":200, "data":[{"user_id":"...", "name":"...", "sign_status":0}, ...]}
    """
    if not req.sign_task_id:
        raise HTTPException(status_code=400, detail="需要提供 sign_task_id")

    conn = None
    cursor = None
    try:
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败")

        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT sr.student_id, ui.name, sr.sign_status
            FROM sign_record sr
            LEFT JOIN user_info ui ON sr.student_id = ui.id
            WHERE sr.sign_task_id = %s
            """,
            (req.sign_task_id,)
        )
        rows = cursor.fetchall()

        data = []
        if rows:
            for r in rows:
                data.append({
                    "user_id": r[0],
                    "name": r[1],
                    "sign_status": r[2]
                })

        return {"code": 200, "data": data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询签到学生名单失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {e}")
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass