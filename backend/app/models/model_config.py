"""
模型配置表
三级配置体系：系统默认、知识库级、用户级
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from app.core.database import Base
from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column


class ConfigType(str, Enum):
    """配置类型枚举"""

    SYSTEM_DEFAULT = "system_default"  # 系统默认配置
    KB_SPECIFIC = "kb_specific"  # 知识库配置
    USER_SPECIFIC = "user_specific"  # 用户配置


class ModelType(str, Enum):
    """配置类型枚举"""

    EMBEDDING = "embedding"
    RERANK = "rerank"
    LLM = "llm"


class ModelConfig(Base):
    """模型配置表"""

    __tablename__ = "model_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config_type: Mapped[ConfigType] = mapped_column(
        SQLEnum(ConfigType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
        default=ConfigType.SYSTEM_DEFAULT,
    )
    model_type: Mapped[ModelType] = mapped_column(
        SQLEnum(ModelType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
        default=ModelType.EMBEDDING,
    )
    # 用户配置时使用
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # 知识库配置时使用
    kb_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Embedding 配置 和 Rerank 配置 共用字段
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    api_base: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    api_key_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    extra_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # 通用配置
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ModelConfig(id={self.id}, type={self.config_type})>"
