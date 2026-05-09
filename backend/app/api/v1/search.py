"""
高级搜索 API

提供统一的搜索接口，支持：
1. 多种检索模式（语义、关键词、混合）
2. 过滤和排序
3. 重排序
4. 缓存
"""

from typing import Any, Dict, List, Optional

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.knowledge_base import KnowledgeBase
from app.models.permission import PermissionLevel, UserKBPermission
from app.models.user import User
from app.services.embeddings.base import EmbeddingConfig
from app.services.retrieval import (
    FusionStrategy,
    RerankConfig,
    RetrievalMode,
    RetrievalPipeline,
    RetrieverFactory,
    SearchConfig,
)
from app.services.retrieval.cache import CacheConfig, SearchCache
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


# ============ 请求/响应模型 ============


class SearchFilters(BaseModel):
    """搜索过滤器"""

    document_ids: Optional[List[str]] = Field(
        None,
        description="限制在指定文档中搜索",
    )
    file_types: Optional[List[str]] = Field(
        None,
        description="限制文件类型 (pdf, docx, md 等)",
    )
    date_from: Optional[str] = Field(
        None,
        description="文档创建时间起始 (ISO 8601)",
    )
    date_to: Optional[str] = Field(
        None,
        description="文档创建时间截止 (ISO 8601)",
    )
    tags: Optional[List[str]] = Field(
        None,
        description="文档标签",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="自定义元数据过滤",
    )


class HybridOptions(BaseModel):
    """混合检索选项"""

    fusion_strategy: str = Field(
        "rrf",
        description="融合策略: rrf, weighted, linear",
    )
    semantic_weight: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="语义检索权重",
    )
    keyword_weight: float = Field(
        0.3,
        ge=0.0,
        le=1.0,
        description="关键词检索权重",
    )
    adaptive: bool = Field(
        False,
        description="是否使用自适应权重",
    )


class RerankOptions(BaseModel):
    """重排序选项"""

    enabled: bool = Field(
        False,
        description="是否启用重排序",
    )
    provider: str = Field(
        "cohere",
        description="重排序提供商: cohere, jina, local, llm",
    )
    model: Optional[str] = Field(
        None,
        description="重排序模型名称",
    )
    top_k: Optional[int] = Field(
        None,
        description="重排序后返回数量",
    )


class SearchRequest(BaseModel):
    """搜索请求"""

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="搜索查询文本",
    )
    knowledge_base_id: str = Field(
        ...,
        description="知识库ID",
    )
    mode: str = Field(
        "hybrid",
        description="检索模式: semantic, keyword, hybrid",
    )
    top_k: int = Field(
        10,
        ge=1,
        le=100,
        description="返回结果数量",
    )
    score_threshold: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="最低分数阈值",
    )
    filters: Optional[SearchFilters] = Field(
        None,
        description="过滤条件",
    )
    hybrid_options: Optional[HybridOptions] = Field(
        None,
        description="混合检索选项",
    )
    rerank: Optional[RerankOptions] = Field(
        None,
        description="重排序选项",
    )
    use_cache: bool = Field(
        True,
        description="是否使用缓存",
    )


class SearchResultItem(BaseModel):
    """搜索结果项"""

    chunk_id: str = Field(..., description="分块ID")
    document_id: str = Field(..., description="文档ID")
    document_name: Optional[str] = Field(None, description="文档名称")
    content: str = Field(..., description="分块内容")
    score: float = Field(..., description="相关性分数")
    highlight: Optional[str] = Field(None, description="高亮片段")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class SearchResponse(BaseModel):
    """搜索响应"""

    query: str = Field(..., description="原始查询")
    mode: str = Field(..., description="使用的检索模式")
    total: int = Field(..., description="结果总数")
    results: List[SearchResultItem] = Field(..., description="搜索结果")
    took_ms: float = Field(..., description="耗时（毫秒）")
    from_cache: bool = Field(False, description="是否来自缓存")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加信息")


# ============ 辅助函数 ============


