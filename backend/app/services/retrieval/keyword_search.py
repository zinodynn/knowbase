"""
关键词检索服务

基于全文搜索的检索，支持 PostgreSQL tsvector
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import List, Optional

from app.services.retrieval.base import BaseRetriever, SearchConfig, SearchResult
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class KeywordSearch(BaseRetriever, ABC):
    """关键词检索抽象基类"""

    @abstractmethod
    async def search(
        self,
        kb_id: str,
        query: str,
        config: Optional[SearchConfig] = None,
    ) -> List[SearchResult]:
        """执行关键词检索"""
        pass

    @abstractmethod
    async def index_chunk(self, kb_id: str, chunk: dict) -> bool:
        """索引单个 chunk"""
        pass

    @abstractmethod
    async def delete_chunk(self, kb_id: str, chunk_id: str) -> bool:
        """删除单个 chunk 的索引"""
        pass


class PostgresKeywordSearch(KeywordSearch):
    """PostgreSQL tsvector 全文检索实现"""

    def __init__(self, db_session_factory):
        """
        初始化 PostgreSQL 关键词检索

        Args:
            db_session_factory: 数据库会话工厂函数
        """
        self.db_session_factory = db_session_factory
        # 默认使用 simple 配置，如果安装了 zhparser 可以使用 chinese
        self.text_search_config = "simple"

    async def search(
        self,
        kb_id: str,
        query: str,
        config: Optional[SearchConfig] = None,
    ) -> List[SearchResult]:
        """
        执行关键词检索

        使用 PostgreSQL 全文搜索

        Args:
            kb_id: 知识库 ID
            query: 查询文本
            config: 检索配置

        Returns:
            检索结果列表
        """
        config = config or SearchConfig()
        start_time = time.time()

        async with self.db_session_factory() as db:
            try:
                # 构建查询条件
                conditions = ["c.kb_id = :kb_id"]
                params = {"kb_id": kb_id, "query": query, "top_k": config.top_k}

                # 文档 ID 过滤
                if config.document_ids:
                    conditions.append("c.document_id = ANY(:document_ids)")
                    params["document_ids"] = config.document_ids

                where_clause = " AND ".join(conditions)

                # 使用 plainto_tsquery 进行查询
                # 支持简单的全文搜索，对中文需要安装 zhparser 扩展
                sql = f"""
                SELECT 
                    c.id::text as chunk_id,
                    c.document_id::text,
                    c.content,
                    c.chunk_index,
                    c.metadata,
                    d.filename as document_filename,
                    ts_rank_cd(
                        to_tsvector('{self.text_search_config}', c.content),
                        plainto_tsquery('{self.text_search_config}', :query)
                    ) as rank
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE {where_clause}
                    AND to_tsvector('{self.text_search_config}', c.content) 
                        @@ plainto_tsquery('{self.text_search_config}', :query)
                ORDER BY rank DESC
                LIMIT :top_k
                """

                result = await db.execute(text(sql), params)
                rows = result.fetchall()

                # 转换结果格式
                results = []
                for row in rows:
                    results.append(
                        SearchResult(
                            chunk_id=row.chunk_id,
                            document_id=row.document_id,
                            content=row.content,
                            score=float(row.rank) if row.rank else 0.0,
                            chunk_index=row.chunk_index or 0,
                            document_filename=row.document_filename or "",
                            metadata=row.metadata or {},
                        )
                    )

                # 应用过滤器
                results = self._apply_filters(results, config)

                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.info(
                    f"Keyword search in {kb_id}: query='{query[:50]}...', "
                    f"results={len(results)}, time={elapsed_ms}ms"
                )

                return results

            except Exception as e:
                logger.error(f"Keyword search failed: {e}")
                raise

    async def search_like(
        self,
        kb_id: str,
        query: str,
        config: Optional[SearchConfig] = None,
    ) -> List[SearchResult]:
        """
        使用 LIKE 进行简单关键词匹配（备选方案）

        当全文搜索不可用时的回退方案

        Args:
            kb_id: 知识库 ID
            query: 查询文本
            config: 检索配置

        Returns:
            检索结果列表
        """
        config = config or SearchConfig()

        async with self.db_session_factory() as db:
            try:
                # 构建查询条件
                conditions = ["c.kb_id = :kb_id", "c.content ILIKE :pattern"]
                params = {
                    "kb_id": kb_id,
                    "pattern": f"%{query}%",
                    "top_k": config.top_k,
                }

                if config.document_ids:
                    conditions.append("c.document_id = ANY(:document_ids)")
                    params["document_ids"] = config.document_ids

                where_clause = " AND ".join(conditions)

                sql = f"""
                SELECT 
                    c.id::text as chunk_id,
                    c.document_id::text,
                    c.content,
                    c.chunk_index,
                    c.metadata,
                    d.filename as document_filename,
                    1.0 as rank
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE {where_clause}
                LIMIT :top_k
                """

                result = await db.execute(text(sql), params)
                rows = result.fetchall()

                results = []
                for row in rows:
                    results.append(
                        SearchResult(
                            chunk_id=row.chunk_id,
                            document_id=row.document_id,
                            content=row.content,
                            score=1.0,
                            chunk_index=row.chunk_index or 0,
                            document_filename=row.document_filename or "",
                            metadata=row.metadata or {},
                        )
                    )

                return self._apply_filters(results, config)

            except Exception as e:
                logger.error(f"LIKE search failed: {e}")
                raise

    async def index_chunk(self, kb_id: str, chunk: dict) -> bool:
        """
        索引单个 chunk（PostgreSQL 不需要额外索引操作）

        Args:
            kb_id: 知识库 ID
            chunk: chunk 数据

        Returns:
            是否成功
        """
        # PostgreSQL tsvector 会自动处理，不需要额外操作
        return True

    async def delete_chunk(self, kb_id: str, chunk_id: str) -> bool:
        """
        删除单个 chunk 的索引

        Args:
            kb_id: 知识库 ID
            chunk_id: chunk ID

        Returns:
            是否成功
        """
        # PostgreSQL 删除记录时索引自动删除
        return True


def get_keyword_search_service(db_session_factory) -> KeywordSearch:
    """
    获取关键词检索服务

    Args:
        db_session_factory: 数据库会话工厂

    Returns:
        关键词检索服务实例
    """
    # 目前只支持 PostgreSQL
    return PostgresKeywordSearch(db_session_factory)
