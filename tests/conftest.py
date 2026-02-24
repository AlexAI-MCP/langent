"""
Langent v3 — Test configuration and shared fixtures
"""
import os
import tempfile
import pytest

# Ensure test mode
os.environ.setdefault("LANGENT_WORKSPACE", ".")
os.environ.setdefault("CHROMA_DB_PATH", "./data/test_chroma")


@pytest.fixture
def tmp_workspace(tmp_path):
    """Create a temporary workspace with sample files."""
    # Create sample markdown file
    md_file = tmp_path / "sample.md"
    md_file.write_text(
        "# AI Research Notes\n\n"
        "Artificial intelligence is transforming the landscape of technology.\n\n"
        "## Vector Databases\n\n"
        "ChromaDB provides fast semantic search using embeddings.\n\n"
        "## Knowledge Graphs\n\n"
        "Neo4j enables graph-based relationship traversal.",
        encoding="utf-8",
    )

    # Create sample text file
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text(
        "LangChain and LangGraph provide powerful agent workflows.\n"
        "Three.js enables 3D visualization in the browser.\n"
        "UMAP reduces high-dimensional embeddings to 3D coordinates.",
        encoding="utf-8",
    )

    # Create sample CSV
    csv_file = tmp_path / "data.csv"
    csv_file.write_text(
        "name,category,score\n"
        "ChromaDB,vector_db,95\n"
        "Neo4j,graph_db,90\n"
        "LangChain,framework,88\n",
        encoding="utf-8",
    )

    return tmp_path


@pytest.fixture
def vector_store(tmp_path):
    """Create a temporary VectorStore instance."""
    from langent.store.vector import VectorStore
    db_path = str(tmp_path / "test_chroma")
    return VectorStore(
        db_path=db_path,
        collection_name="test_collection",
    )


@pytest.fixture
def config():
    """Create a default LangentConfig."""
    from langent.config import LangentConfig
    return LangentConfig()
