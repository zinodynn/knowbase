"""
语义检索服务

基于向量相似度的检索
"""

import logging
import time
from typing import List, Optional

from app.services.embeddings import BaseEmbeddingService
from app.services.retrieval.base import BaseRetriever, SearchConfig, SearchResult
from app.services.vector_store import BaseVectorStore, QdrantVectorStore

logger = logging.getLogger(__name__)


class SemanticSearch(BaseRetriever):
    """语义检索器"""

    def __init__(
        self,
        vector_store: BaseVectorStore,
        embedding_service: BaseEmbeddingService,
    ):
        """
        初始化语义检索器

        Args:
            vector_store: 向量存储服务
            embedding_service: 向量化服务
        """
        self.vector_store = vector_store
        self.embedding_service = embedding_service

    async def search(
        self,
        kb_id: str,
        query: str,
        config: Optional[SearchConfig] = None,
    ) -> List[SearchResult]:
        """
        执行语义检索

        Args:
            kb_id: 知识库 ID
            query: 查询文本
            config: 检索配置

        Returns:
            检索结果列表
        """
        config = config or SearchConfig()
        start_time = time.time()

        try:
            # 1. 将查询文本向量化
            query_vector = await self.embedding_service.embed_text(query)

            # 2. 构建过滤条件
            filters = {}
            if config.document_ids:
                filters["document_id"] = {"$in": config.document_ids}

            # 3. 在向量数据库中搜索
            collection_name = self.vector_store.get_collection_name(kb_id)
            vector_results = await self.vector_store.search(
                collection_name=collection_name,
                query_vector=query_vector,
                top_k=config.top_k,
                filters=filters if filters else None,
            )

            # 4. 转换结果格式
            results = []
            for vr in vector_results:
                results.append(
                    SearchResult(
                        chunk_id=vr.id,
                        document_id=vr.payload.get("document_id", ""),
                        content=vr.payload.get("content", ""),
                        score=vr.score,
                        chunk_index=vr.payload.get("chunk_index", 0),
                        document_filename=vr.payload.get("filename", ""),
                        metadata=vr.payload,
                    )
                )

            # 5. 应用过滤器
            results = self._apply_filters(results, config)

            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.info(
                f"Semantic search in {kb_id}: query='{query[:50]}...', "
                f"results={len(results)}, time={elapsed_ms}ms"
            )

            return results

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            raise

    async def search_with_vector(
        self,
        kb_id: str,
        query_vector: List[float],
        config: Optional[SearchConfig] = None,
    ) -> List[SearchResult]:
        """
        使用预计算的向量进行检索

        Args:
            kb_id: 知识库 ID
            query_vector: 查询向量
            config: 检索配置

        Returns:
            检索结果列表
        """
        config = config or SearchConfig()

        # 构建过滤条件
        filters = {}
        if config.document_ids:
            filters["document_id"] = {"$in": config.document_ids}

        # 在向量数据库中搜索
        collection_name = self.vector_store.get_collection_name(kb_id)
        vector_results = await self.vector_store.search(
            collection_name=collection_name,
            query_vector=query_vector,
            top_k=config.top_k,
            filters=filters if filters else None,
        )

        # 转换结果格式
        results = []
        for vr in vector_results:
            results.append(
                SearchResult(
                    chunk_id=vr.id,
                    document_id=vr.payload.get("document_id", ""),
                    content=vr.payload.get("content", ""),
                    score=vr.score,
                    chunk_index=vr.payload.get("chunk_index", 0),
                    document_filename=vr.payload.get("filename", ""),
                    metadata=vr.payload,
                )
            )

        return self._apply_filters(results, config)
