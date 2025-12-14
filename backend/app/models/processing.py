"""
处理任务相关模型
包含处理任务、模型调用日志等
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.core.database import Base
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class ProcessingTask(Base):
    """处理任务表"""

    __tablename__ = "processing_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 任务类型
    task_type = Column(
        String(20),
        nullable=False,
        comment="任务类型: parse, chunk, embed, sync_git, sync_svn",
    )

    # 任务状态
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="状态: pending, running, completed, failed",
    )

    # 进度 (0-100)
    progress = Column(Integer, default=0)

    # 错误信息
    error_message = Column(Text, nullable=True)

    # 重试次数
    retry_count = Column(Integer, default=0)

    # 时间戳
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # 关系
    document = relationship("Document", back_populates="processing_tasks")


class ModelCallLog(Base):
    """模型调用日志表"""

    __tablename__ = "model_call_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 关联信息
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    kb_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 调用类型
    call_type = Column(
        String(20),
        nullable=False,
        index=True,
        comment="调用类型: embedding, rerank, chat",
    )

    # 模型信息
    model_provider = Column(
        String(50),
        nullable=False,
        comment="提供商: openai, azure, cohere, jina, custom",
    )
    model_name = Column(String(100), nullable=False)

    # 输入输出信息
    input_text_length = Column(Integer, nullable=True, comment="输入文本长度")
    output_dimension = Column(
        Integer, nullable=True, comment="输出向量维度(embedding时)"
    )
    token_count = Column(Integer, nullable=True, comment="Token数量")

    # 性能指标
    latency_ms = Column(Integer, nullable=True, comment="调用延迟(毫秒)")

    # 状态
    status = Column(
        String(20), nullable=False, default="success", comment="状态: success, failed"
    )
    error_message = Column(Text, nullable=True)

    # 成本估算
    cost_estimate = Column(Numeric(10, 6), nullable=True, comment="估算成本(美元)")

    # 时间戳
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
