"""
权限管理路由
"""

import uuid
from typing import Any, List

from app.api.deps import get_current_user
from app.api.v1.knowledge_bases import check_kb_permission
from app.core.database import get_db
from app.models.knowledge_base import KnowledgeBase
from app.models.permission import PermissionLevel, UserKBPermission
from app.models.user import User
from app.schemas.permission import (
    KBPermissionListResponse,
    PermissionCreate,
    PermissionResponse,
    PermissionUpdate,
    PermissionWithUserResponse,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get(
    "/knowledge-bases/{kb_id}/permissions",
    response_model=KBPermissionListResponse,
    summary="获取知识库权限列表",
)
async def list_kb_permissions(
    kb_id: uuid.UUID,
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="获取数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取知识库的所有权限设置"""
    # 检查权限（需要 admin 权限才能查看权限列表）
    await check_kb_permission(kb_id, current_user, db, "admin")

    # 获取总数
    result = await db.execute(
        select(func.count(UserKBPermission.id)).where(UserKBPermission.kb_id == kb_id)
    )
    total = result.scalar()

    # 获取权限列表及用户信息
    result = await db.execute(
        select(UserKBPermission, User.username, User.email)
        .join(User, UserKBPermission.user_id == User.id)
        .where(UserKBPermission.kb_id == kb_id)
        .offset(skip)
        .limit(limit)
        .order_by(UserKBPermission.created_at.desc())
    )
    rows = result.all()

    items = []
    for perm, username, email in rows:
        items.append(
            PermissionWithUserResponse(
                id=perm.id,
                user_id=perm.user_id,
                kb_id=perm.kb_id,
                permission=perm.permission,
                created_at=perm.created_at,
                updated_at=perm.updated_at,
                username=username,
                email=email,
            )
        )

    return KBPermissionListResponse(items=items, total=total)


@router.post(
    "/knowledge-bases/{kb_id}/permissions",
    response_model=PermissionResponse,
    summary="添加知识库权限",
)
async def create_kb_permission(
    kb_id: uuid.UUID,
    perm_in: PermissionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """为用户添加知识库权限"""
    # 检查权限（需要 admin 权限）
    kb = await check_kb_permission(kb_id, current_user, db, "admin")

    # 检查目标用户是否存在
    result = await db.execute(select(User).where(User.id == perm_in.user_id))
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="目标用户不存在"
        )

    # 不能给所有者添加权限
    if target_user.id == kb.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="不能给知识库所有者添加权限"
        )

    # 检查是否已存在权限
    result = await db.execute(
        select(UserKBPermission).where(
            UserKBPermission.user_id == perm_in.user_id, UserKBPermission.kb_id == kb_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已有此知识库的权限，请使用更新接口",
        )

    # 创建权限

    permission = UserKBPermission(
        user_id=perm_in.user_id,
        kb_id=kb_id,
        permission=PermissionLevel(perm_in.permission),
    )

    db.add(permission)
    await db.commit()
    await db.refresh(permission)

    return permission


@router.put(
    "/knowledge-bases/{kb_id}/permissions/{user_id}",
    response_model=PermissionResponse,
    summary="更新知识库权限",
)
async def update_kb_permission(
    kb_id: uuid.UUID,
    user_id: uuid.UUID,
    perm_in: PermissionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """更新用户的知识库权限"""
    # 检查权限（需要 admin 权限）
    await check_kb_permission(kb_id, current_user, db, "admin")

    # 获取权限记录
    result = await db.execute(
        select(UserKBPermission).where(
            UserKBPermission.user_id == user_id, UserKBPermission.kb_id == kb_id
        )
    )
    permission = result.scalar_one_or_none()

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="权限记录不存在"
        )

    # 更新权限
    permission.permission = PermissionLevel(perm_in.permission)  # 字符串转枚举
    await db.commit()
    await db.refresh(permission)

    return permission


@router.delete(
    "/knowledge-bases/{kb_id}/permissions/{user_id}", summary="删除知识库权限"
)
async def delete_kb_permission(
    kb_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """删除用户的知识库权限"""
    # 检查权限（需要 admin 权限）
    await check_kb_permission(kb_id, current_user, db, "admin")

    # 获取权限记录
    result = await db.execute(
        select(UserKBPermission).where(
            UserKBPermission.user_id == user_id, UserKBPermission.kb_id == kb_id
        )
    )
    permission = result.scalar_one_or_none()

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="权限记录不存在"
        )

    await db.delete(permission)
    await db.commit()

    return {"message": "权限已删除"}


@router.get(
    "/my-permissions",
    response_model=List[PermissionResponse],
    summary="获取我的所有权限",
)
async def list_my_permissions(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Any:
    """获取当前用户在所有知识库上的权限"""
    result = await db.execute(
        select(UserKBPermission)
        .where(UserKBPermission.user_id == current_user.id)
        .order_by(UserKBPermission.created_at.desc())
    )
    permissions = result.scalars().all()

    return permissions
