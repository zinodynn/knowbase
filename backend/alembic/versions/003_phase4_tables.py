"""Add Phase 4 tables: vector migration, reembedding, batch operations

Revision ID: 003_phase4_tables
Revises: 002_phase2_tables
Create Date: 2024-12-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003_phase4_tables"
down_revision: Union[str, None] = "002_phase2_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建迁移状态枚举
    migrationstatus_enum = postgresql.ENUM(
        "pending",
        "running",
        "paused",
        "completed",
        "failed",
        "cancelled",
        "rolled_back",
        name="migrationstatus",
        create_type=False,
    )
    migrationstatus_enum.create(op.get_bind(), checkfirst=True)

    # 创建重新向量化策略枚举
    reembeddingstrategy_enum = postgresql.ENUM(
        "replace",
        "create_new_collection",
        "incremental",
        name="reembeddingstrategy",
        create_type=False,
    )
    reembeddingstrategy_enum.create(op.get_bind(), checkfirst=True)

    # 创建批量操作类型枚举
    batchoperationtype_enum = postgresql.ENUM(
        "delete",
        "reprocess",
        "update_metadata",
        "add_tags",
        "remove_tags",
        name="batchoperationtype",
        create_type=False,
    )
    batchoperationtype_enum.create(op.get_bind(), checkfirst=True)

    # 创建批量操作状态枚举
    batchoperationstatus_enum = postgresql.ENUM(
        "pending",
        "running",
        "completed",
        "failed",
        name="batchoperationstatus",
        create_type=False,
    )
    batchoperationstatus_enum.create(op.get_bind(), checkfirst=True)

    # 1. 创建 vector_migrations 表
    op.create_table(
        "vector_migrations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kb_id", sa.UUID(), nullable=True),
        sa.Column(
            "source_type",
            sa.String(length=50),
            nullable=False,
            comment="源向量库类型: milvus, qdrant, weaviate",
        ),
        sa.Column(
            "source_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="源向量库配置参数",
        ),
        sa.Column(
            "target_type",
            sa.String(length=50),
            nullable=False,
            comment="目标向量库类型: milvus, qdrant, weaviate",
        ),
        sa.Column(
            "target_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="目标向量库配置参数",
        ),
        sa.Column(
            "status",
            migrationstatus_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "total_collections",
            sa.Integer(),
            nullable=True,
            server_default="0",
            comment="总 Collection 数",
        ),
        sa.Column(
            "migrated_collections",
            sa.Integer(),
            nullable=True,
            server_default="0",
            comment="已迁移 Collection 数",
        ),
        sa.Column(
            "total_vectors",
            sa.Integer(),
            nullable=True,
            server_default="0",
            comment="总向量数",
        ),
        sa.Column(
            "migrated_vectors",
            sa.Integer(),
            nullable=True,
            server_default="0",
            comment="已迁移向量数",
        ),
        sa.Column(
            "progress",
            sa.Integer(),
            nullable=True,
            server_default="0",
            comment="进度百分比 0-100",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["kb_id"], ["knowledge_bases.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vector_migrations_kb_id", "vector_migrations", ["kb_id"])
    op.create_index("ix_vector_migrations_status", "vector_migrations", ["status"])
    op.create_index(
        "ix_vector_migrations_created_by", "vector_migrations", ["created_by"]
    )

    # 2. 创建 migration_logs 表
    op.create_table(
        "migration_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("migration_id", sa.UUID(), nullable=False),
        sa.Column(
            "log_level",
            sa.String(length=20),
            nullable=False,
            server_default="info",
            comment="日志级别: info, warning, error",
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="详细信息",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["migration_id"], ["vector_migrations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_migration_logs_migration_id", "migration_logs", ["migration_id"]
    )
    op.create_index("ix_migration_logs_created_at", "migration_logs", ["created_at"])

    # 3. 创建 reembedding_tasks 表
    op.create_table(
        "reembedding_tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kb_id", sa.UUID(), nullable=False),
        sa.Column(
            "old_model_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="原模型配置",
        ),
        sa.Column(
            "new_model_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="新模型配置",
        ),
        sa.Column(
            "status",
            migrationstatus_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "strategy",
            reembeddingstrategy_enum,
            nullable=False,
            server_default="replace",
            comment="执行策略",
        ),
        sa.Column(
            "total_chunks",
            sa.Integer(),
            nullable=True,
            server_default="0",
            comment="总 chunk 数",
        ),
        sa.Column(
            "processed_chunks",
            sa.Integer(),
            nullable=True,
            server_default="0",
            comment="已处理 chunk 数",
        ),
        sa.Column(
            "failed_chunks",
            sa.Integer(),
            nullable=True,
            server_default="0",
            comment="失败 chunk 数",
        ),
        sa.Column(
            "progress",
            sa.Integer(),
            nullable=True,
            server_default="0",
            comment="进度百分比 0-100",
        ),
        sa.Column(
            "batch_size",
            sa.Integer(),
            nullable=True,
            server_default="100",
            comment="每批处理数量",
        ),
        sa.Column(
            "new_collection_name",
            sa.String(length=100),
            nullable=True,
            comment="新 Collection 名称",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
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
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reembedding_tasks_kb_id", "reembedding_tasks", ["kb_id"])
    op.create_index("ix_reembedding_tasks_status", "reembedding_tasks", ["status"])
    op.create_index(
        "ix_reembedding_tasks_created_by", "reembedding_tasks", ["created_by"]
    )

    # 4. 创建 batch_operations 表
    op.create_table(
        "batch_operations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kb_id", sa.UUID(), nullable=False),
        sa.Column(
            "operation_type",
            batchoperationtype_enum,
            nullable=False,
        ),
        sa.Column(
            "target_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="目标文档 ID 列表",
        ),
        sa.Column(
            "parameters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="操作参数",
        ),
        sa.Column(
            "status",
            batchoperationstatus_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("total_items", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("processed_items", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("failed_items", sa.Integer(), nullable=True, server_default="0"),
        sa.Column(
            "progress",
            sa.Integer(),
            nullable=True,
            server_default="0",
            comment="进度百分比 0-100",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["kb_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_batch_operations_kb_id", "batch_operations", ["kb_id"])
    op.create_index(
        "ix_batch_operations_operation_type", "batch_operations", ["operation_type"]
    )
    op.create_index("ix_batch_operations_status", "batch_operations", ["status"])
    op.create_index(
        "ix_batch_operations_created_by", "batch_operations", ["created_by"]
    )

    # 5. 创建 rollback_checkpoints 表
    op.create_table(
        "rollback_checkpoints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "operation_type",
            sa.String(length=50),
            nullable=False,
            comment="操作类型: migration, reembedding",
        ),
        sa.Column(
            "operation_id",
            sa.UUID(),
            nullable=False,
            comment="关联的迁移或重新向量化任务 ID",
        ),
        sa.Column(
            "checkpoint_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="检查点数据: 包含配置备份、ID 映射等",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="检查点过期时间",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rollback_checkpoints_operation",
        "rollback_checkpoints",
        ["operation_type", "operation_id"],
    )

    # 6. 为 chunks 表添加 embedding_model_version 字段
    op.add_column(
        "chunks",
        sa.Column(
            "embedding_model_version",
            sa.String(length=100),
            nullable=True,
            comment="使用的 embedding 模型版本标识",
        ),
    )


def downgrade() -> None:
    # 删除 chunks 表的新字段
    op.drop_column("chunks", "embedding_model_version")

    # 按依赖顺序删除表
    op.drop_table("rollback_checkpoints")
    op.drop_table("batch_operations")
    op.drop_table("reembedding_tasks")
    op.drop_table("migration_logs")
    op.drop_table("vector_migrations")

    # 删除枚举类型
    postgresql.ENUM(name="batchoperationstatus").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="batchoperationtype").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="reembeddingstrategy").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="migrationstatus").drop(op.get_bind(), checkfirst=True)
