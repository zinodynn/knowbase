"""
Markdown 文件解析器
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from app.services.parsers.base import (
    BaseParser,
    DocumentMetadata,
    PageContent,
    ParsedDocument,
)

logger = logging.getLogger(__name__)


class MarkdownParser(BaseParser):
    """Markdown 文件解析器"""

    supported_extensions: List[str] = [".md", ".markdown", ".mdown", ".mkd"]
    supported_mime_types: List[str] = ["text/markdown", "text/x-markdown"]

    # 常见编码列表
    ENCODINGS = ["utf-8", "utf-8-sig", "gbk", "gb2312", "latin-1"]

    async def parse(self, file_path: str) -> ParsedDocument:
        """
        解析 Markdown 文件

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
            content = path.read_bytes().decode("latin-1", errors="replace")
            used_encoding = "latin-1"

        # 提取标题和元数据
        title, frontmatter = self._extract_frontmatter(content)
        if not title:
            title = self._extract_title_from_content(content) or path.stem

        # 提取元数据
        stat = path.stat()
        word_count = self.count_words(self._strip_markdown(content))
        language = self.detect_language(content)

        metadata = DocumentMetadata(
            title=title,
            file_type=path.suffix.lower(),
            file_size=stat.st_size,
            word_count=word_count,
            language=language,
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            custom_fields={
                "encoding": used_encoding,
                "frontmatter": frontmatter,
            },
        )

        # 按章节分页
        pages = self._split_by_headers(content)

        return ParsedDocument(
            content=content,
            metadata=metadata,
            pages=pages,
        )

    async def parse_bytes(self, data: bytes, filename: str) -> ParsedDocument:
        """
        从字节数据解析 Markdown 文件

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

        # 提取标题和元数据
        path = Path(filename)
        title, frontmatter = self._extract_frontmatter(content)
        if not title:
            title = self._extract_title_from_content(content) or path.stem

        word_count = self.count_words(self._strip_markdown(content))
        language = self.detect_language(content)

        metadata = DocumentMetadata(
            title=title,
            file_type=path.suffix.lower(),
            file_size=len(data),
            word_count=word_count,
            language=language,
            custom_fields={
                "encoding": used_encoding,
                "frontmatter": frontmatter,
            },
        )

        pages = self._split_by_headers(content)

        return ParsedDocument(
            content=content,
            metadata=metadata,
            pages=pages,
        )

    def _extract_frontmatter(self, content: str) -> Tuple[Optional[str], dict]:
        """
        提取 YAML frontmatter

        Args:
            content: Markdown 内容

        Returns:
            (title, frontmatter_dict)
        """
        frontmatter = {}
        title = None

        # 匹配 YAML frontmatter
        pattern = r"^---\s*\n(.*?)\n---\s*\n"
        match = re.match(pattern, content, re.DOTALL)

        if match:
            try:
                import yaml

                frontmatter = yaml.safe_load(match.group(1)) or {}
                title = frontmatter.get("title")
            except Exception:
                # 如果 YAML 解析失败，忽略
                pass

        return title, frontmatter

    def _extract_title_from_content(self, content: str) -> Optional[str]:
        """
        从内容中提取标题（第一个 # 标题）

        Args:
            content: Markdown 内容

        Returns:
            标题文本
        """
        # 跳过 frontmatter
        content = re.sub(r"^---\s*\n.*?\n---\s*\n", "", content, flags=re.DOTALL)

        # 匹配第一个 # 标题
        match = re.search(r"^#\s+(.+)$", content.strip(), re.MULTILINE)
        if match:
            return match.group(1).strip()

        return None

    def _strip_markdown(self, content: str) -> str:
        """
        移除 Markdown 语法，保留纯文本

        Args:
            content: Markdown 内容

        Returns:
            纯文本内容
        """
        # 移除 frontmatter
        text = re.sub(r"^---\s*\n.*?\n---\s*\n", "", content, flags=re.DOTALL)

        # 移除代码块
        text = re.sub(r"```[\s\S]*?```", "", text)
        text = re.sub(r"`[^`]+`", "", text)

        # 移除链接，保留文本
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)

        # 移除图片
        text = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"\1", text)

        # 移除标题标记
        text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)

        # 移除强调标记
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        text = re.sub(r"__([^_]+)__", r"\1", text)
        text = re.sub(r"_([^_]+)_", r"\1", text)

        # 移除列表标记
        text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)

        # 移除引用标记
        text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)

        # 移除水平线
        text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

        return text.strip()

    def _split_by_headers(self, content: str) -> List[PageContent]:
        """
        按标题分割内容

        Args:
            content: Markdown 内容

        Returns:
            页面内容列表
        """
        # 移除 frontmatter
        content = re.sub(r"^---\s*\n.*?\n---\s*\n", "", content, flags=re.DOTALL)

        # 按一级或二级标题分割
        pattern = r"^(#{1,2}\s+.+)$"
        parts = re.split(pattern, content.strip(), flags=re.MULTILINE)

        pages = []
        current_content = ""
        page_number = 1

        for i, part in enumerate(parts):
            if re.match(r"^#{1,2}\s+", part):
                # 这是标题行，开始新页面
                if current_content.strip():
                    pages.append(
                        PageContent(
                            page_number=page_number,
                            content=current_content.strip(),
                        )
                    )
                    page_number += 1
                current_content = part + "\n"
            else:
                current_content += part

        # 添加最后一部分
        if current_content.strip():
            pages.append(
                PageContent(
                    page_number=page_number,
                    content=current_content.strip(),
                )
            )

        # 如果没有按标题分割，将整个内容作为一页
        if not pages:
            pages.append(
                PageContent(
                    page_number=1,
                    content=content.strip(),
                )
            )

        return pages
