"""
Langent Config v3 — Settings from .env + YAML
"""
import logging
from pathlib import Path
from typing import Optional, List

from pydantic import BaseModel
from pydantic_settings import BaseSettings
import yaml

logger = logging.getLogger(__name__)


class VectorStoreConfig(BaseModel):
    provider: str = "chromadb"
    collection: str = "langent_knowledge"
    embedding_model: str = "all-MiniLM-L6-v2"
    db_path: str = "./data/chroma_db"


class GraphStoreConfig(BaseModel):
    provider: str = "neo4j"
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "password"


class RAGConfig(BaseModel):
    chunk_size: int = 500
    chunk_overlap: int = 50
    min_chunk_size: int = 50
    top_k: int = 5


class VisualizerConfig(BaseModel):
    port: int = 8000
    theme: str = "nebula"
    point_size: float = 3.0
    max_points: int = 50000


class WorkspaceConfig(BaseModel):
    path: str = "."
    watch: bool = True
    extensions: List[str] = [".md", ".txt", ".pdf", ".csv", ".json", ".yaml"]
    ignore: List[str] = ["node_modules", ".git", "__pycache__", ".env"]


class LangentSettings(BaseSettings):
    """Langent settings from environment variables."""
    langent_workspace: str = "."
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    chroma_db_path: str = "./data/chroma_db"
    embedding_model: str = "all-MiniLM-L6-v2"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = ""
    llm_mode: str = "fake"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


class LangentConfig:
    """Unified config: .env vars + YAML file merged."""

    def __init__(self, config_path: Optional[str] = None):
        self.env = LangentSettings()
        self._yaml: dict = {}
        if config_path:
            self._load_yaml(config_path)
        else:
            default_path = Path(__file__).parent.parent / "config" / "default.yaml"
            if default_path.exists():
                self._load_yaml(str(default_path))

        self.workspace = WorkspaceConfig(path=self.env.langent_workspace)
        self.vector = VectorStoreConfig(
            db_path=self.env.chroma_db_path,
            embedding_model=self.env.embedding_model,
        )
        self.graph = GraphStoreConfig(
            uri=self.env.neo4j_uri,
            user=self.env.neo4j_user,
            password=self.env.neo4j_password,
        )
        self.rag = RAGConfig(**self._yaml.get("rag", {}))
        self.visualizer = VisualizerConfig(**self._yaml.get("visualizer", {}))

    def _load_yaml(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._yaml = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning("Failed to load config YAML %s: %s", path, e)
