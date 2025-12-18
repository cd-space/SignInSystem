import logging
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger()


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    """处理请求参数验证异常"""
    return JSONResponse(
        status_code=422,  # 改为实际的 HTTP 状态码
        content={
            "code": 422,
            "message": "参数验证失败",
            "data": exc.errors()
        }
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException
):
    """处理 HTTP 异常"""
    return JSONResponse(
        status_code=exc.status_code,  # 使用异常的状态码
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "data": None
        }
    )


async def global_exception_handler(
    request: Request,
    exc: Exception
):
    """处理所有未捕获的异常"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,  # 改为 500
        content={
            "code": 500,
            "message": "服务器内部错误",
            "data": None
        }
    )
