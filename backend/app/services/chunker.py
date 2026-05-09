"""
文档分块器模块

提供多种分块策略：
- 固定长度分块（带 overlap）
- 语义分块（按段落、句子）
- 递归字符分割
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ChunkStrategy(str, Enum):
    """分块策略"""

    FIXED_SIZE = "fixed_size"  # 固定长度
    RECURSIVE = "recursive"  # 递归分割
    SEMANTIC = "semantic"  # 语义分割（按段落/句子）


@dataclass
class ChunkConfig:
    """分块配置"""

    strategy: ChunkStrategy = ChunkStrategy.RECURSIVE
    chunk_size: int = 1000  # 目标分块大小（字符数）
    chunk_overlap: int = 200  # 分块重叠大小
    separators: List[str] = field(
        default_factory=lambda: [
            "\n\n",  # 段落
            "\n",  # 换行
            "。",  # 中文句号
            ".",  # 英文句号
            "！",  # 中文感叹号
            "!",  # 英文感叹号
            "？",  # 中文问号
            "?",  # 英文问号
            "；",  # 中文分号
            ";",  # 英文分号
            " ",  # 空格
            "",  # 字符
        ]
    )
    min_chunk_size: int = 100  # 最小分块大小
    keep_separator: bool = True  # 是否保留分隔符


@dataclass
class Chunk:
    """文档分块"""

    content: str  # 分块文本内容
    index: int  # 在文档中的序号（从0开始）
    start_char: int  # 在原文中的起始字符位置
    end_char: int  # 在原文中的结束字符位置
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def token_count(self) -> int:
        """估算 token 数量（简单估算：中文1字=1token，英文4字符=1token）"""
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", self.content))
        other_chars = len(self.content) - chinese_chars
        return chinese_chars + (other_chars // 4)


class BaseChunker(ABC):
    """分块器基类"""

    def __init__(self, config: Optional[ChunkConfig] = None):
        self.config = config or ChunkConfig()

    @abstractmethod
    def chunk(
        self, text: str, metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        将文本分块

        Args:
            text: 待分块的文本
            metadata: 附加到每个分块的元数据

        Returns:
            分块列表
        """
        pass

    def _merge_metadata(
        self,
        base_metadata: Optional[Dict[str, Any]],
        chunk_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """合并元数据"""
        result = dict(base_metadata) if base_metadata else {}
        result.update(chunk_metadata)
        return result


class FixedSizeChunker(BaseChunker):
    """固定长度分块器"""

    def chunk(
        self, text: str, metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        按固定长度分块

        Args:
            text: 待分块的文本
            metadata: 附加到每个分块的元数据

        Returns:
            分块列表
        """
        if not text:
            return []

        chunks = []
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap

        start = 0
        index = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end]

            if chunk_text.strip():
                chunk_meta = self._merge_metadata(
                    metadata,
                    {
                        "chunk_index": index,
                        "strategy": "fixed_size",
                    },
                )

                chunks.append(
                    Chunk(
                        content=chunk_text,
                        index=index,
                        start_char=start,
                        end_char=end,
                        metadata=chunk_meta,
                    )
                )
                index += 1

            # 下一个起始位置（考虑重叠）
            start = end - overlap if end < len(text) else len(text)

        return chunks


class RecursiveChunker(BaseChunker):
    """递归字符分割器"""

    def chunk(
        self, text: str, metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        递归分割文本

        使用分隔符列表递归分割，直到每个块小于目标大小

        Args:
            text: 待分块的文本
            metadata: 附加到每个分块的元数据

        Returns:
            分块列表
        """
        if not text:
            return []

        # 递归分割
        texts = self._split_recursive(text, self.config.separators)

        # 合并小块，拆分大块
        merged = self._merge_splits(texts)

        # 创建 Chunk 对象
        chunks = []
        current_pos = 0

        for index, chunk_text in enumerate(merged):
            # 找到在原文中的位置
            start = text.find(chunk_text, current_pos)
            if start == -1:
                start = current_pos
            end = start + len(chunk_text)

            chunk_meta = self._merge_metadata(
                metadata,
                {
                    "chunk_index": index,
                    "strategy": "recursive",
                },
            )

            chunks.append(
                Chunk(
                    content=chunk_text,
                    index=index,
                    start_char=start,
                    end_char=end,
                    metadata=chunk_meta,
                )
            )

            current_pos = end

        return chunks

    def _split_recursive(self, text: str, separators: List[str]) -> List[str]:
        """
        递归分割文本

        Args:
            text: 待分割的文本
            separators: 分隔符列表

        Returns:
            分割后的文本列表
        """
        if not separators:
            return [text]

        separator = separators[0]
        remaining_separators = separators[1:]

        if not separator:
            # 空分隔符表示按字符分割
            return list(text)

        # 使用当前分隔符分割
        if self.config.keep_separator:
            # 保留分隔符在块的末尾
            parts = text.split(separator)
            splits = []
            for i, part in enumerate(parts):
                if i < len(parts) - 1:
                    splits.append(part + separator)
                elif part:
                    splits.append(part)
        else:
            splits = [s for s in text.split(separator) if s]

        # 检查每个块是否需要进一步分割
        final_splits = []
        for split in splits:
            if len(split) > self.config.chunk_size and remaining_separators:
                # 递归分割
                final_splits.extend(self._split_recursive(split, remaining_separators))
            else:
                final_splits.append(split)

        return final_splits

    def _merge_splits(self, splits: List[str]) -> List[str]:
        """
        合并小块，确保块大小在目标范围内

        Args:
            splits: 分割后的文本列表

        Returns:
            合并后的文本列表
        """
        if not splits:
            return []

        merged = []
        current_chunk = ""

        for split in splits:
            # 如果当前块为空，直接添加
            if not current_chunk:
                current_chunk = split
                continue

            # 计算合并后的长度
            combined_length = len(current_chunk) + len(split)

            if combined_length <= self.config.chunk_size:
                # 合并
                current_chunk += split
            else:
                # 保存当前块，开始新块
                if current_chunk.strip():
                    merged.append(current_chunk.strip())

                # 处理重叠
                if self.config.chunk_overlap > 0:
                    overlap_text = current_chunk[-self.config.chunk_overlap :]
                    current_chunk = overlap_text + split
                else:
                    current_chunk = split

        # 添加最后一块
        if current_chunk.strip():
            merged.append(current_chunk.strip())

        return merged


class SemanticChunker(BaseChunker):
    """语义分块器（按段落/句子）"""

    def chunk(
        self, text: str, metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        按语义边界分块

        优先按段落分割，如果段落太长则按句子分割

        Args:
            text: 待分块的文本
            metadata: 附加到每个分块的元数据

        Returns:
            分块列表
        """
        if not text:
            return []

        # 先按段落分割
        paragraphs = self._split_paragraphs(text)

        # 处理每个段落
        chunks = []
        current_pos = 0

        for para in paragraphs:
            if len(para) <= self.config.chunk_size:
                # 段落大小合适，直接作为一个块
                start = text.find(para, current_pos)
                if start == -1:
                    start = current_pos
                end = start + len(para)

                chunk_meta = self._merge_metadata(
                    metadata,
                    {
                        "chunk_index": len(chunks),
                        "strategy": "semantic",
                        "type": "paragraph",
                    },
                )

                chunks.append(
                    Chunk(
                        content=para,
                        index=len(chunks),
                        start_char=start,
                        end_char=end,
                        metadata=chunk_meta,
                    )
                )
                current_pos = end
            else:
                # 段落太长，按句子分割
                sentences = self._split_sentences(para)
                para_chunks = self._merge_sentences(sentences)

                for chunk_text in para_chunks:
                    start = text.find(chunk_text, current_pos)
                    if start == -1:
                        start = current_pos
                    end = start + len(chunk_text)

                    chunk_meta = self._merge_metadata(
                        metadata,
                        {
                            "chunk_index": len(chunks),
                            "strategy": "semantic",
                            "type": "sentences",
                        },
                    )

                    chunks.append(
                        Chunk(
                            content=chunk_text,
                            index=len(chunks),
                            start_char=start,
                            end_char=end,
                            metadata=chunk_meta,
                        )
                    )
                    current_pos = end

        return chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        """按段落分割"""
        # 按双换行分割
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_sentences(self, text: str) -> List[str]:
        """按句子分割"""
        # 中英文句子分隔符
        pattern = r"([。！？.!?]+)"
        parts = re.split(pattern, text)

        # 合并句子和标点
        sentences = []
        i = 0
        while i < len(parts):
            sentence = parts[i]
            if i + 1 < len(parts) and re.match(pattern, parts[i + 1]):
                sentence += parts[i + 1]
                i += 2
            else:
                i += 1
            if sentence.strip():
                sentences.append(sentence.strip())

        return sentences

    def _merge_sentences(self, sentences: List[str]) -> List[str]:
        """合并句子为合适大小的块"""
        if not sentences:
            return []

        merged = []
        current_chunk = ""

        for sentence in sentences:
            if not current_chunk:
                current_chunk = sentence
                continue

            combined_length = len(current_chunk) + len(sentence) + 1  # +1 for space

            if combined_length <= self.config.chunk_size:
                current_chunk += " " + sentence
            else:
                if current_chunk.strip():
                    merged.append(current_chunk.strip())
                current_chunk = sentence

        if current_chunk.strip():
            merged.append(current_chunk.strip())

        return merged


class DocumentChunker:
    """文档分块器（统一入口）"""

    CHUNKERS = {
        ChunkStrategy.FIXED_SIZE: FixedSizeChunker,
        ChunkStrategy.RECURSIVE: RecursiveChunker,
        ChunkStrategy.SEMANTIC: SemanticChunker,
    }

    def __init__(self, config: Optional[ChunkConfig] = None):
        self.config = config or ChunkConfig()
        self._chunker = self.CHUNKERS[self.config.strategy](self.config)

    def chunk(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """
        将文本分块

        Args:
            text: 待分块的文本
            metadata: 附加到每个分块的元数据

        Returns:
            分块列表
        """
        return self._chunker.chunk(text, metadata)

    def chunk_document(
        self,
        content: str,
        document_id: str,
        kb_id: str,
        filename: Optional[str] = None,
    ) -> List[Chunk]:
        """
        分块整个文档

        Args:
            content: 文档内容
            document_id: 文档 ID
            kb_id: 知识库 ID
            filename: 文件名

        Returns:
            分块列表
        """
        metadata = {
            "document_id": document_id,
            "kb_id": kb_id,
        }
        if filename:
            metadata["filename"] = filename

        return self.chunk(content, metadata)


def create_chunker(
    strategy: ChunkStrategy = ChunkStrategy.RECURSIVE,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    **kwargs,
) -> DocumentChunker:
    """
    创建分块器

    Args:
        strategy: 分块策略
        chunk_size: 目标分块大小
        chunk_overlap: 分块重叠大小
        **kwargs: 其他配置参数

    Returns:
        DocumentChunker 实例
    """
    config = ChunkConfig(
        strategy=strategy,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **kwargs,
    )
    return DocumentChunker(config)
