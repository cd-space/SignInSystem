import logging
from .connection import get_connection

logger = logging.getLogger()

def create_student_table():
    """创建学生表"""
    conn = get_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    sql = """
    CREATE TABLE IF NOT EXISTS students (
        id INT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(100) NOT NULL,
        face_data LONGBLOB,
        photo_url VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )     
    """
    
    try:
        cursor.execute(sql)
        conn.commit()
        logger.info("学生表创建成功")
        return True
    except Exception as e:
        logger.error(f"创建表失败: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    create_student_table()