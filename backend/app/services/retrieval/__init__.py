"""
检索服务模块

提供多种检索策略：
1. 语义检索 - 基于向量相似度
2. 关键词检索 - 基于全文搜索
3. 混合检索 - 结合语义和关键词
4. 重排序 - 对检索结果进行二次排序
"""

from .base import BaseRetriever, RetrievalMode, SearchConfig, SearchResult
from .cache import CacheConfig, CachedRetrievalPipeline, SearchCache
from .factory import RetrievalPipeline, RetrieverFactory
from .hybrid_search import (
    AdaptiveHybridRetriever,
    FusionStrategy,
    HybridConfig,
    HybridRetriever,
)
from .keyword_search import (
    KeywordSearch,
    PostgresKeywordSearch,
    get_keyword_search_service,
)
from .rerank import (
    BaseReranker,
    CohereReranker,
    JinaReranker,
    LLMReranker,
    LocalReranker,
    RerankConfig,
    RerankerFactory,
    RerankProvider,
)
from .semantic_search import SemanticSearch

__all__ = [
    # 基础类
    "BaseRetriever",
    "SearchResult",
    "SearchConfig",
    "RetrievalMode",
    # 语义检索
    "SemanticSearch",
    # 关键词检索
    "KeywordSearch",
    "PostgresKeywordSearch",
    "get_keyword_search_service",
    # 混合检索
    "HybridRetriever",
    "AdaptiveHybridRetriever",
    "HybridConfig",
    "FusionStrategy",
    # 重排序
    "BaseReranker",
    "CohereReranker",
    "JinaReranker",
    "LocalReranker",
    "LLMReranker",
    "RerankConfig",
    "RerankProvider",
    "RerankerFactory",
    # 工厂和管道
    "RetrieverFactory",
    "RetrievalPipeline",
    # 缓存
    "SearchCache",
    "CacheConfig",
    "CachedRetrievalPipeline",
]
