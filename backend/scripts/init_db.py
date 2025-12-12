"""
初始化脚本
创建初始超级用户和默认配置
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.core.config import settings
from app.models.user import User
from app.models.model_config import ModelConfig


async def create_superuser(
    username: str = "admin",
    email: str = "admin@example.com",
    password: str = "admin123"
) -> None:
    """创建超级用户"""
    async with AsyncSessionLocal() as db:
        # 检查是否已存在
        result = await db.execute(
            select(User).where(User.username == username)
        )
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
            is_superuser=True
        )
        
        db.add(user)
        await db.commit()
        
        print(f"超级用户 '{username}' 创建成功")
        print(f"  邮箱: {email}")
        print(f"  密码: {password}")
        print("  请登录后立即修改密码！")


async def create_default_model_configs() -> None:
    """创建默认模型配置"""
    async with AsyncSessionLocal() as db:
        # 检查是否已有配置
        result = await db.execute(select(ModelConfig))
        existing = result.scalars().all()
        
        if existing:
            print(f"已存在 {len(existing)} 个模型配置")
            return
        
        # 创建默认 Embedding 配置
        embedding_config = ModelConfig(
            name="OpenAI Embedding",
            model_type="embedding",
            provider="openai",
            model_name="text-embedding-ada-002",
            api_base="https://api.openai.com/v1",
            is_default=True,
            is_active=True,
            extra_params={"dimension": 1536}
        )
        db.add(embedding_config)
        
        # 创建默认 Chat 配置
        chat_config = ModelConfig(
            name="OpenAI GPT-4",
            model_type="chat",
            provider="openai",
            model_name="gpt-4-turbo-preview",
            api_base="https://api.openai.com/v1",
            is_default=True,
            is_active=True,
            extra_params={"max_tokens": 4096, "temperature": 0.7}
        )
        db.add(chat_config)
        
        await db.commit()
        
        print("默认模型配置创建成功:")
        print("  - OpenAI Embedding (text-embedding-ada-002)")
        print("  - OpenAI GPT-4 (gpt-4-turbo-preview)")
        print("  请在管理界面中配置 API Key")


async def init_database() -> None:
    """初始化数据库"""
    print("=" * 50)
    print("KnowBase 数据库初始化")
    print("=" * 50)
    
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
