"""
Celery 任务模块
"""

from app.tasks.celery_app import celery_app
from app.tasks.document_tasks import (
    delete_document_vectors_task,
    process_document_task,
    process_documents_batch_task,
    process_pending_documents_task,
    reprocess_failed_documents_task,
)

__all__ = [
    "celery_app",
    "process_document_task",
    "process_documents_batch_task",
    "reprocess_failed_documents_task",
    "process_pending_documents_task",
    "delete_document_vectors_task",
]
