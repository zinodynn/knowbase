"""
重排序服务

支持多种重排序方案：
1. Cohere Rerank API
2. Jina Rerank API
3. 本地 Cross-Encoder 模型
4. BGE Reranker
5. 基于 LLM 的重排序
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .base import SearchResult


class RerankProvider(str, Enum):
    """重排序提供商"""

    COHERE = "cohere"
    JINA = "jina"
    LOCAL = "local"  # 本地模型
    LLM = "llm"  # 基于 LLM


@dataclass
class RerankConfig:
    """重排序配置"""

    # 返回的最大结果数
    top_k: int = 10

    # 最低分数阈值
    score_threshold: float = 0.0

    # 是否返回原始文档
    return_documents: bool = True

    # 模型名称（根据提供商不同而不同）
    model: Optional[str] = None

    # 请求超时（秒）
    timeout: float = 30.0

    # 最大输入长度
    max_input_length: int = 512


class BaseReranker(ABC):
    """重排序器基类"""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        config: Optional[RerankConfig] = None,
    ) -> List[SearchResult]:
        """重新排序检索结果

        Args:
            query: 查询文本
            results: 初始检索结果
            config: 重排序配置

        Returns:
            重排序后的结果列表
        """
        pass

    def _truncate_text(self, text: str, max_length: int) -> str:
        """截断文本到指定长度

        Args:
            text: 原始文本
            max_length: 最大长度

        Returns:
            截断后的文本
        """
        if len(text) <= max_length:
            return text
        return text[:max_length]


class CohereReranker(BaseReranker):
    """Cohere Rerank API

    文档：https://docs.cohere.com/reference/rerank

    模型：
    - rerank-english-v3.0
    - rerank-multilingual-v3.0
    - rerank-english-v2.0
    - rerank-multilingual-v2.0
    """

    def __init__(
        self,
        api_key: str,
        model: str = "rerank-multilingual-v3.0",
        base_url: str = "https://api.cohere.ai/v1",
    ):
        """初始化 Cohere Reranker

        Args:
            api_key: Cohere API 密钥
            model: 模型名称
            base_url: API 基础 URL
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        config: Optional[RerankConfig] = None,
    ) -> List[SearchResult]:
        """使用 Cohere API 重排序

        Args:
            query: 查询文本
            results: 初始检索结果
            config: 重排序配置

        Returns:
            重排序后的结果列表
        """
        if not results:
            return []

        config = config or RerankConfig()
        model = config.model or self.model

        # 准备文档
        documents = [
            self._truncate_text(r.content, config.max_input_length) for r in results
        ]

        # 调用 API
        response = await self.client.post(
            f"{self.base_url}/rerank",
            json={
                "model": model,
                "query": query,
                "documents": documents,
                "top_n": config.top_k,
                "return_documents": False,
            },
            timeout=config.timeout,
        )
        response.raise_for_status()

        data = response.json()

        # 处理结果
        reranked_results = []
        for item in data["results"]:
            idx = item["index"]
            score = item["relevance_score"]

            if score >= config.score_threshold:
                original = results[idx]
                reranked = SearchResult(
                    chunk_id=original.chunk_id,
                    document_id=original.document_id,
                    content=original.content,
                    score=score,
                    metadata={
                        **original.metadata,
                        "original_score": original.score,
                        "rerank_provider": "cohere",
                        "rerank_model": model,
                    },
                )
                reranked_results.append(reranked)

        return reranked_results

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


