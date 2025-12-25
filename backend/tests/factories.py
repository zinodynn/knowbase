"""
测试数据工厂
使用 factory_boy 创建测试数据
"""

import uuid
from datetime import datetime, timezone

import factory
from app.core.security import get_password_hash
from app.models.document import Chunk, Document, DocumentStatus
from app.models.knowledge_base import KnowledgeBase, KnowledgeBaseVisibility
from app.models.user import User
from factory import LazyAttribute, LazyFunction, Sequence, SubFactory


class UserFactory(factory.Factory):
    """用户工厂"""

    class Meta:
        model = User

    id = LazyFunction(uuid.uuid4)
    username = Sequence(lambda n: f"user_{n}")
    email = LazyAttribute(lambda obj: f"{obj.username}@example.com")
    hashed_password = LazyFunction(lambda: get_password_hash("password123"))
    full_name = Sequence(lambda n: f"User {n}")
    is_active = True
    is_superuser = False
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = LazyFunction(lambda: datetime.now(timezone.utc))


class AdminUserFactory(UserFactory):
    """管理员用户工厂"""

    username = Sequence(lambda n: f"admin_{n}")
    is_superuser = True


class KnowledgeBaseFactory(factory.Factory):
    """知识库工厂"""

    class Meta:
        model = KnowledgeBase

    id = LazyFunction(uuid.uuid4)
    name = Sequence(lambda n: f"知识库_{n}")
    description = Sequence(lambda n: f"这是第 {n} 个测试知识库")
    visibility = KnowledgeBaseVisibility.PRIVATE
    owner_id = None  # 需要手动设置
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = LazyFunction(lambda: datetime.now(timezone.utc))


class DocumentFactory(factory.Factory):
    """文档工厂"""

    class Meta:
        model = Document

    id = LazyFunction(uuid.uuid4)
    knowledge_base_id = None  # 需要手动设置
    title = Sequence(lambda n: f"文档_{n}.pdf")
    file_type = "pdf"
    file_size = 1024
    storage_path = LazyAttribute(lambda obj: f"documents/{obj.id}/{obj.title}")
    status = DocumentStatus.PENDING
    uploader_id = None  # 需要手动设置
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = LazyFunction(lambda: datetime.now(timezone.utc))


class ChunkFactory(factory.Factory):
    """文本块工厂"""

    class Meta:
        model = Chunk

    id = LazyFunction(uuid.uuid4)
    document_id = None  # 需要手动设置
    content = Sequence(lambda n: f"这是第 {n} 个文本块的内容，用于测试向量搜索功能。")
    chunk_index = Sequence(lambda n: n)
    char_start = 0
    char_end = 100
    page_number = 1
    embedding_model_version = "text-embedding-ada-002"
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))


# ==================== 批量创建帮助函数 ====================


def create_users(count: int = 5) -> list[User]:
    """创建多个用户"""
    return [UserFactory.build() for _ in range(count)]


def create_knowledge_bases(owner_id: uuid.UUID, count: int = 3) -> list[KnowledgeBase]:
    """为指定用户创建多个知识库"""
    return [KnowledgeBaseFactory.build(owner_id=owner_id) for _ in range(count)]


def create_documents(
    kb_id: uuid.UUID,
    uploader_id: uuid.UUID,
    count: int = 5,
) -> list[Document]:
    """为指定知识库创建多个文档"""
    return [
        DocumentFactory.build(knowledge_base_id=kb_id, uploader_id=uploader_id)
        for _ in range(count)
    ]


def create_chunks(doc_id: uuid.UUID, count: int = 10) -> list[Chunk]:
    """为指定文档创建多个文本块"""
    return [
        ChunkFactory.build(
            document_id=doc_id,
            chunk_index=i,
            char_start=i * 100,
            char_end=(i + 1) * 100,
        )
        for i in range(count)
    ]
