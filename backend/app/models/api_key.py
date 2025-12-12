"""
API 密钥模型
"""
import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSON

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class ApiKey(Base):
    """API 密钥表"""
    
    __tablename__ = "api_keys"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    key_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    key_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True
    )
    key_prefix: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )
    # 权限范围
    scopes: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: {"read": True, "write": True}
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
    # 关系
    user: Mapped["User"] = relationship(
        "User",
        back_populates="api_keys"
    )
    
    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, key_prefix={self.key_prefix})>"