async def check_kb_access(
    db: AsyncSession,
    knowledge_base_id: str,
    user: User,
) -> KnowledgeBase:
    """检查用户对知识库的访问权限"""
    from sqlalchemy import select

    # 获取知识库
    stmt = select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id)
    result = await db.execute(stmt)
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 检查权限
    if kb.owner_id != user.id and not user.is_superuser:
        # 检查共享权限
        perm_stmt = select(UserKBPermission).where(
            UserKBPermission.kb_id == knowledge_base_id,
            UserKBPermission.user_id == user.id,
            UserKBPermission.permission.in_(
                [
                    PermissionLevel.READ,
                    PermissionLevel.WRITE,
                    PermissionLevel.ADMIN,
                ]
            ),
        )
        perm_result = await db.execute(perm_stmt)
        if not perm_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="无权访问此知识库")

    return kb


def build_filters(search_filters: Optional[SearchFilters]) -> Dict[str, Any]:
    """构建过滤条件字典"""
    if not search_filters:
        return {}

    filters = {}

    if search_filters.document_ids:
        filters["document_ids"] = search_filters.document_ids

    if search_filters.file_types:
        filters["file_types"] = search_filters.file_types

    if search_filters.date_from:
        filters["date_from"] = search_filters.date_from

    if search_filters.date_to:
        filters["date_to"] = search_filters.date_to

    if search_filters.tags:
        filters["tags"] = search_filters.tags

    if search_filters.metadata:
        filters["metadata"] = search_filters.metadata

    return filters


# ============ API 端点 ============


@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """执行搜索

    支持三种检索模式：
    - semantic: 语义检索，基于向量相似度
    - keyword: 关键词检索，基于全文搜索
    - hybrid: 混合检索，结合语义和关键词

    可选配置重排序以提升结果质量。
    """
    import time

    start_time = time.time()

    # 检查权限
    kb = await check_kb_access(db, request.knowledge_base_id, current_user)

    # 解析检索模式
    try:
        mode = RetrievalMode(request.mode)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"无效的检索模式: {request.mode}",
        )

    # 构建过滤条件
    filters = build_filters(request.filters)

    # 构建混合配置
    hybrid_config = {}
    if request.hybrid_options:
        try:
            fusion = FusionStrategy(request.hybrid_options.fusion_strategy)
        except ValueError:
            fusion = FusionStrategy.RRF

        hybrid_config = {
            "fusion_strategy": fusion,
            "semantic_weight": request.hybrid_options.semantic_weight,
            "keyword_weight": request.hybrid_options.keyword_weight,
            "adaptive": request.hybrid_options.adaptive,
        }

    # 初始化服务（实际项目中应使用依赖注入）
    # 这里简化处理，实际需要根据配置创建服务
    from app.services.embeddings.factory import EmbeddingFactory
    from app.services.vector_store.qdrant_store import QdrantVectorStore

    settings_embedding_config = EmbeddingConfig(
        provider=settings.EMBEDDING_PROVIDER,
        api_key=settings.EMBEDDING_API_KEY,
        api_base=settings.EMBEDDING_API_BASE,
        model=settings.EMBEDDING_MODEL,
        dimension=settings.EMBEDDING_DIMENSION,
        azure_endpoint=settings.AZURE_ENDPOINT,
        azure_deployment=settings.AZURE_EMBEDDING_DEPLOYMENT,
        azure_api_version=settings.AZURE_API_VERSION,
    )
    # 创建 embedding 服务
    embedding_service = EmbeddingFactory.create(config=settings_embedding_config)

    # 创建向量存储
    vector_store = QdrantVectorStore(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        api_key=settings.QDRANT_API_KEY,
    )

    # 创建检索管道
    rerank_provider = None
    rerank_api_key = None
    rerank_model = None

    if request.rerank and request.rerank.enabled:
        rerank_provider = request.rerank.provider
        rerank_api_key = getattr(
            settings, f"{request.rerank.provider.upper()}_API_KEY", None
        )
        rerank_model = request.rerank.model

    pipeline = RetrievalPipeline.create(
        mode=mode,
        embedding_service=embedding_service,
        vector_store=vector_store,
        keyword_backend="postgresql",
        keyword_config={"connection_url": settings.DATABASE_URL},
        hybrid_config=hybrid_config,
        rerank_provider=rerank_provider,
        rerank_api_key=rerank_api_key,
        rerank_model=rerank_model,
    )

    # 初始化缓存
    cache = SearchCache(
        redis_url=settings.REDIS_URL,
        config=CacheConfig(enabled=request.use_cache),
    )

    from_cache = False

    # 检查缓存
    if request.use_cache:
        config = SearchConfig(
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            filters=filters,
        )
        cached = await cache.get(
            query=request.query,
            knowledge_base_id=request.knowledge_base_id,
            config=config,
            filters=filters,
        )
        if cached is not None:
            from_cache = True
            search_results = cached
        else:
            search_results = None
    else:
        search_results = None

    # 执行检索
    if search_results is None:
        search_results = await pipeline.search(
            query=request.query,
            knowledge_base_id=request.knowledge_base_id,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            filters=filters,
            rerank=request.rerank.enabled if request.rerank else False,
            rerank_top_k=request.rerank.top_k if request.rerank else None,
        )

        # 缓存结果
        if request.use_cache:
            await cache.set(
                query=request.query,
                knowledge_base_id=request.knowledge_base_id,
                results=search_results,
                config=config,
                filters=filters,
            )

    # 构建响应
    result_items = []
    for r in search_results:
        item = SearchResultItem(
            chunk_id=r.chunk_id,
            document_id=r.document_id,
            content=r.content,
            score=r.score,
            metadata=r.metadata,
        )
        result_items.append(item)

    took_ms = (time.time() - start_time) * 1000

    # 关闭连接
    await cache.close()

    return SearchResponse(
        query=request.query,
        mode=request.mode,
        total=len(result_items),
        results=result_items,
        took_ms=round(took_ms, 2),
        from_cache=from_cache,
        metadata={
            "knowledge_base_name": kb.name,
            "rerank_enabled": request.rerank.enabled if request.rerank else False,
        },
    )


