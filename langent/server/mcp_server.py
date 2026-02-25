"""
Langent MCP Server v3 — Tool Provider for Antigravity/Claude Code
===================================================================
Exposes Langent as MCP tools. No API key needed —
Antigravity's built-in LLM handles reasoning.

Register in mcp_config.json:
{
  "langent": {
    "command": "python",
    "args": ["-m", "langent.server.mcp_server"],
    "env": {
      "LANGENT_WORKSPACE": "/path/to/your/workspace"
    }
  }
}
"""
import json
import os
import asyncio
import logging

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server

logger = logging.getLogger(__name__)

server = Server("langent")

_langent = None


def get_langent():
    global _langent
    if _langent is None:
        from langent.brain import Langent
        workspace = os.environ.get("LANGENT_WORKSPACE", ".")
        _langent = Langent(workspace=workspace, verbose=False)
    return _langent


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """도구 목록을 반환합니다."""
    return [
        types.Tool(
            name="langent_ingest",
            description="워크스페이스 문서를 스캔하고 벡터 DB에 저장합니다. Call this to index new documents.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "수집할 경로 (선택)"}
                },
            },
        ),
        types.Tool(
            name="langent_query",
            description="벡터 DB와 지식 그래프에서 하이브리드 RAG 검색을 수행합니다 (시맨틱 + 그래프).",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색 쿼리"},
                    "top_k": {"type": "number", "default": 5},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="langent_chat",
            description="LangGraph 에이전트와 대화합니다 (RAG + Graph 추론).",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "사용자 메시지"}
                },
                "required": ["message"],
            },
        ),
        types.Tool(
            name="langent_graph",
            description="Neo4j 지식 그래프에서 Cypher 쿼리를 실행합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "cypher": {"type": "string", "description": "Cypher 쿼리"}
                },
                "required": ["cypher"],
            },
        ),
        types.Tool(
            name="langent_status",
            description="Langent 프레임워크의 현재 상태(벡터 수, 그래프 연결 등)를 확인합니다.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="langent_nebula",
            description="3D 성운 시각화용 데이터를 반환하거나 시각화 서버 경로를 안내합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "하이라이트할 검색어 (선택)"}
                },
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """도구 호출을 처리합니다."""
    agent = get_langent()
    arguments = arguments or {}

    if name == "langent_ingest":
        path = arguments.get("path")
        result = agent.ingest(path=path)
        return [types.TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

    elif name == "langent_query":
        query = arguments.get("query", "")
        top_k = int(arguments.get("top_k", 5))
        result = agent.query(query, top_k=top_k)
        return [types.TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

    elif name == "langent_chat":
        message = arguments.get("message", "")
        result = agent.chat(message)
        return [types.TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

    elif name == "langent_graph":
        cypher = arguments.get("cypher", "")
        result = agent.graph_query(cypher)
        return [types.TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

    elif name == "langent_status":
        result = agent.status()
        return [types.TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

    elif name == "langent_nebula":
        query = arguments.get("query")
        if query:
            result = agent.search_nebula(query)
        else:
            result = agent.get_nebula_data()
            result["url"] = "http://localhost:8000"
        return [types.TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    async with stdio_server() as (read, write):
        await server.run(
            read,
            write,
            InitializationOptions(
                server_name="langent",
                server_version="3.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
