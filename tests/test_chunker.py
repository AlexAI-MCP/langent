"""Tests for langent.rag.chunker"""
import pytest
from langent.rag.chunker import SmartChunker


class TestSmartChunker:
    def test_empty_text_returns_empty(self):
        chunker = SmartChunker(chunk_size=100, min_chunk_size=10)
        assert chunker.chunk_document("", {}) == []
        assert chunker.chunk_document("   ", {}) == []

    def test_short_text_below_min_returns_empty(self):
        chunker = SmartChunker(chunk_size=100, min_chunk_size=50)
        result = chunker.chunk_document("Short text", {"source": "test"})
        assert result == []

    def test_single_chunk_within_size(self):
        chunker = SmartChunker(chunk_size=500, chunk_overlap=50, min_chunk_size=10)
        text = "This is a paragraph with enough content to pass the minimum size threshold for chunking."
        result = chunker.chunk_document(text, {"source": "test.md"})
        assert len(result) == 1
        assert result[0]["text"] == text
        assert result[0]["metadata"]["source"] == "test.md"
        assert result[0]["metadata"]["chunk_index"] == 0

    def test_multiple_chunks_created(self):
        chunker = SmartChunker(chunk_size=100, chunk_overlap=20, min_chunk_size=30)
        paragraphs = ["Paragraph one with some content here."] * 10
        text = "\n\n".join(paragraphs)
        result = chunker.chunk_document(text, {"source": "long.md"})
        assert len(result) > 1
        for chunk in result:
            assert chunk["metadata"]["total_chunks"] == len(result)

    def test_chunk_documents_batch(self):
        chunker = SmartChunker(chunk_size=200, min_chunk_size=20)
        docs = [
            {"text": "First document with sufficient content for testing purposes.", "metadata": {"source": "a.md"}},
            {"text": "Second document also has enough content for the chunking test.", "metadata": {"source": "b.md"}},
        ]
        result = chunker.chunk_documents(docs)
        assert len(result) >= 2
        sources = {c["metadata"]["source"] for c in result}
        assert "a.md" in sources
        assert "b.md" in sources

    def test_hard_split_long_paragraph(self):
        chunker = SmartChunker(chunk_size=50, chunk_overlap=0, min_chunk_size=10)
        text = "A" * 200
        result = chunker.chunk_document(text, {"source": "long"})
        assert len(result) >= 2

    def test_metadata_preserved(self):
        chunker = SmartChunker(chunk_size=500, min_chunk_size=10)
        text = "Enough content to create a valid chunk for testing metadata preservation."
        meta = {"source": "doc.md", "custom_field": "value"}
        result = chunker.chunk_document(text, meta)
        assert result[0]["metadata"]["custom_field"] == "value"
