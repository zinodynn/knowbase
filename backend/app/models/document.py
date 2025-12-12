"""
文档模型
"""
import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from enum import Enum

from sqlalchemy import String, DateTime, Text, Integer, BigInteger, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSON

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.knowledge_base import KnowledgeBase


class DocumentStatus(str, Enum):
    """文档状态枚举"""
    PENDING = "pending"       # 等待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"    # 处理完成
    FAILED = "failed"         # 处理失败


class DocumentSourceType(str, Enum):
    """文档来源类型枚举"""
    UPLOAD = "upload"   # 手动上传
    GIT = "git"         # Git 同步
    SVN = "svn"         # SVN 同步
    API = "api"         # API 推送


class Document(Base):
    """文档表"""
    
    __tablename__ = "documents"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    kb_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    file_path: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    file_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )
    file_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True
    )
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus),
        default=DocumentStatus.PENDING,
        nullable=False,
        index=True
    )
    source_type: Mapped[DocumentSourceType] = mapped_column(
        SQLEnum(DocumentSourceType),
        default=DocumentSourceType.UPLOAD,
        nullable=False
    )
    source_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    # 处理信息
    chunk_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    # 元数据
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSON,
        nullable=True
    )
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
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
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    
    # 关系
    knowledge_base: Mapped["KnowledgeBase"] = relationship(
        "KnowledgeBase",
        back_populates="documents"
    )
    chunks: Mapped[List["Chunk"]] = relationship(
        "Chunk",
        back_populates="document",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename={self.filename})>"


class Chunk(Base):
    """文档分块表"""
    
    __tablename__ = "chunks"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    kb_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    # 向量数据库中的向量 ID
    vector_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    # 元数据（页码、标题等）
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSON,
        nullable=True
    )
    token_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    # 嵌入模型版本（用于追踪）
    embedding_model_version: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
    # 关系
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks"
    )
    
    def __repr__(self) -> str:
        return f"<Chunk(id={self.id}, document_id={self.document_id}, index={self.chunk_index})>"
