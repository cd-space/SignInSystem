import logging
import mysql.connector
from mysql.connector import Error

logger = logging.getLogger()

def get_connection():
    """获取数据库连接"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='860066',  # 密码
            database='signinsystem'   # 数据库名
        )
        logger.info("数据库连接成功")
        return connection
    except Error as e:
        print(f"数据库连接失败: {e}")
        return None