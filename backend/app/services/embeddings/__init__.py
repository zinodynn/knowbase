"""
向量化服务模块

支持多种 Embedding 服务提供商：
- OpenAI API
- Azure OpenAI API
- 自定义 API（兼容 OpenAI 格式）
"""

from app.services.embeddings.base import (
    BaseEmbeddingService,
    EmbeddingConfig,
    EmbeddingResult,
)
from app.services.embeddings.factory import EmbeddingFactory, create_embedding_service
from app.services.embeddings.openai_embedding import OpenAIEmbeddingService

__all__ = [
    "BaseEmbeddingService",
    "EmbeddingConfig",
    "EmbeddingResult",
    "OpenAIEmbeddingService",
    "EmbeddingFactory",
    "create_embedding_service",
]
