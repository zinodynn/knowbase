"""
测试配置和 Fixtures
提供测试所需的各种基础设施

使用说明：
1. 集成测试使用真实数据库，每个测试后清理数据
2. 单元测试不需要数据库
3. test_user 和 admin_user fixtures 会自动创建测试用户
"""

import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# 设置测试环境标志
os.environ["TESTING"] = "1"

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.main import app
from app.models.user import User

# 使用主数据库 URL
TEST_DATABASE_URL = settings.DATABASE_URL


# ==================== 事件循环 ====================


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """创建事件循环，供所有异步测试共享"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ==================== 数据库 Fixtures ====================


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """创建测试数据库引擎"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )

    # 确保表结构存在
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    每个测试函数独立的数据库会话
    简单策略：直接使用 session，测试后由清理 fixtures 处理
    """
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    创建测试 HTTP 客户端
    自动注入测试数据库会话
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ==================== 清理 Fixtures ====================

# 记录测试中创建的用户，用于清理
_test_usernames = set()


@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_data(test_engine):
    """
    自动清理测试数据
    在每个测试结束后删除测试创建的用户
    """
    yield

    # 测试结束后清理
    if _test_usernames:
        async_session = async_sessionmaker(
            test_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with async_session() as session:
            for username in list(_test_usernames):
                await session.execute(delete(User).where(User.username == username))
            await session.commit()
        _test_usernames.clear()


# ==================== 用户 Fixtures ====================


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """创建测试普通用户"""
    # 使用唯一用户名避免冲突
    import uuid

    unique_suffix = str(uuid.uuid4())[:8]
    username = f"testuser_{unique_suffix}"

    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # 记录用于清理
    _test_usernames.add(username)

    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """创建测试管理员用户"""
    import uuid

    unique_suffix = str(uuid.uuid4())[:8]
    username = f"admin_{unique_suffix}"

    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash("admin123"),
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # 记录用于清理
    _test_usernames.add(username)

    return user


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, test_user: User) -> dict:
    """获取认证请求头"""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": test_user.username, "password": "testpass123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_auth_headers(client: AsyncClient, admin_user: User) -> dict:
    """获取管理员认证请求头"""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "admin123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ==================== Mock Fixtures ====================


@pytest.fixture
def mock_redis():
    """Mock Redis 客户端"""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_qdrant():
    """Mock Qdrant 客户端"""
    mock = MagicMock()
    mock.search = AsyncMock(return_value=[])
    mock.upsert = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_minio():
    """Mock MinIO 客户端"""
    mock = MagicMock()
    mock.put_object = MagicMock(return_value=None)
    mock.get_object = MagicMock()
    return mock
