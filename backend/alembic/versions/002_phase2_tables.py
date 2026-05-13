"""Add Phase 2 tables: processing, vcs, versions

Revision ID: 002_phase2_tables
Revises: 001_initial
Create Date: 2024-12-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_phase2_tables"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 processing_tasks 表
    op.create_table(
        "processing_tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column(
            "task_type",
            sa.String(length=20),
            nullable=False,
            comment="任务类型: parse, chunk, embed, sync_git, sync_svn",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
            comment="状态: pending, running, completed, failed",
        ),
        sa.Column("progress", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_processing_tasks_document_id", "processing_tasks", ["document_id"]
    )
    op.create_index("ix_processing_tasks_status", "processing_tasks", ["status"])
    op.create_index("ix_processing_tasks_task_type", "processing_tasks", ["task_type"])

    # 创建 model_call_logs 表
    op.create_table(
        "model_call_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("kb_id", sa.UUID(), nullable=True),
        sa.Column(
            "call_type",
            sa.String(length=20),
            nullable=False,
            comment="调用类型: embedding, rerank, chat",
        ),
        sa.Column(
            "model_provider", sa.String(length=50), nullable=False, comment="提供商"
        ),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("input_text_length", sa.Integer(), nullable=True),
        sa.Column("output_dimension", sa.Integer(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="success"
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("cost_estimate", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["kb_id"], ["knowledge_bases.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_model_call_logs_user_id", "model_call_logs", ["user_id"])
    op.create_index("ix_model_call_logs_kb_id", "model_call_logs", ["kb_id"])
    op.create_index("ix_model_call_logs_call_type", "model_call_logs", ["call_type"])
    op.create_index("ix_model_call_logs_created_at", "model_call_logs", ["created_at"])

    # 创建 vcs_configs 表
    op.create_table(
        "vcs_configs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kb_id", sa.UUID(), nullable=False),
        sa.Column(
            "vcs_type",
            sa.String(length=10),
            nullable=False,
            comment="版本控制类型: git, svn",
        ),
        sa.Column("repo_url", sa.Text(), nullable=False),
        sa.Column(
            "branch", sa.String(length=100), nullable=True, server_default="main"
        ),
        sa.Column("sync_path", sa.String(length=500), nullable=True),
        sa.Column(
            "auth_type", sa.String(length=20), nullable=False, server_default="none"
        ),
        sa.Column("username", sa.String(length=100), nullable=True),
        sa.Column("password_encrypted", sa.Text(), nullable=True),
        sa.Column("ssh_key_encrypted", sa.Text(), nullable=True),
        sa.Column("auto_sync", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("sync_interval", sa.Integer(), nullable=True, server_default="60"),
        sa.Column("include_patterns", sa.Text(), nullable=True),
        sa.Column("exclude_patterns", sa.Text(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_commit_hash", sa.String(length=64), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["kb_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kb_id", name="uq_vcs_configs_kb_id"),
    )
    op.create_index("ix_vcs_configs_kb_id", "vcs_configs", ["kb_id"])

    # 创建 kb_versions 表
    op.create_table(
        "kb_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kb_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("commit_hash", sa.String(length=64), nullable=True),
        sa.Column("document_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("chunk_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["kb_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kb_versions_kb_id", "kb_versions", ["kb_id"])
    op.create_index("ix_kb_versions_version", "kb_versions", ["version"])

    # 创建 kb_processing_configs 表
    op.create_table(
        "kb_processing_configs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kb_id", sa.UUID(), nullable=False),
        sa.Column("chunk_size", sa.Integer(), nullable=True, server_default="1000"),
        sa.Column("chunk_overlap", sa.Integer(), nullable=True, server_default="200"),
        sa.Column(
            "chunk_strategy",
            sa.String(length=20),
            nullable=True,
            server_default="recursive",
        ),
        sa.Column("enable_ocr", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column(
            "ocr_languages",
            sa.String(length=100),
            nullable=True,
            server_default="chi_sim,eng",
        ),
        sa.Column(
            "supported_file_types",
            sa.Text(),
            nullable=True,
            server_default='["pdf","docx","doc","txt","md","html","xlsx","xls","csv"]',
        ),
        sa.Column("max_file_size_mb", sa.Integer(), nullable=True, server_default="50"),
        sa.Column("auto_process", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["kb_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kb_id", name="uq_kb_processing_configs_kb_id"),
    )
    op.create_index(
        "ix_kb_processing_configs_kb_id", "kb_processing_configs", ["kb_id"]
    )


def downgrade() -> None:
    op.drop_table("kb_processing_configs")
    op.drop_table("kb_versions")
    op.drop_table("vcs_configs")
    op.drop_table("model_call_logs")
    op.drop_table("processing_tasks")
