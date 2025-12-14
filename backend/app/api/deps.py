"""
认证依赖
获取当前用户、权限检查等
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from app.core.database import get_db
from app.core.security import decode_token, hash_api_key, verify_api_key
from app.models.api_key import ApiKey
from app.models.user import User
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# HTTP Bearer 认证方案
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    获取当前登录用户
    支持 JWT Token 和 API Key 两种认证方式
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # 检查是否是 API Key（以 kb_ 开头）
    if token.startswith("kb_"):
        return await _get_user_from_api_key(token, db)

    # 否则当作 JWT Token 处理
    return await _get_user_from_jwt(token, db)


async def _get_user_from_jwt(token: str, db: AsyncSession) -> User:
    """从 JWT Token 获取用户"""
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查 token 类型
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌类型",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 查询用户
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的用户ID",
        )

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    return user


async def _get_user_from_api_key(api_key: str, db: AsyncSession) -> User:
    """从 API Key 获取用户"""
    key_hash = hash_api_key(api_key)

    result = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
    api_key_obj = result.scalar_one_or_none()

    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 API Key",
        )

    if not api_key_obj.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key 已被禁用",
        )

    # 检查是否过期
    if api_key_obj.expires_at and api_key_obj.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key 已过期",
        )

    # 更新最后使用时间
    api_key_obj.last_used_at = datetime.now(timezone.utc)
    await db.commit()

    # 获取关联的用户
    result = await db.execute(select(User).where(User.id == api_key_obj.user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户不存在或已被禁用",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="用户已被禁用"
        )
    return current_user


async def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    """获取当前超级用户"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="权限不足，需要管理员权限"
        )
    return current_user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    可选的当前用户获取
    未登录时返回 None，不抛出异常
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def check_kb_permission(
    db: AsyncSession,
    kb_id: uuid.UUID,
    user: User,
    require_write: bool = False,
):
    """
    检查用户对知识库的权限

    Args:
        db: 数据库会话
        kb_id: 知识库 ID
        user: 当前用户
        require_write: 是否需要写权限

    Returns:
        KnowledgeBase 对象

    Raises:
        HTTPException: 权限不足或知识库不存在
    """
    from app.models import KnowledgeBase, PermissionLevel, UserKBPermission

    # 获取知识库
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    # 超级管理员拥有所有权限
    if user.is_superuser:
        return kb

    # 所有者拥有所有权限
    if kb.owner_id == user.id:
        return kb

    # 检查权限表
    result = await db.execute(
        select(UserKBPermission).where(
            UserKBPermission.kb_id == kb_id,
            UserKBPermission.user_id == user.id,
        )
    )
    permission = result.scalar_one_or_none()

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this knowledge base",
        )

    # 检查写权限
    if require_write and permission.level == PermissionLevel.READ:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write permission required",
        )

    return kb
