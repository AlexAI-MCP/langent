"""
Langent API Server — FastAPI + WebSocket for 3D Nebula
=======================================================
Serves REST API + 3D visualizer + real-time WebSocket updates.
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Langent Nebula", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy Langent instance
_langent = None

def get_langent():
    global _langent
    if _langent is None:
        from langent.brain import Langent
        # We don't pass workspace here because Langent() will 
        # automatically look at LANGENT_WORKSPACE env var or .env file
        _langent = Langent(verbose=True)
    return _langent

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
async def status():
    return get_langent().status()

@app.post("/api/ingest")
async def ingest(path: Optional[str] = None):
    result = get_langent().ingest(path=path)
    return result

@app.get("/api/query")
async def query(q: str, top_k: int = 5):
    results = get_langent().query(q, top_k=top_k)
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
async def context(q: str, top_k: int = 5):
    return {"context": get_langent().get_context(q, top_k=top_k)}

@app.post("/api/link")
async def link_knowledge():
    """벡터 청크와 그래프 노드 연결 트리거"""
    return get_langent().auto_link()

@app.get("/api/shops/suseo")
async def get_suseo_shops():
    """수서동 상가 지리 정보 반환"""
    import json
    path = os.path.join(os.path.dirname(__file__), "..", "visualizer", "suseo_shops.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@app.post("/api/graph")
async def graph_query(cypher: str):
    return get_langent().graph_query(cypher)

# ─── 3D Nebula Data ──────────────────────────────────

@app.get("/api/nebula")
async def nebula_data(limit: int = 50000):
    """3D 시각화용 전체 데이터"""
    return get_langent().get_nebula_data(limit=limit)

@app.get("/api/nebula/search")
async def nebula_search(q: str, top_k: int = 10):
    """검색 결과 + 3D 좌표"""
    return get_langent().search_nebula(q, top_k=top_k)

# ─── WebSocket (real-time updates) ────────────────────

clients = set()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "search":
                result = get_langent().search_nebula(msg["query"], top_k=10)
                await websocket.send_json({"type": "search_result", "data": result})
            elif msg.get("type") == "ingest":
                result = get_langent().ingest(path=msg.get("path"))
                # Broadcast new data to all clients
                nebula = get_langent().get_nebula_data()
                for client in clients:
                    try:
                        await client.send_json({"type": "nebula_update", "data": nebula})
                    except Exception:
                        pass
                await websocket.send_json({"type": "ingest_result", "data": result})
    except WebSocketDisconnect:
        clients.discard(websocket)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()
    
    print(f"\n[Nebula] Langent Nebula Server starting on http://localhost:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
