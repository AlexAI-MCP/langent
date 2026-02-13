"""
SmartChunker — Paragraph-aware text chunking
==============================================
Splits documents into overlapping chunks preserving paragraph boundaries.
"""
from typing import List, Dict, Any
import re


class SmartChunker:
    """문단/섹션 인식 스마트 청킹"""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        min_chunk_size: int = 50,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_document(
        self, text: str, metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        문서를 청크로 분할합니다.
        Returns: [{text, metadata}, ...]
        """
        if not text or len(text.strip()) < self.min_chunk_size:
            return []

        metadata = metadata or {}
        paragraphs = self._split_paragraphs(text)
        chunks = self._merge_paragraphs(paragraphs)

        results = []
        for i, chunk_text in enumerate(chunks):
            chunk_meta = {**metadata, "chunk_index": i, "total_chunks": len(chunks)}
            results.append({"text": chunk_text, "metadata": chunk_meta})

        return results

    def chunk_documents(
        self, documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """여러 문서를 한번에 청킹합니다."""
        all_chunks = []
        for doc in documents:
            chunks = self.chunk_document(doc["text"], doc.get("metadata", {}))
            all_chunks.extend(chunks)
        return all_chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        """문단 단위로 분할"""
        # Split by double newline, horizontal rule, or markdown headers
        parts = re.split(r'\n\n+|(?=^#{1,3}\s)', text, flags=re.MULTILINE)
        return [p.strip() for p in parts if p.strip()]

    def _merge_paragraphs(self, paragraphs: List[str]) -> List[str]:
        """문단들을 chunk_size에 맞게 병합"""
        chunks = []
        current = ""

        for para in paragraphs:
            if len(current) + len(para) + 2 <= self.chunk_size:
                current = f"{current}\n\n{para}" if current else para
            else:
                if current and len(current) >= self.min_chunk_size:
                    chunks.append(current.strip())
                # If paragraph itself is too long, split it
                if len(para) > self.chunk_size:
                    sub_chunks = self._hard_split(para)
                    chunks.extend(sub_chunks[:-1])
                    current = sub_chunks[-1] if sub_chunks else ""
                else:
                    # Start new chunk with overlap
                    if current and self.chunk_overlap > 0:
                        overlap = current[-self.chunk_overlap:]
                        current = overlap + "\n\n" + para
                    else:
                        current = para

        if current and len(current) >= self.min_chunk_size:
            chunks.append(current.strip())

        return chunks

    def _hard_split(self, text: str) -> List[str]:
        """긴 텍스트를 강제로 chunk_size 단위로 분할"""
        chunks = []
        while len(text) > self.chunk_size:
            # Try splitting at sentence boundary
            split_at = text[:self.chunk_size].rfind(". ")
            if split_at < self.chunk_size // 2:
                split_at = self.chunk_size
            else:
                split_at += 1
            chunks.append(text[:split_at].strip())
            text = text[split_at:].strip()
        if text:
            chunks.append(text)
        return chunks
