"""
迁移与批量操作相关 Schema
Phase 4: 向量库迁移与模型更换
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# ===================== 枚举类型 =====================


class MigrationStatusEnum(str, Enum):
    """迁移状态"""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


class ReembeddingStrategyEnum(str, Enum):
    """重新向量化策略"""

    REPLACE = "replace"
    CREATE_NEW_COLLECTION = "create_new_collection"
    INCREMENTAL = "incremental"


class BatchOperationTypeEnum(str, Enum):
    """批量操作类型"""

    DELETE = "delete"
    REPROCESS = "reprocess"
    UPDATE_METADATA = "update_metadata"
    ADD_TAGS = "add_tags"
    REMOVE_TAGS = "remove_tags"


class BatchOperationStatusEnum(str, Enum):
    """批量操作状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ===================== 向量库迁移 Schema =====================


class VectorMigrationCreate(BaseModel):
    """创建向量库迁移任务"""

    kb_id: Optional[UUID] = Field(None, description="知识库 ID，为空则迁移所有")
    source_type: str = Field(..., description="源向量库类型: milvus, qdrant, weaviate")
    target_type: str = Field(..., description="目标向量库类型")
    source_config: Optional[Dict[str, Any]] = Field(None, description="源向量库配置")
    target_config: Optional[Dict[str, Any]] = Field(None, description="目标向量库配置")
    auto_start: bool = Field(False, description="是否立即开始")


class VectorMigrationResponse(BaseModel):
    """向量库迁移任务响应"""

    id: UUID
    kb_id: Optional[UUID] = None
    source_type: str
    target_type: str
    source_config: Optional[Dict[str, Any]] = None
    target_config: Optional[Dict[str, Any]] = None
    status: MigrationStatusEnum
    total_collections: int = 0
    migrated_collections: int = 0
    total_vectors: int = 0
    migrated_vectors: int = 0
    progress: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    estimated_remaining_time: Optional[str] = None

    class Config:
        from_attributes = True


class VectorMigrationList(BaseModel):
    """向量库迁移任务列表"""

    items: List[VectorMigrationResponse]
    total: int
    page: int
    page_size: int


# ===================== 迁移日志 Schema =====================


class MigrationLogResponse(BaseModel):
    """迁移日志响应"""

    id: UUID
    migration_id: UUID
    log_level: str
    message: str
    details: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MigrationLogList(BaseModel):
    """迁移日志列表"""

    items: List[MigrationLogResponse]
    total: int


# ===================== 重新向量化 Schema =====================


class ModelConfigInfo(BaseModel):
    """模型配置信息"""

    provider: str = Field(
        ..., description="提供商: openai, azure, cohere, jina, custom"
    )
    model_name: str = Field(..., description="模型名称")
    dimension: int = Field(..., description="向量维度")
    api_url: Optional[str] = None
    api_key: Optional[str] = None


class ReembeddingTaskCreate(BaseModel):
    """创建重新向量化任务"""

    new_model_config: ModelConfigInfo
    strategy: ReembeddingStrategyEnum = Field(
        ReembeddingStrategyEnum.REPLACE, description="执行策略"
    )
    batch_size: int = Field(100, ge=10, le=1000, description="每批处理数量")
    auto_start: bool = Field(False, description="是否立即开始")


class ReembeddingTaskResponse(BaseModel):
    """重新向量化任务响应"""

    id: UUID
    kb_id: UUID
    old_model_config: Optional[Dict[str, Any]] = None
    new_model_config: Dict[str, Any]
    status: MigrationStatusEnum
    strategy: ReembeddingStrategyEnum
    total_chunks: int = 0
    processed_chunks: int = 0
    failed_chunks: int = 0
    progress: int = 0
    batch_size: int = 100
    new_collection_name: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    estimated_remaining_time: Optional[str] = None

    class Config:
        from_attributes = True


class ReembeddingTaskList(BaseModel):
    """重新向量化任务列表"""

    items: List[ReembeddingTaskResponse]
    total: int
    page: int
    page_size: int


class ModelChangeCheck(BaseModel):
    """模型变更检测结果"""

    current_model: Optional[Dict[str, Any]] = None
    configured_model: Optional[Dict[str, Any]] = None
    needs_reembed: bool
    dimension_changed: bool
    estimated_cost: Optional[float] = None
    estimated_time: Optional[str] = None


# ===================== 批量操作 Schema =====================


class BatchDeleteRequest(BaseModel):
    """批量删除请求"""

    document_ids: List[UUID] = Field(..., min_length=1, description="文档 ID 列表")
    delete_from_storage: bool = Field(True, description="是否删除 MinIO 中的文件")
    delete_vectors: bool = Field(True, description="是否删除向量")


class BatchReprocessRequest(BaseModel):
    """批量重新处理请求"""

    document_ids: List[UUID] = Field(..., min_length=1, description="文档 ID 列表")
    reparse: bool = Field(True, description="是否重新解析")
    rechunk: bool = Field(True, description="是否重新分块")
    reembed: bool = Field(True, description="是否重新向量化")


class BatchUpdateMetadataRequest(BaseModel):
    """批量更新元数据请求"""

    document_ids: List[UUID] = Field(..., min_length=1, description="文档 ID 列表")
    metadata: Dict[str, Any] = Field(..., description="要更新的元数据")


class BatchTagsRequest(BaseModel):
    """批量标签操作请求"""

    document_ids: List[UUID] = Field(..., min_length=1, description="文档 ID 列表")
    tags: List[str] = Field(..., min_length=1, description="标签列表")


class BatchOperationResponse(BaseModel):
    """批量操作响应"""

    id: UUID
    kb_id: UUID
    operation_type: BatchOperationTypeEnum
    target_ids: List[UUID]
    parameters: Optional[Dict[str, Any]] = None
    status: BatchOperationStatusEnum
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0
    progress: int = 0
    error_message: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BatchOperationList(BaseModel):
    """批量操作列表"""

    items: List[BatchOperationResponse]
    total: int
    page: int
    page_size: int


# ===================== 回滚检查点 Schema =====================


class RollbackCheckpointResponse(BaseModel):
    """回滚检查点响应"""

    id: UUID
    operation_type: str
    operation_id: UUID
    checkpoint_data: Dict[str, Any]
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RollbackRequest(BaseModel):
    """回滚请求"""

    checkpoint_id: Optional[UUID] = Field(
        None, description="检查点 ID，为空则使用最新检查点"
    )
    confirm: bool = Field(False, description="确认回滚")
