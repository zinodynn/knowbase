"""
Alembic environment configuration
Uses synchronous engine for migrations with psycopg2
"""
from logging.config import fileConfig

from alembic import context
# Import config and models
from app.core.config import settings
from app.core.database import Base
# Import all models to ensure they are registered
from app.models import (ApiKey, Chunk, Document, KBTag, KnowledgeBase,
                        ModelConfig, User, UserKBPermission)
from sqlalchemy import engine_from_config, pool

# Alembic config object
config = context.config

# Set database URL (use sync URL for migrations)
config.set_main_option("sqlalchemy.url", settings.database_url_sync)

# 配置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 目标元数据（用于自动生成迁移）
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    离线模式运行迁移
    不需要数据库连接，直接生成 SQL
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Online mode: run migrations with database connection
    Uses synchronous engine for compatibility with psycopg2
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
