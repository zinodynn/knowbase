"""
KnowBase 配置模块
从环境变量加载所有配置
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """应用配置类"""

    print(f"加载配置文件: {ENV_FILE}")
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # 应用配置
    APP_NAME: str = Field(default="KnowBase", validation_alias="PROJECT_NAME")
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Optional extra env vars (commonly present in .env templates)
    ENVIRONMENT: str = "development"
    FULLTEXT_ENGINE: str = "postgres"

    # 数据库配置
    DB_USER: str = "knowbase"
    DB_PASSWORD: str = "knowbase123"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "knowbase"
    DATABASE_URL: Optional[str] = (
        "postgresql+asyncpg://knowbase:knowbase123@localhost:5432/knowbase"
    )

    @property
    def database_url(self) -> str:
        """获取数据库连接 URL"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def database_url_sync(self) -> str:
        """获取同步数据库连接 URL（用于 Alembic）"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_URL: Optional[str] = None

    @property
    def redis_url(self) -> str:
        """获取 Redis 连接 URL"""
        if self.REDIS_URL:
            return self.REDIS_URL
        if self.REDIS_PASSWORD:
            return (
                f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
            )
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # MinIO 配置
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_BUCKET: str = "knowbase"
    MINIO_SECURE: bool = False

    # 向量数据库配置
    VECTOR_DB_TYPE: str = "qdrant"  # qdrant, milvus, weaviate
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[str] = None

    @property
    def QDRANT_URL(self) -> str:
        """获取 Qdrant 连接 URL"""
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

    # Embedding 配置
    EMBEDDING_PROVIDER: str = "openai"  # openai, azure, qwen, private
    EMBEDDING_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    EMBEDDING_MODEL: str = "text-embedding-v2"
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_DIMENSION: int = 1536

    # Azure Embedding 配置（可选）
    AZURE_ENDPOINT: Optional[str] = None
    AZURE_API_KEY: Optional[str] = None
    AZURE_API_VERSION: str = "2024-02-01"
    AZURE_EMBEDDING_DEPLOYMENT: Optional[str] = None

    # Rerank 配置
    RERANK_PROVIDER: str = "cohere"  # cohere, jina, local, llm
    COHERE_API_KEY: Optional[str] = None
    JINA_API_KEY: Optional[str] = None
    RERANK_MODEL: Optional[str] = None  # 使用默认模型

    # OpenAI 配置（用于 LLM Rerank 等）
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # 安全配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ENCRYPTION_KEY: str = "your-encryption-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 3
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # CORS 配置
    # Accept either ALLOWED_ORIGINS (comma-separated) or CORS_ORIGINS (often JSON list)
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000",
        validation_alias="CORS_ORIGINS",
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        """获取允许的域名列表"""
        raw = self.ALLOWED_ORIGINS.strip()
        if raw.startswith("["):
            try:
                value = json.loads(raw)
                if isinstance(value, list):
                    return [
                        str(origin).strip() for origin in value if str(origin).strip()
                    ]
            except Exception:
                pass
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    # Celery 配置
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    @property
    def celery_broker(self) -> str:
        return self.CELERY_BROKER_URL or self.redis_url

    @property
    def celery_backend(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.redis_url


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 全局配置实例
settings = get_settings()
