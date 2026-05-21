"""
Celery 任务模块
"""

from app.tasks.celery_app import celery_app, send_task_async
from app.tasks.document_tasks import (
    delete_document_vectors_task,
    process_document_task,
    process_documents_batch_task,
    process_pending_documents_task,
    reprocess_document_task,
    reprocess_failed_documents_task,
)

# 任务名称常量
TASK_PROCESS_DOCUMENT = "app.tasks.document.process_document"
TASK_PROCESS_BATCH = "app.tasks.document.process_documents_batch"
TASK_REPROCESS_DOCUMENT = "app.tasks.document.reprocess_document"
TASK_REPROCESS_FAILED = "app.tasks.document.reprocess_failed_documents"
TASK_DELETE_VECTORS = "app.tasks.document.delete_document_vectors"
TASK_PROCESS_PENDING = "app.tasks.document.process_pending_documents"

__all__ = [
    "celery_app",
    "send_task_async",
    # 任务函数（用于 Celery Worker）
    "process_document_task",
    "process_documents_batch_task",
    "reprocess_document_task",
    "reprocess_failed_documents_task",
    "process_pending_documents_task",
    "delete_document_vectors_task",
    # 任务名称常量（用于 send_task_async）
    "TASK_PROCESS_DOCUMENT",
    "TASK_PROCESS_BATCH",
    "TASK_REPROCESS_DOCUMENT",
    "TASK_REPROCESS_FAILED",
    "TASK_DELETE_VECTORS",
    "TASK_PROCESS_PENDING",
]
