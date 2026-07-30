"""
初始化脚本
创建初始超级用户和默认配置
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from app.core.config import settings
from app.core.database import async_session_maker


def check_and_migrate() -> None:
    """检查迁移状态，如果不在 head 则自动执行 upgrade head"""
    alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))

    # 使用同步引擎检查当前版本（alembic 不支持异步）
    sync_url = str(settings.DATABASE_URL).replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url)

    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        current_rev = context.get_current_revision()

    script = ScriptDirectory.from_config(alembic_cfg)
    head_rev = script.get_current_head()

    if current_rev == head_rev:
        print(f"  ✓ 数据库迁移已是最新 (revision: {current_rev})")
        return

    print(f"  ! 迁移不是最新: current={current_rev}, head={head_rev}")
    print("  → 自动执行 alembic upgrade head ...")
    command.upgrade(alembic_cfg, "head")
    print("  ✓ 迁移完成")


from app.core.security import get_password_hash
from app.models.model_config import ModelConfig
from app.models.user import User
from sqlalchemy import select


async def create_superuser(
    username: str = "admin",
    email: str = "admin@example.com",
    password: str = "admin123",
) -> None:
    """创建超级用户"""
    async with async_session_maker() as db:
        # 检查是否已存在
        result = await db.execute(select(User).where(User.username == username))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"用户 '{username}' 已存在")
            return

        # 创建超级用户
        user = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            full_name="System Administrator",
            is_active=True,
            is_superuser=True,
        )

        db.add(user)
        await db.commit()

        print(f"超级用户 '{username}' 创建成功")
        print(f"  邮箱: {email}")
        print(f"  密码: {password}")
        print("  请登录后立即修改密码！")


async def create_default_model_configs() -> None:
    """创建默认模型配置（三级配置体系：系统默认）"""
    from app.models.model_config import ConfigType

    async with async_session_maker() as db:
        # 检查是否已有系统默认配置
        result = await db.execute(
            select(ModelConfig).where(
                ModelConfig.config_type == ConfigType.SYSTEM_DEFAULT
            )
        )
        existing = result.scalars().all()

        if existing:
            print(f"已存在 {len(existing)} 个系统默认模型配置")
            return

        # 创建系统默认 Embedding 配置（占位模板，无 API Key，需在管理界面配置后激活）
        default_config = ModelConfig(
            config_type=ConfigType.SYSTEM_DEFAULT,
            user_id=None,
            kb_id=None,
            name="openai",
            description="openai text-embedding-ada-002（模板，请在管理界面填入 API Key 后启用）",
            provider="openai",
            api_base="https://api.openai.com/v1",
            api_key_encrypted=None,
            model_name="text-embedding-ada-002",
            extra_params=dict(dimension=1536),
            timeout_seconds=30,
            max_retries=3,
            is_default=False,  # 无 API Key，不设为默认
            is_active=False,  # 未配置密钥前保持禁用
        )
        db.add(default_config)

        await db.commit()

        print("系统默认模型配置创建成功:")
        print("  - Embedding: OpenAI text-embedding-ada-002 (dimension: 1536)")
        print("  - Rerank: 未配置（可选）")
        print("  请在管理界面中配置 API Key 后方可使用")


async def init_database() -> None:
    """初始化数据库"""
    print("=" * 50)
    print("KnowBase 数据库初始化")
    print("=" * 50)

    # 检查并执行迁移
    print("\n[0/2] 检查数据库迁移状态...")
    check_and_migrate()

    # 创建超级用户
    print("\n[1/2] 创建超级用户...")
    await create_superuser()

    # 创建默认模型配置
    print("\n[2/2] 创建默认模型配置...")
    await create_default_model_configs()

    print("\n" + "=" * 50)
    print("初始化完成！")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(init_database())
