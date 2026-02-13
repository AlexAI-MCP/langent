"""
HybridRetriever — Vector + Graph combined search
===================================================
Merges ChromaDB semantic search with Neo4j graph traversal.
"""
from typing import List, Dict, Any, Optional
from langent.store.vector import VectorStore
from langent.store.graph import GraphStore


class HybridRetriever:
    """
    하이브리드 리트리버: Vector 검색 + Graph 검색을 결합합니다.
    Reciprocal Rank Fusion (RRF) 방식으로 결과를 병합합니다.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        graph_store: Optional[GraphStore] = None,
        vector_weight: float = 0.6,
        graph_weight: float = 0.4,
    ):
        self.vector = vector_store
        self.graph = graph_store
        self.vector_weight = vector_weight
        self.graph_weight = graph_weight

    def search(
        self, query: str, top_k: int = 5, use_graph: bool = True
    ) -> List[Dict[str, Any]]:
        """
        하이브리드 검색을 수행합니다.

        1. Vector DB에서 시맨틱 유사도 검색
        2. (옵션) Graph DB에서 관련 엔티티 검색
        3. RRF로 결과 병합
        """
        # 1. Vector search
        vector_results = self.vector.search(query, top_k=top_k * 2)

        if not use_graph or not self.graph:
            return vector_results[:top_k]

        # 2. Graph search (keyword extraction → graph lookup)
        graph_context = self._graph_search(query)

        # 3. Merge
        combined = self._rrf_merge(vector_results, graph_context, top_k)
        return combined

    def _graph_search(self, query: str) -> List[Dict[str, str]]:
        """쿼리에서 키워드를 추출해 그래프 검색"""
        if not self.graph:
            return []

        # Simple keyword extraction (split by space, filter short words)
        keywords = [w for w in query.split() if len(w) >= 2]

        results = []
        for kw in keywords[:5]:
            try:
                nodes = self.graph.run_cypher(
                    "MATCH (n) WHERE toLower(n.name) CONTAINS toLower($kw) "
                    "OPTIONAL MATCH (n)-[r]->(m) "
                    "RETURN n.name AS entity, type(r) AS relation, "
                    "m.name AS related LIMIT 5",
                    {"kw": kw},
                )
                for n in nodes:
                    results.append({
                        "entity": str(n.get("entity", "")),
                        "relation": str(n.get("relation", "")),
                        "related": str(n.get("related", "")),
                    })
            except Exception:
                continue
        return results

    def _rrf_merge(
        self,
        vector_results: List[Dict],
        graph_context: List[Dict],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Reciprocal Rank Fusion으로 결과 병합"""
        k = 60  # RRF constant

        scored = {}
        # Vector results
        for rank, vr in enumerate(vector_results):
            doc_id = vr["id"]
            rrf_score = self.vector_weight / (k + rank + 1)
            scored[doc_id] = {
                **vr,
                "rrf_score": rrf_score,
                "graph_context": [],
            }

        # Graph context boost: if a vector result mentions a graph entity, boost it
        if graph_context:
            context_str = " ".join(
                f"{g['entity']} {g['relation']} {g['related']}"
                for g in graph_context
            )
            for doc_id, entry in scored.items():
                doc_text = entry.get("document", "").lower()
                for g in graph_context:
                    entity = g.get("entity", "").lower()
                    if entity and entity in doc_text:
                        entry["rrf_score"] += self.graph_weight / k
                        entry["graph_context"].append(g)

        # Sort by RRF score
        ranked = sorted(scored.values(), key=lambda x: x["rrf_score"], reverse=True)
        return ranked[:top_k]

    def get_context(self, query: str, top_k: int = 5) -> str:
        """RAG 컨텍스트 문자열로 반환 (에이전트 프롬프트용)"""
        results = self.search(query, top_k=top_k)
        context_parts = []
        for i, r in enumerate(results):
            src = r.get("metadata", {}).get("source", "unknown")
            context_parts.append(
                f"[{i+1}] (source: {src})\n{r.get('document', '')}"
            )
        return "\n\n---\n\n".join(context_parts)
