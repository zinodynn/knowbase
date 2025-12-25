"""
认证 API 测试
测试登录、注册、Token 刷新等功能
"""

import uuid

import pytest
from app.models.user import User
from httpx import AsyncClient


class TestAuthRegister:
    """注册功能测试"""

    @pytest.mark.asyncio
    @pytest.mark.auth
    async def test_register_success(self, client: AsyncClient):
        """测试正常注册"""
        unique_id = str(uuid.uuid4())[:8]
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": f"newuser_{unique_id}",
                "email": f"newuser_{unique_id}@example.com",
                "password": "password123",
                "full_name": "New User",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == f"newuser_{unique_id}"
        assert data["email"] == f"newuser_{unique_id}@example.com"
        assert "id" in data
        assert "hashed_password" not in data  # 不应返回密码

    @pytest.mark.asyncio
    @pytest.mark.auth
    async def test_register_duplicate_username(
        self, client: AsyncClient, test_user: User
    ):
        """测试重复用户名注册"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": test_user.username,  # 使用已存在的用户名
                "email": "another@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 400
        assert "已被使用" in response.json()["detail"]

    @pytest.mark.asyncio
    @pytest.mark.auth
    async def test_register_invalid_email(self, client: AsyncClient):
        """测试无效邮箱格式"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": f"user_{uuid.uuid4().hex[:8]}",
                "email": "invalid-email",
                "password": "password123",
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    @pytest.mark.auth
    async def test_register_short_password(self, client: AsyncClient):
        """测试密码太短"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": f"user_{uuid.uuid4().hex[:8]}",
                "email": f"user_{uuid.uuid4().hex[:8]}@example.com",
                "password": "123",  # 太短
            },
        )

        assert response.status_code == 422


class TestAuthLogin:
    """登录功能测试"""

    @pytest.mark.asyncio
    @pytest.mark.auth
    async def test_login_success(self, client: AsyncClient, test_user: User):
        """测试正常登录"""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": test_user.username, "password": "testpass123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    @pytest.mark.asyncio
    @pytest.mark.auth
    async def test_login_with_email(self, client: AsyncClient, test_user: User):
        """测试使用邮箱登录"""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": test_user.email, "password": "testpass123"},
        )

        assert response.status_code == 200
        assert "access_token" in response.json()

    @pytest.mark.asyncio
    @pytest.mark.auth
    async def test_login_wrong_password(self, client: AsyncClient, test_user: User):
        """测试错误密码"""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": test_user.username, "password": "wrongpassword"},
        )

        assert response.status_code == 401
        assert "密码错误" in response.json()["detail"]

    @pytest.mark.asyncio
    @pytest.mark.auth
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """测试不存在的用户"""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent_user_xyz", "password": "password123"},
        )

        assert response.status_code == 401


class TestAuthMe:
    """获取当前用户信息测试"""

    @pytest.mark.asyncio
    @pytest.mark.auth
    async def test_get_me_success(
        self, client: AsyncClient, test_user: User, auth_headers: dict
    ):
        """测试获取当前用户信息"""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email

    @pytest.mark.asyncio
    @pytest.mark.auth
    async def test_get_me_no_token(self, client: AsyncClient):
        """测试无 Token 访问"""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.auth
    async def test_get_me_invalid_token(self, client: AsyncClient):
        """测试无效 Token"""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401


class TestAuthRefresh:
    """Token 刷新测试"""

    @pytest.mark.asyncio
    @pytest.mark.auth
    async def test_refresh_token_success(self, client: AsyncClient, test_user: User):
        """测试正常刷新 Token"""
        # 先登录获取 refresh_token
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": test_user.username, "password": "testpass123"},
        )
        assert (
            login_response.status_code == 200
        ), f"Login failed: {login_response.json()}"
        refresh_token = login_response.json()["refresh_token"]

        # 刷新 Token
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    @pytest.mark.auth
    async def test_refresh_invalid_token(self, client: AsyncClient):
        """测试无效的 refresh_token"""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"},
        )

        assert response.status_code == 401
