"""
文档处理 Celery 任务

提供异步文档处理任务
"""

import asyncio
import logging
from typing import List, Optional
from uuid import UUID

from app.tasks.celery_app import celery_app
from celery import shared_task

logger = logging.getLogger(__name__)


def run_async(coro):
    """在同步上下文中运行异步函数"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


@celery_app.task(
    bind=True,
    name="app.tasks.document.process_document",
    max_retries=3,
    default_retry_delay=60,
)
def process_document_task(self, document_id: str, force: bool = False):
    """处理单个文档

    Args:
        document_id: 文档 ID
        force: 是否强制重新处理

    Returns:
        处理结果
    """
    logger.info(f"Starting document processing task: {document_id}")

    async def _process():
        from app.core.database import async_session_maker
        from app.services.document_processor import DocumentProcessor

        async with async_session_maker() as db:
            processor = DocumentProcessor(db)
            result = await processor.process_document(UUID(document_id), force)
            return result

    try:
        result = run_async(_process())

        if result.success:
            logger.info(
                f"Document processed successfully: {document_id}, "
                f"chunks: {result.chunk_count}, time: {result.processing_time_ms}ms"
            )
            return {
                "status": "success",
                "document_id": document_id,
                "chunk_count": result.chunk_count,
                "vector_count": result.vector_count,
                "processing_time_ms": result.processing_time_ms,
            }
        else:
            logger.error(
                f"Document processing failed: {document_id}, error: {result.error_message}"
            )

            # 如果可以重试
            if self.request.retries < self.max_retries:
                raise self.retry(exc=Exception(result.error_message))

            return {
                "status": "failed",
                "document_id": document_id,
                "error": result.error_message,
            }

    except Exception as e:
        logger.error(f"Document processing task error: {document_id}, error: {e}")

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        return {
            "status": "error",
            "document_id": document_id,
            "error": str(e),
        }


@celery_app.task(
    bind=True,
    name="app.tasks.document.process_documents_batch",
    max_retries=1,
)
def process_documents_batch_task(self, document_ids: List[str], force: bool = False):
    """批量处理文档

    Args:
        document_ids: 文档 ID 列表
        force: 是否强制重新处理

    Returns:
        处理结果列表
    """
    logger.info(f"Starting batch document processing: {len(document_ids)} documents")

    results = []
    for doc_id in document_ids:
        try:
            # 调用单个文档处理任务
            result = process_document_task.delay(doc_id, force)
            results.append(
                {
                    "document_id": doc_id,
                    "task_id": result.id,
                    "status": "queued",
                }
            )
        except Exception as e:
            logger.error(f"Failed to queue document {doc_id}: {e}")
            results.append(
                {
                    "document_id": doc_id,
                    "status": "failed",
                    "error": str(e),
                }
            )

    return {
        "total": len(document_ids),
        "queued": sum(1 for r in results if r["status"] == "queued"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "results": results,
    }


@celery_app.task(
    bind=True,
    name="app.tasks.document.reprocess_failed_documents",
)
def reprocess_failed_documents_task(self, kb_id: Optional[str] = None):
    """重新处理失败的文档

    Args:
        kb_id: 知识库 ID（可选，不指定则处理所有）

    Returns:
        处理结果
    """
    logger.info(f"Reprocessing failed documents, kb_id: {kb_id}")

    async def _get_failed_documents():
        from app.core.database import async_session_maker
        from app.models.document import Document, DocumentStatus
        from sqlalchemy import select

        async with async_session_maker() as db:
            query = select(Document.id).where(Document.status == DocumentStatus.FAILED)

            if kb_id:
                query = query.where(Document.kb_id == UUID(kb_id))

            result = await db.execute(query)
            return [str(row[0]) for row in result.fetchall()]

    try:
        failed_doc_ids = run_async(_get_failed_documents())

        if not failed_doc_ids:
            logger.info("No failed documents to reprocess")
            return {
                "status": "success",
                "message": "No failed documents to reprocess",
                "count": 0,
            }

        logger.info(f"Found {len(failed_doc_ids)} failed documents to reprocess")

        # 批量处理
        result = process_documents_batch_task.delay(failed_doc_ids, force=True)

        return {
            "status": "success",
            "message": f"Queued {len(failed_doc_ids)} documents for reprocessing",
            "count": len(failed_doc_ids),
            "batch_task_id": result.id,
        }

    except Exception as e:
        logger.error(f"Failed to reprocess failed documents: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


@celery_app.task(
    bind=True,
    name="app.tasks.document.delete_document_vectors",
)
def delete_document_vectors_task(self, document_id: str):
    """删除文档的向量

    Args:
        document_id: 文档 ID

    Returns:
        删除结果
    """
    logger.info(f"Deleting vectors for document: {document_id}")

    async def _delete():
        from app.core.database import async_session_maker
        from app.services.document_processor import DocumentProcessor

        async with async_session_maker() as db:
            processor = DocumentProcessor(db)
            return await processor.delete_document_vectors(UUID(document_id))

    try:
        success = run_async(_delete())

        if success:
            logger.info(f"Vectors deleted for document: {document_id}")
            return {
                "status": "success",
                "document_id": document_id,
            }
        else:
            return {
                "status": "failed",
                "document_id": document_id,
            }

    except Exception as e:
        logger.error(f"Failed to delete vectors for document {document_id}: {e}")
        return {
            "status": "error",
            "document_id": document_id,
            "error": str(e),
        }


@celery_app.task(
    bind=True,
    name="app.tasks.document.process_pending_documents",
)
def process_pending_documents_task(self, kb_id: Optional[str] = None, limit: int = 50):
    """处理待处理的文档

    Args:
        kb_id: 知识库 ID（可选）
        limit: 最大处理数量

    Returns:
        处理结果
    """
    logger.info(f"Processing pending documents, kb_id: {kb_id}, limit: {limit}")

    async def _get_pending_documents():
        from app.core.database import async_session_maker
        from app.models.document import Document, DocumentStatus
        from sqlalchemy import select

        async with async_session_maker() as db:
            query = (
                select(Document.id)
                .where(Document.status == DocumentStatus.PENDING)
                .order_by(Document.created_at)
                .limit(limit)
            )

            if kb_id:
                query = query.where(Document.kb_id == UUID(kb_id))

            result = await db.execute(query)
            return [str(row[0]) for row in result.fetchall()]

    try:
        pending_doc_ids = run_async(_get_pending_documents())

        if not pending_doc_ids:
            logger.info("No pending documents to process")
            return {
                "status": "success",
                "message": "No pending documents to process",
                "count": 0,
            }

        logger.info(f"Found {len(pending_doc_ids)} pending documents to process")

        # 批量处理
        result = process_documents_batch_task.delay(pending_doc_ids)

        return {
            "status": "success",
            "message": f"Queued {len(pending_doc_ids)} documents for processing",
            "count": len(pending_doc_ids),
            "batch_task_id": result.id,
        }

    except Exception as e:
        logger.error(f"Failed to process pending documents: {e}")
        return {
            "status": "error",
            "error": str(e),
        }
