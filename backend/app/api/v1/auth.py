"""
认证路由
处理用户登录、注册、Token 刷新等
"""

from datetime import timedelta
from typing import Any

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    Token,
)
from app.schemas.user import UserCreate, UserResponse
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/login", response_model=Token, summary="用户登录")
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)) -> Any:
    """
    用户登录，返回访问令牌和刷新令牌

    - **username**: 用户名或邮箱
    - **password**: 密码
    """
    # 支持用户名或邮箱登录
    result = await db.execute(
        select(User).where(
            (User.username == login_data.username) | (User.email == login_data.username)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="用户已被禁用"
        )

    # 更新最后登录时间
    from datetime import datetime, timezone

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    # 创建令牌
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/register", response_model=UserResponse, summary="用户注册")
async def register(
    register_data: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> Any:
    """
    用户注册

    - **username**: 用户名（唯一）
    - **email**: 邮箱（唯一）
    - **password**: 密码
    - **full_name**: 全名（可选）
    """
    # 检查用户名是否已存在
    result = await db.execute(
        select(User).where(User.username == register_data.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已被使用"
        )

    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == register_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已被使用"
        )

    # 创建用户
    user = User(
        username=register_data.username,
        email=register_data.email,
        hashed_password=get_password_hash(register_data.password),
        full_name=register_data.full_name,
        is_active=True,
        is_superuser=False,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


@router.post("/refresh", response_model=Token, summary="刷新令牌")
async def refresh_token(
    refresh_data: RefreshRequest, db: AsyncSession = Depends(get_db)
) -> Any:
    """
    使用刷新令牌获取新的访问令牌

    - **refresh_token**: 刷新令牌
    """
    payload = decode_token(refresh_data.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新令牌"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新令牌"
        )

    # 验证用户是否存在且活跃
    import uuid

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的用户ID"
        )

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已被禁用"
        )

    # 创建新令牌
    access_token = create_access_token(subject=str(user.id))
    new_refresh_token = create_refresh_token(subject=str(user.id))

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def get_me(current_user: User = Depends(get_current_user)) -> Any:
    """获取当前登录用户的信息"""
    return current_user


@router.post("/change-password", summary="修改密码")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    修改当前用户的密码

    - **old_password**: 旧密码
    - **new_password**: 新密码
    """
    # 验证旧密码
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码错误"
        )

    # 更新密码
    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()

    return {"message": "密码修改成功"}
