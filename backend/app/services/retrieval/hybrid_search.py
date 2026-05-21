"""
混合检索服务

支持多种融合策略：
1. RRF (Reciprocal Rank Fusion) - 互惠排名融合
2. 加权融合 - 基于分数的加权组合
3. 线性组合 - 简单的线性加权
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .base import BaseRetriever, SearchConfig, SearchResult
from .keyword_search import KeywordSearch
from .semantic_search import SemanticSearch


class FusionStrategy(str, Enum):
    """融合策略枚举"""

    RRF = "rrf"  # Reciprocal Rank Fusion
    WEIGHTED = "weighted"  # 加权融合
    LINEAR = "linear"  # 线性组合


@dataclass
class HybridConfig(SearchConfig):
    """混合检索配置"""

    # 融合策略
    fusion_strategy: FusionStrategy = FusionStrategy.RRF

    # 语义检索权重 (0-1)
    semantic_weight: float = 0.7

    # 关键词检索权重 (0-1)
    keyword_weight: float = 0.3

    # RRF 参数 k (常数，用于平滑排名)
    rrf_k: int = 60

    # 是否启用语义检索
    enable_semantic: bool = True

    # 是否启用关键词检索
    enable_keyword: bool = True

    # 各检索器返回的最大数量（用于融合前）
    retriever_top_k: int = 50

    # 去重策略
    dedup_by: str = "chunk_id"  # chunk_id 或 content_hash


class HybridRetriever(BaseRetriever):
    """混合检索器

    结合语义检索和关键词检索的优势：
    - 语义检索：理解查询意图，处理同义词
    - 关键词检索：精确匹配，处理专业术语
    """

    def __init__(
        self,
        semantic_retriever: SemanticSearch,
        keyword_retriever: KeywordSearch,
        default_config: Optional[HybridConfig] = None,
    ):
        """初始化混合检索器

        Args:
            semantic_retriever: 语义检索器
            keyword_retriever: 关键词检索器
            default_config: 默认配置
        """
        self.semantic_retriever = semantic_retriever
        self.keyword_retriever = keyword_retriever
        self.default_config = default_config or HybridConfig()

    async def search(
        self,
        query: str,
        knowledge_base_id: str,
        config: Optional[SearchConfig] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """执行混合检索

        Args:
            query: 查询文本
            knowledge_base_id: 知识库ID
            config: 检索配置
            filters: 过滤条件

        Returns:
            融合后的检索结果列表
        """
        # 合并配置
        hybrid_config = self._merge_config(config)

        # 并行执行两种检索
        tasks = []

        # 准备子检索器配置
        retriever_config = SearchConfig(
            top_k=hybrid_config.retriever_top_k,
            score_threshold=0,  # 不在子检索器中过滤
            filters=hybrid_config.filters,
        )

        if hybrid_config.enable_semantic:
            tasks.append(
                self.semantic_retriever.search(
                    query=query,
                    knowledge_base_id=knowledge_base_id,
                    config=retriever_config,
                    filters=filters,
                )
            )
        else:
            tasks.append(asyncio.coroutine(lambda: [])())

        if hybrid_config.enable_keyword:
            tasks.append(
                self.keyword_retriever.search(
                    query=query,
                    knowledge_base_id=knowledge_base_id,
                    config=retriever_config,
                    filters=filters,
                )
            )
        else:
            tasks.append(asyncio.coroutine(lambda: [])())

        # 等待所有检索完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        semantic_results: List[SearchResult] = []
        keyword_results: List[SearchResult] = []

        if hybrid_config.enable_semantic:
            if isinstance(results[0], Exception):
                # 记录错误但继续
                print(f"Semantic search error: {results[0]}")
            else:
                semantic_results = results[0]

        if hybrid_config.enable_keyword:
            idx = 1 if hybrid_config.enable_semantic else 0
            if isinstance(results[idx], Exception):
                print(f"Keyword search error: {results[idx]}")
            else:
                keyword_results = results[idx] if len(results) > idx else []

        # 融合结果
        fused_results = self._fuse_results(
            semantic_results=semantic_results,
            keyword_results=keyword_results,
            config=hybrid_config,
        )

        # 应用分数阈值和 top_k
        filtered_results = [
            r for r in fused_results if r.score >= hybrid_config.score_threshold
        ]

        return filtered_results[: hybrid_config.top_k]

    def _merge_config(self, config: Optional[SearchConfig]) -> HybridConfig:
        """合并配置"""
        if config is None:
            return self.default_config

        if isinstance(config, HybridConfig):
            return config

        # 从基础配置创建混合配置
        return HybridConfig(
            top_k=config.top_k,
            score_threshold=config.score_threshold,
            metadata_filters=config.metadata_filters,
            fusion_strategy=self.default_config.fusion_strategy,
            semantic_weight=self.default_config.semantic_weight,
            keyword_weight=self.default_config.keyword_weight,
            rrf_k=self.default_config.rrf_k,
            enable_semantic=self.default_config.enable_semantic,
            enable_keyword=self.default_config.enable_keyword,
            retriever_top_k=self.default_config.retriever_top_k,
            dedup_by=self.default_config.dedup_by,
        )

    def _fuse_results(
        self,
        semantic_results: List[SearchResult],
        keyword_results: List[SearchResult],
        config: HybridConfig,
    ) -> List[SearchResult]:
        """融合检索结果

        Args:
            semantic_results: 语义检索结果
            keyword_results: 关键词检索结果
            config: 混合配置

        Returns:
            融合后的结果列表
        """
        if config.fusion_strategy == FusionStrategy.RRF:
            return self._rrf_fusion(
                semantic_results,
                keyword_results,
                k=config.rrf_k,
            )
        elif config.fusion_strategy == FusionStrategy.WEIGHTED:
            return self._weighted_fusion(
                semantic_results,
                keyword_results,
                semantic_weight=config.semantic_weight,
                keyword_weight=config.keyword_weight,
            )
        elif config.fusion_strategy == FusionStrategy.LINEAR:
            return self._linear_fusion(
                semantic_results,
                keyword_results,
                semantic_weight=config.semantic_weight,
                keyword_weight=config.keyword_weight,
            )
        else:
            raise ValueError(f"Unknown fusion strategy: {config.fusion_strategy}")

    def _rrf_fusion(
        self,
        semantic_results: List[SearchResult],
        keyword_results: List[SearchResult],
        k: int = 60,
    ) -> List[SearchResult]:
        """Reciprocal Rank Fusion (RRF) 融合

        RRF 分数 = Σ 1 / (k + rank_i)

        其中 k 是一个常数（通常为 60），rank_i 是文档在第 i 个排名列表中的位置。

        优点：
        - 不依赖于原始分数的尺度
        - 对异常值不敏感
        - 实现简单

        Args:
            semantic_results: 语义检索结果
            keyword_results: 关键词检索结果
            k: RRF 常数

        Returns:
            融合后的结果列表
        """
        # 计算每个文档的 RRF 分数
        rrf_scores: Dict[str, float] = {}
        result_map: Dict[str, SearchResult] = {}

        # 处理语义检索结果
        for rank, result in enumerate(semantic_results, start=1):
            doc_id = result.chunk_id
            rrf_score = 1.0 / (k + rank)
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + rrf_score

            if doc_id not in result_map:
                result_map[doc_id] = result
            else:
                # 合并 metadata
                self._merge_metadata(result_map[doc_id], result, "semantic")

        # 处理关键词检索结果
        for rank, result in enumerate(keyword_results, start=1):
            doc_id = result.chunk_id
            rrf_score = 1.0 / (k + rank)
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + rrf_score

            if doc_id not in result_map:
                result_map[doc_id] = result
            else:
                self._merge_metadata(result_map[doc_id], result, "keyword")

        # 更新分数并排序
        fused_results = []
        for doc_id, rrf_score in rrf_scores.items():
            result = result_map[doc_id]
            # 创建新结果，更新分数
            fused_result = SearchResult(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                content=result.content,
                score=rrf_score,
                metadata={
                    **result.metadata,
                    "fusion_method": "rrf",
                    "rrf_k": k,
                },
            )
            fused_results.append(fused_result)

        # 按 RRF 分数降序排序
        fused_results.sort(key=lambda x: x.score, reverse=True)

        return fused_results

    def _weighted_fusion(
        self,
        semantic_results: List[SearchResult],
        keyword_results: List[SearchResult],
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> List[SearchResult]:
        """加权融合

        将原始分数归一化后进行加权组合。

        Args:
            semantic_results: 语义检索结果
            keyword_results: 关键词检索结果
            semantic_weight: 语义检索权重
            keyword_weight: 关键词检索权重

        Returns:
            融合后的结果列表
        """
        # 归一化分数
        semantic_normalized = self._normalize_scores(semantic_results)
        keyword_normalized = self._normalize_scores(keyword_results)

        # 加权分数映射
        weighted_scores: Dict[str, float] = {}
        result_map: Dict[str, SearchResult] = {}

        # 处理语义检索结果
        for result, norm_score in zip(semantic_results, semantic_normalized):
            doc_id = result.chunk_id
            weighted_scores[doc_id] = (
                weighted_scores.get(doc_id, 0) + norm_score * semantic_weight
            )

            if doc_id not in result_map:
                result_map[doc_id] = result

        # 处理关键词检索结果
        for result, norm_score in zip(keyword_results, keyword_normalized):
            doc_id = result.chunk_id
            weighted_scores[doc_id] = (
                weighted_scores.get(doc_id, 0) + norm_score * keyword_weight
            )

            if doc_id not in result_map:
                result_map[doc_id] = result

        # 构建融合结果
        fused_results = []
        for doc_id, weighted_score in weighted_scores.items():
            result = result_map[doc_id]
            fused_result = SearchResult(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                content=result.content,
                score=weighted_score,
                metadata={
                    **result.metadata,
                    "fusion_method": "weighted",
                    "semantic_weight": semantic_weight,
                    "keyword_weight": keyword_weight,
                },
            )
            fused_results.append(fused_result)

        # 按分数降序排序
        fused_results.sort(key=lambda x: x.score, reverse=True)

        return fused_results

    def _linear_fusion(
        self,
        semantic_results: List[SearchResult],
        keyword_results: List[SearchResult],
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> List[SearchResult]:
        """线性融合

        直接使用原始分数进行线性加权，不进行归一化。
        适用于分数已经在相同尺度上的情况。

        Args:
            semantic_results: 语义检索结果
            keyword_results: 关键词检索结果
            semantic_weight: 语义检索权重
            keyword_weight: 关键词检索权重

        Returns:
            融合后的结果列表
        """
        linear_scores: Dict[str, float] = {}
        result_map: Dict[str, SearchResult] = {}

        # 处理语义检索结果
        for result in semantic_results:
            doc_id = result.chunk_id
            linear_scores[doc_id] = (
                linear_scores.get(doc_id, 0) + result.score * semantic_weight
            )

            if doc_id not in result_map:
                result_map[doc_id] = result

        # 处理关键词检索结果
        for result in keyword_results:
            doc_id = result.chunk_id
            linear_scores[doc_id] = (
                linear_scores.get(doc_id, 0) + result.score * keyword_weight
            )

            if doc_id not in result_map:
                result_map[doc_id] = result

        # 构建融合结果
        fused_results = []
        for doc_id, linear_score in linear_scores.items():
            result = result_map[doc_id]
            fused_result = SearchResult(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                content=result.content,
                score=linear_score,
                metadata={
                    **result.metadata,
                    "fusion_method": "linear",
                    "semantic_weight": semantic_weight,
                    "keyword_weight": keyword_weight,
                },
            )
            fused_results.append(fused_result)

        # 按分数降序排序
        fused_results.sort(key=lambda x: x.score, reverse=True)

        return fused_results

    def _normalize_scores(self, results: List[SearchResult]) -> List[float]:
        """归一化分数到 [0, 1] 范围

        使用 min-max 归一化

        Args:
            results: 检索结果列表

        Returns:
            归一化后的分数列表
        """
        if not results:
            return []

        scores = [r.score for r in results]
        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score:
            return [1.0] * len(results)

        return [(s - min_score) / (max_score - min_score) for s in scores]

    def _merge_metadata(
        self,
        target: SearchResult,
        source: SearchResult,
        source_type: str,
    ) -> None:
        """合并元数据"""
        target.metadata[f"{source_type}_score"] = source.score
        target.metadata[f"{source_type}_rank"] = source.metadata.get("rank")


class AdaptiveHybridRetriever(HybridRetriever):
    """自适应混合检索器

    根据查询特征动态调整检索策略：
    - 短查询：更依赖关键词检索
    - 长查询/问句：更依赖语义检索
    - 专业术语：更依赖关键词检索
    """

    def __init__(
        self,
        semantic_retriever: SemanticSearch,
        keyword_retriever: KeywordSearch,
        default_config: Optional[HybridConfig] = None,
    ):
        super().__init__(semantic_retriever, keyword_retriever, default_config)

        # 问句关键词
        self.question_words = {
            "什么",
            "为什么",
            "怎么",
            "如何",
            "哪里",
            "哪个",
            "谁",
            "what",
            "why",
            "how",
            "where",
            "which",
            "who",
            "when",
        }

    async def search(
        self,
        query: str,
        knowledge_base_id: str,
        config: Optional[SearchConfig] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """执行自适应混合检索"""
        # 分析查询特征
        query_features = self._analyze_query(query)

        # 调整权重
        adjusted_config = self._adjust_weights(config, query_features)

        # 执行混合检索
        return await super().search(
            query=query,
            knowledge_base_id=knowledge_base_id,
            config=adjusted_config,
            filters=filters,
        )

    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """分析查询特征

        Args:
            query: 查询文本

        Returns:
            查询特征字典
        """
        query_lower = query.lower()
        words = query.split()

        features = {
            "length": len(query),
            "word_count": len(words),
            "is_question": any(qw in query_lower for qw in self.question_words)
            or query.endswith("?")
            or query.endswith("？"),
            "has_quotes": '"' in query or "'" in query or '"' in query or '"' in query,
            "avg_word_length": sum(len(w) for w in words) / max(len(words), 1),
        }

        return features

    def _adjust_weights(
        self,
        config: Optional[SearchConfig],
        features: Dict[str, Any],
    ) -> HybridConfig:
        """根据查询特征调整权重

        Args:
            config: 原始配置
            features: 查询特征

        Returns:
            调整后的混合配置
        """
        base_config = self._merge_config(config)

        # 基础权重
        semantic_weight = base_config.semantic_weight
        keyword_weight = base_config.keyword_weight

        # 根据特征调整

        # 1. 短查询更依赖关键词
        if features["word_count"] <= 2:
            keyword_weight += 0.1
            semantic_weight -= 0.1

        # 2. 问句更依赖语义
        if features["is_question"]:
            semantic_weight += 0.15
            keyword_weight -= 0.15

        # 3. 引号内容更依赖关键词（精确匹配）
        if features["has_quotes"]:
            keyword_weight += 0.2
            semantic_weight -= 0.2

        # 确保权重在有效范围内
        semantic_weight = max(0.1, min(0.9, semantic_weight))
        keyword_weight = max(0.1, min(0.9, keyword_weight))

        # 归一化权重
        total = semantic_weight + keyword_weight
        semantic_weight /= total
        keyword_weight /= total

        return HybridConfig(
            top_k=base_config.top_k,
            score_threshold=base_config.score_threshold,
            filters=base_config.filters,
            fusion_strategy=base_config.fusion_strategy,
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight,
            rrf_k=base_config.rrf_k,
            enable_semantic=base_config.enable_semantic,
            enable_keyword=base_config.enable_keyword,
            retriever_top_k=base_config.retriever_top_k,
            dedup_by=base_config.dedup_by,
        )
