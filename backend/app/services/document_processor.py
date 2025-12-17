"""
文档处理服务

协调文档的解析、分块、embedding 和向量存储
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.config import get_settings
from app.models.document import Chunk, Document, DocumentStatus
from app.models.processing import ProcessingTask
from app.services.chunker import ChunkConfig, ChunkStrategy, RecursiveChunker
from app.services.embeddings.base import EmbeddingConfig, EmbeddingProvider
from app.services.embeddings.factory import EmbeddingFactory
from app.services.parsers import ParserFactory
from app.services.storage import get_storage_service
from app.services.vector_store.base import VectorRecord, VectorStoreConfig
from app.services.vector_store.qdrant_store import QdrantVectorStore
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ProcessingResult:
    """处理结果"""

    document_id: str
    success: bool
    chunk_count: int = 0
    vector_count: int = 0
    error_message: Optional[str] = None
    processing_time_ms: int = 0


class DocumentProcessor:
    """文档处理器

    处理流程：
    1. 从存储下载文档
    2. 解析文档提取文本
    3. 分块处理
    4. 生成向量
    5. 存储到向量数据库
    6. 更新数据库记录
    """

    def __init__(
        self,
        db: AsyncSession,
        embedding_config: Optional[EmbeddingConfig] = None,
        chunk_config: Optional[ChunkConfig] = None,
        vector_config: Optional[VectorStoreConfig] = None,
    ):
        """初始化文档处理器

        Args:
            db: 数据库会话
            embedding_config: Embedding 配置
            chunk_config: 分块配置
            vector_config: 向量存储配置
        """
        self.db = db

        # 初始化 Embedding 服务
        self.embedding_config = embedding_config or EmbeddingConfig(
            provider=EmbeddingProvider(settings.EMBEDDING_PROVIDER),
            api_key=settings.EMBEDDING_API_KEY,
            api_base=settings.EMBEDDING_API_BASE,
            model=settings.EMBEDDING_MODEL,
            dimension=settings.EMBEDDING_DIMENSION,
        )
        self.embedding_service = EmbeddingFactory.create(self.embedding_config)

        # 初始化分块器
        self.chunk_config = chunk_config or ChunkConfig(
            strategy=ChunkStrategy.RECURSIVE,
            chunk_size=1000,
            chunk_overlap=200,
        )
        self.chunker = RecursiveChunker(self.chunk_config)

        # 初始化向量存储
        self.vector_config = vector_config or VectorStoreConfig(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            api_key=settings.QDRANT_API_KEY,
        )
        self.vector_store = QdrantVectorStore(self.vector_config)

        # 存储服务
        self.storage = get_storage_service()

    async def process_document(
        self,
        document_id: UUID,
        force: bool = False,
    ) -> ProcessingResult:
        """处理单个文档

        Args:
            document_id: 文档 ID
            force: 是否强制重新处理

        Returns:
            处理结果
        """
        start_time = time.time()

        try:
            # 1. 获取文档信息
            result = await self.db.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()

            if not document:
                return ProcessingResult(
                    document_id=str(document_id),
                    success=False,
                    error_message="Document not found",
                )

            # 检查状态
            if document.status == DocumentStatus.COMPLETED and not force:
                return ProcessingResult(
                    document_id=str(document_id),
                    success=True,
                    chunk_count=document.chunk_count,
                    error_message="Document already processed",
                )

            # 2. 更新状态为处理中
            await self._update_document_status(document, DocumentStatus.PROCESSING)

            # 3. 从存储下载文档
            logger.info(f"Downloading document: {document.file_name}")
            content_bytes = await self.storage.download_file(document.storage_path)

            # 4. 解析文档
            logger.info(f"Parsing document: {document.file_name}")
            parser = ParserFactory.get_parser(document.file_name)
            parsed_content = await parser.parse_bytes(content_bytes, document.file_name)

            if not parsed_content.content:
                raise ValueError("Failed to extract text from document")

            # 5. 分块
            logger.info(f"Chunking document: {document.file_name}")
            chunks = self.chunker.chunk(
                text=parsed_content.content,
                metadata={
                    "document_id": str(document.id),
                    "kb_id": str(document.kb_id),
                    "file_name": document.file_name,
                    "file_type": document.file_type,
                },
            )

            if not chunks:
                raise ValueError("No chunks generated from document")

            logger.info(f"Generated {len(chunks)} chunks for {document.file_name}")

            # 6. 删除旧的分块（如果存在）
            await self._delete_existing_chunks(document.id)

            # 7. 生成向量并存储
            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            chunk_records = await self._embed_and_store_chunks(
                document=document,
                chunks=chunks,
            )

            # 8. 保存分块到数据库
            await self._save_chunks_to_db(document, chunk_records)

            # 9. 更新文档状态
            document.status = DocumentStatus.COMPLETED
            document.chunk_count = len(chunk_records)
            document.processed_at = datetime.now(timezone.utc)
            await self.db.commit()

            elapsed_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Document processed successfully: {document.file_name}, "
                f"chunks: {len(chunk_records)}, time: {elapsed_ms}ms"
            )

            return ProcessingResult(
                document_id=str(document_id),
                success=True,
                chunk_count=len(chunk_records),
                vector_count=len(chunk_records),
                processing_time_ms=elapsed_ms,
            )

        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {e}")

            # 更新状态为失败
            try:
                await self.db.execute(
                    update(Document)
                    .where(Document.id == document_id)
                    .values(status=DocumentStatus.FAILED)
                )
                await self.db.commit()
            except Exception:
                pass

            elapsed_ms = int((time.time() - start_time) * 1000)

            return ProcessingResult(
                document_id=str(document_id),
                success=False,
                error_message=str(e),
                processing_time_ms=elapsed_ms,
            )

    async def _update_document_status(
        self,
        document: Document,
        status: DocumentStatus,
    ) -> None:
        """更新文档状态"""
        document.status = status
        await self.db.commit()

    async def _delete_existing_chunks(self, document_id: UUID) -> None:
        """删除文档的现有分块"""
        # 获取现有分块的 vector_id
        result = await self.db.execute(
            select(Chunk.vector_id).where(
                Chunk.document_id == document_id,
                Chunk.vector_id.isnot(None),
            )
        )
        vector_ids = [row[0] for row in result.fetchall()]

        # 删除向量数据库中的向量
        if vector_ids:
            try:
                # 获取知识库 ID
                doc_result = await self.db.execute(
                    select(Document.kb_id).where(Document.id == document_id)
                )
                kb_id = doc_result.scalar_one()
                collection_name = self._get_collection_name(kb_id)

                await self.vector_store.delete_vectors(collection_name, vector_ids)
                logger.info(
                    f"Deleted {len(vector_ids)} vectors for document {document_id}"
                )
            except Exception as e:
                logger.warning(f"Failed to delete vectors: {e}")

        # 删除数据库中的分块记录
        from sqlalchemy import delete

        await self.db.execute(delete(Chunk).where(Chunk.document_id == document_id))
        await self.db.commit()

    async def _embed_and_store_chunks(
        self,
        document: Document,
        chunks: List,
    ) -> List[Dict[str, Any]]:
        """生成向量并存储到向量数据库

        Args:
            document: 文档对象
            chunks: 分块列表

        Returns:
            包含向量 ID 的分块记录列表
        """
        from uuid import uuid4

        collection_name = self._get_collection_name(document.kb_id)

        # 确保集合存在
        if not await self.vector_store.collection_exists(
            collection_name
        ):  # TODO: fix Unexpected Response: 502 (Bad Gateway)\nRaw response content:\nb''")
            await self.vector_store.create_collection(
                collection_name=collection_name,
                dimension=self.embedding_config.dimension,
            )

        # 提取分块文本
        chunk_texts = [chunk.content for chunk in chunks]

        # 批量生成向量
        embedding_result = await self.embedding_service.embed_texts(
            texts=chunk_texts,
            kb_id=str(document.kb_id),
        )

        # 构建向量记录
        vector_records = []
        chunk_records = []

        for i, (chunk, vector) in enumerate(zip(chunks, embedding_result.vectors)):
            vector_id = str(uuid4())

            vector_records.append(
                VectorRecord(
                    id=vector_id,
                    vector=vector,
                    payload={
                        "document_id": str(document.id),
                        "kb_id": str(document.kb_id),
                        "chunk_index": chunk.index,
                        "content": chunk.content,
                        "file_name": document.file_name,
                        "file_type": document.file_type,
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                    },
                )
            )

            chunk_records.append(
                {
                    "vector_id": vector_id,
                    "content": chunk.content,
                    "chunk_index": chunk.index,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "token_count": chunk.token_count,
                    "metadata": chunk.metadata,
                }
            )

        # 插入向量
        await self.vector_store.insert_vectors(collection_name, vector_records)

        logger.info(
            f"Stored {len(vector_records)} vectors for document {document.id}, "
            f"tokens used: {embedding_result.total_tokens}"
        )

        return chunk_records

    async def _save_chunks_to_db(
        self,
        document: Document,
        chunk_records: List[Dict[str, Any]],
    ) -> None:
        """保存分块到数据库

        Args:
            document: 文档对象
            chunk_records: 分块记录列表
        """
        for record in chunk_records:
            chunk = Chunk(
                document_id=document.id,
                kb_id=document.kb_id,
                content=record["content"],
                chunk_index=record["chunk_index"],
                start_char=record.get("start_char"),
                end_char=record.get("end_char"),
                token_count=record.get("token_count"),
                vector_id=record["vector_id"],
                doc_metadata=record.get("metadata"),
            )
            self.db.add(chunk)

        await self.db.flush()

    def _get_collection_name(self, kb_id: UUID) -> str:
        """获取知识库对应的向量集合名称"""
        return f"kb_{str(kb_id).replace('-', '_')}"

    async def delete_document_vectors(self, document_id: UUID) -> bool:
        """删除文档的所有向量

        Args:
            document_id: 文档 ID

        Returns:
            是否成功
        """
        try:
            await self._delete_existing_chunks(document_id)
            return True
        except Exception as e:
            logger.error(f"Failed to delete document vectors: {e}")
            return False


async def process_document_async(
    db: AsyncSession,
    document_id: UUID,
    force: bool = False,
) -> ProcessingResult:
    """异步处理文档的便捷函数

    Args:
        db: 数据库会话
        document_id: 文档 ID
        force: 是否强制重新处理

    Returns:
        处理结果
    """
    processor = DocumentProcessor(db)
    return await processor.process_document(document_id, force)
