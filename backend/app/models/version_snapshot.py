"""
版本快照模型
存储版本创建时文档和分块的完整元信息
"""

import uuid
from datetime import datetime, timezone

from app.core.database import Base
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class VersionSnapshot(Base):
    """版本快照表 - 记录每个版本下文档和分块的元信息"""

    __tablename__ = "version_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kb_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 文档快照：存储文档在该版本时的元信息
    # 包含：file_name, file_type, file_size, content_hash, chunk_count, status 等
    document_snapshot: Mapped[dict] = mapped_column(
        JSON, nullable=False, comment="文档在该版本时的元信息快照"
    )

    # 该版本文档包含的分块 ID 列表
    chunk_ids: Mapped[list] = mapped_column(
        JSON, nullable=True, comment="该版本包含的分块 ID 列表"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # 关系
    kb_version = relationship(
        "KBVersion",
        back_populates="snapshots",
    )

    def __repr__(self) -> str:
        return f"<VersionSnapshot(id={self.id}, version_id={self.version_id})>"
