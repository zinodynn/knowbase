"""
PDF 文件解析器

使用 PyMuPDF (fitz) 进行 PDF 解析
"""

import io
import logging
import tempfile
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


class PdfParser(BaseParser):
    """PDF 文件解析器"""

    supported_extensions: List[str] = [".pdf"]
    supported_mime_types: List[str] = ["application/pdf"]

    async def parse(self, file_path: str) -> ParsedDocument:
        """
        解析 PDF 文件

        Args:
            file_path: 文件路径

        Returns:
            解析后的文档对象
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError(
                "PyMuPDF is required for PDF parsing. "
                "Install it with: pip install pymupdf"
            )

        path = Path(file_path)
        stat = path.stat()

        doc = fitz.open(file_path)

        try:
            return self._parse_pdf_document(doc, path, stat.st_size)
        finally:
            doc.close()

    async def parse_bytes(self, data: bytes, filename: str) -> ParsedDocument:
        """
        从字节数据解析 PDF 文件

        Args:
            data: 文件字节数据
            filename: 文件名

        Returns:
            解析后的文档对象
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError(
                "PyMuPDF is required for PDF parsing. "
                "Install it with: pip install pymupdf"
            )

        path = Path(filename)

        doc = fitz.open(stream=data, filetype="pdf")

        try:
            return self._parse_pdf_document(doc, path, len(data))
        finally:
            doc.close()

    def _parse_pdf_document(
        self,
        doc,
        path: Path,
        file_size: int,
    ) -> ParsedDocument:
        """
        解析 PDF 文档对象

        Args:
            doc: PyMuPDF Document 对象
            path: 文件路径
            file_size: 文件大小

        Returns:
            解析后的文档对象
        """
        import fitz

        # 提取元数据
        pdf_metadata = doc.metadata or {}

        title = pdf_metadata.get("title") or path.stem
        author = pdf_metadata.get("author")

        # 解析日期
        created_at = self._parse_pdf_date(pdf_metadata.get("creationDate"))
        modified_at = self._parse_pdf_date(pdf_metadata.get("modDate"))

        page_count = len(doc)

        # 提取每页内容
        pages = []
        all_content = []

        for page_num in range(page_count):
            page = doc[page_num]

            # 提取文本
            text = page.get_text("text")
            all_content.append(text)

            # 提取图片信息（只记录数量，不实际提取）
            images = []
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                images.append(f"image_{page_num + 1}_{img_index + 1}")

            # 提取表格（简单检测）
            tables = self._detect_tables(page)

            pages.append(
                PageContent(
                    page_number=page_num + 1,
                    content=text,
                    images=images,
                    tables=tables,
                )
            )

        # 合并所有内容
        full_content = "\n\n".join(all_content)
        word_count = self.count_words(full_content)
        language = self.detect_language(full_content)

        metadata = DocumentMetadata(
            title=title,
            author=author,
            created_at=created_at,
            modified_at=modified_at,
            page_count=page_count,
            file_type=".pdf",
            file_size=file_size,
            word_count=word_count,
            language=language,
            custom_fields={
                "producer": pdf_metadata.get("producer"),
                "creator": pdf_metadata.get("creator"),
                "subject": pdf_metadata.get("subject"),
                "keywords": pdf_metadata.get("keywords"),
                "format": pdf_metadata.get("format"),
            },
        )

        return ParsedDocument(
            content=full_content,
            metadata=metadata,
            pages=pages,
        )

    def _parse_pdf_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        解析 PDF 日期格式

        PDF 日期格式: D:YYYYMMDDHHmmSSOHH'mm'

        Args:
            date_str: PDF 日期字符串

        Returns:
            datetime 对象
        """
        if not date_str:
            return None

        try:
            # 移除 "D:" 前缀
            if date_str.startswith("D:"):
                date_str = date_str[2:]

            # 基本格式：YYYYMMDDHHMMSS
            if len(date_str) >= 14:
                return datetime.strptime(date_str[:14], "%Y%m%d%H%M%S")
            elif len(date_str) >= 8:
                return datetime.strptime(date_str[:8], "%Y%m%d")
        except ValueError:
            logger.warning(f"Failed to parse PDF date: {date_str}")

        return None

    def _detect_tables(self, page) -> List[str]:
        """
        简单检测页面中的表格

        Args:
            page: PyMuPDF Page 对象

        Returns:
            表格描述列表
        """
        tables = []

        try:
            # 使用 PyMuPDF 的表格检测（如果可用）
            if hasattr(page, "find_tables"):
                found_tables = page.find_tables()
                for i, table in enumerate(found_tables):
                    tables.append(f"table_{page.number + 1}_{i + 1}")
        except Exception as e:
            logger.debug(f"Table detection failed: {e}")

        return tables
