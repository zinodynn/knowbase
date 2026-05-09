"""Add version management: version_snapshots table + KBVersion fields

Revision ID: 004_version_management
Revises: 003_phase4_tables
Create Date: 2026-05-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004_version_management"
down_revision: Union[str, None] = "003_phase4_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 为 kb_versions 表添加新字段
    op.add_column(
        "kb_versions",
        sa.Column(
            "snapshot_data",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="快照数据：存储该版本下所有文档和分块的元信息",
        ),
    )
    op.add_column(
        "kb_versions",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="是否为当前激活版本",
        ),
    )
    op.add_column(
        "kb_versions",
        sa.Column(
            "tags",
            sa.String(length=200),
            nullable=True,
            comment="版本标签，如 v1.0, stable",
        ),
    )

    # 2. 创建 version_snapshots 表
    op.create_table(
        "version_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("version_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column(
            "document_snapshot",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            comment="文档在该版本时的元信息快照",
        ),
        sa.Column(
            "chunk_ids",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="该版本包含的分块 ID 列表",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["version_id"], ["kb_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_version_snapshots_version_id", "version_snapshots", ["version_id"]
    )
    op.create_index(
        "ix_version_snapshots_document_id", "version_snapshots", ["document_id"]
    )


def downgrade() -> None:
    # 删除 version_snapshots 表
    op.drop_index("ix_version_snapshots_document_id", table_name="version_snapshots")
    op.drop_index("ix_version_snapshots_version_id", table_name="version_snapshots")
    op.drop_table("version_snapshots")

    # 删除 kb_versions 表的新字段
    op.drop_column("kb_versions", "tags")
    op.drop_column("kb_versions", "is_active")
    op.drop_column("kb_versions", "snapshot_data")
