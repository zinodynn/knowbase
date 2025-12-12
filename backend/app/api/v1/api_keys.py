"""
API Key 管理路由
"""
from typing import Any, List
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import generate_api_key, hash_api_key
from app.models.user import User
from app.models.api_key import ApiKey
from app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyUpdate,
    ApiKeyResponse,
    ApiKeyCreateResponse,
    ApiKeyListResponse,
)
from app.api.deps import get_current_user


router = APIRouter()


@router.get("", response_model=ApiKeyListResponse, summary="获取 API Key 列表")
async def list_api_keys(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="获取数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """获取当前用户的 API Key 列表"""
    # 获取总数
    result = await db.execute(
        select(func.count(ApiKey.id)).where(ApiKey.user_id == current_user.id)
    )
    total = result.scalar()
    
    # 获取列表
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .order_by(ApiKey.created_at.desc())
    )
    items = result.scalars().all()
    
    return ApiKeyListResponse(items=items, total=total)


@router.post("", response_model=ApiKeyCreateResponse, summary="创建 API Key")
async def create_api_key(
    key_in: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    创建新的 API Key
    
    注意：完整的 API Key 仅在创建时返回一次，请妥善保管！
    """
    # 生成 API Key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    key_prefix = api_key[:12]  # kb_XXXXXXX...
    
    # 计算过期时间
    expires_at = None
    if key_in.expires_days:
        expires_at = datetime.utcnow() + timedelta(days=key_in.expires_days)
    
    # 创建记录
    api_key_obj = ApiKey(
        user_id=current_user.id,
        name=key_in.name,
        description=key_in.description,
        key_hash=key_hash,
        key_prefix=key_prefix,
        is_active=True,
        expires_at=expires_at
    )
    
    db.add(api_key_obj)
    await db.commit()
    await db.refresh(api_key_obj)
    
    # 返回包含完整 key 的响应
    return ApiKeyCreateResponse(
        id=api_key_obj.id,
        name=api_key_obj.name,
        description=api_key_obj.description,
        key_prefix=api_key_obj.key_prefix,
        is_active=api_key_obj.is_active,
        expires_at=api_key_obj.expires_at,
        last_used_at=api_key_obj.last_used_at,
        created_at=api_key_obj.created_at,
        api_key=api_key  # 仅此处返回完整 key
    )


@router.get("/{key_id}", response_model=ApiKeyResponse, summary="获取 API Key 详情")
async def get_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """获取指定 API Key 的详情"""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.user_id == current_user.id
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key 不存在"
        )
    
    return api_key


@router.put("/{key_id}", response_model=ApiKeyResponse, summary="更新 API Key")
async def update_api_key(
    key_id: uuid.UUID,
    key_in: ApiKeyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """更新 API Key 信息"""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.user_id == current_user.id
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key 不存在"
        )
    
    # 更新字段
    update_data = key_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(api_key, field, value)
    
    await db.commit()
    await db.refresh(api_key)
    
    return api_key


@router.delete("/{key_id}", summary="删除 API Key")
async def delete_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """删除 API Key"""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.user_id == current_user.id
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key 不存在"
        )
    
    await db.delete(api_key)
    await db.commit()
    
    return {"message": "API Key 已删除"}


@router.post("/{key_id}/revoke", response_model=ApiKeyResponse, summary="吊销 API Key")
async def revoke_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """吊销 API Key（禁用）"""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.user_id == current_user.id
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key 不存在"
        )
    
    api_key.is_active = False
    await db.commit()
    await db.refresh(api_key)
    
    return api_key
