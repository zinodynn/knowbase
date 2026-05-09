"""
Celery 应用配置

配置 Celery 异步任务队列
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Optional

from app.core.config import get_settings
from celery import Celery

logger = logging.getLogger(__name__)

settings = get_settings()

# 创建 Celery 应用
celery_app = Celery(
    "knowbase",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# 线程池用于在异步环境中发送任务
_executor = ThreadPoolExecutor(max_workers=4)


def send_task_sync(task_name: str, *args, **kwargs) -> Any:
    """同步发送任务（用于线程池）"""
    return celery_app.send_task(task_name, args=args, kwargs=kwargs)


async def send_task_async(task_name: str, *args, **kwargs) -> Optional[str]:
    """
    异步发送 Celery 任务

    在 FastAPI 的异步环境中安全地发送 Celery 任务

    Args:
        task_name: 任务名称（如 "app.tasks.document.process_document"）
        *args: 任务参数
        **kwargs: 任务关键字参数

    Returns:
        任务 ID 或 None（如果发送失败）
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor, partial(send_task_sync, task_name, *args, **kwargs)
        )
        logger.info(f"Task {task_name} sent with id: {result.id}")
        return result.id
    except Exception as e:
        logger.error(f"Failed to send task {task_name}: {e}")
        return None


# 配置 Celery
celery_app.conf.update(
    # 任务序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # 时区
    timezone="Asia/Shanghai",
    enable_utc=True,
    # 任务配置
    task_track_started=True,
    task_time_limit=3600,  # 任务超时时间（秒）
    task_soft_time_limit=3000,  # 软超时时间（秒）
    # 任务重试配置
    task_acks_late=True,  # 任务完成后才确认
    task_reject_on_worker_lost=True,  # worker 丢失时重新入队
    # 结果配置 - 文档处理结果已落库，不需要长期保存
    result_expires=3600,  # 结果仅保留 1 小时
    result_backend_transport_options={"retry_policy": {"timeout": 5.0}},  # 结果存储超时
    # 对于不需要结果的任务，可以在任务装饰器中设置 ignore_result=True
    task_ignore_result=False,  # 默认保留结果，方便调试
    # Worker 配置
    worker_prefetch_multiplier=1,  # 每次预取的任务数
    worker_concurrency=4,  # 并发 worker 数
    # 任务路由
    task_routes={
        "app.tasks.document.*": {"queue": "document"},
        "app.tasks.vcs.*": {"queue": "vcs"},
    },
    # 任务默认队列
    task_default_queue="default",
    # 定时任务配置（如果需要）
    beat_schedule={
        # 示例：每小时同步 VCS
        # "sync-vcs-hourly": {
        #     "task": "app.tasks.vcs.sync_all_vcs",
        #     "schedule": 3600.0,
        # },
    },
)

# 自动发现任务模块
celery_app.autodiscover_tasks(["app.tasks"])


@celery_app.task(bind=True)
def debug_task(self):
    """调试任务"""
    logger.info(f"Request: {self.request!r}")
    return {"status": "ok", "task_id": self.request.id}
