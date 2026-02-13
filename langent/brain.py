"""
Langent Brain v2 — Main Orchestrator
======================================
Workspace → ChromaDB → 3D Nebula → MCP/API

The central hub connecting all subsystems:
- Workspace file watching & ingestion
- VectorStore (ChromaDB) for semantic search
- GraphStore (Neo4j) for knowledge graph
- RAG pipeline for intelligent retrieval
- MCP/API for Antigravity/Claude Code integration
"""
from typing import Optional, List, Dict, Any
from pathlib import Path

from langent.config import LangentConfig
from langent.store.vector import VectorStore
from langent.store.graph import GraphStore
from langent.rag.ingest import DocumentIngestor
from langent.rag.chunker import SmartChunker
from langent.rag.retriever import HybridRetriever


from langent.llm_proxy import get_llm
from langent.agents.workflows import LangentWorkflows
from langent.agents.delegation import SubAgentManager
from langent.skills.loader import SkillLoader


class Langent:
    """
    Langent v2 — 워크스페이스 기반 RAG Agentic Framework

    1. 워크스페이스 파일들을 스캔·수집
    2. ChromaDB에 벡터화하여 저장
    3. 시맨틱 검색 + 그래프 검색 하이브리드 RAG
    4. 3D 성운 시각화 데이터 제공
    5. MCP/API로 Antigravity LLM과 연동
    6. LangGraph 기반 에이전트 워크플로우 실행
    7. 서브에이전트 위임 및 스킬 시스템
    """

    def __init__(
        self,
        workspace: str = None,
        config_path: str = None,
        neo4j: bool = True,
        llm_mode: str = "fake",
        verbose: bool = True,
    ):
        self.config = LangentConfig(config_path)
        self.verbose = verbose

        # Workspace
        ws = workspace or self.config.workspace.path
        self.workspace = Path(ws)

        # 1. LLM Proxy
        self.llm = get_llm(mode=llm_mode or self.config.env.llm_mode)

        # 2. Vector Store
        self.vector = VectorStore(
            db_path=self.config.vector.db_path,
            collection_name=self.config.vector.collection,
            embedding_model=self.config.vector.embedding_model,
        )

        # 3. Graph Store (optional)
        self.graph = None
        if neo4j:
            try:
                self.graph = GraphStore(
                    uri=self.config.graph.uri,
                    user=self.config.graph.user,
                    password=self.config.graph.password,
                )
                if not self.graph.test_connection():
                    self._log("⚠ Neo4j unavailable, graph features disabled")
                    self.graph = None
            except Exception:
                self.graph = None

        # 4. RAG Pipeline
        self.ingestor = DocumentIngestor(
            workspace_path=str(self.workspace),
            extensions=self.config.workspace.extensions,
            ignore=self.config.workspace.ignore,
        )
        self.chunker = SmartChunker(
            chunk_size=self.config.rag.chunk_size,
            chunk_overlap=self.config.rag.chunk_overlap,
            min_chunk_size=self.config.rag.min_chunk_size,
        )
        self.retriever = HybridRetriever(
            vector_store=self.vector,
            graph_store=self.graph,
        )

        # 5. Agent Workflows
        self.workflows = LangentWorkflows(
            llm=self.llm,
            retriever=self.retriever,
            graph_store=self.graph
        )
        self._rag_graph = self.workflows.build_rag_graph()

        # 6. Sub-Agents & Skills
        self.sub_agents = SubAgentManager()
        self.skills = SkillLoader(
            skills_dir=str(self.workspace / "skills")
        )
        self.skills.load_all()

        self._log(f"[Brain] Langent v2.0 initialized")
        self._log(f"   Workspace: {self.workspace}")
        self._log(f"   LLM Mode: {self.llm.mode}")
        self._log(f"   Skills loaded: {len(self.skills.skills)}")

    # ─── Agent Chat ───────────────────────────────────

    def chat(self, question: str) -> Dict[str, Any]:
        """LangGraph RAG 워크플로우를 실행합니다."""
        self._log(f"[Chat] Chat request: {question}")
        initial_state = {
            "query": question,
            "steps": ["Initialized chat"],
            "metadata": {}
        }
        result = self._rag_graph.invoke(initial_state)
        return result

    # ─── Ingest ───────────────────────────────────────

    def ingest(self, path: str = None) -> Dict[str, int]:
        """
        워크스페이스 파일들을 수집 → 청킹 → 벡터 DB 저장

        Returns:
            {"files_scanned", "chunks_created", "vectors_added"}
        """
        ingestor = self.ingestor
        if path:
            ingestor = DocumentIngestor(
                workspace_path=path,
                extensions=self.config.workspace.extensions,
                ignore=self.config.workspace.ignore,
            )

        self._log("📥 Ingesting workspace files...")

        # 1. Scan & extract
        documents = ingestor.ingest_all()
        self._log(f"   Found {len(documents)} files")

        if not documents:
            return {"files_scanned": 0, "chunks_created": 0, "vectors_added": 0}

        # 2. Chunk
        chunks = self.chunker.chunk_documents(documents)
        self._log(f"   Created {len(chunks)} chunks")

        # 3. Store in vector DB
        texts = [c["text"] for c in chunks]
        metas = [c["metadata"] for c in chunks]
        added = self.vector.add_documents(texts, metas)
        self._log(f"   Added {added} new vectors (total: {self.vector.count()})")

        return {
            "files_scanned": len(documents),
            "chunks_created": len(chunks),
            "vectors_added": added,
        }

    def ingest_text(self, text: str, source: str = "manual") -> int:
        """단일 텍스트를 수집합니다."""
        chunks = self.chunker.chunk_document(
            text, {"source": source, "filename": source}
        )
        texts = [c["text"] for c in chunks]
        metas = [c["metadata"] for c in chunks]
        return self.vector.add_documents(texts, metas)

    # ─── Query ────────────────────────────────────────

    def query(self, question: str, top_k: int = 5) -> List[Dict]:
        """하이브리드 RAG 검색"""
        return self.retriever.search(question, top_k=top_k)

    def get_context(self, question: str, top_k: int = 5) -> str:
        """LLM 프롬프트용 컨텍스트 문자열 반환"""
        return self.retriever.get_context(question, top_k=top_k)

    # ─── 3D Nebula Visualization ──────────────────────

    def get_nebula_data(self, limit: int = 50000) -> Dict[str, Any]:
        """
        3D 성운 시각화용 데이터를 반환합니다.
        Returns: {points: [...], graph: {nodes, edges}, cross_links, stats}
        """
        points = self.vector.get_3d_positions(limit=limit)

        graph_data = {"nodes": [], "edges": []}
        cross_links = []
        
        if self.graph:
            try:
                graph_data = self.graph.export_for_viz(limit=1000)
                # Fetch cross-links (Chunk to Entity)
                links_raw = self.graph.run_cypher(
                    "MATCH (c:Chunk)-[:MENTIONS]->(e) "
                    "RETURN c.id AS chunk_id, id(e) AS node_id LIMIT 2000"
                )
                cross_links = [
                    {"source": str(l["chunk_id"]), "target": str(l["node_id"])}
                    for l in links_raw
                ]
            except Exception:
                pass

        return {
            "points": points,
            "graph": graph_data,
            "cross_links": cross_links,
            "stats": {
                "total_vectors": self.vector.count(),
                "total_graph_nodes": len(graph_data["nodes"]),
                "total_graph_edges": len(graph_data["edges"]),
                "total_cross_links": len(cross_links),
            },
        }

    def search_nebula(self, query: str, top_k: int = 10) -> Dict:
        """검색 결과와 3D 시각화 데이터를 함께 반환합니다."""
        return self.vector.search_with_positions(query, top_k=top_k)

    # ─── Graph Operations ─────────────────────────────

    def graph_query(self, cypher: str, params: Dict = None) -> List[Dict]:
        """Neo4j Cypher 쿼리 실행"""
        if not self.graph:
            return [{"error": "Neo4j not connected"}]
        return self.graph.run_cypher(cypher, params)

    def graph_schema(self) -> Dict:
        """그래프 스키마 반환"""
        if not self.graph:
            return {"error": "Neo4j not connected"}
        return self.graph.get_schema()

    def auto_link(self) -> Dict[str, int]:
        """
        벡터 청크와 그래프 노드를 자동으로 연결합니다.
        1. 그래프에서 이름(name) 속성이 있는 모든 노드 추출
        2. 벡터 청크 텍스트에서 해당 이름이 포함되어 있는지 검색
        3. 일치할 경우 Neo4j에 (:Chunk)-[:MENTIONS]->(Node) 관계 생성
        """
        if not self.graph:
            return {"error": "Neo4j not connected"}

        self._log("🔗 Auto-linking vector chunks to graph entities...")
        
        # 1. Get entities from graph
        entities = self.graph.run_cypher(
            "MATCH (n) WHERE n.name IS NOT NULL RETURN id(n) AS id, n.name AS name, labels(n)[0] AS label"
        )
        entity_map = {e["name"].lower(): e for e in entities if e["name"]}
        self._log(f"   Found {len(entity_map)} unique entities in graph")

        # 2. Get chunks from vector store
        data = self.vector.get_all_embeddings(limit=10000)
        chunks = []
        for i in range(len(data["ids"])):
            chunks.append({
                "id": data["ids"][i],
                "text": data["documents"][i].lower()
            })

        # 3. Match and link
        linked_count = 0
        for chunk in chunks:
            mentions = []
            for name, entity in entity_map.items():
                if len(name) < 2: continue
                if name in chunk["text"]:
                    mentions.append(entity["id"])
            
            if mentions:
                # Create Chunk node and relationships
                self.graph.run_cypher(
                    "MERGE (c:Chunk {id: $cid})", {"cid": chunk["id"]}
                )
                for eid in mentions:
                    self.graph.run_cypher(
                        "MATCH (c:Chunk {id: $cid}), (e) WHERE id(e) = $eid "
                        "MERGE (c)-[:MENTIONS]->(e)",
                        {"cid": chunk["id"], "eid": eid}
                    )
                linked_count += 1
                if linked_count % 100 == 0:
                    self._log(f"   Linked {linked_count} chunks...")

        self._log(f"✅ Linking complete: {linked_count} chunks linked")
        return {"chunks_linked": linked_count}

    # ─── Status ───────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        """시스템 상태를 반환합니다."""
        return {
            "workspace": str(self.workspace),
            "vector_count": self.vector.count(),
            "graph_connected": self.graph is not None,
            "graph_schema": self.graph.get_schema() if self.graph else None,
            "collections": self.vector.list_collections(),
        }

    def _log(self, msg: str):
        if self.verbose:
            print(msg)

    def close(self):
        if self.graph:
            self.graph.close()

    def __repr__(self):
        return (
            f"<Langent(workspace='{self.workspace}', "
            f"vectors={self.vector.count()}, "
            f"graph={'✓' if self.graph else '✗'})>"
        )
