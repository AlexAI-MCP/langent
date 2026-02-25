"""Tests for langent.llm_proxy"""
from langent.llm_proxy import HostLLMProxy, get_llm


class TestHostLLMProxy:
    def test_get_llm_returns_proxy(self):
        llm = get_llm(mode="fake")
        assert isinstance(llm, HostLLMProxy)
        assert llm.mode == "fake"

    def test_fake_mode_responds(self):
        llm = get_llm(mode="fake")
        result = llm.invoke("Hello")
        assert result.content
        assert "Langent" in result.content

    def test_fake_mode_korean(self):
        llm = get_llm(mode="fake")
        result = llm.invoke("안녕하세요")
        assert "Langent" in result.content

    def test_mcp_mode_returns_marker(self):
        llm = get_llm(mode="mcp")
        result = llm.invoke("test question")
        assert "HOST_AI_REQUIRED" in result.content

    def test_unknown_mode_fallback(self):
        llm = get_llm(mode="nonexistent")
        result = llm.invoke("test")
        assert "not yet implemented" in result.content

    def test_llm_type_property(self):
        llm = get_llm()
        assert llm._llm_type == "host-llm-proxy"

    def test_v3_in_fake_response(self):
        llm = get_llm(mode="fake")
        result = llm.invoke("안녕")
        assert "v3" in result.content