class JinaReranker(BaseReranker):
    """Jina Rerank API

    文档：https://jina.ai/reranker/

    模型：
    - jina-reranker-v2-base-multilingual
    - jina-reranker-v1-base-en
    - jina-reranker-v1-turbo-en
    """

    def __init__(
        self,
        api_key: str,
        model: str = "jina-reranker-v2-base-multilingual",
        base_url: str = "https://api.jina.ai/v1",
    ):
        """初始化 Jina Reranker

        Args:
            api_key: Jina API 密钥
            model: 模型名称
            base_url: API 基础 URL
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        config: Optional[RerankConfig] = None,
    ) -> List[SearchResult]:
        """使用 Jina API 重排序

        Args:
            query: 查询文本
            results: 初始检索结果
            config: 重排序配置

        Returns:
            重排序后的结果列表
        """
        if not results:
            return []

        config = config or RerankConfig()
        model = config.model or self.model

        # 准备文档
        documents = [
            self._truncate_text(r.content, config.max_input_length) for r in results
        ]

        # 调用 API
        response = await self.client.post(
            f"{self.base_url}/rerank",
            json={
                "model": model,
                "query": query,
                "documents": documents,
                "top_n": config.top_k,
            },
            timeout=config.timeout,
        )
        response.raise_for_status()

        data = response.json()

        # 处理结果
        reranked_results = []
        for item in data["results"]:
            idx = item["index"]
            score = item["relevance_score"]

            if score >= config.score_threshold:
                original = results[idx]
                reranked = SearchResult(
                    chunk_id=original.chunk_id,
                    document_id=original.document_id,
                    content=original.content,
                    score=score,
                    metadata={
                        **original.metadata,
                        "original_score": original.score,
                        "rerank_provider": "jina",
                        "rerank_model": model,
                    },
                )
                reranked_results.append(reranked)

        return reranked_results

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


class LocalReranker(BaseReranker):
    """本地 Cross-Encoder 重排序器

    使用 sentence-transformers 的 CrossEncoder 模型进行本地重排序。

    推荐模型：
    - cross-encoder/ms-marco-MiniLM-L-6-v2 (快速)
    - cross-encoder/ms-marco-MiniLM-L-12-v2 (平衡)
    - BAAI/bge-reranker-base (中文支持好)
    - BAAI/bge-reranker-large (更准确)
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-base",
        device: Optional[str] = None,
    ):
        """初始化本地重排序器

        Args:
            model_name: 模型名称或路径
            device: 运行设备 (cpu/cuda)
        """
        self.model_name = model_name
        self.device = device
        self._model = None

    def _load_model(self):
        """延迟加载模型"""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(
                    self.model_name,
                    device=self.device,
                )
            except ImportError:
                raise ImportError(
                    "Please install sentence-transformers: "
                    "pip install sentence-transformers"
                )
        return self._model

    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        config: Optional[RerankConfig] = None,
    ) -> List[SearchResult]:
        """使用本地模型重排序

        Args:
            query: 查询文本
            results: 初始检索结果
            config: 重排序配置

        Returns:
            重排序后的结果列表
        """
        if not results:
            return []

        config = config or RerankConfig()

        # 在线程池中运行模型推理
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(
            None,
            self._compute_scores,
            query,
            [r.content for r in results],
            config.max_input_length,
        )

        # 创建 (分数, 索引) 对并排序
        scored_indices: List[Tuple[float, int]] = [
            (score, idx) for idx, score in enumerate(scores)
        ]
        scored_indices.sort(key=lambda x: x[0], reverse=True)

        # 构建重排序结果
        reranked_results = []
        for score, idx in scored_indices[: config.top_k]:
            if score >= config.score_threshold:
                original = results[idx]
                reranked = SearchResult(
                    chunk_id=original.chunk_id,
                    document_id=original.document_id,
                    content=original.content,
                    score=float(score),
                    metadata={
                        **original.metadata,
                        "original_score": original.score,
                        "rerank_provider": "local",
                        "rerank_model": self.model_name,
                    },
                )
                reranked_results.append(reranked)

        return reranked_results

    def _compute_scores(
        self,
        query: str,
        documents: List[str],
        max_length: int,
    ) -> List[float]:
        """计算重排序分数

        Args:
            query: 查询文本
            documents: 文档列表
            max_length: 最大输入长度

        Returns:
            分数列表
        """
        model = self._load_model()

        # 准备输入对
        pairs = [[query, self._truncate_text(doc, max_length)] for doc in documents]

        # 计算分数
        scores = model.predict(pairs)

        return scores.tolist()


