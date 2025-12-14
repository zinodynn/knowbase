"""
Embedding 服务工厂

根据配置创建对应的 Embedding 服务实例
"""

import logging
from typing import Optional

from app.services.embeddings.base import (
    BaseEmbeddingService,
    EmbeddingConfig,
    EmbeddingProvider,
)
from app.services.embeddings.openai_embedding import (
    AzureEmbeddingService,
    OpenAIEmbeddingService,
)

logger = logging.getLogger(__name__)


class EmbeddingFactory:
    """Embedding 服务工厂"""

    @staticmethod
    def create(config: EmbeddingConfig) -> BaseEmbeddingService:
        """
        根据配置创建 Embedding 服务

        Args:
            config: 服务配置

        Returns:
            Embedding 服务实例

        Raises:
            ValueError: 不支持的提供商
        """
        if config.provider == EmbeddingProvider.OPENAI:
            return OpenAIEmbeddingService(config)

        elif config.provider == EmbeddingProvider.AZURE:
            return AzureEmbeddingService(config)

        elif config.provider == EmbeddingProvider.CUSTOM:
            # 自定义 API 使用 OpenAI 兼容格式
            return OpenAIEmbeddingService(config)

        else:
            raise ValueError(f"Unsupported embedding provider: {config.provider}")

    @staticmethod
    def from_model_config(model_config: dict) -> BaseEmbeddingService:
        """
        从数据库模型配置创建 Embedding 服务

        Args:
            model_config: 模型配置字典（来自 model_configs 表）

        Returns:
            Embedding 服务实例
        """
        # 解析提供商
        provider_str = model_config.get("provider", "openai").lower()
        try:
            provider = EmbeddingProvider(provider_str)
        except ValueError:
            provider = EmbeddingProvider.CUSTOM

        config = EmbeddingConfig(
            provider=provider,
            api_key=model_config.get("api_key", ""),
            api_base=model_config.get("api_base"),
            model=model_config.get("model_name", "text-embedding-3-small"),
            dimension=model_config.get("embedding_dimension", 1536),
            azure_endpoint=model_config.get("azure_endpoint"),
            azure_deployment=model_config.get("azure_deployment"),
            api_version=model_config.get("api_version", "2024-02-01"),
            timeout=model_config.get("timeout", 30),
            max_retries=model_config.get("max_retries", 3),
            batch_size=model_config.get("batch_size", 100),
        )

        return EmbeddingFactory.create(config)


def create_embedding_service(
    provider: str = "openai",
    api_key: str = "",
    model: str = "text-embedding-3-small",
    dimension: int = 1536,
    api_base: Optional[str] = None,
    **kwargs,
) -> BaseEmbeddingService:
    """
    创建 Embedding 服务的便捷函数

    Args:
        provider: 提供商（openai, azure, custom）
        api_key: API 密钥
        model: 模型名称
        dimension: 向量维度
        api_base: API 基础 URL（custom 提供商必需）
        **kwargs: 其他配置参数

    Returns:
        Embedding 服务实例
    """
    try:
        provider_enum = EmbeddingProvider(provider.lower())
    except ValueError:
        provider_enum = EmbeddingProvider.CUSTOM

    config = EmbeddingConfig(
        provider=provider_enum,
        api_key=api_key,
        api_base=api_base,
        model=model,
        dimension=dimension,
        **kwargs,
    )

    return EmbeddingFactory.create(config)
