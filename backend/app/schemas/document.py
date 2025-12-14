"""
文档相关 Pydantic 模型

用于请求验证和响应序列化
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    """文档状态"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ChunkResponse(BaseModel):
    """分块响应"""

    id: UUID
    content: str
    chunk_index: int
    token_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentCreate(BaseModel):
    """文档创建请求（API 推送）"""

    filename: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentResponse(BaseModel):
    """文档响应"""

    id: UUID
    kb_id: UUID
    file_name: str
    description: Optional[str] = None
    file_type: Optional[str] = None
    file_size: int
    storage_path: Optional[str] = None
    status: DocumentStatus
    error_message: Optional[str] = None
    chunk_count: int = 0
    doc_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """文档列表响应"""

    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    pages: int


class DocumentDetailResponse(DocumentResponse):
    """文档详情响应（包含分块信息）"""

    chunks: List[ChunkResponse] = Field(default_factory=list)


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""

    id: UUID
    filename: str
    status: DocumentStatus
    message: str


class BatchUploadResponse(BaseModel):
    """批量上传响应"""

    uploaded: List[DocumentUploadResponse]
    failed: List[Dict[str, str]] = Field(default_factory=list)
    total: int
    success_count: int
    failure_count: int


class DocumentReprocessRequest(BaseModel):
    """文档重新处理请求"""

    document_ids: List[UUID] = Field(..., min_items=1)


class ProcessingTaskResponse(BaseModel):
    """处理任务响应"""

    id: UUID
    document_id: UUID
    task_type: str
    status: str
    progress: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    """搜索请求"""

    query: str = Field(..., min_length=1)
    top_k: int = Field(default=10, ge=1, le=100)
    filters: Dict[str, Any] = Field(default_factory=dict)
    with_content: bool = True


class SearchHit(BaseModel):
    """搜索结果项"""

    chunk_id: UUID
    document_id: UUID
    document_filename: str
    content: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """搜索响应"""

    query: str
    hits: List[SearchHit]
    total: int
    took_ms: int
