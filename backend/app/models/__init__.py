"""
数据模型初始化
导出所有模型
"""
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase, KBTag, KBVisibility
from app.models.document import Document, Chunk, DocumentStatus, DocumentSourceType
from app.models.api_key import ApiKey
from app.models.permission import UserKBPermission, PermissionLevel
from app.models.model_config import ModelConfig, ConfigType

__all__ = [
    # 用户
    "User",
    # 知识库
    "KnowledgeBase",
    "KBTag",
    "KBVisibility",
    # 文档
    "Document",
    "Chunk",
    "DocumentStatus",
    "DocumentSourceType",
    # API 密钥
    "ApiKey",
    # 权限
    "UserKBPermission",
    "PermissionLevel",
    # 模型配置
    "ModelConfig",
    "ConfigType",
]
