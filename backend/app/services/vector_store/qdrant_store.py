"""
Qdrant 向量数据库服务
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.services.vector_store.base import (
    BaseVectorStore,
    SearchResult,
    VectorRecord,
    VectorStoreConfig,
    VectorStoreType,
)

logger = logging.getLogger(__name__)


class QdrantVectorStore(BaseVectorStore):
    """Qdrant 向量数据库服务"""

    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        self._client = None

    @property
    def client(self):
        """获取 Qdrant 客户端（延迟初始化）"""
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
            except ImportError:
                raise ImportError(
                    "qdrant-client is required for Qdrant vector store. "
                    "Install it with: pip install qdrant-client"
                )

            if self.config.prefer_grpc:
                self._client = QdrantClient(
                    host=self.config.host,
                    grpc_port=self.config.grpc_port,
                    api_key=self.config.api_key,
                    prefer_grpc=True,
                    timeout=self.config.timeout,
                )
            else:
                self._client = QdrantClient(
                    host=self.config.host,
                    port=self.config.port,
                    api_key=self.config.api_key,
                    timeout=self.config.timeout,
                )

        return self._client

    def _get_distance_metric(self, metric: Optional[str] = None):
        """获取距离度量方式"""
        from qdrant_client.models import Distance

        metric = metric or self.config.distance_metric

        mapping = {
            "cosine": Distance.COSINE,
            "dot": Distance.DOT,
            "euclidean": Distance.EUCLID,
        }

        return mapping.get(metric.lower(), Distance.COSINE)

    async def create_collection(
        self,
        collection_name: str,
        dimension: int,
        distance_metric: Optional[str] = None,
    ) -> bool:
        """
        创建集合

        Args:
            collection_name: 集合名称
            dimension: 向量维度
            distance_metric: 距离度量方式

        Returns:
            是否成功
        """
        from qdrant_client.models import VectorParams

        try:
            distance = self._get_distance_metric(distance_metric)

            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=distance,
                ),
            )

            logger.info(
                f"Created Qdrant collection: {collection_name}, dimension: {dimension}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            raise

    async def delete_collection(self, collection_name: str) -> bool:
        """
        删除集合

        Args:
            collection_name: 集合名称

        Returns:
            是否成功
        """
        try:
            self.client.delete_collection(collection_name=collection_name)
            logger.info(f"Deleted Qdrant collection: {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")
            raise

    async def collection_exists(self, collection_name: str) -> bool:
        """
        检查集合是否存在

        Args:
            collection_name: 集合名称

        Returns:
            是否存在
        """
        try:
            collections = self.client.get_collections().collections
            return any(c.name == collection_name for c in collections)

        except Exception as e:
            logger.error(f"Failed to check collection existence: {e}")
            return False

    async def insert_vectors(
        self,
        collection_name: str,
        records: List[VectorRecord],
    ) -> List[str]:
        """
        插入向量

        Args:
            collection_name: 集合名称
            records: 向量记录列表

        Returns:
            插入的向量 ID 列表
        """
        from qdrant_client.models import PointStruct

        if not records:
            return []

        try:
            points = []
            for record in records:
                # 尝试将 ID 转换为 UUID
                try:
                    point_id = str(UUID(record.id))
                except ValueError:
                    point_id = record.id

                points.append(
                    PointStruct(
                        id=point_id,
                        vector=record.vector,
                        payload=record.payload,
                    )
                )

            self.client.upsert(
                collection_name=collection_name,
                points=points,
            )

            logger.info(f"Inserted {len(records)} vectors into {collection_name}")
            return [r.id for r in records]

        except Exception as e:
            logger.error(f"Failed to insert vectors into {collection_name}: {e}")
            raise

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        with_vectors: bool = False,
    ) -> List[SearchResult]:
        """
        搜索相似向量

        Args:
            collection_name: 集合名称
            query_vector: 查询向量
            top_k: 返回数量
            filters: 过滤条件
            with_vectors: 是否返回向量

        Returns:
            搜索结果列表
        """
        try:
            # 构建过滤条件
            qdrant_filter = None
            if filters:
                qdrant_filter = self._build_filter(filters)

            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=qdrant_filter,
                with_vectors=with_vectors,
            )

            return [
                SearchResult(
                    id=str(r.id),
                    score=r.score,
                    payload=r.payload or {},
                    vector=r.vector if with_vectors else None,
                )
                for r in results
            ]

        except Exception as e:
            logger.error(f"Failed to search in {collection_name}: {e}")
            raise

    async def delete_vectors(
        self,
        collection_name: str,
        vector_ids: List[str],
    ) -> bool:
        """
        删除向量

        Args:
            collection_name: 集合名称
            vector_ids: 向量 ID 列表

        Returns:
            是否成功
        """
        from qdrant_client.models import PointIdsList

        if not vector_ids:
            return True

        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=PointIdsList(
                    points=vector_ids,
                ),
            )

            logger.info(f"Deleted {len(vector_ids)} vectors from {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete vectors from {collection_name}: {e}")
            raise

    async def get_vectors(
        self,
        collection_name: str,
        vector_ids: List[str],
        with_vectors: bool = False,
    ) -> List[VectorRecord]:
        """
        获取向量

        Args:
            collection_name: 集合名称
            vector_ids: 向量 ID 列表
            with_vectors: 是否返回向量

        Returns:
            向量记录列表
        """
        if not vector_ids:
            return []

        try:
            results = self.client.retrieve(
                collection_name=collection_name,
                ids=vector_ids,
                with_vectors=with_vectors,
            )

            return [
                VectorRecord(
                    id=str(r.id),
                    vector=r.vector if with_vectors and r.vector else [],
                    payload=r.payload or {},
                )
                for r in results
            ]

        except Exception as e:
            logger.error(f"Failed to get vectors from {collection_name}: {e}")
            raise

    async def count_vectors(self, collection_name: str) -> int:
        """
        统计向量数量

        Args:
            collection_name: 集合名称

        Returns:
            向量数量
        """
        try:
            collection_info = self.client.get_collection(collection_name)
            return collection_info.points_count

        except Exception as e:
            logger.error(f"Failed to count vectors in {collection_name}: {e}")
            raise

    def _build_filter(self, filters: Dict[str, Any]):
        """
        构建 Qdrant 过滤条件

        支持的过滤格式:
        - {"field": value} - 精确匹配
        - {"field": {"$in": [v1, v2]}} - 包含于
        - {"field": {"$ne": value}} - 不等于
        - {"field": {"$gte": value}} - 大于等于
        - {"field": {"$lte": value}} - 小于等于

        Args:
            filters: 过滤条件

        Returns:
            Qdrant Filter 对象
        """
        from qdrant_client.models import (
            FieldCondition,
            Filter,
            MatchAny,
            MatchValue,
            Range,
        )

        conditions = []

        for key, value in filters.items():
            if isinstance(value, dict):
                # 操作符形式
                for op, op_value in value.items():
                    if op == "$in":
                        conditions.append(
                            FieldCondition(
                                key=key,
                                match=MatchAny(any=op_value),
                            )
                        )
                    elif op == "$gte":
                        conditions.append(
                            FieldCondition(
                                key=key,
                                range=Range(gte=op_value),
                            )
                        )
                    elif op == "$lte":
                        conditions.append(
                            FieldCondition(
                                key=key,
                                range=Range(lte=op_value),
                            )
                        )
            else:
                # 精确匹配
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value),
                    )
                )

        return Filter(must=conditions) if conditions else None

    async def delete_by_filter(
        self,
        collection_name: str,
        filters: Dict[str, Any],
    ) -> bool:
        """
        按条件删除向量

        Args:
            collection_name: 集合名称
            filters: 过滤条件

        Returns:
            是否成功
        """
        from qdrant_client.models import FilterSelector

        try:
            qdrant_filter = self._build_filter(filters)

            if qdrant_filter:
                self.client.delete(
                    collection_name=collection_name,
                    points_selector=FilterSelector(filter=qdrant_filter),
                )

                logger.info(f"Deleted vectors by filter from {collection_name}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete by filter from {collection_name}: {e}")
            raise


def create_qdrant_store(
    host: str = "localhost",
    port: int = 6333,
    api_key: Optional[str] = None,
    **kwargs,
) -> QdrantVectorStore:
    """
    创建 Qdrant 向量存储服务

    Args:
        host: 主机地址
        port: 端口
        api_key: API 密钥
        **kwargs: 其他配置参数

    Returns:
        QdrantVectorStore 实例
    """
    config = VectorStoreConfig(
        store_type=VectorStoreType.QDRANT,
        host=host,
        port=port,
        api_key=api_key,
        **kwargs,
    )

    return QdrantVectorStore(config)
