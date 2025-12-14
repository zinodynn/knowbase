"""
Celery 应用配置

配置 Celery 异步任务队列
"""

import logging

from celery import Celery

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# 创建 Celery 应用
celery_app = Celery(
    "knowbase",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

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
    
    # 结果配置
    result_expires=86400,  # 结果过期时间（秒）
    
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
