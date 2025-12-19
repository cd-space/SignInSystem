import numpy as np


def feature_to_bytes(feature: np.ndarray) -> bytes:
    """
    将特征向量转换为二进制数据用于存储到数据库
    
    参数:
        feature: numpy 数组，形状通常为 (512,)
        
    返回:
        bytes: 二进制数据
    """
    return feature.tobytes()


def bytes_to_feature(feature_bytes: bytes, shape: tuple = (512,), dtype=np.float32) -> np.ndarray:
    """
    将二进制数据转换回特征向量
    
    参数:
        feature_bytes: 二进制数据
        shape: 特征向量的形状，默认 (512,)
        dtype: 数据类型，默认 np.float32
        
    返回:
        numpy 数组
    """
    return np.frombuffer(feature_bytes, dtype=dtype).reshape(shape)
