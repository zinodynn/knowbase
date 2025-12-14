"""
MinIO 文件存储服务

提供文件上传、下载、删除和预签名URL生成功能
"""

import io
import logging
from datetime import timedelta
from pathlib import Path
from typing import BinaryIO, List, Optional, Tuple
from uuid import uuid4

from app.core.config import get_settings
from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)


class StorageService:
    """MinIO 文件存储服务封装"""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket: Optional[str] = None,
        secure: Optional[bool] = None,
    ):
        """
        初始化 MinIO 客户端

        Args:
            endpoint: MinIO 服务端点
            access_key: 访问密钥
            secret_key: 秘密密钥
            bucket: 默认存储桶
            secure: 是否使用 HTTPS
        """
        settings = get_settings()

        self.endpoint = endpoint or settings.MINIO_ENDPOINT
        self.access_key = access_key or settings.MINIO_ACCESS_KEY
        self.secret_key = secret_key or settings.MINIO_SECRET_KEY
        self.bucket = bucket or settings.MINIO_BUCKET
        self.secure = secure if secure is not None else settings.MINIO_SECURE

        self._client: Optional[Minio] = None
        self._initialized = False

    @property
    def client(self) -> Minio:
        """获取 MinIO 客户端（延迟初始化）"""
        if self._client is None:
            self._client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )
        return self._client

    async def initialize(self) -> None:
        """
        初始化存储服务
        确保存储桶存在
        """
        if self._initialized:
            return

        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"Created bucket: {self.bucket}")
            else:
                logger.info(f"Bucket exists: {self.bucket}")
            self._initialized = True
        except S3Error as e:
            logger.error(f"Failed to initialize storage: {e}")
            raise

    def _generate_object_name(
        self,
        kb_id: str,
        filename: str,
        document_id: Optional[str] = None,
    ) -> str:
        """
        生成对象名称（存储路径）

        路径格式: knowledge_bases/{kb_id}/documents/{document_id}/{filename}
        或: knowledge_bases/{kb_id}/documents/{uuid}/{filename}

        Args:
            kb_id: 知识库 ID
            filename: 原始文件名
            document_id: 文档 ID（可选）

        Returns:
            对象名称
        """
        doc_id = document_id or str(uuid4())
        safe_filename = Path(filename).name  # 确保只使用文件名，移除路径
        return f"knowledge_bases/{kb_id}/documents/{doc_id}/{safe_filename}"

    async def upload_file(
        self,
        file_data: BinaryIO,
        kb_id: str,
        filename: str,
        document_id: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        上传文件到 MinIO

        Args:
            file_data: 文件数据流
            kb_id: 知识库 ID
            filename: 原始文件名
            document_id: 文档 ID（可选）
            content_type: 文件 MIME 类型

        Returns:
            Tuple[object_name, etag]: 对象名称和 ETag

        Raises:
            S3Error: 上传失败
        """
        await self.initialize()

        object_name = self._generate_object_name(kb_id, filename, document_id)

        # 获取文件大小
        file_data.seek(0, 2)  # 移到文件末尾
        file_size = file_data.tell()
        file_data.seek(0)  # 移回开头

        try:
            result = self.client.put_object(
                bucket_name=self.bucket,
                object_name=object_name,
                data=file_data,
                length=file_size,
                content_type=content_type or "application/octet-stream",
            )
            logger.info(f"Uploaded file: {object_name}, etag: {result.etag}")
            return object_name, result.etag
        except S3Error as e:
            logger.error(f"Failed to upload file {filename}: {e}")
            raise

    async def upload_bytes(
        self,
        data: bytes,
        kb_id: str,
        filename: str,
        document_id: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        上传字节数据到 MinIO

        Args:
            data: 字节数据
            kb_id: 知识库 ID
            filename: 文件名
            document_id: 文档 ID（可选）
            content_type: 文件 MIME 类型

        Returns:
            Tuple[object_name, etag]: 对象名称和 ETag
        """
        return await self.upload_file(
            file_data=io.BytesIO(data),
            kb_id=kb_id,
            filename=filename,
            document_id=document_id,
            content_type=content_type,
        )

    async def download_file(self, object_name: str) -> bytes:
        """
        下载文件

        Args:
            object_name: 对象名称

        Returns:
            文件内容

        Raises:
            S3Error: 下载失败
        """
        await self.initialize()

        try:
            response = self.client.get_object(
                bucket_name=self.bucket,
                object_name=object_name,
            )
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Failed to download file {object_name}: {e}")
            raise

    async def download_to_file(
        self,
        object_name: str,
        file_path: str,
    ) -> None:
        """
        下载文件到本地路径

        Args:
            object_name: 对象名称
            file_path: 本地文件路径

        Raises:
            S3Error: 下载失败
        """
        await self.initialize()

        try:
            self.client.fget_object(
                bucket_name=self.bucket,
                object_name=object_name,
                file_path=file_path,
            )
            logger.info(f"Downloaded file to: {file_path}")
        except S3Error as e:
            logger.error(f"Failed to download file {object_name} to {file_path}: {e}")
            raise

    async def delete_file(self, object_name: str) -> None:
        """
        删除文件

        Args:
            object_name: 对象名称

        Raises:
            S3Error: 删除失败
        """
        await self.initialize()

        try:
            self.client.remove_object(
                bucket_name=self.bucket,
                object_name=object_name,
            )
            logger.info(f"Deleted file: {object_name}")
        except S3Error as e:
            logger.error(f"Failed to delete file {object_name}: {e}")
            raise

    async def delete_files(self, object_names: List[str]) -> None:
        """
        批量删除文件

        Args:
            object_names: 对象名称列表
        """
        await self.initialize()

        from minio.deleteobjects import DeleteObject

        delete_objects = [DeleteObject(name) for name in object_names]

        try:
            errors = list(self.client.remove_objects(self.bucket, delete_objects))
            if errors:
                for error in errors:
                    logger.error(f"Failed to delete {error.name}: {error.message}")
            else:
                logger.info(f"Deleted {len(object_names)} files")
        except S3Error as e:
            logger.error(f"Failed to delete files: {e}")
            raise

    async def delete_by_prefix(self, prefix: str) -> int:
        """
        删除指定前缀的所有文件

        Args:
            prefix: 对象名称前缀（如 knowledge_bases/{kb_id}/）

        Returns:
            删除的文件数量
        """
        await self.initialize()

        try:
            objects = list(
                self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
            )
            if not objects:
                return 0

            object_names = [obj.object_name for obj in objects]
            await self.delete_files(object_names)
            return len(object_names)
        except S3Error as e:
            logger.error(f"Failed to delete files with prefix {prefix}: {e}")
            raise

    async def file_exists(self, object_name: str) -> bool:
        """
        检查文件是否存在

        Args:
            object_name: 对象名称

        Returns:
            是否存在
        """
        await self.initialize()

        try:
            self.client.stat_object(self.bucket, object_name)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise

    async def get_file_info(self, object_name: str) -> Optional[dict]:
        """
        获取文件信息

        Args:
            object_name: 对象名称

        Returns:
            文件信息字典，包含 size, content_type, last_modified 等
        """
        await self.initialize()

        try:
            stat = self.client.stat_object(self.bucket, object_name)
            return {
                "object_name": stat.object_name,
                "size": stat.size,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
                "etag": stat.etag,
                "metadata": stat.metadata,
            }
        except S3Error as e:
            if e.code == "NoSuchKey":
                return None
            raise

    async def generate_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=1),
        response_headers: Optional[dict] = None,
    ) -> str:
        """
        生成预签名下载 URL

        Args:
            object_name: 对象名称
            expires: URL 有效期（默认1小时）
            response_headers: 响应头（如 Content-Disposition）

        Returns:
            预签名 URL
        """
        await self.initialize()

        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket,
                object_name=object_name,
                expires=expires,
                response_headers=response_headers,
            )
            return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL for {object_name}: {e}")
            raise

    async def generate_presigned_upload_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=1),
    ) -> str:
        """
        生成预签名上传 URL

        Args:
            object_name: 对象名称
            expires: URL 有效期（默认1小时）

        Returns:
            预签名上传 URL
        """
        await self.initialize()

        try:
            url = self.client.presigned_put_object(
                bucket_name=self.bucket,
                object_name=object_name,
                expires=expires,
            )
            return url
        except S3Error as e:
            logger.error(
                f"Failed to generate presigned upload URL for {object_name}: {e}"
            )
            raise

    async def list_files(
        self,
        prefix: str = "",
        recursive: bool = True,
    ) -> List[dict]:
        """
        列出文件

        Args:
            prefix: 对象名称前缀
            recursive: 是否递归列出子目录

        Returns:
            文件信息列表
        """
        await self.initialize()

        try:
            objects = self.client.list_objects(
                bucket_name=self.bucket,
                prefix=prefix,
                recursive=recursive,
            )
            return [
                {
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag,
                    "is_dir": obj.is_dir,
                }
                for obj in objects
            ]
        except S3Error as e:
            logger.error(f"Failed to list files with prefix {prefix}: {e}")
            raise

    async def list_kb_files(self, kb_id: str) -> List[dict]:
        """
        列出知识库的所有文件

        Args:
            kb_id: 知识库 ID

        Returns:
            文件信息列表
        """
        prefix = f"knowledge_bases/{kb_id}/"
        return await self.list_files(prefix=prefix)

    async def get_kb_storage_size(self, kb_id: str) -> int:
        """
        获取知识库存储占用大小

        Args:
            kb_id: 知识库 ID

        Returns:
            总大小（字节）
        """
        files = await self.list_kb_files(kb_id)
        return sum(f.get("size", 0) for f in files if not f.get("is_dir"))


# 存储服务单例
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """获取存储服务单例"""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service


async def init_storage_service() -> StorageService:
    """初始化存储服务"""
    service = get_storage_service()
    await service.initialize()
    return service
