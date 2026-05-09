"""
搜索缓存服务

提供基于 Redis 的搜索结果缓存，减少重复检索的开销。
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

from .base import SearchConfig, SearchResult


@dataclass
class CacheConfig:
    """缓存配置"""

    # 缓存过期时间（秒）
    ttl: int = 3600  # 默认1小时

    # 是否启用缓存
    enabled: bool = True

    # 缓存键前缀
    key_prefix: str = "knowbase:search"

    # 最大缓存结果数
    max_results: int = 100

    # 是否缓存空结果
    cache_empty: bool = True


class SearchCache:
    """搜索缓存

    使用 Redis 缓存搜索结果，支持：
    1. 基于查询和配置的缓存键生成
    2. 自动过期
    3. 批量操作
    4. 缓存预热
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        config: Optional[CacheConfig] = None,
    ):
        """初始化搜索缓存

        Args:
            redis_url: Redis 连接 URL
            config: 缓存配置
        """
        self.redis_url = redis_url
        self.config = config or CacheConfig()
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

    def _generate_cache_key(
        self,
        query: str,
        knowledge_base_id: str,
        config: Optional[SearchConfig] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """生成缓存键

        基于查询内容、知识库ID、配置和过滤条件生成唯一的缓存键。

        Args:
            query: 查询文本
            knowledge_base_id: 知识库ID
            config: 检索配置
            filters: 过滤条件

        Returns:
            缓存键
        """
        # 构建用于哈希的数据
        key_data = {
            "query": query.strip().lower(),
            "kb_id": knowledge_base_id,
            "config": asdict(config) if config else {},
            "filters": filters or {},
        }

        # 生成 MD5 哈希
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()

        return f"{self.config.key_prefix}:{knowledge_base_id}:{key_hash}"

    async def get(
        self,
        query: str,
        knowledge_base_id: str,
        config: Optional[SearchConfig] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Optional[List[SearchResult]]:
        """从缓存获取搜索结果

        Args:
            query: 查询文本
            knowledge_base_id: 知识库ID
            config: 检索配置
            filters: 过滤条件

        Returns:
            缓存的搜索结果，如果缓存未命中则返回 None
        """
        if not self.config.enabled:
            return None

        try:
            r = await self._get_redis()
            key = self._generate_cache_key(query, knowledge_base_id, config, filters)

            cached = await r.get(key)
            if cached is None:
                return None

            # 解析缓存数据
            data = json.loads(cached)

            # 重建 SearchResult 对象
            results = [
                SearchResult(
                    chunk_id=item["chunk_id"],
                    document_id=item["document_id"],
                    content=item["content"],
                    score=item["score"],
                    metadata=item.get("metadata", {}),
                )
                for item in data
            ]

            return results

        except Exception as e:
            # 缓存错误不应影响主流程
            print(f"Cache get error: {e}")
            return None

    async def set(
        self,
        query: str,
        knowledge_base_id: str,
        results: List[SearchResult],
        config: Optional[SearchConfig] = None,
        filters: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """缓存搜索结果

        Args:
            query: 查询文本
            knowledge_base_id: 知识库ID
            results: 搜索结果
            config: 检索配置
            filters: 过滤条件
            ttl: 过期时间（秒），None 使用默认值

        Returns:
            是否成功缓存
        """
        if not self.config.enabled:
            return False

        # 检查是否缓存空结果
        if not results and not self.config.cache_empty:
            return False

        try:
            r = await self._get_redis()
            key = self._generate_cache_key(query, knowledge_base_id, config, filters)

            # 限制缓存的结果数量
            results_to_cache = results[: self.config.max_results]

            # 序列化结果
            data = [
                {
                    "chunk_id": r.chunk_id,
                    "document_id": r.document_id,
                    "content": r.content,
                    "score": r.score,
                    "metadata": r.metadata,
                }
                for r in results_to_cache
            ]

            # 设置缓存
            cache_ttl = ttl or self.config.ttl
            await r.setex(
                key,
                cache_ttl,
                json.dumps(data, ensure_ascii=False),
            )

            return True

        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    async def delete(
        self,
        query: str,
        knowledge_base_id: str,
        config: Optional[SearchConfig] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """删除缓存

        Args:
            query: 查询文本
            knowledge_base_id: 知识库ID
            config: 检索配置
            filters: 过滤条件

        Returns:
            是否成功删除
        """
        try:
            r = await self._get_redis()
            key = self._generate_cache_key(query, knowledge_base_id, config, filters)
            await r.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

    async def invalidate_knowledge_base(
        self,
        knowledge_base_id: str,
    ) -> int:
        """使知识库的所有缓存失效

        当知识库内容更新时调用此方法。

        Args:
            knowledge_base_id: 知识库ID

        Returns:
            删除的缓存键数量
        """
        try:
            r = await self._get_redis()
            pattern = f"{self.config.key_prefix}:{knowledge_base_id}:*"

            # 使用 SCAN 避免阻塞
            deleted = 0
            async for key in r.scan_iter(match=pattern, count=100):
                await r.delete(key)
                deleted += 1

            return deleted

        except Exception as e:
            print(f"Cache invalidate error: {e}")
            return 0

    async def clear_all(self) -> int:
        """清除所有搜索缓存

        Returns:
            删除的缓存键数量
        """
        try:
            r = await self._get_redis()
            pattern = f"{self.config.key_prefix}:*"

            deleted = 0
            async for key in r.scan_iter(match=pattern, count=100):
                await r.delete(key)
                deleted += 1

            return deleted

        except Exception as e:
            print(f"Cache clear error: {e}")
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息

        Returns:
            统计信息字典
        """
        try:
            r = await self._get_redis()

            # 统计缓存键数量
            pattern = f"{self.config.key_prefix}:*"
            count = 0
            async for _ in r.scan_iter(match=pattern, count=100):
                count += 1

            # 获取 Redis 信息
            info = await r.info("memory")

            return {
                "total_keys": count,
                "enabled": self.config.enabled,
                "ttl": self.config.ttl,
                "redis_memory_used": info.get("used_memory_human", "unknown"),
            }

        except Exception as e:
            return {
                "error": str(e),
                "enabled": self.config.enabled,
            }

    async def close(self):
        """关闭连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None


class CachedRetrievalPipeline:
    """带缓存的检索管道

    在 RetrievalPipeline 基础上添加缓存支持。
    """

    def __init__(
        self,
        pipeline,  # RetrievalPipeline
        cache: SearchCache,
    ):
        """初始化带缓存的检索管道

        Args:
            pipeline: 检索管道
            cache: 搜索缓存
        """
        self.pipeline = pipeline
        self.cache = cache

    async def search(
        self,
        query: str,
        knowledge_base_id: str,
        top_k: int = 10,
        score_threshold: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
        rerank: bool = True,
        rerank_top_k: Optional[int] = None,
        use_cache: bool = True,
    ):
        """执行带缓存的检索

        Args:
            query: 查询文本
            knowledge_base_id: 知识库ID
            top_k: 返回结果数量
            score_threshold: 分数阈值
            filters: 过滤条件
            rerank: 是否使用重排序
            rerank_top_k: 重排序返回数量
            use_cache: 是否使用缓存

        Returns:
            检索结果列表
        """

        config = SearchConfig(
            top_k=top_k,
            score_threshold=score_threshold,
            filters=filters or {},
        )

        # 尝试从缓存获取
        if use_cache:
            cached_results = await self.cache.get(
                query=query,
                knowledge_base_id=knowledge_base_id,
                config=config,
                filters=filters,
            )

            if cached_results is not None:
                # 缓存命中
                return cached_results

        # 缓存未命中，执行检索
        results = await self.pipeline.search(
            query=query,
            knowledge_base_id=knowledge_base_id,
            top_k=top_k,
            score_threshold=score_threshold,
            filters=filters,
            rerank=rerank,
            rerank_top_k=rerank_top_k,
        )

        # 缓存结果
        if use_cache:
            await self.cache.set(
                query=query,
                knowledge_base_id=knowledge_base_id,
                results=results,
                config=config,
                filters=filters,
            )

        return results
