"""
知识库统计与文档可见性辅助函数
"""

from typing import List, Optional
from uuid import UUID

from app.models.document import Document, DocumentStatus
from app.models.knowledge_base import KnowledgeBase
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession


async def refresh_kb_stats(db: AsyncSession, kb_id: UUID) -> None:
    """根据当前激活文档重算知识库 document_count / chunk_count"""
    result = await db.execute(
        select(
            func.count(Document.id),
            func.coalesce(func.sum(Document.chunk_count), 0),
        ).where(
            Document.kb_id == kb_id,
            Document.is_active.is_(True),
            Document.status != DocumentStatus.FAILED,
        )
    )
    doc_count, chunk_count = result.one()
    kb = await db.get(KnowledgeBase, kb_id)
    if kb:
        kb.document_count = int(doc_count or 0)
        kb.chunk_count = int(chunk_count or 0)


async def get_active_document_ids(
    db: AsyncSession, kb_id: UUID
) -> List[str]:
    """获取知识库中当前激活文档 ID 列表（字符串）"""
    result = await db.execute(
        select(Document.id).where(
            Document.kb_id == kb_id,
            Document.is_active.is_(True),
            Document.status == DocumentStatus.COMPLETED,
        )
    )
    return [str(row[0]) for row in result.fetchall()]


async def apply_version_document_visibility(
    db: AsyncSession,
    kb_id: UUID,
    snapshot_document_ids: List[Optional[UUID]],
) -> None:
    """
    按版本快照调整文档可见性（非破坏性）

    - 快照中仍存在的文档 → is_active=True
    - 其余文档 → is_active=False
    - 新上传文档默认 is_active=True，切换回含该文档的版本时会重新激活
    """
    active_ids = {doc_id for doc_id in snapshot_document_ids if doc_id is not None}

    # 先全部设为不可见
    await db.execute(
        update(Document)
        .where(Document.kb_id == kb_id)
        .values(is_active=False)
    )

    if active_ids:
        await db.execute(
            update(Document)
            .where(Document.kb_id == kb_id, Document.id.in_(active_ids))
            .values(is_active=True)
        )
