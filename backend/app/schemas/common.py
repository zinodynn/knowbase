"""
通用响应 Schema
"""
from typing import TypeVar, Generic, Optional, Any
from pydantic import BaseModel
from datetime import datetime

T = TypeVar("T")


class ResponseBase(BaseModel, Generic[T]):
    """通用响应基类"""
    success: bool = True
    data: Optional[T] = None
    message: str = "操作成功"
    timestamp: datetime = None
    
    def __init__(self, **data):
        if "timestamp" not in data:
            data["timestamp"] = datetime.utcnow()
        super().__init__(**data)


class ErrorDetail(BaseModel):
    """错误详情"""
    code: str
    message: str
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error: ErrorDetail
    timestamp: datetime = None
    
    def __init__(self, **data):
        if "timestamp" not in data:
            data["timestamp"] = datetime.utcnow()
        super().__init__(**data)


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    success: bool = True
    data: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    message: str = "获取成功"
    timestamp: datetime = None
    
    def __init__(self, **data):
        if "timestamp" not in data:
            data["timestamp"] = datetime.utcnow()
        # 计算总页数
        if "total_pages" not in data and "total" in data and "page_size" in data:
            data["total_pages"] = (data["total"] + data["page_size"] - 1) // data["page_size"]
        super().__init__(**data)


class MessageResponse(BaseModel):
    """简单消息响应"""
    success: bool = True
    message: str
    timestamp: datetime = None
    
    def __init__(self, **data):
        if "timestamp" not in data:
            data["timestamp"] = datetime.utcnow()
        super().__init__(**data)
