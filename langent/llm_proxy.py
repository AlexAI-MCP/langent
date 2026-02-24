"""
HostLLMProxy v3 — LLM access without direct API keys
======================================================
Leverages host AI (Antigravity/Claude Code) via MCP or CLI,
or uses local models/proxies.

Supported modes:
- "fake": Simulated responses for testing
- "mcp": Returns instructions for the host AI to process (when used as MCP tool)
- "ollama": Local Ollama API (localhost:11434)
- "proxy": LiteLLM or OpenClaw-style OAuth proxy
"""
import logging
from typing import List, Any, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult, ChatGeneration

logger = logging.getLogger(__name__)


class HostLLMProxy(BaseChatModel):
    """LangChain compatible ChatModel that proxies calls to host AI."""

    mode: str = "fake"
    model_name: str = "host-llm"
    temperature: float = 0.7

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """메시지를 처리하고 응답을 생성합니다."""
        last_msg = messages[-1].content if messages else ""

        if self.mode == "fake":
            response_text = self._fake_response(last_msg)
        elif self.mode == "ollama":
            response_text = self._ollama_response(messages)
        elif self.mode == "mcp":
            response_text = (
                f"[HOST_AI_REQUIRED: Please process this request "
                f"based on the following context: {last_msg}]"
            )
        else:
            response_text = (
                f"Mode '{self.mode}' is not yet implemented. "
                f"Using fake response: Hello! I am Langent v3."
            )

        message = AIMessage(content=response_text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    @property
    def _llm_type(self) -> str:
        return "host-llm-proxy"

    def _fake_response(self, prompt: str) -> str:
        """시뮬레이션 응답 (테스트용)"""
        p_lower = prompt.lower()
        if "안녕" in p_lower or "hello" in p_lower:
            return "안녕하세요! Langent v3 프레임워크의 에이전트입니다. 무엇을 도와드릴까요?"
        if "치킨" in p_lower:
            return (
                "서울에 위치한 60계치킨, 처갓집양념치킨 등 다양한 치킨집 정보가 "
                "벡터 DB에 저장되어 있습니다. 특정 지역을 말씀하시면 상세히 찾아드릴게요."
            )
        if "cypher" in p_lower or "match" in p_lower:
            return "MATCH (n:Person) RETURN n LIMIT 5"

        return (
            f"Langent 프레임워크가 요청을 처리 중입니다. "
            f"현재는 테스트 모드(fake)입니다."
        )

    def _ollama_response(self, messages: List[BaseMessage]) -> str:
        """로컬 Ollama를 통한 응답"""
        import requests

        url = "http://localhost:11434/api/chat"
        payload = {
            "model": "llama3",
            "messages": [
                {
                    "role": (
                        "system" if isinstance(m, SystemMessage)
                        else "user" if isinstance(m, HumanMessage)
                        else "assistant"
                    ),
                    "content": m.content,
                }
                for m in messages
            ],
            "stream": False,
        }
        try:
            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            return resp.json()["message"]["content"]
        except Exception as e:
            logger.error("Ollama connection error: %s", e)
            return f"Ollama connection error: {e}"


def get_llm(mode: str = "fake", **kwargs):
    """설정에 따른 LLM 인스턴스 반환"""
    return HostLLMProxy(mode=mode, **kwargs)
