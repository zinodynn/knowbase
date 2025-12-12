"""
权限相关 Schema
"""
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class PermissionBase(BaseModel):
    """权限基础 Schema"""
    permission: str = Field(..., pattern="^(read|write|admin)$", description="权限级别")


class PermissionCreate(PermissionBase):
    """创建权限请求"""
    user_id: UUID = Field(..., description="用户 ID")


class PermissionUpdate(BaseModel):
    """更新权限请求"""
    permission: str = Field(..., pattern="^(read|write|admin)$", description="权限级别")


class PermissionResponse(BaseModel):
    """权限响应"""
    id: UUID
    user_id: UUID
    kb_id: UUID
    permission: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PermissionWithUserResponse(PermissionResponse):
    """权限响应（包含用户信息）"""
    username: Optional[str] = None
    email: Optional[str] = None


class KBPermissionListResponse(BaseModel):
    """知识库权限列表响应"""
    items: List[PermissionWithUserResponse]
    total: int
