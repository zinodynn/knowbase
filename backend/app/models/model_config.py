"""
模型配置表
三级配置体系：系统默认、知识库级、用户级
"""
import uuid
from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class ConfigType(str, Enum):
    """配置类型枚举"""
    SYSTEM_DEFAULT = "system_default"  # 系统默认配置
    KB_SPECIFIC = "kb_specific"        # 知识库配置
    USER_SPECIFIC = "user_specific"    # 用户配置


class ModelConfig(Base):
    """模型配置表"""
    
    __tablename__ = "model_configs"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    config_type: Mapped[ConfigType] = mapped_column(
        SQLEnum(ConfigType),
        nullable=False,
        index=True
    )
    # 用户配置时使用
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    # 知识库配置时使用
    kb_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Embedding 配置
    embedding_provider: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    embedding_api_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    embedding_api_key_encrypted: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    embedding_model_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    embedding_dimension: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    
    # Rerank 配置
    rerank_provider: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    rerank_api_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    rerank_api_key_encrypted: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    rerank_model_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    
    # 通用配置
    timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        default=30,
        nullable=False
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    def __repr__(self) -> str:
        return f"<ModelConfig(id={self.id}, type={self.config_type})>"
