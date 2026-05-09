"""
模型配置相关 Schema
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ModelConfigBase(BaseModel):
    """模型配置基础 Schema"""
    name: str = Field(..., min_length=1, max_length=100, description="配置名称")
    model_type: str = Field(..., description="模型类型：embedding, chat, rerank")
    provider: str = Field(..., description="提供商：openai, azure, ollama, custom")
    model_name: str = Field(..., description="模型名称")
    api_base: Optional[str] = Field(None, description="API 基础地址")
    api_key: Optional[str] = Field(None, description="API Key（会加密存储）")
    extra_params: Optional[Dict[str, Any]] = Field(None, description="额外参数")
    is_default: bool = Field(False, description="是否为默认配置")


class ModelConfigCreate(ModelConfigBase):
    """创建模型配置请求"""
    pass


class ModelConfigUpdate(BaseModel):
    """更新模型配置请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="配置名称")
    api_base: Optional[str] = Field(None, description="API 基础地址")
    api_key: Optional[str] = Field(None, description="API Key（会加密存储）")
    extra_params: Optional[Dict[str, Any]] = Field(None, description="额外参数")
    is_default: Optional[bool] = Field(None, description="是否为默认配置")
    is_active: Optional[bool] = Field(None, description="是否激活")


class ModelConfigResponse(BaseModel):
    """模型配置响应（不包含 API Key）"""
    id: UUID
    name: str
    model_type: str
    provider: str
    model_name: str
    api_base: Optional[str]
    extra_params: Optional[Dict[str, Any]]
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ModelConfigListResponse(BaseModel):
    """模型配置列表响应"""
    items: List[ModelConfigResponse]
    total: int


class ModelConfigTestRequest(BaseModel):
    """测试模型配置请求"""
    test_input: str = Field("Hello", description="测试输入")


class ModelConfigTestResponse(BaseModel):
    """测试模型配置响应"""
    success: bool
    message: str
    latency_ms: Optional[float] = None
    output: Optional[Any] = None