@router.get("/suggest")
async def suggest(
    q: str = Query(..., min_length=1, max_length=100, description="查询前缀"),
    knowledge_base_id: str = Query(..., description="知识库ID"),
    limit: int = Query(5, ge=1, le=20, description="建议数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """搜索建议

    基于用户输入提供搜索建议，可用于实现自动补全。
    """
    # 检查权限
    await check_kb_access(db, knowledge_base_id, current_user)

    # TODO: 实现搜索建议逻辑
    # 可以基于：
    # 1. 热门搜索词
    # 2. 用户历史搜索
    # 3. 文档标题/关键词

    return {
        "query": q,
        "suggestions": [],  # 待实现
    }


@router.post("/multi")
async def multi_search(
    queries: List[str] = Body(..., min_length=1, max_length=10),
    knowledge_base_id: str = Body(...),
    mode: str = Body("hybrid"),
    top_k: int = Body(5, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量搜索

    同时执行多个查询，适用于多轮对话或对比分析场景。
    """
    # 检查权限
    await check_kb_access(db, knowledge_base_id, current_user)

    # TODO: 实现批量搜索逻辑
    # 可以并行执行多个查询

    return {
        "results": [],  # 待实现
    }


@router.delete("/cache/{knowledge_base_id}")
async def clear_cache(
    knowledge_base_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """清除知识库搜索缓存

    当知识库内容更新后，可调用此接口清除缓存。
    """
    # 检查权限（需要写权限）
    kb = await check_kb_access(db, knowledge_base_id, current_user)

    if kb.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="需要知识库所有者权限")

    cache = SearchCache(redis_url=settings.REDIS_URL)
    deleted = await cache.invalidate_knowledge_base(knowledge_base_id)
    await cache.close()

    return {
        "message": f"已清除 {deleted} 条缓存",
        "knowledge_base_id": knowledge_base_id,
    }


@router.get("/stats")
async def search_stats(
    current_user: User = Depends(get_current_user),
):
    """获取搜索统计信息

    仅管理员可用。
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="需要管理员权限")

    cache = SearchCache(redis_url=settings.REDIS_URL)
    stats = await cache.get_stats()
    await cache.close()

    return stats
