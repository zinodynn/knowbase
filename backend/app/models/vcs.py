"""
版本控制配置相关模型
"""

import uuid
from datetime import datetime
from typing import Optional

from app.core.database import Base
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class VCSConfig(Base):
    """版本控制配置表"""

    __tablename__ = "vcs_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kb_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # VCS 类型
    vcs_type = Column(String(10), nullable=False, comment="版本控制类型: git, svn")

    # 仓库信息
    repo_url = Column(Text, nullable=False, comment="仓库URL")
    branch = Column(String(100), default="main", comment="分支名(Git)")
    sync_path = Column(String(500), nullable=True, comment="仓库内的子路径")

    # 认证信息
    auth_type = Column(
        String(20),
        nullable=False,
        default="none",
        comment="认证类型: none, basic, ssh_key",
    )
    username = Column(String(100), nullable=True)
    password_encrypted = Column(Text, nullable=True, comment="加密的密码")
    ssh_key_encrypted = Column(Text, nullable=True, comment="加密的SSH密钥")

    # 同步设置
    auto_sync = Column(Boolean, default=False, comment="是否自动同步")
    sync_interval = Column(Integer, default=60, comment="同步间隔(分钟)")

    # 文件过滤
    include_patterns = Column(Text, nullable=True, comment="包含的文件模式(JSON数组)")
    exclude_patterns = Column(Text, nullable=True, comment="排除的文件模式(JSON数组)")

    # 状态
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_commit_hash = Column(String(64), nullable=True, comment="最后同步的提交哈希")
    last_error = Column(Text, nullable=True)

    # 时间戳
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
    knowledge_base = relationship("KnowledgeBase", back_populates="vcs_config")


class KBVersion(Base):
    """知识库版本表"""

    __tablename__ = "kb_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kb_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 版本信息
    version = Column(Integer, nullable=False, comment="版本号")
    description = Column(Text, nullable=True, comment="版本描述")
    commit_hash = Column(String(64), nullable=True, comment="Git/SVN提交哈希")

    # 统计信息
    document_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)

    # 创建信息
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # 关系
    knowledge_base = relationship("KnowledgeBase", back_populates="versions")
    creator = relationship("User")


class KBProcessingConfig(Base):
    """知识库处理配置表"""

    __tablename__ = "kb_processing_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kb_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # 分块配置
    chunk_size = Column(Integer, default=1000, comment="分块大小(字符)")
    chunk_overlap = Column(Integer, default=200, comment="分块重叠(字符)")
    chunk_strategy = Column(
        String(20), default="recursive", comment="分块策略: fixed, recursive, semantic"
    )

    # OCR 配置
    enable_ocr = Column(Boolean, default=False, comment="是否启用OCR")
    ocr_languages = Column(String(100), default="chi_sim,eng", comment="OCR语言")

    # 支持的文件类型
    supported_file_types = Column(
        Text,
        default='["pdf","docx","doc","txt","md","html","xlsx","xls","csv"]',
        comment="支持的文件类型(JSON数组)",
    )

    # 处理配置
    max_file_size_mb = Column(Integer, default=50, comment="最大文件大小(MB)")
    auto_process = Column(Boolean, default=True, comment="上传后自动处理")

    # 时间戳
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
    knowledge_base = relationship("KnowledgeBase", back_populates="processing_config")
