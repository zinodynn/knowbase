"""
Phase 1 功能检查脚本
验证所有基础组件是否正常工作
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


async def check_config():
    """检查配置加载"""
    print("\n[1/6] 检查配置加载...")
    try:
        from app.core.config import settings

        print(settings)
        print(f"  ✓ 项目名称: {settings.APP_NAME}")
        print(f"  ✓ 环境: {settings.ENVIRONMENT}")
        print(f"  ✓ 数据库URL: {settings.DATABASE_URL[:50]}...")
        return True
    except Exception as e:
        print(f"  ✗ 配置加载失败: {e}")
        return False


async def check_database():
    """检查数据库连接"""
    print("\n[2/6] 检查数据库连接...")
    try:
        # 1. 导入正确的依赖（从数据库模块导入会话工厂，而非 AsyncGenerator）
        from app.core.database import async_session_maker
        from sqlalchemy import text

        # 2. 使用 async_session_maker 创建异步会话（正确的会话获取方式）
        async with async_session_maker() as db:
            result = await db.execute(text("SELECT 1"))
            result.scalar()  # 执行简单查询验证连接
        print("  ✓ PostgreSQL 连接成功")
        return True
    except Exception as e:
        print(f"  ✗ PostgreSQL 连接失败: {e}")
        print("  提示: 请确保 Docker 服务已启动 (docker-compose up -d)")
        return False


async def check_redis():
    """检查 Redis 连接"""
    print("\n[3/6] 检查 Redis 连接...")
    try:
        import redis.asyncio as redis
        from app.core.config import settings

        client = redis.from_url(settings.REDIS_URL, password=settings.REDIS_PASSWORD)
        await client.ping()
        await client.close()
        print("  ✓ Redis 连接成功")
        return True
    except Exception as e:
        print(f"  ✗ Redis 连接失败: {e}")
        return False


async def check_minio():
    """检查 MinIO 连接"""
    print("\n[4/6] 检查 MinIO 连接...")
    try:
        from app.core.config import settings
        from minio import Minio

        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        # 尝试列出 bucket
        buckets = client.list_buckets()
        print(f"  ✓ MinIO 连接成功 (Buckets: {len(buckets)})")
        return True
    except Exception as e:
        print(f"  ✗ MinIO 连接失败: {e}")
        return False


async def check_qdrant():
    """检查 Qdrant 连接"""
    print("\n[5/6] 检查 Qdrant 连接...")
    try:
        from app.core.config import settings
        from qdrant_client import QdrantClient

        client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        # 尝试获取集合列表
        collections = client.get_collections()
        print(f"  ✓ Qdrant 连接成功 (Collections: {len(collections.collections)})")
        return True
    except Exception as e:
        print(f"  ✗ Qdrant 连接失败: {e}")
        return False


async def check_models():
    """检查模型导入"""
    print("\n[6/6] 检查模型导入...")
    try:
        from app.models import (
            ApiKey,
            Chunk,
            Document,
            KBTag,
            KnowledgeBase,
            ModelConfig,
            User,
            UserKBPermission,
        )

        print("  ✓ User 模型")
        print("  ✓ KnowledgeBase 模型")
        print("  ✓ KBTag 模型")
        print("  ✓ Document 模型")
        print("  ✓ Chunk 模型")
        print("  ✓ ApiKey 模型")
        print("  ✓ UserKBPermission 模型")
        print("  ✓ ModelConfig 模型")
        return True
    except Exception as e:
        print(f"  ✗ 模型导入失败: {e}")
        return False


async def main():
    """运行所有检查"""
    print("=" * 60)
    print("KnowBase Phase 1 功能检查")
    print("=" * 60)

    results = []

    results.append(await check_config())
    results.append(await check_database())
    results.append(await check_redis())
    results.append(await check_minio())
    results.append(await check_qdrant())
    results.append(await check_models())

    print("\n" + "=" * 60)
    print("检查结果汇总")
    print("=" * 60)

    checks = ["配置加载", "PostgreSQL", "Redis", "MinIO", "Qdrant", "数据模型"]

    passed = sum(results)
    total = len(results)

    for check, result in zip(checks, results):
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {check}: {status}")

    print(f"\n总计: {passed}/{total} 检查通过")

    if passed == total:
        print("\n🎉 Phase 1 所有组件正常！可以启动服务了。")
        print("\n启动命令:")
        print("  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        print("\nAPI 文档:")
        print("  http://localhost:8000/docs")
    else:
        print("\n⚠️ 部分组件检查失败，请检查配置和服务状态。")
        print("\n常见解决方案:")
        print("  1. 启动 Docker 服务: docker-compose up -d")
        print("  2. 检查 .env 配置文件")
        print("  3. 等待服务完全启动后重试")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
