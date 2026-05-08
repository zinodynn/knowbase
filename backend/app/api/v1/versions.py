"""
版本管理 API 路由

提供知识库版本快照创建、列表、切换、删除、对比等接口。
"""

import uuid
from typing import Optional

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User
from app.schemas.version import (
    VersionCompareResponse,
    VersionCreate,
    VersionDetailResponse,
    VersionListResponse,
    VersionResponse,
)
from app.services.version_manager import VersionManager
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


async def check_kb_exists(
    kb_id: uuid.UUID, db: AsyncSession
) -> KnowledgeBase:
    """验证知识库存在"""
    from sqlalchemy import select

    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在"
        )
    return kb


@router.post(
    "/knowledge-bases/{kb_id}/versions",
    response_model=VersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建版本快照",
)
async def create_snapshot(
    kb_id: uuid.UUID,
    body: VersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    为知识库创建版本快照

    保存当前所有文档和分块的元信息，生成新的版本号。
    """
    await check_kb_exists(kb_id, db)

    manager = VersionManager(db)
    try:
        version = await manager.create_snapshot(
            kb_id=kb_id,
            description=body.description,
            created_by=current_user.id,
            tags=body.tags,
        )
        await db.commit()

        return VersionResponse(
            id=str(version.id),
            kb_id=str(version.kb_id),
            version=version.version,
            description=version.description,
            document_count=version.document_count,
            chunk_count=version.chunk_count,
            is_active=version.is_active,
            tags=version.tags,
            created_by=str(version.created_by) if version.created_by else None,
            created_at=version.created_at.isoformat() if version.created_at else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/knowledge-bases/{kb_id}/versions",
    response_model=VersionListResponse,
    summary="获取版本列表",
)
async def list_versions(
    kb_id: uuid.UUID,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取知识库的版本列表（分页）
    """
    await check_kb_exists(kb_id, db)

    manager = VersionManager(db)
    versions, total = await manager.list_versions(kb_id, page, page_size)

    items = [
        VersionResponse(
            id=str(v.id),
            kb_id=str(v.kb_id),
            version=v.version,
            description=v.description,
            document_count=v.document_count,
            chunk_count=v.chunk_count,
            is_active=v.is_active,
            tags=v.tags,
            created_by=str(v.created_by) if v.created_by else None,
            created_at=v.created_at.isoformat() if v.created_at else None,
        )
        for v in versions
    ]

    return VersionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/versions/{version_id}",
    response_model=VersionDetailResponse,
    summary="获取版本详情",
)
async def get_version_detail(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取版本详情（含快照内容）
    """
    manager = VersionManager(db)
    detail = await manager.get_version_detail(version_id)

    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="版本不存在"
        )

    return VersionDetailResponse(**detail)


@router.post(
    "/versions/{version_id}/switch",
    response_model=VersionResponse,
    summary="切换版本",
)
async def switch_version(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    切换到指定版本

    会将当前知识库的文档和分块状态恢复到目标版本的快照状态。
    """
    manager = VersionManager(db)
    try:
        version = await manager.switch_version(version_id)
        await db.commit()

        return VersionResponse(
            id=str(version.id),
            kb_id=str(version.kb_id),
            version=version.version,
            description=version.description,
            document_count=version.document_count,
            chunk_count=version.chunk_count,
            is_active=version.is_active,
            tags=version.tags,
            created_by=str(version.created_by) if version.created_by else None,
            created_at=version.created_at.isoformat() if version.created_at else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/versions/{version_id}",
    response_model=dict,
    summary="删除版本",
)
async def delete_version(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除指定版本（不可删除当前激活版本）
    """
    manager = VersionManager(db)
    try:
        await manager.delete_version(version_id)
        await db.commit()
        return {"success": True, "message": "版本已删除"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/versions/compare",
    response_model=VersionCompareResponse,
    summary="版本对比",
)
async def compare_versions(
    v1: uuid.UUID = Query(..., description="版本1 ID"),
    v2: uuid.UUID = Query(..., description="版本2 ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    对比两个版本的差异

    返回新增文档、删除文档、修改文档列表。
    """
    manager = VersionManager(db)
    try:
        result = await manager.compare_versions(v1, v2)
        return VersionCompareResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
