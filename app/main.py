import logging
from .utils.logging import setup_logging
from .services.FaceRecognitionService import FaceRecognitionService
from PIL import Image
import uvicorn
from fastapi import FastAPI
from .api import userInfo


def main():
    setup_logging()
    logger = logging.getLogger()

    logger.info("程序启动")

    app=FastAPI()
    app.include_router(userInfo.router)

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