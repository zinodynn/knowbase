"""
向量数据库服务基类和数据结构定义
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class VectorStoreType(str, Enum):
    """向量数据库类型"""

    QDRANT = "qdrant"
    MILVUS = "milvus"
    WEAVIATE = "weaviate"


@dataclass
class VectorStoreConfig:
    """向量数据库配置"""

    store_type: VectorStoreType = VectorStoreType.QDRANT
    host: str = "localhost"
    port: int = 6333
    api_key: Optional[str] = None

    # Qdrant 特有配置
    grpc_port: int = 6334
    prefer_grpc: bool = False

    # 连接配置
    timeout: int = 30

    # 集合配置
    default_dimension: int = 1536
    distance_metric: str = "cosine"  # cosine, dot, euclidean

    # 额外配置
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorRecord:
    """向量记录"""

    id: str  # 向量 ID
    vector: List[float]  # 向量数据
    payload: Dict[str, Any] = field(default_factory=dict)  # 元数据

    @property
    def dimension(self) -> int:
        """向量维度"""
        return len(self.vector)


@dataclass
class SearchResult:
    """搜索结果"""

    id: str  # 向量 ID
    score: float  # 相似度分数
    payload: Dict[str, Any] = field(default_factory=dict)  # 元数据
    vector: Optional[List[float]] = None  # 向量（可选返回）


class BaseVectorStore(ABC):
    """向量数据库服务基类"""

    def __init__(self, config: VectorStoreConfig):
        """
        初始化向量数据库服务

        Args:
            config: 服务配置
        """
        self.config = config

    @property
    def store_type(self) -> str:
        """获取存储类型"""
        return self.config.store_type.value

    @abstractmethod
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
        pass

    @abstractmethod
    async def delete_collection(self, collection_name: str) -> bool:
        """
        删除集合

        Args:
            collection_name: 集合名称

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    async def collection_exists(self, collection_name: str) -> bool:
        """
        检查集合是否存在

        Args:
            collection_name: 集合名称

        Returns:
            是否存在
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def count_vectors(self, collection_name: str) -> int:
        """
        统计向量数量

        Args:
            collection_name: 集合名称

        Returns:
            向量数量
        """
        pass

    @staticmethod
    def get_collection_name(kb_id: str) -> str:
        """
        根据知识库 ID 生成集合名称

        Args:
            kb_id: 知识库 ID

        Returns:
            集合名称
        """
        # 移除 UUID 中的连字符，确保名称有效
        return f"kb_{kb_id.replace('-', '_')}"

    async def ensure_collection(
        self,
        kb_id: str,
        dimension: int,
    ) -> str:
        """
        确保知识库对应的集合存在

        Args:
            kb_id: 知识库 ID
            dimension: 向量维度

        Returns:
            集合名称
        """
        collection_name = self.get_collection_name(kb_id)

        if not await self.collection_exists(collection_name):
            await self.create_collection(collection_name, dimension)
            logger.info(f"Created collection: {collection_name}")

        return collection_name
