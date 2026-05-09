"""
文档解析器基类和数据结构定义
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PageContent:
    """页面内容"""

    page_number: int  # 页码（从1开始）
    content: str  # 页面文本内容
    images: List[str] = field(default_factory=list)  # 图片路径列表
    tables: List[str] = field(default_factory=list)  # 表格内容列表


@dataclass
class DocumentMetadata:
    """文档元数据"""

    title: Optional[str] = None  # 文档标题
    author: Optional[str] = None  # 作者
    created_at: Optional[datetime] = None  # 创建时间
    modified_at: Optional[datetime] = None  # 修改时间
    page_count: Optional[int] = None  # 页数
    word_count: int = 0  # 字数
    language: str = "unknown"  # 检测到的语言
    file_type: str = ""  # 文件类型
    file_size: int = 0  # 文件大小（字节）
    custom_fields: Dict[str, Any] = field(default_factory=dict)  # 自定义字段

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "author": self.author,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "page_count": self.page_count,
            "word_count": self.word_count,
            "language": self.language,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "custom_fields": self.custom_fields,
        }


@dataclass
class ParsedDocument:
    """解析后的文档"""

    content: str  # 完整文本内容
    metadata: DocumentMetadata  # 元数据
    pages: List[PageContent] = field(default_factory=list)  # 按页分割的内容

    @property
    def total_content(self) -> str:
        """获取完整内容（如果 content 为空则合并 pages）"""
        if self.content:
            return self.content
        return "\n\n".join(page.content for page in self.pages if page.content)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "content": self.content,
            "metadata": self.metadata.to_dict(),
            "pages": [
                {
                    "page_number": p.page_number,
                    "content": p.content,
                    "images": p.images,
                    "tables": p.tables,
                }
                for p in self.pages
            ],
        }


class BaseParser(ABC):
    """文档解析器基类"""

    # 支持的文件扩展名列表
    supported_extensions: List[str] = []

    # MIME 类型列表
    supported_mime_types: List[str] = []

    @classmethod
    def can_parse(cls, file_path: str) -> bool:
        """
        检查是否能解析该文件

        Args:
            file_path: 文件路径

        Returns:
            是否支持解析
        """
        ext = Path(file_path).suffix.lower()
        return ext in cls.supported_extensions

    @classmethod
    def get_mime_type(cls, file_path: str) -> Optional[str]:
        """
        获取文件的 MIME 类型

        Args:
            file_path: 文件路径

        Returns:
            MIME 类型
        """
        import mimetypes

        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type

    @abstractmethod
    async def parse(self, file_path: str) -> ParsedDocument:
        """
        解析文档

        Args:
            file_path: 文件路径

        Returns:
            解析后的文档对象
        """
        pass

    @abstractmethod
    async def parse_bytes(self, data: bytes, filename: str) -> ParsedDocument:
        """
        从字节数据解析文档

        Args:
            data: 文件字节数据
            filename: 文件名（用于确定文件类型）

        Returns:
            解析后的文档对象
        """
        pass

    def extract_metadata(self, file_path: str) -> DocumentMetadata:
        """
        提取文档元数据

        Args:
            file_path: 文件路径

        Returns:
            文档元数据
        """
        path = Path(file_path)
        stat = path.stat()

        return DocumentMetadata(
            file_type=path.suffix.lower(),
            file_size=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime),
        )

    @staticmethod
    def count_words(text: str) -> int:
        """
        统计字数

        对于中文按字符计数，对于英文按空格分词计数

        Args:
            text: 文本内容

        Returns:
            字数
        """
        if not text:
            return 0

        # 简单的字数统计：中文字符 + 英文单词
        import re

        # 中文字符数
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))

        # 移除中文后计算英文单词数
        text_without_chinese = re.sub(r"[\u4e00-\u9fff]", " ", text)
        english_words = len(text_without_chinese.split())

        return chinese_chars + english_words

    @staticmethod
    def detect_language(text: str) -> str:
        """
        检测文本语言

        简单实现：根据中文字符比例判断

        Args:
            text: 文本内容

        Returns:
            语言代码（zh, en, mixed）
        """
        if not text:
            return "unknown"

        import re

        total_chars = len(text.replace(" ", "").replace("\n", ""))
        if total_chars == 0:
            return "unknown"

        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        chinese_ratio = chinese_chars / total_chars

        if chinese_ratio > 0.5:
            return "zh"
        elif chinese_ratio > 0.1:
            return "mixed"
        else:
            return "en"
