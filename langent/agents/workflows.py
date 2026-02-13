"""
Langent Workflows — LangGraph based agentic logic
===================================================
Defines the standard RAG + Graph reasoning state machine.
"""
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END

from langent.llm_proxy import HostLLMProxy
from langent.rag.retriever import HybridRetriever
from langent.store.graph import GraphStore


class AgentState(TypedDict):
    """LangGraph 워크플로우 상태 정의"""
    query: str                       # 사용자 질문
    context: str                     # RAG 검색 결과 텍스트
    graph_results: List[Dict]        # 그래프 검색 결과
    cypher_query: Optional[str]      # 생성된 Cypher 쿼리
    answer: str                      # 최종 답변
    steps: List[str]                 # 실행된 단계 기록
    metadata: Dict[str, Any]         # 추가 메타데이터


class LangentWorkflows:
    """
    Langent의 표준 에이전트 워크플로우 모음.
    RAG, Graph, Skill 실행 등 다양한 그래프 정의.
    """

    def __init__(
        self,
        llm: HostLLMProxy,
        retriever: HybridRetriever,
        graph_store: Optional[GraphStore] = None,
    ):
        self.llm = llm
        self.retriever = retriever
        self.graph = graph_store

    def build_rag_graph(self) -> StateGraph:
        """기본 RAG + Graph 하이브리드 워크플로우 생성"""
        workflow = StateGraph(AgentState)

        # 1. 노드 추가
        workflow.add_node("retrieve", self.node_retrieve)
        workflow.add_node("graph_search", self.node_graph_search)
        workflow.add_node("generate", self.node_generate)

        # 2. 엣지 연결
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "graph_search")
        workflow.add_edge("graph_search", "generate")
        workflow.add_edge("generate", END)

        return workflow.compile()

    # ─── Nodes ───────────────────────────────────────

    def node_retrieve(self, state: AgentState) -> Dict:
        """Vector DB에서 컨텍스트 검색"""
        query = state["query"]
        context = self.retriever.get_context(query, top_k=5)
        return {
            "context": context,
            "steps": state.get("steps", []) + ["Retrieved vector context"]
        }

    def node_graph_search(self, state: AgentState) -> Dict:
        """관련 엔티티 및 관계를 그래프에서 검색 (RAG 결과 보강)"""
        if not self.graph:
            return {"steps": state.get("steps", []) + ["Skipped graph search (not connected)"]}

        query = state["query"]
        # 하이브리드 리트리버의 로직 재사용
        graph_results = self.retriever._graph_search(query)
        
        return {
            "graph_results": graph_results,
            "steps": state.get("steps", []) + [f"Found {len(graph_results)} graph relations"]
        }

    def node_generate(self, state: AgentState) -> Dict:
        """최종 답변 생성"""
        query = state["query"]
        context = state.get("context", "")
        graph = state.get("graph_results", [])
        
        graph_str = "\n".join([f"- {g['entity']} -[{g['relation']}]-> {g['related']}" for g in graph])
        
        prompt = f"""당신은 우수한 AI 비서 Langent입니다. 
제공된 컨텍스트와 지식 그래프 정보를 바탕으로 사용자의 질문에 답변하세요.

[사용자 질문]
${query}

[벡터 컨텍스트]
${context}

[지식 그래프 정보]
${graph_str}

지식에 근거하여 상세하고 친절하게 답변하세요. 만약 모르는 내용이라면 확실하지 않다고 솔직하게 답변하세요.
"""
        response = self.llm.invoke(prompt)
        return {
            "answer": response.content,
            "steps": state.get("steps", []) + ["Generated answer"]
        }
