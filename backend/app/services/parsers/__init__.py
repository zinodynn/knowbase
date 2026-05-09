"""
文档解析器模块

支持多种文档格式的解析：
- PDF
- Word (DOCX)
- Markdown
- TXT
- HTML
- Excel
- 代码文件
"""

from app.services.parsers.base import (
    BaseParser,
    DocumentMetadata,
    PageContent,
    ParsedDocument,
)
from app.services.parsers.factory import ParserFactory, get_parser

__all__ = [
    "BaseParser",
    "DocumentMetadata",
    "PageContent",
    "ParsedDocument",
    "ParserFactory",
    "get_parser",
]
