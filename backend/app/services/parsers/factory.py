"""
文档解析器工厂

根据文件类型自动选择合适的解析器
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Type

from app.services.parsers.base import BaseParser, ParsedDocument

logger = logging.getLogger(__name__)


class ParserFactory:
    """文档解析器工厂"""

    _parsers: Dict[str, Type[BaseParser]] = {}
    _initialized: bool = False

    @classmethod
    def _ensure_initialized(cls) -> None:
        """确保解析器已注册"""
        if cls._initialized:
            return

        # 延迟导入，避免循环依赖
        from app.services.parsers.docx_parser import DocxParser
        from app.services.parsers.excel_parser import ExcelParser
        from app.services.parsers.html_parser import HtmlParser
        from app.services.parsers.markdown_parser import MarkdownParser
        from app.services.parsers.pdf_parser import PdfParser
        from app.services.parsers.txt_parser import TxtParser

        # 注册所有解析器
        cls.register_parser(TxtParser)
        cls.register_parser(MarkdownParser)
        cls.register_parser(HtmlParser)
        cls.register_parser(PdfParser)
        cls.register_parser(DocxParser)
        cls.register_parser(ExcelParser)

        cls._initialized = True

    @classmethod
    def register_parser(cls, parser_class: Type[BaseParser]) -> None:
        """
        注册解析器

        Args:
            parser_class: 解析器类
        """
        for ext in parser_class.supported_extensions:
            cls._parsers[ext.lower()] = parser_class
            logger.debug(f"Registered parser for {ext}: {parser_class.__name__}")

    @classmethod
    def get_parser(cls, file_path: str) -> Optional[BaseParser]:
        """
        获取适合的解析器实例

        Args:
            file_path: 文件路径或文件名

        Returns:
            解析器实例，如果不支持则返回 None
        """
        cls._ensure_initialized()

        ext = Path(file_path).suffix.lower()
        parser_class = cls._parsers.get(ext)

        if parser_class:
            return parser_class()

        return None

    @classmethod
    def get_parser_by_extension(cls, extension: str) -> Optional[BaseParser]:
        """
        根据扩展名获取解析器

        Args:
            extension: 文件扩展名（如 ".pdf" 或 "pdf"）

        Returns:
            解析器实例
        """
        cls._ensure_initialized()

        ext = extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"

        parser_class = cls._parsers.get(ext)

        if parser_class:
            return parser_class()

        return None

    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """
        获取所有支持的文件扩展名

        Returns:
            扩展名列表
        """
        cls._ensure_initialized()
        return list(cls._parsers.keys())

    @classmethod
    def is_supported(cls, file_path: str) -> bool:
        """
        检查文件是否支持解析

        Args:
            file_path: 文件路径或文件名

        Returns:
            是否支持
        """
        cls._ensure_initialized()
        ext = Path(file_path).suffix.lower()
        return ext in cls._parsers

    @classmethod
    async def parse(cls, file_path: str) -> ParsedDocument:
        """
        解析文件

        Args:
            file_path: 文件路径

        Returns:
            解析后的文档

        Raises:
            ValueError: 不支持的文件类型
        """
        parser = cls.get_parser(file_path)

        if not parser:
            ext = Path(file_path).suffix
            raise ValueError(f"Unsupported file type: {ext}")

        return await parser.parse(file_path)

    @classmethod
    async def parse_bytes(
        cls,
        data: bytes,
        filename: str,
    ) -> ParsedDocument:
        """
        从字节数据解析文件

        Args:
            data: 文件字节数据
            filename: 文件名（用于确定类型）

        Returns:
            解析后的文档

        Raises:
            ValueError: 不支持的文件类型
        """
        parser = cls.get_parser(filename)

        if not parser:
            ext = Path(filename).suffix
            raise ValueError(f"Unsupported file type: {ext}")

        return await parser.parse_bytes(data, filename)


def get_parser(file_path: str) -> Optional[BaseParser]:
    """
    获取适合的解析器实例

    快捷函数，等同于 ParserFactory.get_parser

    Args:
        file_path: 文件路径或文件名

    Returns:
        解析器实例
    """
    return ParserFactory.get_parser(file_path)
