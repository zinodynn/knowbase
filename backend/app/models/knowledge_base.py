"""
知识库模型
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from app.core.database import Base
from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.user import User


class KBVisibility(str, Enum):
    """知识库可见性枚举"""

    PRIVATE = "private"  # 仅创建者可见
    TEAM = "team"  # 团队可见
    PUBLIC = "public"  # 公开可见


class KnowledgeBase(Base):
    """知识库表"""

    __tablename__ = "knowledge_bases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    visibility: Mapped[KBVisibility] = mapped_column(
        SQLEnum(KBVisibility, values_callable=lambda x: [e.value for e in x]),
        default=KBVisibility.PRIVATE,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # 嵌入模型信息
    embedding_model_info: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # 统计信息
    document_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
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

    # 关系
    owner: Mapped["User"] = relationship("User", back_populates="knowledge_bases")
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="knowledge_base",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    tags: Mapped[List["KBTag"]] = relationship(
        "KBTag",
        back_populates="knowledge_base",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    # Phase 2 关系
    vcs_config = relationship(
        "VCSConfig",
        back_populates="knowledge_base",
        uselist=False,
        cascade="all, delete-orphan",
    )
    versions = relationship(
        "KBVersion",
        back_populates="knowledge_base",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    processing_config = relationship(
        "KBProcessingConfig",
        back_populates="knowledge_base",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<KnowledgeBase(id={self.id}, name={self.name})>"


class KBTag(Base):
    """知识库标签表"""

    __tablename__ = "kb_tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    kb_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tag_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # 关系
    knowledge_base: Mapped["KnowledgeBase"] = relationship(
        "KnowledgeBase", back_populates="tags"
    )

    def __repr__(self) -> str:
        return f"<KBTag(kb_id={self.kb_id}, tag_name={self.tag_name})>"
