"""
HTML 文件解析器
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.services.parsers.base import (
    BaseParser,
    DocumentMetadata,
    PageContent,
    ParsedDocument,
)

logger = logging.getLogger(__name__)


class HtmlParser(BaseParser):
    """HTML 文件解析器"""

    supported_extensions: List[str] = [".html", ".htm", ".xhtml"]
    supported_mime_types: List[str] = [
        "text/html",
        "application/xhtml+xml",
    ]

    # 常见编码列表
    ENCODINGS = ["utf-8", "utf-8-sig", "gbk", "gb2312", "latin-1"]

    async def parse(self, file_path: str) -> ParsedDocument:
        """
        解析 HTML 文件

        Args:
            file_path: 文件路径

        Returns:
            解析后的文档对象
        """
        path = Path(file_path)

        # 先读取字节，然后检测编码
        raw_data = path.read_bytes()
        content, used_encoding = self._decode_html(raw_data)

        return self._parse_html_content(content, path, len(raw_data), used_encoding)

    async def parse_bytes(self, data: bytes, filename: str) -> ParsedDocument:
        """
        从字节数据解析 HTML 文件

        Args:
            data: 文件字节数据
            filename: 文件名

        Returns:
            解析后的文档对象
        """
        content, used_encoding = self._decode_html(data)
        path = Path(filename)

        return self._parse_html_content(content, path, len(data), used_encoding)

    def _decode_html(self, data: bytes) -> tuple:
        """
        解码 HTML 内容，优先使用 HTML 中声明的编码

        Args:
            data: 字节数据

        Returns:
            (content, encoding)
        """
        # 先尝试检测 HTML 中的编码声明
        declared_encoding = self._detect_html_encoding(data)

        if declared_encoding:
            try:
                return data.decode(declared_encoding), declared_encoding
            except (UnicodeDecodeError, LookupError):
                pass

        # 回退到常见编码列表
        for encoding in self.ENCODINGS:
            try:
                return data.decode(encoding), encoding
            except (UnicodeDecodeError, LookupError):
                continue

        return data.decode("latin-1", errors="replace"), "latin-1"

    def _detect_html_encoding(self, data: bytes) -> Optional[str]:
        """
        从 HTML 内容中检测编码声明

        Args:
            data: 字节数据

        Returns:
            编码名称
        """
        # 只检查前 1024 字节
        head = data[:1024].decode("ascii", errors="ignore")

        # 检查 meta charset
        match = re.search(r'<meta[^>]+charset=["\']?([^"\'\s>]+)', head, re.I)
        if match:
            return match.group(1)

        # 检查 Content-Type
        match = re.search(
            r'<meta[^>]+content=["\'][^"\']*charset=([^"\'\s;]+)', head, re.I
        )
        if match:
            return match.group(1)

        return None

    def _parse_html_content(
        self,
        content: str,
        path: Path,
        file_size: int,
        encoding: str,
    ) -> ParsedDocument:
        """
        解析 HTML 内容

        Args:
            content: HTML 内容
            path: 文件路径
            file_size: 文件大小
            encoding: 使用的编码

        Returns:
            解析后的文档对象
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("BeautifulSoup4 not installed, using basic HTML parsing")
            return self._parse_html_basic(content, path, file_size, encoding)

        soup = BeautifulSoup(content, "html.parser")

        # 提取标题
        title = None
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)
        if not title:
            h1_tag = soup.find("h1")
            if h1_tag:
                title = h1_tag.get_text(strip=True)
        if not title:
            title = path.stem

        # 提取作者
        author = None
        author_meta = soup.find("meta", attrs={"name": "author"})
        if author_meta:
            author = author_meta.get("content")

        # 移除脚本和样式
        for tag in soup(
            ["script", "style", "noscript", "iframe", "nav", "footer", "header"]
        ):
            tag.decompose()

        # 提取纯文本
        text_content = soup.get_text(separator="\n", strip=True)

        # 清理多余空行
        text_content = re.sub(r"\n{3,}", "\n\n", text_content)

        word_count = self.count_words(text_content)
        language = self.detect_language(text_content)

        # 提取图片
        images = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if src:
                images.append(src)

        # 提取表格
        tables = []
        for table in soup.find_all("table"):
            tables.append(str(table))

        metadata = DocumentMetadata(
            title=title,
            author=author,
            file_type=path.suffix.lower(),
            file_size=file_size,
            word_count=word_count,
            language=language,
            custom_fields={
                "encoding": encoding,
                "image_count": len(images),
                "table_count": len(tables),
            },
        )

        # 按主要内容区域分页（简单实现：整个内容作为一页）
        pages = [
            PageContent(
                page_number=1,
                content=text_content,
                images=images,
                tables=tables,
            )
        ]

        return ParsedDocument(
            content=text_content,
            metadata=metadata,
            pages=pages,
        )

    def _parse_html_basic(
        self,
        content: str,
        path: Path,
        file_size: int,
        encoding: str,
    ) -> ParsedDocument:
        """
        基础 HTML 解析（不使用 BeautifulSoup）

        Args:
            content: HTML 内容
            path: 文件路径
            file_size: 文件大小
            encoding: 使用的编码

        Returns:
            解析后的文档对象
        """
        # 移除脚本和样式
        text = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL | re.I)
        text = re.sub(r"<style[^>]*>.*?</style>", "", content, flags=re.DOTALL | re.I)

        # 移除所有标签
        text = re.sub(r"<[^>]+>", " ", text)

        # 解码 HTML 实体
        text = self._decode_html_entities(text)

        # 清理空白
        text = re.sub(r"\s+", " ", text).strip()

        # 提取标题
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", content, re.I)
        title = title_match.group(1).strip() if title_match else path.stem

        word_count = self.count_words(text)
        language = self.detect_language(text)

        metadata = DocumentMetadata(
            title=title,
            file_type=path.suffix.lower(),
            file_size=file_size,
            word_count=word_count,
            language=language,
            custom_fields={
                "encoding": encoding,
                "parser": "basic",
            },
        )

        pages = [
            PageContent(
                page_number=1,
                content=text,
            )
        ]

        return ParsedDocument(
            content=text,
            metadata=metadata,
            pages=pages,
        )

    def _decode_html_entities(self, text: str) -> str:
        """
        解码 HTML 实体

        Args:
            text: 包含 HTML 实体的文本

        Returns:
            解码后的文本
        """
        import html

        return html.unescape(text)
