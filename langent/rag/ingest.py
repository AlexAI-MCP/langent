"""
DocumentIngestor v3 — Multi-format file ingestion
===================================================
Watches workspace folder, extracts text from PDF/MD/TXT/CSV,
feeds into chunker -> vector store.
"""
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class DocumentIngestor:
    """
    워크스페이스 파일들을 읽어 텍스트를 추출합니다.
    PDF, Markdown, TXT, CSV 지원.
    """

    SUPPORTED = {".md", ".txt", ".pdf", ".csv", ".json", ".yaml", ".yml"}

    def __init__(self, workspace_path: str, extensions: Optional[List[str]] = None,
                 ignore: Optional[List[str]] = None):
        self.workspace = Path(workspace_path)
        self.extensions = set(extensions) if extensions else self.SUPPORTED
        self.ignore = set(ignore) if ignore else {
            "node_modules", ".git", "__pycache__", ".env", "chroma_db"
        }

    def scan_files(self) -> List[Path]:
        """워크스페이스에서 지원 파일 목록을 스캔합니다."""
        files = []
        for root, dirs, filenames in os.walk(self.workspace):
            dirs[:] = [d for d in dirs if d not in self.ignore]
            for fname in filenames:
                fpath = Path(root) / fname
                if fpath.suffix.lower() in self.extensions:
                    files.append(fpath)
        return sorted(files)

    def extract_text(self, file_path: Path) -> Optional[str]:
        """파일에서 텍스트를 추출합니다."""
        suffix = file_path.suffix.lower()

        try:
            if suffix in (".md", ".txt", ".yaml", ".yml", ".json"):
                return self._read_text(file_path)
            elif suffix == ".pdf":
                return self._read_pdf(file_path)
            elif suffix == ".csv":
                return self._read_csv(file_path)
        except Exception as e:
            logger.warning("Error extracting %s: %s", file_path.name, e)
        return None

    def ingest_all(self) -> List[Dict[str, Any]]:
        """
        전체 워크스페이스를 수집합니다.
        Returns: [{text, metadata}, ...]
        """
        files = self.scan_files()
        results = []

        for fpath in files:
            text = self.extract_text(fpath)
            if text and len(text.strip()) > 20:
                rel_path = str(fpath.relative_to(self.workspace))
                results.append({
                    "text": text,
                    "metadata": {
                        "source": rel_path,
                        "filename": fpath.name,
                        "extension": fpath.suffix,
                        "size_bytes": fpath.stat().st_size,
                    },
                })
        return results

    # ─── File Readers ─────────────────────────────────

    def _read_text(self, path: Path) -> str:
        encodings = ["utf-8", "cp949", "euc-kr", "latin-1"]
        for enc in encodings:
            try:
                return path.read_text(encoding=enc)
            except (UnicodeDecodeError, ValueError):
                continue
        return ""

    def _read_pdf(self, path: Path) -> str:
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n\n".join(pages)
        except ImportError:
            logger.warning("pypdf not installed. Run: pip install pypdf")
            return ""

    def _read_csv(self, path: Path) -> str:
        import csv
        rows = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for i, row in enumerate(reader):
                    if i > 200:
                        break
                    rows.append(" | ".join(row))
        except Exception as e:
            logger.warning("CSV read failed for %s: %s", path.name, e)
        return "\n".join(rows)
