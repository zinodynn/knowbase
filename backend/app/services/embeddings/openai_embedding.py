"""
OpenAI Embedding 服务

支持 OpenAI API 和兼容 OpenAI 格式的自定义 API
"""

import asyncio
import logging
import time
from typing import List, Optional

import httpx
from app.services.embeddings.base import (
    BaseEmbeddingService,
    EmbeddingConfig,
    EmbeddingProvider,
    EmbeddingResult,
)

logger = logging.getLogger(__name__)


class OpenAIEmbeddingService(BaseEmbeddingService):
    """OpenAI Embedding 服务"""

    # OpenAI API 默认地址
    DEFAULT_API_BASE = "https://api.openai.com/v1"

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)

        # 确定 API 基础 URL
        if config.provider == EmbeddingProvider.AZURE:
            if not config.azure_endpoint:
                raise ValueError("Azure endpoint is required for Azure provider")
            self.api_base = f"{config.azure_endpoint.rstrip('/')}/openai/deployments/{config.azure_deployment}"
        else:
            self.api_base = config.api_base or self.DEFAULT_API_BASE

        # HTTP 客户端配置
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            )
        return self._client

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_headers(self) -> dict:
        """获取请求头"""
        if self.config.provider == EmbeddingProvider.AZURE:
            return {
                "api-key": self.config.api_key,
                "Content-Type": "application/json",
            }
        else:
            return {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            }

    def _get_embedding_url(self) -> str:
        """获取 embedding API URL"""
        if self.config.provider == EmbeddingProvider.AZURE:
            return f"{self.api_base}/embeddings?api-version={self.config.azure_api_version}"
        else:
            return f"{self.api_base}/embeddings"

    async def embed_text(
        self,
        text: str,
        user_id: Optional[str] = None,
        kb_id: Optional[str] = None,
    ) -> List[float]:
        """
        将单个文本转换为向量

        Args:
            text: 输入文本
            user_id: 用户 ID
            kb_id: 知识库 ID

        Returns:
            向量
        """
        result = await self.embed_texts([text], user_id, kb_id)
        return result.vectors[0] if result.vectors else []

    async def embed_texts(
        self,
        texts: List[str],
        user_id: Optional[str] = None,
        kb_id: Optional[str] = None,
    ) -> EmbeddingResult:
        """
        批量将文本转换为向量

        Args:
            texts: 输入文本列表
            user_id: 用户 ID
            kb_id: 知识库 ID

        Returns:
            EmbeddingResult 结果对象
        """
        if not texts:
            return EmbeddingResult(vectors=[], model=self.model)

        all_vectors = []
        total_usage = {"prompt_tokens": 0, "total_tokens": 0}
        total_latency = 0

        # 分批处理
        batch_size = self.config.batch_size
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            result = await self._embed_batch(batch, user_id, kb_id)

            all_vectors.extend(result.vectors)
            total_usage["prompt_tokens"] += result.usage.get("prompt_tokens", 0)
            total_usage["total_tokens"] += result.usage.get("total_tokens", 0)
            total_latency += result.latency_ms

        return EmbeddingResult(
            vectors=all_vectors,
            model=self.model,
            usage=total_usage,
            latency_ms=total_latency,
        )

    async def _embed_batch(
        self,
        texts: List[str],
        user_id: Optional[str] = None,
        kb_id: Optional[str] = None,
    ) -> EmbeddingResult:
        """
        处理一批文本的 embedding

        Args:
            texts: 输入文本列表
            user_id: 用户 ID
            kb_id: 知识库 ID

        Returns:
            EmbeddingResult 结果对象
        """
        url = self._get_embedding_url()
        headers = self._get_headers()

        # 构建请求体
        payload = {
            "input": texts,
            "model": self.model,
        }

        # 如果指定了维度（OpenAI 新模型支持）
        if self.config.dimension and "text-embedding-3" in self.model:
            payload["dimensions"] = self.config.dimension

        # 发送请求（带重试）
        start_time = time.time()
        last_error = None

        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.post(
                    url,
                    headers=headers,
                    json=payload,
                )

                latency_ms = int((time.time() - start_time) * 1000)

                if response.status_code == 200:
                    data = response.json()

                    # 提取向量（按 index 排序）
                    embeddings = sorted(data.get("data", []), key=lambda x: x["index"])
                    vectors = [e["embedding"] for e in embeddings]

                    usage = data.get("usage", {})

                    # 记录日志
                    self._log_call(
                        user_id=user_id,
                        kb_id=kb_id,
                        input_length=sum(len(t) for t in texts),
                        output_dimension=len(vectors[0]) if vectors else 0,
                        token_count=usage.get("total_tokens", 0),
                        latency_ms=latency_ms,
                    )

                    return EmbeddingResult(
                        vectors=vectors,
                        model=data.get("model", self.model),
                        usage=usage,
                        latency_ms=latency_ms,
                    )
                else:
                    error_msg = f"API error: {response.status_code} - {response.text}"
                    logger.warning(f"Embedding request failed: {error_msg}")
                    last_error = error_msg

                    # 429 (Rate limit) 或 5xx 错误时重试
                    if response.status_code == 429 or response.status_code >= 500:
                        await asyncio.sleep(2**attempt)  # 指数退避
                        continue
                    else:
                        break

            except httpx.TimeoutException as e:
                last_error = f"Request timeout: {e}"
                logger.warning(f"Embedding request timeout: {e}")
                await asyncio.sleep(2**attempt)

            except Exception as e:
                last_error = str(e)
                logger.error(f"Embedding request error: {e}")
                await asyncio.sleep(2**attempt)

        # 所有重试都失败
        latency_ms = int((time.time() - start_time) * 1000)
        self._log_call(
            user_id=user_id,
            kb_id=kb_id,
            input_length=sum(len(t) for t in texts),
            output_dimension=0,
            token_count=0,
            latency_ms=latency_ms,
            status="failed",
            error_message=last_error,
        )

        raise RuntimeError(
            f"Embedding request failed after {self.config.max_retries} retries: {last_error}"
        )


class AzureEmbeddingService(OpenAIEmbeddingService):
    """Azure OpenAI Embedding 服务"""

    def __init__(self, config: EmbeddingConfig):
        # 确保使用 Azure provider
        config.provider = EmbeddingProvider.AZURE
        super().__init__(config)
