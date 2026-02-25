"""
Langent API Server v3 — FastAPI + WebSocket for 3D Nebula
==========================================================
Serves REST API + 3D visualizer + real-time WebSocket updates.
Features: Dependency injection, optional API key auth, Pydantic models.
"""
import json
import logging
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Header, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(title="Langent Nebula", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Dependency injection ────────────────────────────

_langent = None


def get_langent():
    """FastAPI dependency that provides the Langent instance."""
    global _langent
    if _langent is None:
        from langent.brain import Langent
        _langent = Langent(verbose=True)
    return _langent


def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Optional API key verification. Skips if API_KEY is not configured."""
    from langent.config import LangentSettings
    settings = LangentSettings()
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ─── Request/Response Models ─────────────────────────

class IngestRequest(BaseModel):
    path: Optional[str] = None


class GraphQueryRequest(BaseModel):
    cypher: str


class QueryResult(BaseModel):
    score: float
    source: str
    preview: str
    id: str


# ─── Static files (visualizer) ───────────────────────

VIZ_DIR = Path(__file__).parent.parent / "visualizer"


@app.get("/")
async def index():
    return FileResponse(str(VIZ_DIR / "index.html"))


@app.get("/app.js")
async def app_js():
    return FileResponse(str(VIZ_DIR / "app.js"), media_type="application/javascript")


@app.get("/style.css")
async def style_css():
    return FileResponse(str(VIZ_DIR / "style.css"), media_type="text/css")


# ─── REST API ─────────────────────────────────────────

@app.get("/api/status")
async def status(langent=Depends(get_langent)):
    return langent.status()


@app.post("/api/ingest")
async def ingest(
    request: IngestRequest,
    langent=Depends(get_langent),
    _auth=Depends(verify_api_key),
):
    return langent.ingest(path=request.path)


@app.get("/api/query")
async def query(
    q: str,
    top_k: int = Query(default=5, ge=1, le=100),
    langent=Depends(get_langent),
):
    results = langent.query(q, top_k=top_k)
    output = []
    for r in results:
        output.append({
            "score": round(r.get("score", r.get("rrf_score", 0)), 4),
            "source": r.get("metadata", {}).get("source", "unknown"),
            "preview": r.get("document", "")[:300],
            "id": r.get("id", ""),
        })
    return output


@app.get("/api/context")
async def context(
    q: str,
    top_k: int = Query(default=5, ge=1, le=100),
    langent=Depends(get_langent),
):
    return {"context": langent.get_context(q, top_k=top_k)}


@app.post("/api/link")
async def link_knowledge(
    langent=Depends(get_langent),
    _auth=Depends(verify_api_key),
):
    return langent.auto_link()


@app.get("/api/shops/suseo")
async def get_suseo_shops():
    """수서동 상가 지리 정보 반환"""
    shops_path = Path(__file__).parent.parent / "visualizer" / "suseo_shops.json"
    if shops_path.exists():
        with open(shops_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


@app.post("/api/graph")
async def graph_query(
    request: GraphQueryRequest,
    langent=Depends(get_langent),
    _auth=Depends(verify_api_key),
):
    return langent.graph_query(request.cypher)


# ─── 3D Nebula Data ──────────────────────────────────

@app.get("/api/nebula")
async def nebula_data(
    limit: int = Query(default=50000, ge=1, le=100000),
    langent=Depends(get_langent),
):
    return langent.get_nebula_data(limit=limit)


@app.get("/api/nebula/search")
async def nebula_search(
    q: str,
    top_k: int = Query(default=10, ge=1, le=100),
    langent=Depends(get_langent),
):
    return langent.search_nebula(q, top_k=top_k)


# ─── WebSocket (real-time updates) ────────────────────

clients: set = set()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    langent = get_langent()
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "search":
                result = langent.search_nebula(msg["query"], top_k=10)
                await websocket.send_json({"type": "search_result", "data": result})
            elif msg.get("type") == "ingest":
                result = langent.ingest(path=msg.get("path"))
                nebula = langent.get_nebula_data()
                for client in clients:
                    try:
                        await client.send_json({"type": "nebula_update", "data": nebula})
                    except Exception:
                        clients.discard(client)
                await websocket.send_json({"type": "ingest_result", "data": result})
    except WebSocketDisconnect:
        clients.discard(websocket)


# ─── Health check ─────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.0.0"}
