"""
单元测试 - 文本分块器
测试 chunker 模块
"""

import pytest
from app.services.chunker import ChunkConfig, ChunkStrategy, DocumentChunker


class TestTextChunker:
    """文本分块器测试"""

    @pytest.fixture
    def chunker(self):
        """创建默认分块器"""
        return DocumentChunker(
            config=ChunkConfig(
                chunk_size=100,
                chunk_overlap=20,
                strategy=ChunkStrategy.FIXED_SIZE,
            )
        )

    @pytest.mark.unit
    def test_chunker_initialization(self, chunker):
        """测试分块器初始化"""
        assert chunker.config.chunk_size == 100
        assert chunker.config.chunk_overlap == 20

    @pytest.mark.unit
    def test_chunk_short_text(self, chunker):
        """测试短文本不分块"""
        text = "这是一段短文本。"
        chunks = chunker.chunk(text)

        assert len(chunks) == 1
        assert chunks[0].content == text

    @pytest.mark.unit
    def test_chunk_long_text(self, chunker):
        """测试长文本分块"""
        # 创建超过 chunk_size 的文本
        text = "这是一段很长的文本。" * 20
        chunks = chunker.chunk(text)

        assert len(chunks) > 1
        # 每个块都不应超过 chunk_size（允许一些余量）
        for chunk in chunks:
            assert len(chunk.content) <= chunker.config.chunk_size + 50

    @pytest.mark.unit
    def test_chunk_overlap(self, chunker):
        """测试分块重叠"""
        text = "A" * 50 + "B" * 50 + "C" * 50 + "D" * 50
        chunks = chunker.chunk(text)

        if len(chunks) > 1:
            # 第二个块应该包含第一个块末尾的内容
            first_end = chunks[0].content[-20:]
            second_start = chunks[1].content[:20]
            # 检查是否有重叠
            assert any(c in second_start for c in first_end)

    @pytest.mark.unit
    def test_chunk_metadata(self, chunker):
        """测试分块元数据"""
        text = "这是测试文本。" * 30
        chunks = chunker.chunk(text)

        for i, chunk in enumerate(chunks):
            assert hasattr(chunk, "content")
            assert hasattr(chunk, "index")
            assert chunk.index == i
            assert hasattr(chunk, "start_char")
            assert hasattr(chunk, "end_char")

    @pytest.mark.unit
    def test_chunk_empty_text(self, chunker):
        """测试空文本"""
        chunks = chunker.chunk("")

        assert len(chunks) == 0 or (len(chunks) == 1 and chunks[0].content == "")

    @pytest.mark.unit
    def test_chunk_whitespace_text(self, chunker):
        """测试纯空白文本"""
        chunks = chunker.chunk("   \n\t  ")

        # 应该处理或忽略纯空白
        assert len(chunks) <= 1


class TestChunkingStrategies:
    """不同分块策略测试"""

    @pytest.mark.unit
    def test_fixed_size_strategy(self):
        """测试固定大小策略"""
        chunker = DocumentChunker(
            config=ChunkConfig(
                chunk_size=50,
                chunk_overlap=10,
                strategy=ChunkStrategy.FIXED_SIZE,
            )
        )

        text = "A" * 100
        chunks = chunker.chunk(text)

        assert len(chunks) >= 2

    @pytest.mark.unit
    def test_sentence_strategy(self):
        """测试按句子分块策略"""
        chunker = DocumentChunker(
            config=ChunkConfig(
                chunk_size=100,
                chunk_overlap=0,
                strategy=ChunkStrategy.SEMANTIC,
            )
        )

        text = "第一句话。第二句话。第三句话。第四句话。第五句话。"
        chunks = chunker.chunk(text)

        # 句子策略应该在句子边界分割
        for chunk in chunks:
            # 每个块应该以句号结尾（除了最后一个可能不完整）
            content = chunk.content.strip()
            if content and chunk != chunks[-1]:
                assert content.endswith("。") or content.endswith(".")

    @pytest.mark.unit
    def test_paragraph_strategy(self):
        """测试按段落分块策略"""
        chunker = DocumentChunker(
            config=ChunkConfig(
                chunk_size=200,
                chunk_overlap=0,
                strategy=ChunkStrategy.SEMANTIC,
            )
        )

        text = "第一段内容。\n\n第二段内容。\n\n第三段内容。"
        chunks = chunker.chunk(text)

        # 段落策略应该在段落边界分割
        assert len(chunks) >= 1
