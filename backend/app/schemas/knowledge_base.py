"""
知识库相关 Schema
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from app.models.knowledge_base import KBTag, KBVisibility, KnowledgeBase
from pydantic import BaseModel, Field


class KnowledgeBaseBase(BaseModel):
    """知识库基础 Schema"""

    name: str = Field(..., min_length=1, max_length=200, description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")
    visibility: KBVisibility = Field(KBVisibility.PRIVATE, description="是否公开")
    embedding_model: str = Field("text-embedding-ada-002", description="向量化模型")
    embedding_dimension: int = Field(1536, description="向量维度")


class KnowledgeBaseCreate(KnowledgeBaseBase):
    """创建知识库请求"""

    tags: Optional[List[str]] = Field(None, description="标签列表")


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求"""

    name: Optional[str] = Field(
        None, min_length=1, max_length=200, description="知识库名称"
    )
    description: Optional[str] = Field(None, description="知识库描述")
    visibility: Optional[KBVisibility] = Field(
        None, description="可见性：private(私有), team(团队), public(公开)"
    )
    tags: Optional[List[str]] = Field(None, description="标签列表")


class KBTagResponse(BaseModel):
    """知识库标签响应"""

    id: UUID
    tag_name: str

    class Config:
        from_attributes = True


class KnowledgeBaseResponse(BaseModel):
    """知识库响应"""

    id: UUID
    name: str
    description: Optional[str]
    visibility: str
    embedding_model: str = ""
    embedding_dimension: int = 1536
    document_count: int
    chunk_count: int
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
    tags: List[KBTagResponse] = []
    embedding_model_info: Optional[dict] = None

    class Config:
        from_attributes = True

    def __init__(self, **data):
        # 从 embedding_model_info 解包
        if "embedding_model_info" in data and data["embedding_model_info"]:
            info = data["embedding_model_info"]
            data["embedding_model"] = info.get("model", "text-embedding-ada-002")
            data["embedding_dimension"] = info.get("dimension", 1536)
        super().__init__(**data)


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
    last_updated: Optional[datetime]
    last_updated: Optional[datetime]
