"""
管理员 API

提供系统管理功能，仅管理员可访问：
1. 系统统计
2. 用户管理
3. 配额管理
4. 缓存管理
"""

from typing import Any, Dict, List, Optional

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.user import User
from app.services.retrieval.cache import SearchCache
from app.services.statistics import DatabaseStatistics, MetricType, StatisticsService
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin", tags=["admin"])


# ============ 依赖项 ============


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """要求管理员权限"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="需要管理员权限",
        )
    return current_user


# ============ 请求/响应模型 ============


class SystemOverview(BaseModel):
    """系统概览"""

    users: Dict[str, Any]
    knowledge_bases: Dict[str, Any]
    documents: Dict[str, Any]


class UserListItem(BaseModel):
    """用户列表项"""

    id: str
    email: str
    username: Optional[str]
    is_active: bool
    is_superuser: bool
    created_at: str


class UserUpdate(BaseModel):
    """用户更新"""

    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class QuotaConfig(BaseModel):
    """配额配置"""

    api_calls: int = Field(1000, description="每日 API 调用限制")
    search_queries: int = Field(500, description="每日搜索限制")
    embedding_tokens: int = Field(100000, description="每日 Embedding Token 限制")
    rerank_calls: int = Field(100, description="每日 Rerank 调用限制")


# ============ 系统统计 ============


@router.get("/overview", response_model=SystemOverview)
async def get_system_overview(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """获取系统概览

    返回用户、知识库、文档的统计信息。
    """
    stats = DatabaseStatistics(db)
    overview = await stats.get_overview()
    return overview


@router.get("/usage")
async def get_usage_stats(
    metric: str = Query("search_query", description="指标类型"),
    hours: int = Query(24, ge=1, le=168, description="查询小时数"),
    admin: User = Depends(require_admin),
):
    """获取使用量统计

    返回指定时间范围内的使用量数据。
    """
    try:
        metric_type = MetricType(metric)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"无效的指标类型: {metric}",
        )

    stats_service = StatisticsService(redis_url=settings.redis_url)
    usage = await stats_service.get_global_usage(metric_type, hours)
    await stats_service.close()

    return {
        "metric": metric,
        "hours": hours,
        "data": usage,
    }


# ============ 用户管理 ============


@router.get("/users")
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="搜索邮箱或用户名"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """列出所有用户"""
    stmt = select(User)

    if search:
        stmt = stmt.where(
            (User.email.ilike(f"%{search}%")) | (User.username.ilike(f"%{search}%"))
        )

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    users = result.scalars().all()

    return {
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "username": u.username,
                "is_active": u.is_active,
                "is_superuser": u.is_superuser,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "skip": skip,
        "limit": limit,
    }


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """获取用户详情"""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 获取用户统计
    db_stats = DatabaseStatistics(db)
    user_stats = await db_stats.get_user_stats(user_id)

    # 获取使用量统计
    stats_service = StatisticsService(redis_url=settings.redis_url)
    usage = await stats_service.get_user_summary(user_id, days=30)
    await stats_service.close()

    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        },
        "stats": user_stats,
        "usage": usage,
    }


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """更新用户状态"""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 不能修改自己的管理员状态
    if str(user.id) == str(admin.id) and data.is_superuser is False:
        raise HTTPException(
            status_code=400,
            detail="不能取消自己的管理员权限",
        )

    # 更新字段
    update_data = {}
    if data.is_active is not None:
        update_data["is_active"] = data.is_active
    if data.is_superuser is not None:
        update_data["is_superuser"] = data.is_superuser

    if update_data:
        stmt = update(User).where(User.id == user_id).values(**update_data)
        await db.execute(stmt)
        await db.commit()

    return {"message": "用户已更新"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """删除用户

    警告：这将删除用户及其所有数据。
    """
    # 不能删除自己
    if str(user_id) == str(admin.id):
        raise HTTPException(
            status_code=400,
            detail="不能删除自己的账户",
        )

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 删除用户（级联删除相关数据）
    await db.delete(user)
    await db.commit()

    return {"message": "用户已删除"}


# ============ 配额管理 ============


@router.get("/users/{user_id}/quota")
async def get_user_quota(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """获取用户配额状态"""
    # 检查用户是否存在
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="用户不存在")

    # 默认配额
    quotas = {
        MetricType.API_CALL: 1000,
        MetricType.SEARCH_QUERY: 500,
        MetricType.EMBEDDING: 100000,
        MetricType.RERANK: 100,
    }

    stats_service = StatisticsService(redis_url=settings.redis_url)
    status = await stats_service.get_quota_status(user_id, quotas)
    await stats_service.close()

    return {
        "user_id": user_id,
        "quotas": status,
    }


@router.get("/users/{user_id}/cost")
async def get_user_cost(
    user_id: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """获取用户成本估算"""
    # 检查用户是否存在
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="用户不存在")

    stats_service = StatisticsService(redis_url=settings.redis_url)
    cost = await stats_service.estimate_cost(user_id, days)
    await stats_service.close()

    return {
        "user_id": user_id,
        "cost_estimation": cost,
    }


# ============ 缓存管理 ============


@router.get("/cache/stats")
async def get_cache_stats(
    admin: User = Depends(require_admin),
):
    """获取缓存统计"""
    cache = SearchCache(redis_url=settings.redis_url)
    stats = await cache.get_stats()
    await cache.close()
    return stats


@router.delete("/cache")
async def clear_all_cache(
    admin: User = Depends(require_admin),
):
    """清除所有搜索缓存"""
    cache = SearchCache(redis_url=settings.redis_url)
    deleted = await cache.clear_all()
    await cache.close()

    return {
        "message": f"已清除 {deleted} 条缓存",
    }


@router.delete("/cache/kb/{knowledge_base_id}")
async def clear_kb_cache(
    knowledge_base_id: str,
    admin: User = Depends(require_admin),
):
    """清除指定知识库的缓存"""
    cache = SearchCache(redis_url=settings.redis_url)
    deleted = await cache.invalidate_knowledge_base(knowledge_base_id)
    await cache.close()

    return {
        "message": f"已清除 {deleted} 条缓存",
        "knowledge_base_id": knowledge_base_id,
    }


# ============ 系统配置 ============


@router.get("/config")
async def get_system_config(
    admin: User = Depends(require_admin),
):
    """获取系统配置（脱敏）"""
    return {
        "app_name": settings.APP_NAME,
        "debug": settings.DEBUG,
        "environment": settings.ENVIRONMENT,
        "database": {
            "host": settings.DB_HOST,
            "port": settings.DB_PORT,
            "name": settings.DB_NAME,
        },
        "redis": {
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
        },
        "vector_db": {
            "type": settings.VECTOR_DB_TYPE,
            "host": settings.QDRANT_HOST,
            "port": settings.QDRANT_PORT,
        },
        "embedding": {
            "provider": settings.EMBEDDING_PROVIDER,
            "model": settings.EMBEDDING_MODEL,
            "dimension": settings.EMBEDDING_DIMENSION,
        },
        "rerank": {
            "provider": settings.RERANK_PROVIDER,
        },
        "storage": {
            "endpoint": settings.MINIO_ENDPOINT,
            "bucket": settings.MINIO_BUCKET,
        },
    }
