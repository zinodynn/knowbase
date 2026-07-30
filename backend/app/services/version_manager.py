"""
版本管理服务

提供知识库版本快照创建、版本切换、版本对比等功能。
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.models.document import Chunk, Document, DocumentStatus
from app.models.knowledge_base import KnowledgeBase
from app.models.vcs import KBVersion
from app.models.version_snapshot import VersionSnapshot
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
settings = get_settings()


class VersionManager:
    """知识库版本管理服务"""

    def __init__(self, db: AsyncSession):
        """
        初始化版本管理器

        Args:
            db: 数据库会话
        """
        self.db = db

    async def create_snapshot(
        self,
        kb_id: uuid.UUID,
        description: str,
        created_by: Optional[uuid.UUID] = None,
        tags: Optional[str] = None,
    ) -> KBVersion:
        """
        创建版本快照

        1. 获取知识库当前所有文档和分块信息
        2. 将当前激活版本设为非激活
        3. 创建新的 KBVersion 记录
        4. 为每个文档创建 VersionSnapshot 记录
        5. 更新知识库的 version 计数

        Args:
            kb_id: 知识库 ID
            description: 版本描述
            created_by: 创建者用户 ID
            tags: 版本标签

        Returns:
            创建的 KBVersion 实例
        """
        # 1. 获取知识库当前所有文档
        kb = await self.db.get(KnowledgeBase, kb_id)
        if not kb:
            raise ValueError(f"知识库不存在: {kb_id}")

        documents_result = await self.db.execute(
            select(Document).where(
                and_(
                    Document.kb_id == kb_id,
                    Document.status != DocumentStatus.FAILED,
                    Document.is_active == True,
                )
            )
        )
        documents = documents_result.scalars().all()

        # 2. 获取激活文档的分块信息
        active_doc_ids = [doc.id for doc in documents]
        if active_doc_ids:
            chunks_result = await self.db.execute(
                select(Chunk).where(Chunk.document_id.in_(active_doc_ids))
            )
            chunks = chunks_result.scalars().all()
        else:
            chunks = []

        # 按 document_id 组织分块
        chunks_by_doc: Dict[uuid.UUID, List[Dict[str, Any]]] = {}
        for chunk in chunks:
            if chunk.document_id not in chunks_by_doc:
                chunks_by_doc[chunk.document_id] = []
            chunks_by_doc[chunk.document_id].append({
                "id": str(chunk.id),
                "index": chunk.chunk_index,
                "vector_id": chunk.vector_id,
            })

        # 3. 计算下一个版本号
        max_version_result = await self.db.execute(
            select(func.max(KBVersion.version)).where(KBVersion.kb_id == kb_id)
        )
        max_version = max_version_result.scalar() or 0
        new_version_number = max_version + 1

        # 4. 将当前激活版本设为非激活
        await self.db.execute(
            update(KBVersion)
            .where(and_(KBVersion.kb_id == kb_id, KBVersion.is_active == True))
            .values(is_active=False)
        )

        # 5. 构建快照摘要数据
        snapshot_data = {
            "version": new_version_number,
            "description": description,
            "document_count": len(documents),
            "total_chunks": len(chunks),
            "document_ids": [str(doc.id) for doc in documents],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # 6. 创建新的 KBVersion 记录
        new_version = KBVersion(
            kb_id=kb_id,
            version=new_version_number,
            description=description,
            document_count=len(documents),
            chunk_count=len(chunks),
            created_by=created_by,
            snapshot_data=snapshot_data,
            is_active=True,
            tags=tags,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(new_version)
        await self.db.flush()

        # 7. 为每个文档创建 VersionSnapshot 记录
        for doc in documents:
            doc_chunks = chunks_by_doc.get(doc.id, [])
            snapshot = VersionSnapshot(
                version_id=new_version.id,
                document_id=doc.id,
                document_snapshot={
                    "file_name": doc.file_name,
                    "file_type": doc.file_type,
                    "file_size": doc.file_size,
                    "content_hash": doc.content_hash,
                    "chunk_count": doc.chunk_count,
                    "status": doc.status.value if doc.status else "completed",
                    "source_type": doc.source_type.value if doc.source_type else "upload",
                    "description": doc.description,
                    "storage_path": doc.storage_path,
                    "doc_metadata": doc.doc_metadata,
                    "version": doc.version,
                },
                chunk_ids=[c["id"] for c in doc_chunks],
            )
            self.db.add(snapshot)

        # 8. 更新知识库版本计数
        kb.version = new_version_number
        kb.chunk_count = len(chunks)
        kb.document_count = len(documents)

        await self.db.flush()
        logger.info(
            f"创建版本快照成功: kb_id={kb_id}, version={new_version_number}, "
            f"documents={len(documents)}, chunks={len(chunks)}"
        )

        return new_version

    async def list_versions(
        self,
        kb_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[KBVersion], int]:
        """
        获取知识库版本列表（分页）

        Args:
            kb_id: 知识库 ID
            page: 页码（从1开始）
            page_size: 每页数量

        Returns:
            (版本列表, 总数)
        """
        # 总数
        count_result = await self.db.execute(
            select(func.count(KBVersion.id)).where(KBVersion.kb_id == kb_id)
        )
        total = count_result.scalar() or 0

        # 分页查询
        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(KBVersion)
            .where(KBVersion.kb_id == kb_id)
            .order_by(KBVersion.version.desc())
            .offset(offset)
            .limit(page_size)
        )
        versions = result.scalars().all()

        return list(versions), total

    async def get_version_detail(self, version_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        获取版本详情（含快照内容）

        Args:
            version_id: 版本 ID

        Returns:
            版本详情字典，包含快照列表
        """
        version = await self.db.get(KBVersion, version_id)
        if not version:
            return None

        # 获取快照列表
        snapshots_result = await self.db.execute(
            select(VersionSnapshot).where(VersionSnapshot.version_id == version_id)
        )
        snapshots = snapshots_result.scalars().all()

        return {
            "id": str(version.id),
            "kb_id": str(version.kb_id),
            "version": version.version,
            "description": version.description,
            "commit_hash": version.commit_hash,
            "document_count": version.document_count,
            "chunk_count": version.chunk_count,
            "is_active": version.is_active,
            "tags": version.tags,
            "snapshot_data": version.snapshot_data,
            "created_by": str(version.created_by) if version.created_by else None,
            "created_at": version.created_at.isoformat() if version.created_at else None,
            "snapshots": [
                {
                    "id": str(s.id),
                    "document_id": str(s.document_id) if s.document_id else None,
                    "document_snapshot": s.document_snapshot,
                    "chunk_ids": s.chunk_ids or [],
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in snapshots
            ],
        }

    async def switch_version(self, version_id: uuid.UUID) -> KBVersion:
        """
        切换到指定版本（非破坏性）

        1. 切换 is_active 版本标记
        2. 按快照调整文档 is_active 可见性（不删文档/向量）
        3. 更新知识库统计信息

        说明：快照创建后已物理删除的文档无法恢复（FK SET NULL）。
        """
        from app.services.kb_stats import (
            apply_version_document_visibility,
            refresh_kb_stats,
        )

        # 1. 验证目标版本存在
        target_version = await self.db.get(KBVersion, version_id)
        if not target_version:
            raise ValueError(f"版本不存在: {version_id}")

        kb_id = target_version.kb_id

        # 2. 将所有当前激活版本设为非激活
        await self.db.execute(
            update(KBVersion)
            .where(
                and_(
                    KBVersion.kb_id == kb_id,
                    KBVersion.is_active == True,
                    KBVersion.id != version_id,
                )
            )
            .values(is_active=False)
        )

        # 3. 将目标版本设为激活
        target_version.is_active = True

        # 4. 按快照调整文档可见性
        snapshots_result = await self.db.execute(
            select(VersionSnapshot).where(VersionSnapshot.version_id == version_id)
        )
        snapshots = snapshots_result.scalars().all()
        await apply_version_document_visibility(
            self.db,
            kb_id,
            [s.document_id for s in snapshots],
        )

        # 5. 更新知识库统计信息
        kb = await self.db.get(KnowledgeBase, kb_id)
        if kb:
            kb.version = target_version.version
        await refresh_kb_stats(self.db, kb_id)

        await self.db.flush()
        logger.info(
            f"版本切换成功（非破坏性）: kb_id={kb_id}, "
            f"to_version={target_version.version}, "
            f"snapshot_docs={len(snapshots)}"
        )

        return target_version

    async def delete_version(self, version_id: uuid.UUID) -> bool:
        """
        删除指定版本（不可删除当前激活版本）

        Args:
            version_id: 版本 ID

        Returns:
            是否删除成功
        """
        version = await self.db.get(KBVersion, version_id)
        if not version:
            raise ValueError(f"版本不存在: {version_id}")

        if version.is_active:
            raise ValueError("不能删除当前激活的版本，请先切换到其他版本")

        await self.db.delete(version)
        await self.db.flush()

        logger.info(f"版本删除成功: version_id={version_id}, version={version.version}")
        return True

    async def compare_versions(
        self,
        version_id_1: uuid.UUID,
        version_id_2: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        对比两个版本的差异

        Args:
            version_id_1: 版本1 ID
            version_id_2: 版本2 ID

        Returns:
            差异对比结果，包含 added_docs, removed_docs, modified_docs
        """
        v1 = await self.db.get(KBVersion, version_id_1)
        v2 = await self.db.get(KBVersion, version_id_2)

        if not v1:
            raise ValueError(f"版本不存在: {version_id_1}")
        if not v2:
            raise ValueError(f"版本不存在: {version_id_2}")

        # 获取版本1的快照
        snapshots1_result = await self.db.execute(
            select(VersionSnapshot).where(VersionSnapshot.version_id == version_id_1)
        )
        snapshots1 = snapshots1_result.scalars().all()

        # 获取版本2的快照
        snapshots2_result = await self.db.execute(
            select(VersionSnapshot).where(VersionSnapshot.version_id == version_id_2)
        )
        snapshots2 = snapshots2_result.scalars().all()

        # 构建文档映射
        docs1 = {
            str(s.document_id): s.document_snapshot
            for s in snapshots1
            if s.document_id
        }
        docs2 = {
            str(s.document_id): s.document_snapshot
            for s in snapshots2
            if s.document_id
        }

        doc_ids1 = set(docs1.keys())
        doc_ids2 = set(docs2.keys())

        # 新增的文档（在 v2 中但不在 v1 中）
        added_docs = [
            {"document_id": did, "file_name": docs2[did].get("file_name", "unknown")}
            for did in (doc_ids2 - doc_ids1)
        ]

        # 删除的文档（在 v1 中但不在 v2 中）
        removed_docs = [
            {"document_id": did, "file_name": docs1[did].get("file_name", "unknown")}
            for did in (doc_ids1 - doc_ids2)
        ]

        # 修改的文档（在两个版本中都存在但内容哈希不同）
        modified_docs = []
        for did in doc_ids1 & doc_ids2:
            hash1 = docs1[did].get("content_hash")
            hash2 = docs2[did].get("content_hash")
            if hash1 != hash2:
                modified_docs.append({
                    "document_id": did,
                    "file_name": docs1[did].get("file_name", "unknown"),
                    "old_hash": hash1,
                    "new_hash": hash2,
                })

        return {
            "version_1": {
                "id": str(v1.id),
                "version": v1.version,
                "description": v1.description,
                "document_count": v1.document_count,
                "chunk_count": v1.chunk_count,
            },
            "version_2": {
                "id": str(v2.id),
                "version": v2.version,
                "description": v2.description,
                "document_count": v2.document_count,
                "chunk_count": v2.chunk_count,
            },
            "added_docs": added_docs,
            "removed_docs": removed_docs,
            "modified_docs": modified_docs,
            "summary": {
                "added_count": len(added_docs),
                "removed_count": len(removed_docs),
                "modified_count": len(modified_docs),
                "total_changes": len(added_docs) + len(removed_docs) + len(modified_docs),
            },
        }

    async def _delete_vectors_from_store(
        self, kb_id: uuid.UUID, vector_ids: List[str]
    ) -> None:
        """
        从向量数据库删除指定向量

        Args:
            kb_id: 知识库 ID
            vector_ids: 向量 ID 列表
        """
        if not vector_ids:
            return

        try:
            from app.services.vector_store.base import VectorStoreConfig
            from app.services.vector_store.qdrant_store import QdrantVectorStore

            config = VectorStoreConfig(
                host=settings.QDRANT_HOST or "localhost",
                port=settings.QDRANT_PORT or 6333,
                api_key=settings.QDRANT_API_KEY,
            )
            store = QdrantVectorStore(config)
            collection_name = store.get_collection_name(str(kb_id))
            await store.delete_vectors(collection_name, vector_ids)
        except Exception as e:
            logger.warning(f"向量数据库操作失败: {e}")
