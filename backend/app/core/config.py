"""
KnowBase 配置模块
从环境变量加载所有配置
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用配置
    APP_NAME: str = "KnowBase"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    
    # 数据库配置
    DB_USER: str = "knowbase"
    DB_PASSWORD: str = "knowbase123"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "knowbase"
    DATABASE_URL: Optional[str] = None
    
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
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
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
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ENCRYPTION_KEY: str = "your-encryption-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    
    # CORS 配置
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """获取允许的域名列表"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    # Celery 配置
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    
    @property
    def celery_broker(self) -> str:
        return self.CELERY_BROKER_URL or self.redis_url
    
    @property
    def celery_backend(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.redis_url
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 全局配置实例
settings = get_settings()
