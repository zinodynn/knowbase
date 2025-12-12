"""
Schema 模块初始化
"""
from app.schemas.user import UserBase, UserCreate, UserUpdate, UserResponse, UserInDB
from app.schemas.auth import (
    Token,
    TokenPayload,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ChangePasswordRequest,
)
from app.schemas.knowledge_base import (
    KnowledgeBaseBase,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    KnowledgeBaseListResponse,
    KnowledgeBaseStats,
    KBTagResponse,
)
from app.schemas.api_key import (
    ApiKeyBase,
    ApiKeyCreate,
    ApiKeyUpdate,
    ApiKeyResponse,
    ApiKeyCreateResponse,
    ApiKeyListResponse,
)
from app.schemas.permission import (
    PermissionBase,
    PermissionCreate,
    PermissionUpdate,
    PermissionResponse,
    PermissionWithUserResponse,
    KBPermissionListResponse,
)
from app.schemas.model_config import (
    ModelConfigBase,
    ModelConfigCreate,
    ModelConfigUpdate,
    ModelConfigResponse,
    ModelConfigListResponse,
    ModelConfigTestRequest,
    ModelConfigTestResponse,
)


__all__ = [
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserInDB",
    # Auth
    "Token",
    "TokenPayload",
    "LoginRequest",
    "RefreshRequest",
    "RegisterRequest",
    "ChangePasswordRequest",
    # Knowledge Base
    "KnowledgeBaseBase",
    "KnowledgeBaseCreate",
    "KnowledgeBaseUpdate",
    "KnowledgeBaseResponse",
    "KnowledgeBaseListResponse",
    "KnowledgeBaseStats",
    "KBTagResponse",
    # API Key
    "ApiKeyBase",
    "ApiKeyCreate",
    "ApiKeyUpdate",
    "ApiKeyResponse",
    "ApiKeyCreateResponse",
    "ApiKeyListResponse",
    # Permission
    "PermissionBase",
    "PermissionCreate",
    "PermissionUpdate",
    "PermissionResponse",
    "PermissionWithUserResponse",
    "KBPermissionListResponse",
    # Model Config
    "ModelConfigBase",
    "ModelConfigCreate",
    "ModelConfigUpdate",
    "ModelConfigResponse",
    "ModelConfigListResponse",
    "ModelConfigTestRequest",
    "ModelConfigTestResponse",
]
