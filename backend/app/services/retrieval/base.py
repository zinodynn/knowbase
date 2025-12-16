"""
检索服务基类和数据结构定义
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FusionMethod(str, Enum):
    """融合方法"""

    RRF = "rrf"  # Reciprocal Rank Fusion
    WEIGHTED = "weighted"  # 加权融合


@dataclass
class SearchConfig:
    """检索配置"""

    # 基础配置
    top_k: int = 10
    score_threshold: float = 0.0

    # 混合检索配置
    search_type: str = "hybrid"  # semantic, keyword, hybrid
    semantic_weight: float = 0.7
    keyword_weight: float = 0.3
    fusion_method: FusionMethod = FusionMethod.RRF
    rrf_k: int = 60  # RRF 参数

    # Rerank 配置
    enable_rerank: bool = False
    rerank_top_k: int = 5

    # 过滤器
    document_ids: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    date_start: Optional[datetime] = None
    date_end: Optional[datetime] = None
    metadata_filters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """检索结果"""

    chunk_id: str
    document_id: str
    content: str
    score: float
    chunk_index: int = 0
    document_filename: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    highlights: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "content": self.content,
            "score": self.score,
            "chunk_index": self.chunk_index,
            "document_filename": self.document_filename,
            "metadata": self.metadata,
            "highlights": self.highlights,
        }


class BaseRetriever(ABC):
    """检索器基类"""

    @abstractmethod
    async def search(
        self,
        kb_id: str,
        query: str,
        config: Optional[SearchConfig] = None,
    ) -> List[SearchResult]:
        """
        执行检索

        Args:
            kb_id: 知识库 ID
            query: 查询文本
            config: 检索配置

        Returns:
            检索结果列表
        """
        pass

    def _apply_filters(
        self,
        results: List[SearchResult],
        config: SearchConfig,
    ) -> List[SearchResult]:
        """
        应用过滤器

        Args:
            results: 原始结果
            config: 检索配置

        Returns:
            过滤后的结果
        """
        filtered = results

        # 按分数阈值过滤
        if config.score_threshold > 0:
            filtered = [r for r in filtered if r.score >= config.score_threshold]

        # 按文档 ID 过滤
        if config.document_ids:
            doc_ids_set = set(config.document_ids)
            filtered = [r for r in filtered if r.document_id in doc_ids_set]

        # 按标签过滤
        if config.tags:
            tags_set = set(config.tags)
            filtered = [
                r for r in filtered if tags_set.intersection(r.metadata.get("tags", []))
            ]

        return filtered

    def _normalize_scores(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Min-Max 归一化分数

        Args:
            results: 结果列表

        Returns:
            归一化后的结果
        """
        if not results:
            return results

        scores = [r.score for r in results]
        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score:
            for r in results:
                r.score = 1.0
        else:
            for r in results:
                r.score = (r.score - min_score) / (max_score - min_score)

        return results


class RetrievalMode(Enum):
    """检索模式枚举"""

    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
