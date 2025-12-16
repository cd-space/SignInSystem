from facenet_pytorch import MTCNN, InceptionResnetV1
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import matplotlib.pylab as plt
import cv2
import torch

import logging

logger = logging.getLogger()

class FaceRecognitionService:
    def __init__(self):
    # """初始化人脸检测器"""
        self.mtcnn = MTCNN(keep_all=True, device='cpu')  # keep_all=True 检测所有人脸
        logger.info("MTCNN 人脸检测器初始化成功")
        self.resnet = InceptionResnetV1(pretrained='vggface2').eval()
        logger.info("InceptionResnetV1 特征提取模型初始化成功")


    def detect_faces(self, image):
        """
        检测图片中的所有人脸并分割
        
        参数:
            image: PIL Image 对象或 numpy array
            
        返回:
            faces: 人脸图像列表（tensor 格式）
            boxes: 人脸位置框列表 [[x1,y1,x2,y2], ...]
        """
        try:
            # 如果是 numpy array，转换为 PIL Image
            if isinstance(image, np.ndarray):
                image = Image.fromarray(image)
            
            # 确保是 RGB 格式
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 检测人脸，返回裁剪后的人脸、概率和位置框
            boxes, probs = self.mtcnn.detect(image)
            
            if boxes is None:
                logger.warning("未在图片中检测到人脸")
                return [], []
            
            # 提取人脸区域
            faces = self.mtcnn(image, return_prob=False)
            
            logger.info(f"检测到 {len(boxes)} 个人脸")
            logger.info(f"人脸位置框: {boxes}")
            return faces, boxes
            
        except Exception as e:
            logger.error(f"人脸检测失败: {e}")
            return [], []
        
    def extract_features(self, faces):
            """
            从检测到的人脸中提取特征向量
            
            参数:
                faces: torch.Tensor 格式的人脸图像 (N, 3, 160, 160)
                
            返回:
                features: 特征向量列表，每个特征向量形状为 (512,)
            """
            try:
                if faces is None or len(faces) == 0:
                    logger.warning("没有人脸可以提取特征")
                    return []
                
                # 使用 FaceNet 提取特征
                with torch.no_grad():
                    embeddings = self.resnet(faces)
                
                logger.info(f"成功提取 {len(embeddings)} 个人脸特征，每个特征维度: {embeddings.shape[1]}")
                
                # 转换为 numpy 数组列表
                features = [embedding.cpu().numpy() for embedding in embeddings]
                
                return features
                
            except Exception as e:
                logger.error(f"特征提取失败: {e}")
                return []
    
    def detect_and_extract(self, image):
        """
        检测人脸并提取特征
        
        参数:
            image: PIL Image 对象或 numpy array
            
        返回:
            features: 特征向量列表
            boxes: 人脸位置框列表
        """
        faces, boxes = self.detect_faces(image)
        
        if len(faces) == 0:
            return [], []
        
        features = self.extract_features(faces)
        
        return features, boxes
    
    def compare_features(self, feature1, feature2, threshold=0.6):
        """
        比对两个人脸特征向量
        
        参数:
            feature1: numpy array 或 torch.Tensor, 第一个人脸特征向量 (512,)
            feature2: numpy array 或 torch.Tensor, 第二个人脸特征向量 (512,)
            threshold: float, 距离阈值，默认 0.6
            
        返回:
            is_match: bool, 是否匹配
            similarity: float, 距离分数 (越小越相似)
        """
        try:
            # 转为 numpy array
            if isinstance(feature1, torch.Tensor):
                x1 = feature1.detach().cpu().numpy()
            else:
                x1 = np.asarray(feature1)
            
            if isinstance(feature2, torch.Tensor):
                x2 = feature2.detach().cpu().numpy()
            else:
                x2 = np.asarray(feature2)
            
            # 展平成一维
            x1 = x1.ravel()
            x2 = x2.ravel()
            
            # 计算欧氏距离
            distance = float(np.linalg.norm(x1 - x2))
            
            is_match = distance <= threshold
            
            logger.info(f"人脸比对距离: {distance:.4f}, 是否匹配: {is_match}")
            
            return is_match, distance
            
        except Exception as e:
            logger.error(f"特征比对失败: {e}")
            return False, 0.0