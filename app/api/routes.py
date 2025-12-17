import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.db.connection import get_connection


logger = logging.getLogger()
app = FastAPI(title="SignInSystem API", version="1.0.0")

class StudentCreate(BaseModel):
    name: str
    photo_url: str = ""

class StudentResponse(BaseModel):
    id: int
    name: str
    photo_url: str


@app.post("/api/students", response_model=dict, status_code=201)
def add_student(student: StudentCreate):
    """
    新增学生接口
    
    请求体:
    {
        "name": "张三",
        "photo_url": "http://example.com/photo.jpg"
    }
    
    响应:
    {
        "code": 0,
        "message": "成功",
        "student_id": 1
    }
    """
    try:
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败")
        
        cursor = conn.cursor()
        
        # 插入学生记录
        sql = "INSERT INTO user_info (name, face_feature) VALUES (%s, %s)"
        cursor.execute(sql, (student.name, student.photo_url))
        conn.commit()
        
        student_id = cursor.lastrowid
        
        logger.info(f"新增学生成功: ID={student_id}, 名字={student.name}")
        
        cursor.close()
        conn.close()
        
        return {
            "code": 0,
            "message": "成功",
            "student_id": student_id
        }
        
    except Exception as e:
        logger.error(f"新增学生失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {e}")