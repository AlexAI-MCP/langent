"""
Langent v2 — Quick Smoke Test
================================
Verifies: import → config → ingest → vector search → 3D positions
"""
import sys
sys.path.insert(0, ".")

def test_basic():
    print("=" * 50)
    print("🧪 Langent v2 Smoke Test")
    print("=" * 50)

    # 1. Import test
    print("\n1️⃣  Import test...")
    from langent.config import LangentConfig
    from langent.store.vector import VectorStore
    from langent.rag.ingest import DocumentIngestor
    from langent.rag.chunker import SmartChunker
    from langent.rag.retriever import HybridRetriever
    print("   ✓ All modules imported")

    # 2. Config test
    print("\n2️⃣  Config test...")
    config = LangentConfig()
    print(f"   ✓ Workspace: {config.workspace.path}")
    print(f"   ✓ Embedding: {config.vector.embedding_model}")

    # 3. Vector Store test
    print("\n3️⃣  Vector Store test...")
    vs = VectorStore(db_path="./data/test_chroma", collection_name="test")
    
    # Add sample docs
    docs = [
        "인공지능 기반 조경 설계 시스템을 개발합니다",
        "Neo4j 그래프 데이터베이스로 지식 그래프를 구축합니다",
        "Three.js를 사용하여 3D 시각화를 구현합니다",
        "LangChain과 LangGraph로 에이전트 워크플로우를 만듭니다",
        "ChromaDB 벡터 데이터베이스에 임베딩을 저장합니다",
    ]
    metas = [
        {"source": "design.md", "filename": "design.md", "extension": ".md"},
        {"source": "graph.py", "filename": "graph.py", "extension": ".py"},
        {"source": "viz.js", "filename": "viz.js", "extension": ".js"},
        {"source": "agents.py", "filename": "agents.py", "extension": ".py"},
        {"source": "vector.md", "filename": "vector.md", "extension": ".md"},
    ]
    added = vs.add_documents(docs, metas)
    print(f"   ✓ Added {added} documents (total: {vs.count()})")

    # 4. Search test
    print("\n4️⃣  Search test...")
    results = vs.search("3D 시각화", top_k=3)
    for r in results:
        print(f"   📄 [{r['score']:.3f}] {r['metadata'].get('source', '?')} — {r['document'][:40]}...")

    # 5. 3D Position test
    print("\n5️⃣  3D Position test...")
    points = vs.get_3d_positions()
    print(f"   ✓ Generated {len(points)} 3D points")
    if points:
        p = points[0]
        print(f"   📍 First point: ({p['x']:.2f}, {p['y']:.2f}, {p['z']:.2f}) — {p['source']}")

    # 6. Chunker test
    print("\n6️⃣  Chunker test...")
    chunker = SmartChunker(chunk_size=100, chunk_overlap=20)
    long_text = "\n\n".join(docs * 3)
    chunks = chunker.chunk_document(long_text, {"source": "test"})
    print(f"   ✓ Created {len(chunks)} chunks from {len(long_text)} chars")

    # 7. Brain test (no Neo4j dependency)
    print("\n7️⃣  Brain orchestrator test...")
    from langent.brain import Langent
    agent = Langent(
        workspace=".",
        neo4j=False,  # Skip Neo4j for smoke test
        verbose=False,
    )
    print(f"   ✓ {agent}")
    status = agent.status()
    print(f"   ✓ Vectors: {status['vector_count']}, Graph: {status['graph_connected']}")

    print("\n" + "=" * 50)
    print("✅ ALL TESTS PASSED")
    print("=" * 50)
    print(f"\nTo launch the Nebula visualizer:")
    print(f"  python server/api.py")
    print(f"  → Open http://localhost:8000")

if __name__ == "__main__":
    test_basic()
