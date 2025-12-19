import logging
from .utils.logging import setup_logging
from .services.FaceRecognitionService import FaceRecognitionService
from PIL import Image
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from .api import userInfo,signIn,classInfo
from fastapi.middleware.cors import CORSMiddleware
from .middlewares.exception_handlers import (
    validation_exception_handler,
    http_exception_handler,
    global_exception_handler
)


def main():
    setup_logging()
    logger = logging.getLogger()

    logger.info("程序启动")

    app = FastAPI()
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],              # 或 ["https://example.com"]
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册异常处理器
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)
    
    app.include_router(userInfo.router)
    app.include_router(signIn.router)
    app.include_router(classInfo.router)

    uvicorn.run(app, host="0.0.0.0", port=8000)

    # service = FaceRecognitionService()
    # image1 = Image.open("./6.jpg")
    # image2 = Image.open("./10.jpg")
    
    # faces1, boxes1 = service.detect_faces(image1)
    # faces2, boxes2 = service.detect_faces(image2)

    # is_match,similarity = service.compare_features(faces1, faces2)
    # logger.info(f"比对结果: 是否匹配: {is_match}, 相似度: {similarity:.4f}")





if __name__ == '__main__':
    main()