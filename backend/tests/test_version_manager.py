"""
版本管理服务单元测试
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


class TestVersionManager:
    """VersionManager 单元测试"""

    @pytest.fixture
    def mock_db(self):
        """创建模拟的数据库会话"""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.get = AsyncMock()
        session.add = MagicMock()
        session.delete = AsyncMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def manager(self, mock_db):
        """创建 VersionManager 实例"""
        from app.services.version_manager import VersionManager
        return VersionManager(mock_db)

    def test_create_manager(self, manager):
        """测试 VersionManager 初始化"""
        assert manager is not None
        assert manager.db is not None

    async def test_list_versions_empty(self, manager, mock_db):
        """测试获取空知识库的版本列表"""
        kb_id = uuid.uuid4()

        # 模拟返回空结果
        mock_db.execute.side_effect = [
            AsyncMock(scalar=MagicMock(return_value=0)),  # count result
            AsyncMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),  # versions result
        ]

        versions, total = await manager.list_versions(kb_id)
        assert total == 0
        assert len(versions) == 0

    async def test_list_versions_with_data(self, manager, mock_db):
        """测试获取有版本的列表"""
        kb_id = uuid.uuid4()
        mock_version = MagicMock()
        mock_version.id = uuid.uuid4()
        mock_version.version = 1
        mock_version.description = "测试版本"
        mock_version.document_count = 5
        mock_version.chunk_count = 20
        mock_version.is_active = True
        mock_version.tags = "v1.0"
        mock_version.created_by = uuid.uuid4()
        mock_version.created_at = None

        mock_db.execute.side_effect = [
            AsyncMock(scalar=MagicMock(return_value=1)),  # count result
            AsyncMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_version])))),  # versions
        ]

        versions, total = await manager.list_versions(kb_id)
        assert total == 1
        assert len(versions) == 1
        assert versions[0].version == 1
        assert versions[0].description == "测试版本"

    async def test_get_version_detail_not_found(self, manager, mock_db):
        """测试获取不存在的版本详情"""
        version_id = uuid.uuid4()
        mock_db.get.return_value = None

        detail = await manager.get_version_detail(version_id)
        assert detail is None

    async def test_compare_versions(self, manager, mock_db):
        """测试版本对比"""
        v1_id = uuid.uuid4()
        v2_id = uuid.uuid4()

        # 模拟两个版本
        mock_v1 = MagicMock()
        mock_v1.id = v1_id
        mock_v1.version = 1
        mock_v1.description = "版本1"
        mock_v1.document_count = 3
        mock_v1.chunk_count = 10

        mock_v2 = MagicMock()
        mock_v2.id = v2_id
        mock_v2.version = 2
        mock_v2.description = "版本2"
        mock_v2.document_count = 5
        mock_v2.chunk_count = 15

        mock_db.get.side_effect = [mock_v1, mock_v2]

        # 模拟快照
        mock_s1 = MagicMock()
        mock_s1.document_id = uuid.uuid4()
        mock_s1.document_snapshot = {"file_name": "doc1.pdf", "content_hash": "hash1"}
        mock_s1.chunk_ids = ["chunk1"]

        mock_s2 = MagicMock()
        mock_s2.document_id = uuid.uuid4()
        mock_s2.document_snapshot = {"file_name": "doc2.pdf", "content_hash": "hash2"}

        mock_db.execute.side_effect = [
            AsyncMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_s1])))),
            AsyncMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_s2])))),
        ]

        result = await manager.compare_versions(v1_id, v2_id)
        assert result is not None
        assert "version_1" in result
        assert "version_2" in result
        assert "added_docs" in result
        assert "removed_docs" in result
        assert "modified_docs" in result
        assert "summary" in result
        assert result["version_1"]["version"] == 1
        assert result["version_2"]["version"] == 2

    async def test_delete_version_not_found(self, manager, mock_db):
        """测试删除不存在的版本"""
        version_id = uuid.uuid4()
        mock_db.get.return_value = None

        with pytest.raises(ValueError, match="版本不存在"):
            await manager.delete_version(version_id)

    async def test_delete_active_version(self, manager, mock_db):
        """测试删除当前激活版本（应失败）"""
        version_id = uuid.uuid4()
        mock_version = MagicMock()
        mock_version.id = version_id
        mock_version.is_active = True
        mock_db.get.return_value = mock_version

        with pytest.raises(ValueError, match="不能删除当前激活的版本"):
            await manager.delete_version(version_id)

    async def test_delete_version_success(self, manager, mock_db):
        """测试成功删除非激活版本"""
        version_id = uuid.uuid4()
        mock_version = MagicMock()
        mock_version.id = version_id
        mock_version.is_active = False
        mock_version.version = 2
        mock_db.get.return_value = mock_version

        result = await manager.delete_version(version_id)
        assert result is True
        mock_db.delete.assert_called_once_with(mock_version)


class TestVersionSnapshot:
    """VersionSnapshot 模型测试"""

    def test_snapshot_creation(self):
        """测试 VersionSnapshot 模型字段"""
        from app.models.version_snapshot import VersionSnapshot

        assert hasattr(VersionSnapshot, '__tablename__')
        assert VersionSnapshot.__tablename__ == 'version_snapshots'

    def test_snapshot_fields(self):
        """测试 VersionSnapshot 必需的字段"""
        from app.models.version_snapshot import VersionSnapshot
        from sqlalchemy.orm import Mapped

        columns = VersionSnapshot.__table__.columns
        column_names = [c.name for c in columns]

        assert 'id' in column_names
        assert 'version_id' in column_names
        assert 'document_id' in column_names
        assert 'document_snapshot' in column_names
        assert 'chunk_ids' in column_names
        assert 'created_at' in column_names


class TestKBVersionExtended:
    """KBVersion 扩展字段测试"""

    def test_new_fields_exist(self):
        """测试 KBVersion 包含新字段"""
        from app.models.vcs import KBVersion

        columns = KBVersion.__table__.columns
        column_names = [c.name for c in columns]

        assert 'snapshot_data' in column_names, "snapshot_data 字段缺失"
        assert 'is_active' in column_names, "is_active 字段缺失"
        assert 'tags' in column_names, "tags 字段缺失"


class TestVersionSchemas:
    """Pydantic Schema 测试"""

    def test_version_create_schema(self):
        """测试 VersionCreate Schema"""
        from app.schemas.version import VersionCreate

        data = VersionCreate(description="测试版本", tags="v1.0")
        assert data.description == "测试版本"
        assert data.tags == "v1.0"

    def test_version_create_minimal(self):
        """测试 VersionCreate 最小字段"""
        from app.schemas.version import VersionCreate

        data = VersionCreate(description="最小版本")
        assert data.description == "最小版本"
        assert data.tags is None

    def test_version_response_schema(self):
        """测试 VersionResponse Schema"""
        from app.schemas.version import VersionResponse

        resp = VersionResponse(
            id="test-id",
            kb_id="kb-id",
            version=1,
            description="测试",
            document_count=5,
            chunk_count=10,
            is_active=True,
            tags="v1.0",
        )
        assert resp.version == 1
        assert resp.is_active is True

    def test_version_compare_response(self):
        """测试 VersionCompareResponse Schema"""
        from app.schemas.version import (
            VersionCompareResponse,
            VersionCompareVersionInfo,
            VersionCompareSummary,
        )

        resp = VersionCompareResponse(
            version_1=VersionCompareVersionInfo(
                id="v1", version=1, document_count=3, chunk_count=5
            ),
            version_2=VersionCompareVersionInfo(
                id="v2", version=2, document_count=5, chunk_count=8
            ),
            added_docs=[],
            removed_docs=[],
            modified_docs=[],
            summary=VersionCompareSummary(
                added_count=0, removed_count=0, modified_count=0, total_changes=0
            ),
        )
        assert resp.version_1.version == 1
        assert resp.version_2.version == 2
        assert resp.summary.total_changes == 0
