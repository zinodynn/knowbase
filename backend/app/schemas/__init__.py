"""
Schema 模块初始化
"""

from app.schemas.api_key import (
    ApiKeyBase,
    ApiKeyCreate,
    ApiKeyCreateResponse,
    ApiKeyListResponse,
    ApiKeyResponse,
    ApiKeyUpdate,
)
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    Token,
    TokenPayload,
)
from app.schemas.document import (
    BatchUploadResponse,
    ChunkResponse,
    DocumentCreate,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentReprocessRequest,
    DocumentResponse,
    DocumentStatus,
    DocumentUploadResponse,
    ProcessingTaskResponse,
    SearchHit,
    SearchRequest,
    SearchResponse,
)
from app.schemas.knowledge_base import (
    KBTagResponse,
    KnowledgeBaseBase,
    KnowledgeBaseCreate,
    KnowledgeBaseListResponse,
    KnowledgeBaseResponse,
    KnowledgeBaseStats,
    KnowledgeBaseUpdate,
)
from app.schemas.model_config import (
    ModelConfigBase,
    ModelConfigCreate,
    ModelConfigListResponse,
    ModelConfigResponse,
    ModelConfigTestRequest,
    ModelConfigTestResponse,
    ModelConfigUpdate,
)
from app.schemas.permission import (
    KBPermissionListResponse,
    PermissionBase,
    PermissionCreate,
    PermissionResponse,
    PermissionUpdate,
    PermissionWithUserResponse,
)
from app.schemas.user import UserBase, UserCreate, UserInDB, UserResponse, UserUpdate

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
    # Document
    "DocumentStatus",
    "ChunkResponse",
    "DocumentCreate",
    "DocumentResponse",
    "DocumentListResponse",
    "DocumentDetailResponse",
    "DocumentUploadResponse",
    "BatchUploadResponse",
    "DocumentReprocessRequest",
    "ProcessingTaskResponse",
    "SearchRequest",
    "SearchHit",
    "SearchResponse",
]
