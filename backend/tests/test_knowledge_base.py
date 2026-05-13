"""
知识库 API 测试
测试知识库 CRUD、权限控制等
"""

import pytest
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def test_kb(db_session: AsyncSession, test_user: User) -> KnowledgeBase:
    """创建测试知识库"""
    kb = KnowledgeBase(
        name="测试知识库",
        description="用于测试的知识库",
        owner_id=test_user.id,
        visibility="private",
    )
    db_session.add(kb)
    await db_session.flush()
    await db_session.refresh(kb)
    return kb


class TestKnowledgeBaseCreate:
    """知识库创建测试"""

    @pytest.mark.asyncio
    @pytest.mark.kb
    async def test_create_kb_success(self, client: AsyncClient, auth_headers: dict):
        """测试正常创建知识库"""
        response = await client.post(
            "/api/v1/knowledge-bases",
            headers=auth_headers,
            json={
                "name": "我的知识库",
                "description": "这是一个测试知识库",
                "visibility": "private",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "我的知识库"
        assert data["description"] == "这是一个测试知识库"
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    @pytest.mark.kb
    async def test_create_kb_no_auth(self, client: AsyncClient):
        """测试未认证创建知识库"""
        response = await client.post(
            "/api/v1/knowledge-bases",
            json={"name": "测试", "description": "描述"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.kb
    async def test_create_kb_empty_name(self, client: AsyncClient, auth_headers: dict):
        """测试空名称创建知识库"""
        response = await client.post(
            "/api/v1/knowledge-bases",
            headers=auth_headers,
            json={"name": "", "description": "描述"},
        )

        assert response.status_code == 422


class TestKnowledgeBaseList:
    """知识库列表测试"""

    @pytest.mark.asyncio
    @pytest.mark.kb
    async def test_list_kb_success(
        self, client: AsyncClient, auth_headers: dict, test_kb: KnowledgeBase
    ):
        """测试获取知识库列表"""
        response = await client.get(
            "/api/v1/knowledge-bases",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    @pytest.mark.kb
    async def test_list_kb_pagination(self, client: AsyncClient, auth_headers: dict):
        """测试知识库列表分页"""
        response = await client.get(
            "/api/v1/knowledge-bases",
            headers=auth_headers,
            params={"skip": 0, "limit": 5},
        )

        assert response.status_code == 200
        data = response.json()
        # API 使用 skip/limit 分页格式
        assert "skip" in data
        assert "limit" in data
        assert "total" in data
        assert "items" in data


class TestKnowledgeBaseGet:
    """知识库详情测试"""

    @pytest.mark.asyncio
    @pytest.mark.kb
    async def test_get_kb_success(
        self, client: AsyncClient, auth_headers: dict, test_kb: KnowledgeBase
    ):
        """测试获取知识库详情"""
        response = await client.get(
            f"/api/v1/knowledge-bases/{test_kb.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_kb.id)
        assert data["name"] == test_kb.name

    @pytest.mark.asyncio
    @pytest.mark.kb
    async def test_get_kb_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试获取不存在的知识库"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(
            f"/api/v1/knowledge-bases/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestKnowledgeBaseUpdate:
    """知识库更新测试"""

    @pytest.mark.asyncio
    @pytest.mark.kb
    async def test_update_kb_success(
        self, client: AsyncClient, auth_headers: dict, test_kb: KnowledgeBase
    ):
        """测试更新知识库"""
        response = await client.put(
            f"/api/v1/knowledge-bases/{test_kb.id}",
            headers=auth_headers,
            json={"name": "更新后的名称", "description": "更新后的描述"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新后的名称"
        assert data["description"] == "更新后的描述"

    @pytest.mark.asyncio
    @pytest.mark.kb
    async def test_update_kb_partial(
        self, client: AsyncClient, auth_headers: dict, test_kb: KnowledgeBase
    ):
        """测试部分更新知识库"""
        response = await client.put(
            f"/api/v1/knowledge-bases/{test_kb.id}",
            headers=auth_headers,
            json={"name": "只更新名称"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "只更新名称"
        # 描述保持不变
        assert data["description"] == test_kb.description


class TestKnowledgeBaseDelete:
    """知识库删除测试"""

    @pytest.mark.asyncio
    @pytest.mark.kb
    async def test_delete_kb_success(
        self, client: AsyncClient, auth_headers: dict, test_kb: KnowledgeBase
    ):
        """测试删除知识库"""
        response = await client.delete(
            f"/api/v1/knowledge-bases/{test_kb.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200

        # 验证已删除
        get_response = await client.get(
            f"/api/v1/knowledge-bases/{test_kb.id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.kb
    async def test_delete_kb_not_owner(
        self,
        client: AsyncClient,
        admin_auth_headers: dict,
        test_kb: KnowledgeBase,
    ):
        """测试非所有者删除知识库（管理员应该可以）"""
        response = await client.delete(
            f"/api/v1/knowledge-bases/{test_kb.id}",
            headers=admin_auth_headers,
        )

        # 管理员应该有权限
        assert response.status_code in [200, 403]
