"""
KnowBase 服务层模块
"""

from app.services.chunker import (
    Chunk,
    ChunkConfig,
    ChunkStrategy,
    DocumentChunker,
    create_chunker,
)
from app.services.embeddings import (
    BaseEmbeddingService,
    EmbeddingConfig,
    EmbeddingFactory,
    EmbeddingResult,
    create_embedding_service,
)
from app.services.parsers import BaseParser, ParsedDocument, ParserFactory, get_parser
from app.services.storage import StorageService, get_storage_service
from app.services.vector_store import (
    BaseVectorStore,
    QdrantVectorStore,
    SearchResult,
    VectorRecord,
)

__all__ = [
    # Storage
    "StorageService",
    "get_storage_service",
    # Chunker
    "ChunkConfig",
    "ChunkStrategy",
    "Chunk",
    "DocumentChunker",
    "create_chunker",
    # Parsers
    "BaseParser",
    "ParsedDocument",
    "ParserFactory",
    "get_parser",
    # Embeddings
    "BaseEmbeddingService",
    "EmbeddingConfig",
    "EmbeddingResult",
    "EmbeddingFactory",
    "create_embedding_service",
    # Vector Store
    "BaseVectorStore",
    "VectorRecord",
    "SearchResult",
    "QdrantVectorStore",
]
