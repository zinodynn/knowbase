"""
TXT 文本文件解析器
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List

from app.services.parsers.base import (
    BaseParser,
    DocumentMetadata,
    PageContent,
    ParsedDocument,
)

logger = logging.getLogger(__name__)


class TxtParser(BaseParser):
    """纯文本文件解析器"""

    supported_extensions: List[str] = [".txt", ".text", ".log"]
    supported_mime_types: List[str] = ["text/plain"]

    # 常见编码列表，按优先级排序
    ENCODINGS = ["utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030", "latin-1"]

    async def parse(self, file_path: str) -> ParsedDocument:
        """
        解析文本文件

        Args:
            file_path: 文件路径

        Returns:
            解析后的文档对象
        """
        path = Path(file_path)

        # 尝试多种编码读取
        content = None
        used_encoding = None

        for encoding in self.ENCODINGS:
            try:
                content = path.read_text(encoding=encoding)
                used_encoding = encoding
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if content is None:
            # 如果所有编码都失败，使用 latin-1（不会失败）
            content = path.read_bytes().decode("latin-1", errors="replace")
            used_encoding = "latin-1"

        # 提取元数据
        stat = path.stat()
        word_count = self.count_words(content)
        language = self.detect_language(content)

        metadata = DocumentMetadata(
            title=path.stem,
            file_type=path.suffix.lower(),
            file_size=stat.st_size,
            word_count=word_count,
            language=language,
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            custom_fields={
                "encoding": used_encoding,
            },
        )

        # 简单地将整个内容作为一页
        pages = [
            PageContent(
                page_number=1,
                content=content,
            )
        ]

        return ParsedDocument(
            content=content,
            metadata=metadata,
            pages=pages,
        )

    async def parse_bytes(self, data: bytes, filename: str) -> ParsedDocument:
        """
        从字节数据解析文本文件

        Args:
            data: 文件字节数据
            filename: 文件名

        Returns:
            解析后的文档对象
        """
        # 尝试多种编码解码
        content = None
        used_encoding = None

        for encoding in self.ENCODINGS:
            try:
                content = data.decode(encoding)
                used_encoding = encoding
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if content is None:
            content = data.decode("latin-1", errors="replace")
            used_encoding = "latin-1"

        # 提取元数据
        word_count = self.count_words(content)
        language = self.detect_language(content)

        path = Path(filename)
        metadata = DocumentMetadata(
            title=path.stem,
            file_type=path.suffix.lower(),
            file_size=len(data),
            word_count=word_count,
            language=language,
            custom_fields={
                "encoding": used_encoding,
            },
        )

        pages = [
            PageContent(
                page_number=1,
                content=content,
            )
        ]

        return ParsedDocument(
            content=content,
            metadata=metadata,
            pages=pages,
        )
