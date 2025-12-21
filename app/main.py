# import logging
# from .utils.logging import setup_logging
# from .services.FaceRecognitionService import FaceRecognitionService
# from PIL import Image
# import uvicorn
# from fastapi import FastAPI, HTTPException
# from fastapi.exceptions import RequestValidationError
# from .api import userInfo,signIn,classInfo
# from fastapi.middleware.cors import CORSMiddleware
# from .middlewares.exception_handlers import (
#     validation_exception_handler,
#     http_exception_handler,
#     global_exception_handler
# )
# from app.db import connection


# def main():
#     setup_logging()
#     connection.get_connection()
#     logger = logging.getLogger()

#     logger.info("程序启动")

#     app = FastAPI()
    
#     app.add_middleware(
#         CORSMiddleware,
#         allow_origins=["*"],              # 或 ["https://example.com"]
#         allow_credentials=True,
#         allow_methods=["*"],
#         allow_headers=["*"],
#     )
    
#     # 注册异常处理器
#     app.add_exception_handler(RequestValidationError, validation_exception_handler)
#     app.add_exception_handler(HTTPException, http_exception_handler)
#     app.add_exception_handler(Exception, global_exception_handler)
    
#     app.include_router(userInfo.router)
#     app.include_router(signIn.router)
#     app.include_router(classInfo.router)

#     uvicorn.run(app, host="0.0.0.0", port=8000)





# if __name__ == '__main__':
#     main()



import logging
from .utils.logging import setup_logging
from .services.FaceRecognitionService import FaceRecognitionService
from PIL import Image
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from .api import userInfo,signIn,classInfo,signTask,faceRecognitionService
from fastapi.middleware.cors import CORSMiddleware
from .middlewares.exception_handlers import (
    validation_exception_handler,
    http_exception_handler,
    global_exception_handler
)
import uvicorn
from app.db import connection

# -----------------------------
# 全局初始化
# -----------------------------
#读yaml

setup_logging()
logger = logging.getLogger()
e = connection.get_connection()
if e is None:
    logger.error("数据库连接失败，程序退出")
    exit(1)

# -----------------------------
# FastAPI app 实例
# -----------------------------
app = FastAPI()


# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 或者写你的前端域名列表
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 异常处理
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# 注册路由
app.include_router(userInfo.router)
app.include_router(signIn.router)
app.include_router(classInfo.router)
app.include_router(signTask.router)
app.include_router(faceRecognitionService.router)

logger.info("程序启动")

uvicorn.run(app, host="0.0.0.0", port=8000)