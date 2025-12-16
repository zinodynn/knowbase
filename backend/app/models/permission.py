"""
用户知识库权限模型
"""

import uuid
from datetime import datetime, timezone
from enum import Enum

from app.core.database import Base
from sqlalchemy import DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class PermissionLevel(str, Enum):
    """权限级别枚举"""

    READ = "read"  # 只读
    WRITE = "write"  # 读写
    ADMIN = "admin"  # 管理员（可授权他人）


class UserKBPermission(Base):
    """用户知识库权限表"""

    __tablename__ = "user_kb_permissions"
    __table_args__ = (
        UniqueConstraint("user_id", "kb_id", name="uq_user_kb_permission"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kb_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    permission: Mapped[PermissionLevel] = mapped_column(
        SQLEnum(PermissionLevel, values_callable=lambda x: [e.value for e in x]),
        default=PermissionLevel.READ,
        nullable=False,
    )
    granted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<UserKBPermission(user_id={self.user_id}, kb_id={self.kb_id}, permission={self.permission})>"
