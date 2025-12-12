"""
API Key 相关 Schema
"""
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ApiKeyBase(BaseModel):
    """API Key 基础 Schema"""
    name: str = Field(..., min_length=1, max_length=100, description="API Key 名称")
    description: Optional[str] = Field(None, description="描述")


class ApiKeyCreate(ApiKeyBase):
    """创建 API Key 请求"""
    expires_days: Optional[int] = Field(None, ge=1, le=365, description="过期天数")


class ApiKeyUpdate(BaseModel):
    """更新 API Key 请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="API Key 名称")
    description: Optional[str] = Field(None, description="描述")
    is_active: Optional[bool] = Field(None, description="是否激活")


class ApiKeyResponse(BaseModel):
    """API Key 响应（不包含密钥）"""
    id: UUID
    name: str
    description: Optional[str]
    key_prefix: str
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ApiKeyCreateResponse(ApiKeyResponse):
    """创建 API Key 响应（包含完整密钥，仅在创建时返回一次）"""
    api_key: str = Field(..., description="完整的 API Key（仅显示一次）")


class ApiKeyListResponse(BaseModel):
    """API Key 列表响应"""
    items: List[ApiKeyResponse]
    total: int
