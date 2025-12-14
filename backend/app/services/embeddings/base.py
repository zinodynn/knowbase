"""
向量化服务基类和数据结构定义
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EmbeddingProvider(str, Enum):
    """Embedding 服务提供商"""

    OPENAI = "openai"
    AZURE = "azure"
    CUSTOM = "custom"  # 自定义 API（兼容 OpenAI 格式）


@dataclass
class EmbeddingConfig:
    """Embedding 服务配置"""

    provider: EmbeddingProvider = EmbeddingProvider.OPENAI
    api_key: str = ""
    api_base: Optional[str] = None  # API 基础 URL
    model: str = "text-embedding-3-small"  # 模型名称
    dimension: int = 1536  # 向量维度

    # Azure 特有配置
    azure_endpoint: Optional[str] = None
    azure_deployment: Optional[str] = None
    api_version: str = "2024-02-01"

    # 请求配置
    timeout: int = 30  # 超时时间（秒）
    max_retries: int = 3  # 最大重试次数
    batch_size: int = 100  # 批量请求大小

    # 额外配置
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmbeddingResult:
    """Embedding 结果"""

    vectors: List[List[float]]  # 向量列表
    model: str  # 使用的模型
    usage: Dict[str, int] = field(default_factory=dict)  # token 使用量
    latency_ms: int = 0  # 延迟（毫秒）

    @property
    def dimension(self) -> int:
        """向量维度"""
        if self.vectors and len(self.vectors) > 0:
            return len(self.vectors[0])
        return 0

    @property
    def total_tokens(self) -> int:
        """总 token 数"""
        return self.usage.get("total_tokens", 0)


@dataclass
class CallLog:
    """API 调用日志"""

    user_id: Optional[str] = None
    kb_id: Optional[str] = None
    call_type: str = "embedding"
    model_provider: str = ""
    model_name: str = ""
    input_text_length: int = 0
    output_dimension: int = 0
    token_count: int = 0
    latency_ms: int = 0
    status: str = "success"
    error_message: Optional[str] = None
    cost_estimate: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)


class BaseEmbeddingService(ABC):
    """Embedding 服务基类"""

    def __init__(self, config: EmbeddingConfig):
        """
        初始化 Embedding 服务

        Args:
            config: 服务配置
        """
        self.config = config
        self._call_logs: List[CallLog] = []

    @property
    def provider(self) -> str:
        """获取提供商名称"""
        return self.config.provider.value

    @property
    def model(self) -> str:
        """获取模型名称"""
        return self.config.model

    @property
    def dimension(self) -> int:
        """获取向量维度"""
        return self.config.dimension

    @abstractmethod
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
            user_id: 用户 ID（用于日志记录）
            kb_id: 知识库 ID（用于日志记录）

        Returns:
            向量
        """
        pass

    @abstractmethod
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
            user_id: 用户 ID（用于日志记录）
            kb_id: 知识库 ID（用于日志记录）

        Returns:
            EmbeddingResult 结果对象
        """
        pass

    def _log_call(
        self,
        user_id: Optional[str],
        kb_id: Optional[str],
        input_length: int,
        output_dimension: int,
        token_count: int,
        latency_ms: int,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> CallLog:
        """
        记录 API 调用日志

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID
            input_length: 输入文本长度
            output_dimension: 输出向量维度
            token_count: token 数量
            latency_ms: 延迟（毫秒）
            status: 状态
            error_message: 错误信息

        Returns:
            CallLog 对象
        """
        log = CallLog(
            user_id=user_id,
            kb_id=kb_id,
            call_type="embedding",
            model_provider=self.provider,
            model_name=self.model,
            input_text_length=input_length,
            output_dimension=output_dimension,
            token_count=token_count,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
            cost_estimate=self._estimate_cost(token_count),
        )

        self._call_logs.append(log)

        # 只保留最近 1000 条日志
        if len(self._call_logs) > 1000:
            self._call_logs = self._call_logs[-1000:]

        return log

    def _estimate_cost(self, token_count: int) -> float:
        """
        估算成本

        Args:
            token_count: token 数量

        Returns:
            估算成本（美元）
        """
        # 默认使用 text-embedding-3-small 的价格
        # $0.00002 per 1K tokens
        cost_per_1k = 0.00002

        # 根据模型调整价格
        model = self.model.lower()
        if "text-embedding-3-large" in model:
            cost_per_1k = 0.00013
        elif "text-embedding-ada-002" in model:
            cost_per_1k = 0.0001

        return (token_count / 1000) * cost_per_1k

    def get_recent_logs(self, limit: int = 100) -> List[CallLog]:
        """
        获取最近的调用日志

        Args:
            limit: 返回数量限制

        Returns:
            日志列表
        """
        return self._call_logs[-limit:]

    def clear_logs(self) -> None:
        """清空调用日志"""
        self._call_logs.clear()
