"""
统计服务

提供使用量统计、成本估算等功能。
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class MetricType(str, Enum):
    """指标类型"""

    API_CALL = "api_call"  # API 调用
    SEARCH_QUERY = "search_query"  # 搜索查询
    EMBEDDING = "embedding"  # Embedding 调用
    RERANK = "rerank"  # Rerank 调用
    TOKEN_USAGE = "token_usage"  # Token 使用
    STORAGE = "storage"  # 存储使用


@dataclass
class UsageRecord:
    """使用记录"""

    metric_type: MetricType
    user_id: str
    knowledge_base_id: Optional[str]
    value: float  # 数量或 token 数
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class StatisticsService:
    """统计服务

    使用 Redis 存储实时统计数据，提供：
    1. 使用量追踪
    2. 成本估算
    3. 配额管理
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "knowbase:stats",
    ):
        """初始化统计服务

        Args:
            redis_url: Redis 连接 URL
            key_prefix: 键前缀
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self._redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> redis.Redis:
        """获取 Redis 连接"""
        if self._redis is None:
            self._redis = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    # ============ 使用量记录 ============

    async def record_usage(self, record: UsageRecord) -> None:
        """记录使用量

        Args:
            record: 使用记录
        """
        r = await self._get_redis()

        # 生成时间维度的键
        date_str = record.timestamp.strftime("%Y-%m-%d")
        hour_str = record.timestamp.strftime("%Y-%m-%d:%H")

        # 用户维度统计
        user_day_key = (
            f"{self.key_prefix}:user:{record.user_id}:{record.metric_type}:{date_str}"
        )
        await r.incrbyfloat(user_day_key, record.value)
        await r.expire(user_day_key, 86400 * 90)  # 保留90天

        # 知识库维度统计
        if record.knowledge_base_id:
            kb_day_key = f"{self.key_prefix}:kb:{record.knowledge_base_id}:{record.metric_type}:{date_str}"
            await r.incrbyfloat(kb_day_key, record.value)
            await r.expire(kb_day_key, 86400 * 90)

        # 全局统计
        global_hour_key = f"{self.key_prefix}:global:{record.metric_type}:{hour_str}"
        await r.incrbyfloat(global_hour_key, record.value)
        await r.expire(global_hour_key, 86400 * 7)  # 保留7天

        # 记录详细日志（可选）
        log_key = f"{self.key_prefix}:log:{date_str}"
        log_entry = {
            "type": record.metric_type,
            "user_id": record.user_id,
            "kb_id": record.knowledge_base_id,
            "value": record.value,
            "ts": record.timestamp.isoformat(),
            "meta": record.metadata,
        }
        await r.lpush(log_key, json.dumps(log_entry, ensure_ascii=False))
        await r.ltrim(log_key, 0, 9999)  # 保留最近10000条
        await r.expire(log_key, 86400 * 30)

    async def record_api_call(
        self,
        user_id: str,
        endpoint: str,
        knowledge_base_id: Optional[str] = None,
    ) -> None:
        """记录 API 调用"""
        await self.record_usage(
            UsageRecord(
                metric_type=MetricType.API_CALL,
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
                value=1,
                metadata={"endpoint": endpoint},
            )
        )

    async def record_search(
        self,
        user_id: str,
        knowledge_base_id: str,
        query_length: int,
        result_count: int,
        mode: str,
    ) -> None:
        """记录搜索查询"""
        await self.record_usage(
            UsageRecord(
                metric_type=MetricType.SEARCH_QUERY,
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
                value=1,
                metadata={
                    "query_length": query_length,
                    "result_count": result_count,
                    "mode": mode,
                },
            )
        )

    async def record_embedding(
        self,
        user_id: str,
        knowledge_base_id: Optional[str],
        token_count: int,
        model: str,
    ) -> None:
        """记录 Embedding 调用"""
        await self.record_usage(
            UsageRecord(
                metric_type=MetricType.EMBEDDING,
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
                value=token_count,
                metadata={"model": model},
            )
        )

    async def record_rerank(
        self,
        user_id: str,
        knowledge_base_id: str,
        doc_count: int,
        provider: str,
    ) -> None:
        """记录 Rerank 调用"""
        await self.record_usage(
            UsageRecord(
                metric_type=MetricType.RERANK,
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
                value=doc_count,
                metadata={"provider": provider},
            )
        )

    # ============ 使用量查询 ============

    async def get_user_usage(
        self,
        user_id: str,
        metric_type: MetricType,
        days: int = 30,
    ) -> Dict[str, float]:
        """获取用户使用量

        Args:
            user_id: 用户ID
            metric_type: 指标类型
            days: 查询天数

        Returns:
            日期到使用量的映射
        """
        r = await self._get_redis()

        usage = {}
        now = datetime.utcnow()

        for i in range(days):
            date = now - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            key = f"{self.key_prefix}:user:{user_id}:{metric_type}:{date_str}"

            value = await r.get(key)
            if value:
                usage[date_str] = float(value)

        return usage

    async def get_kb_usage(
        self,
        knowledge_base_id: str,
        metric_type: MetricType,
        days: int = 30,
    ) -> Dict[str, float]:
        """获取知识库使用量

        Args:
            knowledge_base_id: 知识库ID
            metric_type: 指标类型
            days: 查询天数

        Returns:
            日期到使用量的映射
        """
        r = await self._get_redis()

        usage = {}
        now = datetime.utcnow()

        for i in range(days):
            date = now - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            key = f"{self.key_prefix}:kb:{knowledge_base_id}:{metric_type}:{date_str}"

            value = await r.get(key)
            if value:
                usage[date_str] = float(value)

        return usage

    async def get_global_usage(
        self,
        metric_type: MetricType,
        hours: int = 24,
    ) -> Dict[str, float]:
        """获取全局使用量（按小时）

        Args:
            metric_type: 指标类型
            hours: 查询小时数

        Returns:
            时间到使用量的映射
        """
        r = await self._get_redis()

        usage = {}
        now = datetime.utcnow()

        for i in range(hours):
            hour = now - timedelta(hours=i)
            hour_str = hour.strftime("%Y-%m-%d:%H")
            key = f"{self.key_prefix}:global:{metric_type}:{hour_str}"

            value = await r.get(key)
            if value:
                usage[hour_str] = float(value)

        return usage

    async def get_user_summary(
        self,
        user_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """获取用户使用摘要

        Args:
            user_id: 用户ID
            days: 统计天数

        Returns:
            使用摘要
        """
        summary = {}

        for metric_type in MetricType:
            usage = await self.get_user_usage(user_id, metric_type, days)
            total = sum(usage.values())
            summary[metric_type.value] = {
                "total": total,
                "daily_average": total / max(days, 1),
                "daily_breakdown": usage,
            }

        return summary

    # ============ 成本估算 ============

    # 价格配置（美元）
    PRICING = {
        "embedding": {
            "openai/text-embedding-3-small": 0.00002 / 1000,  # per token
            "openai/text-embedding-3-large": 0.00013 / 1000,
            "openai/text-embedding-ada-002": 0.0001 / 1000,
        },
        "rerank": {
            "cohere/rerank-multilingual-v3.0": 0.001,  # per search
            "jina/jina-reranker-v2-base-multilingual": 0.0005,
        },
    }

    async def estimate_cost(
        self,
        user_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """估算用户成本

        Args:
            user_id: 用户ID
            days: 统计天数

        Returns:
            成本估算
        """
        # 获取 Embedding 使用量
        embedding_usage = await self.get_user_usage(user_id, MetricType.EMBEDDING, days)
        embedding_tokens = sum(embedding_usage.values())

        # 获取 Rerank 使用量
        rerank_usage = await self.get_user_usage(user_id, MetricType.RERANK, days)
        rerank_calls = sum(rerank_usage.values())

        # 使用默认价格估算
        embedding_cost = embedding_tokens * self.PRICING["embedding"].get(
            "openai/text-embedding-3-small", 0.00002 / 1000
        )
        rerank_cost = rerank_calls * self.PRICING["rerank"].get(
            "cohere/rerank-multilingual-v3.0", 0.001
        )

        return {
            "period_days": days,
            "embedding": {
                "tokens": embedding_tokens,
                "estimated_cost_usd": round(embedding_cost, 4),
            },
            "rerank": {
                "calls": rerank_calls,
                "estimated_cost_usd": round(rerank_cost, 4),
            },
            "total_estimated_cost_usd": round(embedding_cost + rerank_cost, 4),
        }

    # ============ 配额管理 ============

    async def check_quota(
        self,
        user_id: str,
        metric_type: MetricType,
        quota: float,
    ) -> bool:
        """检查是否超出配额

        Args:
            user_id: 用户ID
            metric_type: 指标类型
            quota: 配额限制

        Returns:
            是否在配额内
        """
        usage = await self.get_user_usage(user_id, metric_type, days=1)
        today = datetime.utcnow().strftime("%Y-%m-%d")
        current = usage.get(today, 0)

        return current < quota

    async def get_quota_status(
        self,
        user_id: str,
        quotas: Dict[MetricType, float],
    ) -> Dict[str, Any]:
        """获取配额状态

        Args:
            user_id: 用户ID
            quotas: 各指标的配额

        Returns:
            配额状态
        """
        status = {}
        today = datetime.utcnow().strftime("%Y-%m-%d")

        for metric_type, quota in quotas.items():
            usage = await self.get_user_usage(user_id, metric_type, days=1)
            current = usage.get(today, 0)

            status[metric_type.value] = {
                "quota": quota,
                "used": current,
                "remaining": max(0, quota - current),
                "percentage": round(current / quota * 100, 2) if quota > 0 else 0,
            }

        return status

    async def close(self):
        """关闭连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None


