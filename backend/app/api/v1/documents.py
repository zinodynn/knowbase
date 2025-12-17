"""
文档管理 API 路由

提供文档上传、列表、删除和搜索功能
"""

import logging
import math
import tempfile
import time
from pathlib import Path
from typing import List, Optional
from uuid import UUID, uuid4

from app.api.deps import check_kb_permission, get_current_user, get_db
from app.models import Chunk, Document, DocumentStatus, KnowledgeBase, User
from app.models.document import DocumentSourceType
from app.schemas.document import (
    BatchUploadResponse,
    ChunkResponse,
    DocumentCreate,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentReprocessRequest,
    DocumentResponse,
    DocumentUploadResponse,
    SearchHit,
    SearchRequest,
    SearchResponse,
)
from app.services import ParserFactory, get_storage_service
from app.tasks import TASK_DELETE_VECTORS, TASK_PROCESS_DOCUMENT, send_task_async
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/knowledge-bases/{kb_id}/documents/upload",
    response_model=BatchUploadResponse,
    summary="上传文档",
)
async def upload_documents(
    kb_id: UUID,
    description: Optional[str] = None,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    上传一个或多个文档到知识库

    支持的文件格式：PDF, DOCX, MD, TXT, HTML, XLSX
    """
    # 检查知识库权限
    kb = await check_kb_permission(db, kb_id, current_user, require_write=True)

    storage = get_storage_service()
    uploaded = []
    failed = []

    for file in files:
        try:
            # 检查文件类型
            if not ParserFactory.is_supported(file.filename):
                failed.append(
                    {
                        "filename": file.filename,
                        "error": f"Unsupported file type: {Path(file.filename).suffix}",
                    }
                )
                continue

            # 读取文件内容
            content = await file.read()
            file_size = len(content)

            # 创建文档记录
            document_id = uuid4()
            file_type = Path(file.filename).suffix.lower()

            # 上传到 MinIO
            object_name, etag = await storage.upload_bytes(
                data=content,
                kb_id=str(kb_id),
                filename=file.filename,
                document_id=str(document_id),
                content_type=file.content_type,
            )

            # 创建数据库记录
            document = Document(
                id=document_id,
                kb_id=kb_id,
                description=description,
                file_name=file.filename,
                file_type=file_type,
                file_size=file_size,
                storage_path=object_name,
                status=DocumentStatus.PENDING,
                source_type=DocumentSourceType.UPLOAD,
                # created_by=current_user.id, # TODO: 添加创建者信息
            )

            db.add(document)

            uploaded.append(
                DocumentUploadResponse(
                    id=document_id,
                    filename=file.filename,
                    status=DocumentStatus.PENDING,
                    message="Document uploaded, pending processing",
                )
            )

        except Exception as e:
            logger.error(f"Failed to upload {file.filename}: {e}")
            failed.append(
                {
                    "filename": file.filename,
                    "error": str(e),
                }
            )

    await db.commit()

    # 触发异步处理任务
    for doc in uploaded:
        await send_task_async(TASK_PROCESS_DOCUMENT, str(doc.id))

    return BatchUploadResponse(
        uploaded=uploaded,
        failed=failed,
        total=len(files),
        success_count=len(uploaded),
        failure_count=len(failed),
    )


@router.post(
    "/knowledge-bases/{kb_id}/documents/push",
    response_model=DocumentUploadResponse,
    summary="推送文档内容",
)
async def push_document(
    kb_id: UUID,
    doc_data: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    通过 API 推送文档内容

    适用于直接推送文本内容而非上传文件的场景
    """
    # 检查知识库权限
    kb = await check_kb_permission(db, kb_id, current_user, require_write=True)

    storage = get_storage_service()

    # 创建文档记录
    document_id = uuid4()
    content_bytes = doc_data.content.encode("utf-8")
    file_size = len(content_bytes)
    file_type = Path(doc_data.filename).suffix.lower() or ".txt"

    # 上传到 MinIO
    object_name, etag = await storage.upload_bytes(
        data=content_bytes,
        kb_id=str(kb_id),
        filename=doc_data.filename,
        document_id=str(document_id),
        content_type="text/plain; charset=utf-8",
    )

    # 创建数据库记录
    document = Document(
        id=document_id,
        kb_id=kb_id,
        filename=doc_data.filename,
        file_type=file_type,
        file_size=file_size,
        storage_path=object_name,
        status=DocumentStatus.PENDING,
        metadata=doc_data.metadata,
        # created_by=current_user.id, # TODO: 添加创建者信息
    )

    db.add(document)
    await db.commit()

    # 触发异步处理任务
    await send_task_async(TASK_PROCESS_DOCUMENT, str(document_id))

    return DocumentUploadResponse(
        id=document_id,
        filename=doc_data.filename,
        status=DocumentStatus.PENDING,
        message="Document pushed, pending processing",
    )


@router.get(
    "/knowledge-bases/{kb_id}/documents",
    response_model=DocumentListResponse,
    summary="获取文档列表",
)
async def list_documents(
    kb_id: UUID,
    status: Optional[str] = Query(None, description="按状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取知识库中的文档列表"""
    # 检查知识库权限
    kb = await check_kb_permission(db, kb_id, current_user, require_write=False)

    # 构建查询
    query = select(Document).where(Document.kb_id == kb_id)
    count_query = select(func.count(Document.id)).where(Document.kb_id == kb_id)

    if status:
        try:
            status_enum = DocumentStatus(status)
            query = query.where(Document.status == status_enum)
            count_query = count_query.where(Document.status == status_enum)
        except ValueError:
            pass

    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    query = query.order_by(Document.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    documents = result.scalars().all()

    # 计算总页数
    pages = math.ceil(total / page_size) if total > 0 else 1

    return DocumentListResponse(
        items=[DocumentResponse.model_validate(doc) for doc in documents],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/documents/{doc_id}",
    response_model=DocumentDetailResponse,
    summary="获取文档详情",
)
async def get_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取文档详情，包含分块信息"""
    # 获取文档
    result = await db.execute(select(Document).where(Document.id == doc_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # 检查权限
    await check_kb_permission(db, document.kb_id, current_user, require_write=False)

    # 获取分块
    chunks_result = await db.execute(
        select(Chunk).where(Chunk.document_id == doc_id).order_by(Chunk.chunk_index)
    )
    chunks = chunks_result.scalars().all()

    doc_response = DocumentDetailResponse.model_validate(document)
    doc_response.chunks = [ChunkResponse.model_validate(c) for c in chunks]
    doc_response.chunk_count = len(chunks)

    return doc_response


@router.delete(
    "/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除文档",
)
async def delete_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除文档及其所有分块和向量"""
    # 获取文档
    result = await db.execute(select(Document).where(Document.id == doc_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # 检查权限
    await check_kb_permission(db, document.kb_id, current_user, require_write=True)

    # 删除 MinIO 中的文件
    if document.storage_path:
        try:
            storage = get_storage_service()
            await storage.delete_file(document.storage_path)
        except Exception as e:
            logger.warning(f"Failed to delete file from storage: {e}")

    # 删除向量数据库中的向量
    await send_task_async(TASK_DELETE_VECTORS, str(doc_id))

    # 删除分块（通过级联删除）
    # 删除文档
    await db.delete(document)
    await db.commit()


@router.post(
    "/documents/reprocess",
    response_model=List[DocumentUploadResponse],
    summary="重新处理文档",
)
async def reprocess_documents(
    request: DocumentReprocessRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重新处理指定的文档"""
    responses = []

    for doc_id in request.document_ids:
        # 获取文档
        result = await db.execute(select(Document).where(Document.id == doc_id))
        document = result.scalar_one_or_none()

        if not document:
            responses.append(
                DocumentUploadResponse(
                    id=doc_id,
                    filename="",
                    status=DocumentStatus.FAILED,
                    message="Document not found",
                )
            )
            continue

        # 检查权限
        try:
            await check_kb_permission(
                db, document.kb_id, current_user, require_write=True
            )
        except HTTPException:
            responses.append(
                DocumentUploadResponse(
                    id=doc_id,
                    filename=document.filename,
                    status=DocumentStatus.FAILED,
                    message="Permission denied",
                )
            )
            continue

        # 重置状态
        document.status = DocumentStatus.PENDING
        # document.error_message = None

        responses.append(
            DocumentUploadResponse(
                id=doc_id,
                filename=document.file_name,
                status=DocumentStatus.PENDING,
                message="Document queued for reprocessing",
            )
        )

    await db.commit()

    # 触发异步重新处理任务（强制模式）
    for resp in responses:
        if resp.status == DocumentStatus.PENDING:
            await send_task_async(TASK_PROCESS_DOCUMENT, str(resp.id), force=True)

    return responses


@router.get(
    "/documents/{doc_id}/download-url",
    summary="获取文档下载链接",
)
async def get_download_url(
    doc_id: UUID,
    expires_hours: int = Query(1, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取文档的预签名下载链接"""
    from datetime import timedelta

    # 获取文档
    result = await db.execute(select(Document).where(Document.id == doc_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # 检查权限
    await check_kb_permission(db, document.kb_id, current_user, require_write=False)

    if not document.storage_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found",
        )

    # 生成预签名 URL
    storage = get_storage_service()
    url = await storage.generate_presigned_url(
        document.storage_path,
        expires=timedelta(hours=expires_hours),
    )

    return {
        "url": url,
        "filename": document.file_name,
        "expires_in_hours": expires_hours,
    }


@router.post(
    "/knowledge-bases/{kb_id}/search",
    response_model=SearchResponse,
    summary="搜索文档",
)
async def search_documents(
    kb_id: UUID,
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    在知识库中搜索文档

    使用向量相似度搜索
    """
    start_time = time.time()

    # 检查知识库权限
    kb = await check_kb_permission(db, kb_id, current_user, require_write=False)

    # TODO: 实现向量搜索
    # 1. 将查询文本向量化
    # 2. 在向量数据库中搜索
    # 3. 根据结果获取文档和分块信息

    # 临时返回空结果
    took_ms = int((time.time() - start_time) * 1000)

    return SearchResponse(
        query=request.query,
        hits=[],
        total=0,
        took_ms=took_ms,
    )
