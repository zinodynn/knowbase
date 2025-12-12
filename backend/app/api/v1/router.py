"""
API v1 路由汇总
"""
from fastapi import APIRouter

from app.api.v1 import auth, users, knowledge_bases, api_keys, permissions, model_configs


api_router = APIRouter()

# 认证路由
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["认证"]
)

# 用户管理路由
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["用户管理"]
)

# 知识库路由
api_router.include_router(
    knowledge_bases.router,
    prefix="/knowledge-bases",
    tags=["知识库"]
)

# API Key 路由
api_router.include_router(
    api_keys.router,
    prefix="/api-keys",
    tags=["API Key"]
)

# 权限管理路由
api_router.include_router(
    permissions.router,
    prefix="",
    tags=["权限管理"]
)

# 模型配置路由
api_router.include_router(
    model_configs.router,
    prefix="/model-configs",
    tags=["模型配置"]
)