class LLMReranker(BaseReranker):
    """基于 LLM 的重排序器

    使用大语言模型对检索结果进行重排序。
    适用于需要深度理解的场景，但速度较慢。
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
    ):
        """初始化 LLM Reranker

        Args:
            api_key: OpenAI API 密钥
            model: 模型名称
            base_url: API 基础 URL
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )

    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        config: Optional[RerankConfig] = None,
    ) -> List[SearchResult]:
        """使用 LLM 重排序

        Args:
            query: 查询文本
            results: 初始检索结果
            config: 重排序配置

        Returns:
            重排序后的结果列表
        """
        if not results:
            return []

        config = config or RerankConfig()

        # 限制处理的文档数量（LLM 上下文限制）
        max_docs = min(len(results), 20)
        results_to_rank = results[:max_docs]

        # 构建提示
        prompt = self._build_prompt(query, results_to_rank, config)

        # 调用 LLM
        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a search relevance expert. Your task is to "
                            "rank documents by their relevance to the query. "
                            "Output only a JSON array of document indices in order "
                            "of relevance, from most to least relevant. "
                            "Example output: [3, 1, 5, 2, 4]"
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "temperature": 0,
                "max_tokens": 500,
            },
            timeout=config.timeout,
        )
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        # 解析排序结果
        try:
            import json

            # 提取 JSON 数组
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                ranking = json.loads(content[start:end])
            else:
                ranking = list(range(len(results_to_rank)))
        except (json.JSONDecodeError, ValueError):
            # 解析失败，保持原顺序
            ranking = list(range(len(results_to_rank)))

        # 构建重排序结果
        reranked_results = []
        for rank, idx in enumerate(ranking):
            if 0 <= idx < len(results_to_rank):
                original = results_to_rank[idx]
                # 使用排名位置生成分数 (1.0 -> 0.0)
                score = 1.0 - (rank / len(ranking))

                if score >= config.score_threshold:
                    reranked = SearchResult(
                        chunk_id=original.chunk_id,
                        document_id=original.document_id,
                        content=original.content,
                        score=score,
                        metadata={
                            **original.metadata,
                            "original_score": original.score,
                            "rerank_provider": "llm",
                            "rerank_model": self.model,
                            "rerank_rank": rank + 1,
                        },
                    )
                    reranked_results.append(reranked)

        return reranked_results[: config.top_k]

    def _build_prompt(
        self,
        query: str,
        results: List[SearchResult],
        config: RerankConfig,
    ) -> str:
        """构建重排序提示

        Args:
            query: 查询文本
            results: 检索结果
            config: 配置

        Returns:
            提示文本
        """
        docs_text = ""
        for idx, result in enumerate(results):
            truncated = self._truncate_text(result.content, config.max_input_length)
            docs_text += f"\n[Document {idx}]\n{truncated}\n"

        return f"""Query: {query}

Documents to rank:
{docs_text}

Rank the documents by relevance to the query. Return only a JSON array of document indices from most to least relevant."""

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


class RerankerFactory:
    """重排序器工厂"""

    @staticmethod
    def create(
        provider: RerankProvider,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> BaseReranker:
        """创建重排序器

        Args:
            provider: 提供商类型
            api_key: API 密钥
            model: 模型名称
            **kwargs: 其他参数

        Returns:
            重排序器实例
        """
        if provider == RerankProvider.COHERE:
            if not api_key:
                raise ValueError("Cohere API key is required")
            return CohereReranker(
                api_key=api_key,
                model=model or "rerank-multilingual-v3.0",
                **kwargs,
            )

        elif provider == RerankProvider.JINA:
            if not api_key:
                raise ValueError("Jina API key is required")
            return JinaReranker(
                api_key=api_key,
                model=model or "jina-reranker-v2-base-multilingual",
                **kwargs,
            )

        elif provider == RerankProvider.LOCAL:
            return LocalReranker(
                model_name=model or "BAAI/bge-reranker-base",
                **kwargs,
            )

        elif provider == RerankProvider.LLM:
            if not api_key:
                raise ValueError("LLM API key is required")
            return LLMReranker(
                api_key=api_key,
                model=model or "gpt-4o-mini",
                **kwargs,
            )

        else:
            raise ValueError(f"Unknown rerank provider: {provider}")
