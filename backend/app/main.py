"""
KnowBase - 知识库管理系统
FastAPI 主应用入口
"""

import logging
from contextlib import asynccontextmanager

from app.api.v1.router import api_router
from app.core.config import settings
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("Starting KnowBase API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    yield

    # 关闭时执行
    logger.info("Shutting down KnowBase API...")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    description="""
KnowBase 知识库管理系统 API

## 功能特性

- 🔐 **用户认证**: JWT Token 和 API Key 双重认证
- 📚 **知识库管理**: 创建、编辑、删除知识库
- 📄 **文档处理**: 多格式文档上传与智能分块
- 🔍 **智能检索**: 向量检索 + 全文检索混合搜索
- 🤖 **AI 对话**: 基于知识库的智能问答
- 👥 **权限控制**: 细粒度的知识库访问权限

## 认证方式

1. **JWT Token**: 通过 `/api/v1/auth/login` 获取
2. **API Key**: 通过 `/api/v1/api-keys` 创建，以 `kb_` 开头

在请求头中添加: `Authorization: Bearer <token_or_api_key>`
    """,
    version="1.0.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# CORS 中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误"},
    )


# 注册 API 路由
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# 健康检查端点
@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": settings.APP_NAME, "version": "1.0.0"}


@app.get("/", tags=["根路径"])
async def root():
    """根路径重定向到文档"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
