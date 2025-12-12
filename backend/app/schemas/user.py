"""
用户相关 Schema
"""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class UserBase(BaseModel):
    """用户基础信息"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")
    
    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("用户名只能包含字母、数字和下划线")
        return v


class UserCreate(UserBase):
    """用户创建"""
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    
    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("密码至少6个字符")
        return v


class UserUpdate(BaseModel):
    """用户更新"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = None
    
    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("用户名只能包含字母、数字和下划线")
        return v


class UserResponse(UserBase):
    """用户响应"""
    id: uuid.UUID
    avatar_url: Optional[str] = None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserInDB(UserResponse):
    """数据库中的用户（包含哈希密码）"""
    hashed_password: str
