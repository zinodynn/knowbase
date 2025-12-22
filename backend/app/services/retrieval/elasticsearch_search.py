"""
Elasticsearch 全文检索服务

提供基于 Elasticsearch 的全文检索功能，支持中文分词
"""

import logging
from typing import Any, Dict, List, Optional

from app.services.retrieval.base import BaseRetriever, SearchConfig, SearchResult

logger = logging.getLogger(__name__)

# Elasticsearch 索引映射配置
CHUNK_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                # IK 分词器配置（需要安装 elasticsearch-analysis-ik 插件）
                "ik_smart_analyzer": {
                    "type": "custom",
                    "tokenizer": "ik_smart",
                    "filter": ["lowercase"],
                },
                "ik_max_analyzer": {
                    "type": "custom",
                    "tokenizer": "ik_max_word",
                    "filter": ["lowercase"],
                },
                # 标准分词器（回退方案）
                "standard_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding"],
                },
            }
        },
    },
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "kb_id": {"type": "keyword"},
            "document_id": {"type": "keyword"},
            "content": {
                "type": "text",
                "analyzer": "standard",  # 默认使用标准分词器
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "chunk_index": {"type": "integer"},
            "metadata": {"type": "object", "enabled": True},
            "document_filename": {"type": "keyword"},
            "created_at": {"type": "date"},
        }
    },
}

# 中文优化的索引映射（需要 IK 插件）
CHUNK_INDEX_MAPPING_CHINESE = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "ik_smart_analyzer": {
                    "type": "custom",
                    "tokenizer": "ik_smart",
                    "filter": ["lowercase"],
                },
                "ik_max_analyzer": {
                    "type": "custom",
                    "tokenizer": "ik_max_word",
                    "filter": ["lowercase"],
                },
            }
        },
    },
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "kb_id": {"type": "keyword"},
            "document_id": {"type": "keyword"},
            "content": {
                "type": "text",
                "analyzer": "ik_max_analyzer",
                "search_analyzer": "ik_smart_analyzer",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "chunk_index": {"type": "integer"},
            "metadata": {"type": "object", "enabled": True},
            "document_filename": {"type": "keyword"},
            "created_at": {"type": "date"},
        }
    },
}