class DatabaseStatistics:
    """数据库统计

    从数据库查询统计信息。
    """

    def __init__(self, db: AsyncSession):
        """初始化

        Args:
            db: 数据库会话
        """
        self.db = db

    async def get_overview(self) -> Dict[str, Any]:
        """获取系统概览

        Returns:
            系统统计概览
        """
        from app.models.document import Document
        from app.models.knowledge_base import KnowledgeBase
        from app.models.user import User

        # 用户统计
        user_count = await self.db.scalar(select(func.count(User.id)))

        # 知识库统计
        kb_count = await self.db.scalar(select(func.count(KnowledgeBase.id)))

        # 文档统计
        doc_count = await self.db.scalar(select(func.count(Document.id)))

        # 存储统计
        total_size = await self.db.scalar(select(func.sum(Document.file_size))) or 0

        return {
            "users": {
                "total": user_count,
            },
            "knowledge_bases": {
                "total": kb_count,
            },
            "documents": {
                "total": doc_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
            },
        }

    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户统计

        Args:
            user_id: 用户ID

        Returns:
            用户统计信息
        """
        from app.models.document import Document
        from app.models.knowledge_base import KnowledgeBase

        # 用户知识库数量
        kb_count = await self.db.scalar(
            select(func.count(KnowledgeBase.id)).where(
                KnowledgeBase.owner_id == user_id
            )
        )

        # 用户文档数量和大小
        doc_stats = await self.db.execute(
            select(
                func.count(Document.id),
                func.sum(Document.file_size),
            ).where(Document.uploaded_by == user_id)
        )
        doc_count, total_size = doc_stats.one()
        total_size = total_size or 0

        return {
            "knowledge_bases": kb_count,
            "documents": {
                "count": doc_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
            },
        }

    async def get_kb_stats(self, knowledge_base_id: str) -> Dict[str, Any]:
        """获取知识库统计

        Args:
            knowledge_base_id: 知识库ID

        Returns:
            知识库统计信息
        """
        from app.models.document import Document
        from app.models.processing import DocumentChunk

        # 文档统计
        doc_stats = await self.db.execute(
            select(
                func.count(Document.id),
                func.sum(Document.file_size),
            ).where(Document.kb_id == knowledge_base_id)
        )
        doc_count, total_size = doc_stats.one()
        total_size = total_size or 0

        # 分块统计
        chunk_count = await self.db.scalar(
            select(func.count(DocumentChunk.id)).where(
                DocumentChunk.document_id.in_(
                    select(Document.id).where(Document.kb_id == knowledge_base_id)
                )
            )
        )

        return {
            "documents": {
                "count": doc_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
            },
            "chunks": {
                "count": chunk_count or 0,
            },
        }
