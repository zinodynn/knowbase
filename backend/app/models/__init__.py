"""
数据模型初始化
导出所有模型
"""

from app.models.api_key import ApiKey
from app.models.document import Chunk, Document, DocumentSourceType, DocumentStatus
from app.models.knowledge_base import KBTag, KBVisibility, KnowledgeBase

# Phase 4: 迁移与批量操作
from app.models.migration import (
    BatchOperation,
    BatchOperationStatus,
    BatchOperationType,
    MigrationLog,
    MigrationStatus,
    ReembeddingStrategy,
    ReembeddingTask,
    RollbackCheckpoint,
    VectorMigration,
)
from app.models.model_config import ConfigType, ModelConfig
from app.models.permission import PermissionLevel, UserKBPermission
from app.models.processing import ModelCallLog, ProcessingTask
from app.models.user import User
from app.models.vcs import KBProcessingConfig, KBVersion, VCSConfig

__all__ = [
    # 用户
    "User",
    # 知识库
    "KnowledgeBase",
    "KBTag",
    "KBVisibility",
    # 文档
    "Document",
    "Chunk",
    "DocumentStatus",
    "DocumentSourceType",
    # API 密钥
    "ApiKey",
    # 权限
    "UserKBPermission",
    "PermissionLevel",
    # 模型配置
    "ModelConfig",
    "ConfigType",
    # Phase 2: 处理任务
    "ProcessingTask",
    "ModelCallLog",
    # Phase 2: VCS
    "VCSConfig",
    "KBVersion",
    "KBProcessingConfig",
    # Phase 4: 迁移与批量操作
    "VectorMigration",
    "MigrationLog",
    "MigrationStatus",
    "ReembeddingTask",
    "ReembeddingStrategy",
    "BatchOperation",
    "BatchOperationType",
    "BatchOperationStatus",
    "RollbackCheckpoint",
]
