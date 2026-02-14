"""
VectorStore — ChromaDB Adapter for Langent
============================================
Workspace files → embeddings → ChromaDB → 3D visualization data
"""
import os
import hashlib
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings


class VectorStore:
    """
    ChromaDB 기반 벡터 저장소.

    워크스페이스 파일들을 벡터화하고, 시맨틱 검색 및
    3D 시각화용 임베딩 데이터를 제공합니다.
    """

    def __init__(
        self,
        db_path: str = "./data/chroma_db",
        collection_name: str = "langent_knowledge",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=str(self.db_path))
        self.collection_name = collection_name
        self._embedding_model_name = embedding_model
        self._ef = None
        self._cache_count = -1
        self._coords_cache = []
        self._cache_file = self.db_path.parent / "nebula_cache.json"

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def _embedding_function(self):
        if self._ef is None:
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
            self._ef = SentenceTransformerEmbeddingFunction(
                model_name=self._embedding_model_name
            )
        return self._ef

    # ─── CRUD ──────────────────────────────────────────

    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]] = None,
        ids: List[str] = None,
    ) -> int:
        """문서 청크들을 벡터화하여 저장합니다."""
        if not documents:
            return 0

        if ids is None:
            ids = []
            for i, (doc, meta) in enumerate(zip(documents, metadatas or [{}] * len(documents))):
                source = meta.get("source", "") if meta else ""
                chunk_idx = meta.get("chunk_index", i) if meta else i
                unique_str = f"{source}::{chunk_idx}::{doc[:100]}"
                ids.append(self._make_id(unique_str))

        if metadatas is None:
            metadatas = [{}] * len(documents)

        # Remove duplicates
        existing = set()
        try:
            result = self.collection.get(ids=ids)
            existing = set(result["ids"]) if result["ids"] else set()
        except Exception:
            pass

        new_docs, new_metas, new_ids = [], [], []
        for doc, meta, doc_id in zip(documents, metadatas, ids):
            if doc_id not in existing:
                new_docs.append(doc)
                new_metas.append(meta)
                new_ids.append(doc_id)

        if not new_docs:
            return 0

        batch_size = 100
        added = 0
        for i in range(0, len(new_docs), batch_size):
            b_docs = new_docs[i: i + batch_size]
            b_metas = new_metas[i: i + batch_size]
            b_ids = new_ids[i: i + batch_size]
            self.collection.add(documents=b_docs, metadatas=b_metas, ids=b_ids)
            added += len(b_docs)

        # Clear cache on new data
        self._cache_count = -1
        return added

    def search(
        self,
        query: str,
        top_k: int = 5,
        where: Dict = None,
    ) -> List[Dict[str, Any]]:
        """시맨틱 유사도 검색을 수행합니다."""
        kwargs = {
            "query_texts": [query],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = self.collection.query(**kwargs)

        output = []
        for i in range(len(results["ids"][0])):
            output.append({
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
                "score": 1.0 - results["distances"][0][i],
            })
        return output

    def delete(self, ids: List[str] = None, where: Dict = None):
        """문서를 삭제합니다."""
        if ids:
            self.collection.delete(ids=ids)
        elif where:
            self.collection.delete(where=where)
        self._cache_count = -1

    def count(self) -> int:
        return self.collection.count()

    # ─── 3D Visualization Export ──────────────────────

    def get_all_embeddings(self, limit: int = 50000) -> Dict[str, Any]:
        """
        3D 시각화용 임베딩 데이터를 내보냅니다.
        Returns: {ids, embeddings, metadatas, documents}
        """
        result = self.collection.get(
            include=["embeddings", "metadatas", "documents"],
            limit=limit,
        )
        return {
            "ids": result["ids"],
            "embeddings": result["embeddings"],
            "metadatas": result["metadatas"],
            "documents": result["documents"],
        }

    def get_3d_positions(self, limit: int = 50000) -> List[Dict]:
        """
        UMAP으로 고차원 임베딩을 3D 좌표로 변환합니다. (캐싱 지원)
        Each point: {id, x, y, z, metadata, document_preview}
        """
        current_count = self.count()
        
        # 1. Try In-memory cache
        if self._cache_count == current_count and self._coords_cache:
            return self._coords_cache

        # 2. Try Disk cache
        if self._cache_file.exists():
            try:
                with open(self._cache_file, "r") as f:
                    cached = json.load(f)
                    if cached.get("count") == current_count:
                        self._coords_cache = cached.get("points", [])
                        self._cache_count = current_count
                        return self._coords_cache
            except Exception:
                pass

        # 3. Recalculate
        data = self.get_all_embeddings(limit=limit)
        if data["embeddings"] is None or len(data["embeddings"]) < 2:
            return []

        import numpy as np
        try:
            import umap
        except ImportError:
            # Fallback: random projection
            embeddings = np.array(data["embeddings"])
            rng = np.random.RandomState(42)
            proj = rng.randn(embeddings.shape[1], 3)
            coords = embeddings @ proj
            coords = (coords - coords.mean(axis=0)) / (coords.std(axis=0) + 1e-8)
            return self._build_points(coords, data)

        embeddings = np.array(data["embeddings"])
        n_neighbors = min(15, len(embeddings) - 1)
        reducer = umap.UMAP(
            n_components=3,
            n_neighbors=max(2, n_neighbors),
            min_dist=0.1,
            metric="cosine",
            random_state=42,
        )
        coords_3d = reducer.fit_transform(embeddings)
        # Normalize to [-50, 50] range for Three.js scene
        coords_3d = (coords_3d - coords_3d.mean(axis=0)) / (coords_3d.std(axis=0) + 1e-8) * 30

        self._coords_cache = self._build_points(coords_3d, data)
        self._cache_count = current_count
        
        # 4. Save to Disk
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._cache_file, "w") as f:
                json.dump({"count": current_count, "points": self._coords_cache}, f)
        except Exception:
            pass
            
        return self._coords_cache

    def _build_points(self, coords, data) -> List[Dict]:
        points = []
        for i, (x, y, z) in enumerate(coords):
            meta = data["metadatas"][i] if data["metadatas"] else {}
            doc = data["documents"][i] if data["documents"] else ""
            points.append({
                "id": data["ids"][i],
                "x": float(x),
                "y": float(y),
                "z": float(z),
                "metadata": meta,
                "preview": doc[:120] if doc else "",
                "source": meta.get("source", "unknown"),
            })
        return points

    # ─── Search + Highlight for Viz ───────────────────

    def search_with_positions(self, query: str, top_k: int = 10) -> Dict:
        """검색 결과 + 3D 좌표 (시각화 하이라이트용)"""
        results = self.search(query, top_k=top_k)
        hit_ids = {r["id"] for r in results}
        all_points = self.get_3d_positions()
        for pt in all_points:
            pt["highlighted"] = pt["id"] in hit_ids
        return {
            "query": query,
            "results": results,
            "points": all_points,
        }

    # ─── Helpers ──────────────────────────────────────

    def _make_id(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()[:16]

    def list_collections(self) -> List[str]:
        return [c.name for c in self.client.list_collections()]

    def __repr__(self):
        return f"<VectorStore(collection='{self.collection_name}', count={self.count()})>"