class ElasticsearchService:
    """Elasticsearch 服务类

    提供索引管理和搜索功能
    """

    def __init__(
        self,
        es_url: str,
        index_prefix: str = "knowbase",
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_chinese_analyzer: bool = False,
    ):
        """
        初始化 Elasticsearch 服务

        Args:
            es_url: Elasticsearch URL
            index_prefix: 索引名称前缀
            username: 用户名（可选）
            password: 密码（可选）
            use_chinese_analyzer: 是否使用中文分词器
        """
        self.es_url = es_url
        self.index_prefix = index_prefix
        self.use_chinese_analyzer = use_chinese_analyzer
        self._client = None
        self._username = username
        self._password = password

    @property
    def client(self):
        """延迟加载 Elasticsearch 客户端"""
        if self._client is None:
            try:
                from elasticsearch import AsyncElasticsearch

                auth = None
                if self._username and self._password:
                    auth = (self._username, self._password)

                self._client = AsyncElasticsearch(
                    [self.es_url],
                    basic_auth=auth,
                    verify_certs=False,  # 开发环境禁用证书验证
                )
            except ImportError:
                raise ImportError(
                    "elasticsearch package is required. "
                    "Install it with: pip install elasticsearch[async]"
                )
        return self._client

    def _get_index_name(self, kb_id: str) -> str:
        """获取知识库对应的索引名称"""
        return f"{self.index_prefix}_chunks_{kb_id}"

    def _get_mapping(self) -> Dict[str, Any]:
        """获取索引映射配置"""
        if self.use_chinese_analyzer:
            return CHUNK_INDEX_MAPPING_CHINESE
        return CHUNK_INDEX_MAPPING

    async def create_index(self, kb_id: str) -> bool:
        """
        创建知识库索引

        Args:
            kb_id: 知识库 ID

        Returns:
            是否成功
        """
        index_name = self._get_index_name(kb_id)
        try:
            if not await self.client.indices.exists(index=index_name):
                await self.client.indices.create(
                    index=index_name,
                    body=self._get_mapping(),
                )
                logger.info(f"Created Elasticsearch index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create Elasticsearch index {index_name}: {e}")
            return False

    async def delete_index(self, kb_id: str) -> bool:
        """
        删除知识库索引

        Args:
            kb_id: 知识库 ID

        Returns:
            是否成功
        """
        index_name = self._get_index_name(kb_id)
        try:
            if await self.client.indices.exists(index=index_name):
                await self.client.indices.delete(index=index_name)
                logger.info(f"Deleted Elasticsearch index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete Elasticsearch index {index_name}: {e}")
            return False

    async def index_chunk(self, kb_id: str, chunk: Dict[str, Any]) -> bool:
        """
        索引单个 chunk

        Args:
            kb_id: 知识库 ID
            chunk: chunk 数据

        Returns:
            是否成功
        """
        index_name = self._get_index_name(kb_id)
        try:
            await self.client.index(
                index=index_name,
                id=chunk["id"],
                document={
                    "id": chunk["id"],
                    "kb_id": kb_id,
                    "document_id": chunk["document_id"],
                    "content": chunk["content"],
                    "chunk_index": chunk.get("chunk_index", 0),
                    "metadata": chunk.get("metadata", {}),
                    "document_filename": chunk.get("document_filename", ""),
                    "created_at": chunk.get("created_at"),
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to index chunk {chunk['id']}: {e}")
            return False

    async def bulk_index_chunks(self, kb_id: str, chunks: List[Dict[str, Any]]) -> int:
        """
        批量索引 chunks

        Args:
            kb_id: 知识库 ID
            chunks: chunk 数据列表

        Returns:
            成功索引的数量
        """
        if not chunks:
            return 0

        index_name = self._get_index_name(kb_id)

        try:
            from elasticsearch.helpers import async_bulk

            actions = [
                {
                    "_index": index_name,
                    "_id": chunk["id"],
                    "_source": {
                        "id": chunk["id"],
                        "kb_id": kb_id,
                        "document_id": chunk["document_id"],
                        "content": chunk["content"],
                        "chunk_index": chunk.get("chunk_index", 0),
                        "metadata": chunk.get("metadata", {}),
                        "document_filename": chunk.get("document_filename", ""),
                        "created_at": chunk.get("created_at"),
                    },
                }
                for chunk in chunks
            ]

            success, failed = await async_bulk(
                self.client, actions, raise_on_error=False
            )

            if failed:
                logger.warning(f"Bulk index failed for {len(failed)} chunks")

            return success

        except Exception as e:
            logger.error(f"Bulk index failed: {e}")
            return 0

    async def delete_chunk(self, kb_id: str, chunk_id: str) -> bool:
        """
        删除单个 chunk

        Args:
            kb_id: 知识库 ID
            chunk_id: chunk ID

        Returns:
            是否成功
        """
        index_name = self._get_index_name(kb_id)
        try:
            await self.client.delete(index=index_name, id=chunk_id)
            return True
        except Exception as e:
            logger.error(f"Failed to delete chunk {chunk_id}: {e}")
            return False

    async def delete_document_chunks(self, kb_id: str, document_id: str) -> int:
        """
        删除文档的所有 chunks

        Args:
            kb_id: 知识库 ID
            document_id: 文档 ID

        Returns:
            删除的数量
        """
        index_name = self._get_index_name(kb_id)
        try:
            result = await self.client.delete_by_query(
                index=index_name,
                body={"query": {"term": {"document_id": document_id}}},
            )
            deleted = result.get("deleted", 0)
            logger.info(
                f"Deleted {deleted} chunks for document {document_id} from {index_name}"
            )
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete document chunks: {e}")
            return 0

    async def search(
        self,
        kb_id: str,
        query: str,
        top_k: int = 10,
        document_ids: Optional[List[str]] = None,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        全文搜索

        Args:
            kb_id: 知识库 ID
            query: 搜索查询
            top_k: 返回结果数量
            document_ids: 可选的文档 ID 过滤
            min_score: 最低分数阈值

        Returns:
            搜索结果列表
        """
        index_name = self._get_index_name(kb_id)

        # 检查索引是否存在
        if not await self.client.indices.exists(index=index_name):
            logger.warning(f"Index {index_name} does not exist")
            return []

        # 构建查询
        must_clauses = [
            {
                "multi_match": {
                    "query": query,
                    "fields": ["content^2", "content.keyword"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            }
        ]

        filter_clauses = []
        if document_ids:
            filter_clauses.append({"terms": {"document_id": document_ids}})

        search_body = {
            "query": {
                "bool": {
                    "must": must_clauses,
                    "filter": filter_clauses if filter_clauses else None,
                }
            },
            "min_score": min_score if min_score > 0 else None,
            "size": top_k,
            "_source": [
                "id",
                "document_id",
                "content",
                "chunk_index",
                "metadata",
                "document_filename",
            ],
            "highlight": {
                "fields": {
                    "content": {
                        "fragment_size": 200,
                        "number_of_fragments": 3,
                    }
                }
            },
        }

        # 移除 None 值
        if not filter_clauses:
            del search_body["query"]["bool"]["filter"]
        if min_score <= 0:
            del search_body["min_score"]

        try:
            response = await self.client.search(index=index_name, body=search_body)

            results = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                results.append(
                    {
                        "chunk_id": hit["_id"],
                        "document_id": source["document_id"],
                        "content": source["content"],
                        "chunk_index": source.get("chunk_index", 0),
                        "metadata": source.get("metadata", {}),
                        "document_filename": source.get("document_filename", ""),
                        "score": hit["_score"],
                        "highlights": hit.get("highlight", {}).get("content", []),
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Elasticsearch search failed: {e}")
            return []

    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.close()
            self._client = None


class ElasticsearchKeywordSearch(BaseRetriever):
    """基于 Elasticsearch 的关键词检索"""

    def __init__(self, es_service: ElasticsearchService):
        """
        初始化 Elasticsearch 关键词检索

        Args:
            es_service: Elasticsearch 服务实例
        """
        self.es_service = es_service

    async def search(
        self,
        kb_id: str,
        query: str,
        config: Optional[SearchConfig] = None,
    ) -> List[SearchResult]:
        """
        执行关键词检索

        Args:
            kb_id: 知识库 ID
            query: 查询文本
            config: 检索配置

        Returns:
            检索结果列表
        """
        import time

        config = config or SearchConfig()
        start_time = time.time()

        results = await self.es_service.search(
            kb_id=kb_id,
            query=query,
            top_k=config.top_k,
            document_ids=config.document_ids,
            min_score=config.score_threshold,
        )

        # 转换为 SearchResult 格式
        search_results = []
        for item in results:
            search_results.append(
                SearchResult(
                    chunk_id=item["chunk_id"],
                    document_id=item["document_id"],
                    content=item["content"],
                    score=item["score"],
                    chunk_index=item.get("chunk_index", 0),
                    document_filename=item.get("document_filename", ""),
                    metadata=item.get("metadata", {}),
                )
            )

        # 应用过滤器
        search_results = self._apply_filters(search_results, config)

        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(
            f"Elasticsearch search in {kb_id}: query='{query[:50]}...', "
            f"results={len(search_results)}, time={elapsed_ms}ms"
        )

        return search_results

    async def index_chunk(self, kb_id: str, chunk: Dict[str, Any]) -> bool:
        """索引单个 chunk"""
        return await self.es_service.index_chunk(kb_id, chunk)

    async def bulk_index_chunks(self, kb_id: str, chunks: List[Dict[str, Any]]) -> int:
        """批量索引 chunks"""
        return await self.es_service.bulk_index_chunks(kb_id, chunks)

    async def delete_chunk(self, kb_id: str, chunk_id: str) -> bool:
        """删除单个 chunk 的索引"""
        return await self.es_service.delete_chunk(kb_id, chunk_id)

    async def delete_document_chunks(self, kb_id: str, document_id: str) -> int:
        """删除文档的所有 chunks"""
        return await self.es_service.delete_document_chunks(kb_id, document_id)


def get_elasticsearch_service(
    es_url: str,
    index_prefix: str = "knowbase",
    username: Optional[str] = None,
    password: Optional[str] = None,
    use_chinese_analyzer: bool = False,
) -> ElasticsearchService:
    """
    获取 Elasticsearch 服务实例

    Args:
        es_url: Elasticsearch URL
        index_prefix: 索引前缀
        username: 用户名
        password: 密码
        use_chinese_analyzer: 是否使用中文分词器

    Returns:
        Elasticsearch 服务实例
    """
    return ElasticsearchService(
        es_url=es_url,
        index_prefix=index_prefix,
        username=username,
        password=password,
        use_chinese_analyzer=use_chinese_analyzer,
    )
