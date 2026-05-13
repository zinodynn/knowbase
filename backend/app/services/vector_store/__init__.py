"""
向量数据库服务模块

支持多种向量数据库：
- Qdrant
- Milvus（规划中）
- Weaviate（规划中）
"""

from app.services.vector_store.base import (
    BaseVectorStore,
    SearchResult,
    VectorRecord,
    VectorStoreConfig,
)
from app.services.vector_store.qdrant_store import QdrantVectorStore

__all__ = [
    "BaseVectorStore",
    "VectorRecord",
    "SearchResult",
    "VectorStoreConfig",
    "QdrantVectorStore",
]
