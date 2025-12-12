"""
知识库相关 Schema
"""
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class KnowledgeBaseBase(BaseModel):
    """知识库基础 Schema"""
    name: str = Field(..., min_length=1, max_length=200, description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")
    is_public: bool = Field(False, description="是否公开")
    embedding_model: str = Field("text-embedding-ada-002", description="向量化模型")
    embedding_dimension: int = Field(1536, description="向量维度")


class KnowledgeBaseCreate(KnowledgeBaseBase):
    """创建知识库请求"""
    tags: Optional[List[str]] = Field(None, description="标签列表")


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")
    is_public: Optional[bool] = Field(None, description="是否公开")
    tags: Optional[List[str]] = Field(None, description="标签列表")


class KBTagResponse(BaseModel):
    """知识库标签响应"""
    id: UUID
    name: str
    
    class Config:
        from_attributes = True


class KnowledgeBaseResponse(BaseModel):
    """知识库响应"""
    id: UUID
    name: str
    description: Optional[str]
    is_public: bool
    embedding_model: str
    embedding_dimension: int
    document_count: int
    total_chunks: int
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
    tags: List[KBTagResponse] = []
    
    class Config:
        from_attributes = True


class KnowledgeBaseListResponse(BaseModel):
    """知识库列表响应"""
    items: List[KnowledgeBaseResponse]
    total: int
    skip: int
    limit: int


class KnowledgeBaseStats(BaseModel):
    """知识库统计信息"""
    document_count: int
    total_chunks: int
    total_size_bytes: int
    last_updated: Optional[datetime]
