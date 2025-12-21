import logging
import mysql.connector
from mysql.connector import Error

logger = logging.getLogger()

def get_connection():

    # host="223.26.59.193"
    # user="admin"
    # password="Dhy20040501-"  # 密码
    # database="signinsystem"   # 数据库名
    # host="localhost"
    # user="root"
    # password="Dhy20040501-"  # 密码
    # database="signinsystem"   # 数据库名
    host="host.docker.internal"
    user="signin"
    password="Dhy20040501-"  # 密码
    database="signin"   # 数据库名
    try:
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        logger.info("数据库连接成功")
        return connection
    except Error as e:
        logger.info(f"数据库连接信息: {host, user, password, database}")
        logger.error(f"数据库连接失败: {e}")
        return None
    

