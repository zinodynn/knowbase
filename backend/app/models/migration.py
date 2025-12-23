"""
向量库迁移与重新向量化模型
Phase 4: 向量库迁移与模型更换
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from app.core.database import Base
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship


class MigrationStatus(str, Enum):
    """迁移/任务状态枚举"""

    PENDING = "pending"  # 等待开始
    RUNNING = "running"  # 运行中
    PAUSED = "paused"  # 已暂停
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消
    ROLLED_BACK = "rolled_back"  # 已回滚


class VectorMigration(Base):
    """向量库迁移任务表"""

    __tablename__ = "vector_migrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 迁移范围: NULL 表示迁移所有知识库
    kb_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # 源向量库配置
    source_type = Column(
        String(50),
        nullable=False,
        comment="源向量库类型: milvus, qdrant, weaviate",
    )
    source_config = Column(
        JSONB,
        nullable=True,
        comment="源向量库配置参数",
    )
    
    # 目标向量库配置
    target_type = Column(
        String(50),
        nullable=False,
        comment="目标向量库类型: milvus, qdrant, weaviate",
    )
    target_config = Column(
        JSONB,
        nullable=True,
        comment="目标向量库配置参数",
    )
    
    # 迁移状态
    status = Column(
        SQLEnum(MigrationStatus, values_callable=lambda x: [e.value for e in x]),
        default=MigrationStatus.PENDING,
        nullable=False,
        index=True,
    )
    
    # 进度统计
    total_collections = Column(Integer, default=0, comment="总 Collection 数")
    migrated_collections = Column(Integer, default=0, comment="已迁移 Collection 数")
    total_vectors = Column(Integer, default=0, comment="总向量数")
    migrated_vectors = Column(Integer, default=0, comment="已迁移向量数")
    progress = Column(Integer, default=0, comment="进度百分比 0-100")
    
    # 错误信息
    error_message = Column(Text, nullable=True)
    
    # 时间戳
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    
    # 关系
    creator = relationship("User", foreign_keys=[created_by])
    knowledge_base = relationship("KnowledgeBase")
    logs = relationship(
        "MigrationLog",
        back_populates="migration",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class MigrationLog(Base):
    """迁移日志表"""

    __tablename__ = "migration_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    migration_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vector_migrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # 日志级别
    log_level = Column(
        String(20),
        nullable=False,
        default="info",
        comment="日志级别: info, warning, error",
    )
    
    # 日志内容
    message = Column(Text, nullable=False)
    details = Column(JSONB, nullable=True, comment="详细信息")
    
    # 时间戳
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
    
    # 关系
    migration = relationship("VectorMigration", back_populates="logs")


class ReembeddingStrategy(str, Enum):
    """重新向量化策略"""

    REPLACE = "replace"  # 原地替换
    CREATE_NEW_COLLECTION = "create_new_collection"  # 创建新 Collection
    INCREMENTAL = "incremental"  # 增量更新


class ReembeddingTask(Base):
    """重新向量化任务表"""

    __tablename__ = "reembedding_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 目标知识库
    kb_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # 模型配置
    old_model_config = Column(JSONB, nullable=True, comment="原模型配置")
    new_model_config = Column(JSONB, nullable=False, comment="新模型配置")
    
    # 任务状态
    status = Column(
        SQLEnum(MigrationStatus, values_callable=lambda x: [e.value for e in x]),
        default=MigrationStatus.PENDING,
        nullable=False,
        index=True,
    )
    
    # 执行策略
    strategy = Column(
        SQLEnum(ReembeddingStrategy, values_callable=lambda x: [e.value for e in x]),
        default=ReembeddingStrategy.REPLACE,
        nullable=False,
        comment="执行策略",
    )
    
    # 进度统计
    total_chunks = Column(Integer, default=0, comment="总 chunk 数")
    processed_chunks = Column(Integer, default=0, comment="已处理 chunk 数")
    failed_chunks = Column(Integer, default=0, comment="失败 chunk 数")
    progress = Column(Integer, default=0, comment="进度百分比 0-100")
    
    # 批量大小
    batch_size = Column(Integer, default=100, comment="每批处理数量")
    
    # 新 Collection 名称 (策略为 create_new_collection 时使用)
    new_collection_name = Column(String(100), nullable=True)
    
    # 错误信息
    error_message = Column(Text, nullable=True)
    
    # 时间戳
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    
    # 关系
    creator = relationship("User", foreign_keys=[created_by])
    knowledge_base = relationship("KnowledgeBase")


class BatchOperationType(str, Enum):
    """批量操作类型"""

    DELETE = "delete"  # 批量删除
    REPROCESS = "reprocess"  # 批量重新处理
    UPDATE_METADATA = "update_metadata"  # 批量更新元数据
    ADD_TAGS = "add_tags"  # 批量添加标签
    REMOVE_TAGS = "remove_tags"  # 批量删除标签


class BatchOperationStatus(str, Enum):
    """批量操作状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BatchOperation(Base):
    """批量操作记录表"""

    __tablename__ = "batch_operations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 目标知识库
    kb_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # 操作类型
    operation_type = Column(
        SQLEnum(BatchOperationType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    
    # 目标文档 IDs
    target_ids = Column(JSONB, nullable=False, comment="目标文档 ID 列表")
    
    # 操作参数
    parameters = Column(JSONB, nullable=True, comment="操作参数")
    
    # 状态
    status = Column(
        SQLEnum(BatchOperationStatus, values_callable=lambda x: [e.value for e in x]),
        default=BatchOperationStatus.PENDING,
        nullable=False,
        index=True,
    )
    
    # 进度统计
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    progress = Column(Integer, default=0, comment="进度百分比 0-100")
    
    # 错误信息
    error_message = Column(Text, nullable=True)
    
    # 创建信息
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # 关系
    creator = relationship("User", foreign_keys=[created_by])
    knowledge_base = relationship("KnowledgeBase")


class RollbackCheckpoint(Base):
    """回滚检查点表"""

    __tablename__ = "rollback_checkpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 操作类型
    operation_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="操作类型: migration, reembedding",
    )
    
    # 关联的操作 ID
    operation_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="关联的迁移或重新向量化任务 ID",
    )
    
    # 检查点数据
    checkpoint_data = Column(
        JSONB,
        nullable=False,
        comment="检查点数据: 包含配置备份、ID 映射等",
    )
    
    # 时间戳
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="检查点过期时间",
    )
