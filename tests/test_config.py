"""Tests for langent.config"""
from langent.config import (
    LangentConfig,
    LangentSettings,
    VectorStoreConfig,
    GraphStoreConfig,
    RAGConfig,
    WorkspaceConfig,
)


class TestLangentConfig:
    def test_default_config_loads(self, config):
        assert config.workspace is not None
        assert config.vector is not None
        assert config.graph is not None
        assert config.rag is not None
        assert config.visualizer is not None

    def test_vector_config_defaults(self):
        vc = VectorStoreConfig()
        assert vc.provider == "chromadb"
        assert vc.embedding_model == "all-MiniLM-L6-v2"
        assert vc.collection == "langent_knowledge"

    def test_graph_config_no_hardcoded_password(self):
        gc = GraphStoreConfig()
        assert gc.password == "password"
        assert "yw" not in gc.password

    def test_rag_config_defaults(self):
        rc = RAGConfig()
        assert rc.chunk_size == 500
        assert rc.chunk_overlap == 50
        assert rc.min_chunk_size == 50

    def test_workspace_config_defaults(self):
        wc = WorkspaceConfig()
        assert ".md" in wc.extensions
        assert ".git" in wc.ignore

    def test_settings_has_api_key_field(self):
        settings = LangentSettings()
        assert hasattr(settings, "api_key")
        assert settings.api_key == ""

    def test_config_with_nonexistent_yaml(self):
        config = LangentConfig(config_path="/nonexistent/config.yaml")
        assert config.rag.chunk_size == 500  # Falls back to defaults
