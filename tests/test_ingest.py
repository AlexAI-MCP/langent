"""Tests for langent.rag.ingest"""
import pytest
from langent.rag.ingest import DocumentIngestor


class TestDocumentIngestor:
    def test_scan_files_finds_supported_types(self, tmp_workspace):
        ingestor = DocumentIngestor(workspace_path=str(tmp_workspace))
        files = ingestor.scan_files()
        extensions = {f.suffix for f in files}
        assert ".md" in extensions
        assert ".txt" in extensions
        assert ".csv" in extensions

    def test_scan_files_ignores_directories(self, tmp_workspace):
        # Create an ignored directory
        git_dir = tmp_workspace / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("git config")

        ingestor = DocumentIngestor(workspace_path=str(tmp_workspace))
        files = ingestor.scan_files()
        for f in files:
            assert ".git" not in str(f)

    def test_extract_text_markdown(self, tmp_workspace):
        ingestor = DocumentIngestor(workspace_path=str(tmp_workspace))
        md_file = tmp_workspace / "sample.md"
        text = ingestor.extract_text(md_file)
        assert text is not None
        assert "AI Research" in text

    def test_extract_text_csv(self, tmp_workspace):
        ingestor = DocumentIngestor(workspace_path=str(tmp_workspace))
        csv_file = tmp_workspace / "data.csv"
        text = ingestor.extract_text(csv_file)
        assert text is not None
        assert "ChromaDB" in text

    def test_ingest_all(self, tmp_workspace):
        ingestor = DocumentIngestor(workspace_path=str(tmp_workspace))
        results = ingestor.ingest_all()
        assert len(results) >= 3  # md, txt, csv
        for doc in results:
            assert "text" in doc
            assert "metadata" in doc
            assert "source" in doc["metadata"]
            assert "filename" in doc["metadata"]

    def test_custom_extensions(self, tmp_workspace):
        ingestor = DocumentIngestor(
            workspace_path=str(tmp_workspace),
            extensions=[".md"],
        )
        files = ingestor.scan_files()
        assert all(f.suffix == ".md" for f in files)

    def test_empty_workspace(self, tmp_path):
        ingestor = DocumentIngestor(workspace_path=str(tmp_path))
        results = ingestor.ingest_all()
        assert results == []
