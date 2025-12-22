"""
检索器工厂

统一管理检索器的创建和配置
"""

from typing import Any, Dict, Optional

from ..embeddings.base import BaseEmbeddingService
from ..vector_store.base import BaseVectorStore
from .base import BaseRetriever, RetrievalMode
from .hybrid_search import (
    AdaptiveHybridRetriever,
    FusionStrategy,
    HybridConfig,
    HybridRetriever,
)
from .keyword_search import KeywordSearch, PostgresKeywordSearch
from .rerank import BaseReranker, RerankerFactory, RerankProvider
from .semantic_search import SemanticSearch


class RetrieverFactory:
    """检索器工厂

    提供统一的接口来创建各种类型的检索器。
    """

    @staticmethod
    def create_semantic_retriever(
        embedding_service: BaseEmbeddingService,
        vector_store: BaseVectorStore,
    ) -> SemanticSearch:
        """创建语义检索器

        Args:
            embedding_service: Embedding 服务
            vector_store: 向量存储

        Returns:
            语义检索器实例
        """
        return SemanticSearch(
            vector_store=vector_store,
            embedding_service=embedding_service,
        )

    @staticmethod
    def create_keyword_retriever(
        backend: str = "postgresql",
        **kwargs,
    ) -> KeywordSearch:
        """创建关键词检索器

        Args:
            backend: 后端类型 ("postgresql", "elasticsearch")
            **kwargs: 后端特定参数

        Returns:
            关键词检索器实例
        """
        if backend == "postgresql":
            db_session_factory = kwargs.get("db_session_factory")
            if not db_session_factory:
                raise ValueError(
                    "db_session_factory is required for PostgreSQL backend"
                )
            return PostgresKeywordSearch(db_session_factory=db_session_factory)

        elif backend == "elasticsearch":
            from .elasticsearch_search import (
                ElasticsearchKeywordSearch,
                get_elasticsearch_service,
            )

            es_url = kwargs.get("es_url")
            if not es_url:
                raise ValueError("es_url is required for Elasticsearch backend")

            es_service = get_elasticsearch_service(
                es_url=es_url,
                index_prefix=kwargs.get("index_prefix", "knowbase"),
                username=kwargs.get("username"),
                password=kwargs.get("password"),
                use_chinese_analyzer=kwargs.get("use_chinese_analyzer", False),
            )
            return ElasticsearchKeywordSearch(es_service)

        else:
            raise ValueError(f"Unknown keyword backend: {backend}")

    @staticmethod
    def create_hybrid_retriever(
        semantic_retriever: SemanticSearch,
        keyword_retriever: KeywordSearch,
        fusion_strategy: FusionStrategy = FusionStrategy.RRF,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        adaptive: bool = False,
    ) -> HybridRetriever:
        """创建混合检索器

        Args:
            semantic_retriever: 语义检索器
            keyword_retriever: 关键词检索器
            fusion_strategy: 融合策略
            semantic_weight: 语义检索权重
            keyword_weight: 关键词检索权重
            adaptive: 是否使用自适应混合检索

        Returns:
            混合检索器实例
        """
        config = HybridConfig(
            fusion_strategy=fusion_strategy,
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight,
        )

        if adaptive:
            return AdaptiveHybridRetriever(
                semantic_retriever=semantic_retriever,
                keyword_retriever=keyword_retriever,
                default_config=config,
            )

        return HybridRetriever(
            semantic_retriever=semantic_retriever,
            keyword_retriever=keyword_retriever,
            default_config=config,
        )

    @staticmethod
    def create_reranker(
        provider: str = "cohere",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> BaseReranker:
        """创建重排序器

        Args:
            provider: 提供商 ("cohere", "jina", "local", "llm")
            api_key: API 密钥
            model: 模型名称
            **kwargs: 其他参数

        Returns:
            重排序器实例
        """
        provider_enum = RerankProvider(provider)
        return RerankerFactory.create(
            provider=provider_enum,
            api_key=api_key,
            model=model,
            **kwargs,
        )

    @staticmethod
    def create_retriever(
        mode: RetrievalMode,
        embedding_service: Optional[BaseEmbeddingService] = None,
        vector_store: Optional[BaseVectorStore] = None,
        keyword_backend: str = "postgresql",
        keyword_config: Optional[Dict[str, Any]] = None,
        hybrid_config: Optional[Dict[str, Any]] = None,
    ) -> BaseRetriever:
        """根据模式创建检索器

        Args:
            mode: 检索模式
            embedding_service: Embedding 服务（语义/混合模式需要）
            vector_store: 向量存储（语义/混合模式需要）
            keyword_backend: 关键词后端类型
            keyword_config: 关键词检索器配置
            hybrid_config: 混合检索器配置

        Returns:
            检索器实例
        """
        keyword_config = keyword_config or {}
        hybrid_config = hybrid_config or {}

        if mode == RetrievalMode.SEMANTIC:
            if not embedding_service or not vector_store:
                raise ValueError(
                    "Embedding service and vector store are required "
                    "for semantic retrieval"
                )
            return RetrieverFactory.create_semantic_retriever(
                embedding_service=embedding_service,
                vector_store=vector_store,
            )

        elif mode == RetrievalMode.KEYWORD:
            return RetrieverFactory.create_keyword_retriever(
                backend=keyword_backend,
                **keyword_config,
            )

        elif mode == RetrievalMode.HYBRID:
            if not embedding_service or not vector_store:
                raise ValueError(
                    "Embedding service and vector store are required "
                    "for hybrid retrieval"
                )

            semantic = RetrieverFactory.create_semantic_retriever(
                embedding_service=embedding_service,
                vector_store=vector_store,
            )

            keyword = RetrieverFactory.create_keyword_retriever(
                backend=keyword_backend,
                **keyword_config,
            )

            return RetrieverFactory.create_hybrid_retriever(
                semantic_retriever=semantic,
                keyword_retriever=keyword,
                fusion_strategy=hybrid_config.get(
                    "fusion_strategy", FusionStrategy.RRF
                ),
                semantic_weight=hybrid_config.get("semantic_weight", 0.7),
                keyword_weight=hybrid_config.get("keyword_weight", 0.3),
                adaptive=hybrid_config.get("adaptive", False),
            )

        else:
            raise ValueError(f"Unknown retrieval mode: {mode}")


class RetrievalPipeline:
    """检索管道

    组合检索器和重排序器，提供端到端的检索体验。
    """

    def __init__(
        self,
        retriever: BaseRetriever,
        reranker: Optional[BaseReranker] = None,
    ):
        """初始化检索管道

        Args:
            retriever: 检索器
            reranker: 重排序器（可选）
        """
        self.retriever = retriever
        self.reranker = reranker

    async def search(
        self,
        query: str,
        knowledge_base_id: str,
        top_k: int = 10,
        score_threshold: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
        rerank: bool = True,
        rerank_top_k: Optional[int] = None,
    ):
        """执行检索

        Args:
            query: 查询文本
            knowledge_base_id: 知识库ID
            top_k: 返回结果数量
            score_threshold: 分数阈值
            filters: 过滤条件
            rerank: 是否使用重排序
            rerank_top_k: 重排序返回数量

        Returns:
            检索结果列表
        """
        from .base import SearchConfig

        # 如果需要重排序，获取更多初始结果
        initial_top_k = top_k * 3 if rerank and self.reranker else top_k

        config = SearchConfig(
            top_k=initial_top_k,
            score_threshold=0,  # 不在检索阶段过滤
            filters=filters or {},
        )

        # 执行检索
        results = await self.retriever.search(
            query=query,
            knowledge_base_id=knowledge_base_id,
            config=config,
            filters=filters,
        )

        # 重排序
        if rerank and self.reranker and results:
            from .rerank import RerankConfig

            rerank_config = RerankConfig(
                top_k=rerank_top_k or top_k,
                score_threshold=score_threshold,
            )

            results = await self.reranker.rerank(
                query=query,
                results=results,
                config=rerank_config,
            )
        else:
            # 不重排序时，应用阈值和 top_k
            results = [r for r in results if r.score >= score_threshold][:top_k]

        return results

    @classmethod
    def create(
        cls,
        mode: RetrievalMode = RetrievalMode.HYBRID,
        embedding_service: Optional[BaseEmbeddingService] = None,
        vector_store: Optional[BaseVectorStore] = None,
        keyword_backend: str = "postgresql",
        keyword_config: Optional[Dict[str, Any]] = None,
        hybrid_config: Optional[Dict[str, Any]] = None,
        rerank_provider: Optional[str] = None,
        rerank_api_key: Optional[str] = None,
        rerank_model: Optional[str] = None,
    ) -> "RetrievalPipeline":
        """创建检索管道

        Args:
            mode: 检索模式
            embedding_service: Embedding 服务
            vector_store: 向量存储
            keyword_backend: 关键词后端
            keyword_config: 关键词配置
            hybrid_config: 混合配置
            rerank_provider: 重排序提供商
            rerank_api_key: 重排序 API 密钥
            rerank_model: 重排序模型

        Returns:
            检索管道实例
        """
        # 创建检索器
        retriever = RetrieverFactory.create_retriever(
            mode=mode,
            embedding_service=embedding_service,
            vector_store=vector_store,
            keyword_backend=keyword_backend,
            keyword_config=keyword_config,
            hybrid_config=hybrid_config,
        )

        # 创建重排序器（可选）
        reranker = None
        if rerank_provider:
            reranker = RetrieverFactory.create_reranker(
                provider=rerank_provider,
                api_key=rerank_api_key,
                model=rerank_model,
            )

        return cls(retriever=retriever, reranker=reranker)
