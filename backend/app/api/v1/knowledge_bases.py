"""
知识库管理路由
"""

import uuid
from typing import Any, List, Optional

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.knowledge_base import KBTag, KBVisibility, KnowledgeBase
from app.models.permission import UserKBPermission
from app.models.user import User
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseListResponse,
    KnowledgeBaseResponse,
    KnowledgeBaseStats,
    KnowledgeBaseUpdate,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


async def check_kb_permission(
    kb_id: uuid.UUID, user: User, db: AsyncSession, required_permission: str = "read"
) -> KnowledgeBase:
    """
    检查用户对知识库的权限

    Args:
        kb_id: 知识库 ID
        user: 当前用户
        db: 数据库会话
        required_permission: 所需权限 (read, write, admin)

    Returns:
        KnowledgeBase: 知识库对象

    Raises:
        HTTPException: 无权限或不存在时抛出
    """
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在"
        )

    # 超级用户拥有所有权限
    if user.is_superuser:
        return kb

    # 所有者拥有所有权限
    if kb.owner_id == user.id:
        return kb

    # 公开知识库允许读取
    if kb.visibility == KBVisibility.PUBLIC and required_permission == "read":
        return kb

    # 检查用户权限
    result = await db.execute(
        select(UserKBPermission).where(
            UserKBPermission.user_id == user.id, UserKBPermission.kb_id == kb_id
        )
    )
    permission = result.scalar_one_or_none()

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此知识库"
        )

    # 权限等级检查
    permission_levels = {"read": 1, "write": 2, "admin": 3}
    # 如果 permission.permission 是枚举，获取其 value
    perm_value = (
        permission.permission.value
        if hasattr(permission.permission, "value")
        else permission.permission
    )
    if permission_levels.get(perm_value, 0) < permission_levels.get(
        required_permission, 0
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")

    return kb


@router.get("", response_model=KnowledgeBaseListResponse, summary="获取知识库列表")
async def list_knowledge_bases(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="获取数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    include_public: bool = Query(True, description="是否包含公开知识库"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    获取当前用户可访问的知识库列表

    包含：
    - 用户自己创建的知识库
    - 被授权访问的知识库
    - 公开的知识库（如果 include_public=True）
    """
    # 构建查询条件
    conditions = []

    # 自己的知识库
    conditions.append(KnowledgeBase.owner_id == current_user.id)

    # 被授权的知识库
    subquery = select(UserKBPermission.kb_id).where(
        UserKBPermission.user_id == current_user.id
    )
    conditions.append(KnowledgeBase.id.in_(subquery))

    # 公开知识库
    if include_public:
        conditions.append(KnowledgeBase.visibility == KBVisibility.PUBLIC)

    # 基础查询
    query = select(KnowledgeBase).where(or_(*conditions))

    # 搜索过滤
    if search:
        query = query.where(
            or_(
                KnowledgeBase.name.ilike(f"%{search}%"),
                KnowledgeBase.description.ilike(f"%{search}%"),
            )
        )

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar()

    # 获取列表
    query = query.offset(skip).limit(limit).order_by(KnowledgeBase.updated_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()

    return KnowledgeBaseListResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=KnowledgeBaseResponse, summary="创建知识库")
async def create_knowledge_base(
    kb_in: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    创建新知识库
    """
    # 创建知识库
    kb = KnowledgeBase(
        name=kb_in.name,
        description=kb_in.description,
        visibility=kb_in.visibility,
        embedding_model_info={
            "model": kb_in.embedding_model,
            "dimension": kb_in.embedding_dimension,
        },
        owner_id=current_user.id,
        document_count=0,
        chunk_count=0,
    )

    db.add(kb)
    await db.flush()  # 获取 ID

    # 添加标签
    if kb_in.tags:
        for tag_name in kb_in.tags:
            tag = KBTag(kb_id=kb.id, tag_name=tag_name)
            db.add(tag)

    await db.commit()
    await db.refresh(kb)

    return kb


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse, summary="获取知识库详情")
async def get_knowledge_base(
    kb_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取知识库详情"""
    kb = await check_kb_permission(kb_id, current_user, db, "read")
    return kb


@router.put("/{kb_id}", response_model=KnowledgeBaseResponse, summary="更新知识库")
async def update_knowledge_base(
    kb_id: uuid.UUID,
    kb_in: KnowledgeBaseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """更新知识库信息"""
    kb = await check_kb_permission(kb_id, current_user, db, "admin")

    # 更新基本字段
    update_data = kb_in.model_dump(exclude_unset=True, exclude={"tags"})
    for field, value in update_data.items():
        setattr(kb, field, value)

    # 更新标签
    if kb_in.tags is not None:
        # 删除旧标签
        await db.execute(select(KBTag).where(KBTag.kb_id == kb_id))
        result = await db.execute(select(KBTag).where(KBTag.kb_id == kb_id))
        old_tags = result.scalars().all()
        for tag in old_tags:
            await db.delete(tag)

        # 添加新标签
        for tag_name in kb_in.tags:
            tag = KBTag(kb_id=kb.id, tag_name=tag_name)
            db.add(tag)

    await db.commit()
    await db.refresh(kb)

    return kb


@router.delete("/{kb_id}", summary="删除知识库")
async def delete_knowledge_base(
    kb_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    删除知识库

    注意：只有所有者和超级管理员可以删除知识库
    """
    kb = await check_kb_permission(kb_id, current_user, db, "admin")

    # 非超级用户只能删除自己的知识库
    if not current_user.is_superuser and kb.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="只有所有者可以删除知识库"
        )

    await db.delete(kb)
    await db.commit()

    return {"message": "知识库已删除"}


@router.get(
    "/{kb_id}/stats", response_model=KnowledgeBaseStats, summary="获取知识库统计"
)
async def get_knowledge_base_stats(
    kb_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取知识库统计信息"""
    from app.models.document import Document

    kb = await check_kb_permission(kb_id, current_user, db, "read")

    # 获取文档总大小
    result = await db.execute(
        select(func.sum(Document.file_size)).where(Document.kb_id == kb_id)
    )
    total_size = result.scalar() or 0

    # 获取最后更新时间
    result = await db.execute(
        select(Document.updated_at)
        .where(Document.kb_id == kb_id)
        .order_by(Document.updated_at.desc())
        .limit(1)
    )
    last_doc = result.scalar_one_or_none()

    return KnowledgeBaseStats(
        document_count=kb.document_count,
        total_chunks=kb.chunk_count,
        total_size_bytes=total_size,
        last_updated=last_doc,
    )
