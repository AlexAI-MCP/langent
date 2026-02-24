# Langent v3 — Personal Ontology & 3D Knowledge Nebula

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/AlexAI-MCP/langent/actions/workflows/ci.yml/badge.svg)](https://github.com/AlexAI-MCP/langent/actions)

**Langent** is a RAG (Retrieval-Augmented Generation) framework that transforms your local workspace into a 3D cosmic nebula of knowledge. It combines vector embeddings (ChromaDB) with knowledge graphs (Neo4j) to provide a deeply connected AI experience.

![Langent Nebula Showcase](docs/IMG_6158.jpeg)

### Watch the Demo
[![Watch the video](https://img.youtube.com/vi/8HLQO52VO5g/0.jpg)](https://youtu.be/8HLQO52VO5g)

![Langent Nebula Showcase](docs/nebula_full.png)

---

## What's New in v3

- **Security**: Removed all hardcoded credentials, added Cypher injection prevention, optional API key auth
- **Logging**: Replaced all `print()` with structured `logging` module
- **Testing**: Comprehensive pytest suite with 40+ test cases
- **CI/CD**: GitHub Actions for lint + test across Python 3.10/3.11/3.12
- **Tooling**: ruff (lint), mypy (type check), Dockerfile for containerized deployment
- **API**: Pydantic request models, FastAPI dependency injection, health check endpoint
- **Bug fixes**: Fixed `${}` interpolation bug in workflows, fixed MCP server method call error

---

## Key Features

- **Auto-Ingestion**: Automatically scans and indexes MD, PDF, TXT, CSV, JSON, and YAML files.
- **Hybrid RAG**: Merges semantic vector search with graph-based relationship traversal for superior context.
- **3D Nebula Visualizer**: Explore your knowledge base in an interactive Three.js 3D environment.
- **Knowledge Linking**: Automatically discovers and creates relationships between your documents and entities.
- **MCP Integration**: Built-in support for Model Context Protocol (MCP) to plug into Claude Desktop, Antigravity, and more.
- **LangGraph Workflows**: Agent state machines with RAG + Graph reasoning pipeline.

---

## Installation & Quick Start

### 1. Install via Pip

```bash
git clone https://github.com/AlexAI-MCP/langent.git
cd langent
pip install -e .
```

### 2. Configure Environment

```bash
cp .env.example .env
```
Edit `.env` to set your `LANGENT_WORKSPACE` (the folder containing your documents).

### 3. Ingest & Serve

```bash
langent ingest --workspace ./samples  # Start with sample data
langent serve                         # Open http://localhost:8000
```

### 4. Docker (Alternative)

```bash
docker build -t langent .
docker run -p 8000:8000 -v ./workspace:/app/workspace langent
```

---

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check langent/ tests/

# Type check
mypy langent/
```

---

## Data Workflow: From Workspace to 3D Nebula

Langent automates the journey from raw files to an interactive 3D knowledge universe.

1.  **Gather Data (Workspace)**: Drop your PDFs, Markdown notes, CSV spreadsheets, and research papers into your `LANGENT_WORKSPACE` folder.
2.  **Chunking**: Langent automatically breaks these large files into smaller, semantically meaningful chunks (300-500 tokens).
3.  **Vectorization (ChromaDB)**:
    - Using local embedding models (e.g., `all-MiniLM-L6-v2`), each chunk is transformed into a high-dimensional vector.
    - These vectors are stored in **ChromaDB** for lightning-fast semantic retrieval.
4.  **3D Projection**:
    - Langent uses UMAP to project high-dimensional vectors into a **3D Point Cloud**.
    - Semantically similar points cluster together, forming knowledge constellations.

> **Result**: Your messy folder becomes a beautiful, searchable, and navigable 3D cosmic map.

---

## Advanced Setup

### 1. Connecting to Neo4j (Graph Store)
To enable **Knowledge Graph** features, you need a Neo4j instance.

- **Option A: Docker (Recommended)**
  ```bash
  docker run \
      --name langent-neo4j \
      -p 7474:7474 -p 7687:7687 \
      -e NEO4J_AUTH=neo4j/your_password \
      neo4j:latest
  ```
- **Option B: Neo4j Desktop**
  Install [Neo4j Desktop](https://neo4j.com/download/), create a local project, and update your `.env`:
  ```env
  NEO4J_URI="bolt://localhost:7687"
  NEO4J_USER="neo4j"
  NEO4J_PASSWORD="your_password"
  ```

### 2. API Authentication

Set an API key in your `.env` to protect write endpoints:
```env
API_KEY="your-secret-api-key"
```
Then pass it via the `X-API-Key` header for protected endpoints (`/api/ingest`, `/api/link`, `/api/graph`).

### 3. MCP Integration (Claude & Antigravity)
Langent acts as an **MCP server**, allowing AI agents like Claude to use your workspace as long-term memory.

Add the following to your `mcp_config.json`:
```json
"langent": {
  "command": "python",
  "args": ["-m", "langent.server.mcp_server"],
  "env": {
    "LANGENT_WORKSPACE": "/path/to/your/workspace"
  }
}
```

### Using Langent with AI Agents (Antigravity, Claude Code)
Once connected via MCP, you can talk to your workspace as if it's an intelligent entity.

- **Data Ingestion**:
  > "Langent의 mcp 도구를 사용해서 내 워크스페이스에 있는 새로운 문서들을 인덱싱해줘."
- **Semantic Search**:
  > "내 워크스페이스에서 'AI 미래 전략'과 관련된 내용을 네뷸라에서 검색해서 요약해줘."
- **Graph Insight**:
  > "내 연구 주제인 'AI 에이전트'와 가장 많이 연결된 핵심 키워드들을 그래프로 분석해서 보고서로 만들어줘."

---

## Nebula 3D Visualizer

Once you run `langent serve`, navigate to `http://localhost:8000`.

- **Points (Star Dust)**: Each point represents a chunk of your documents.
- **Nodes (Planets)**: Entities extracted into the Neo4j Graph.
- **Lines (Cosmic Strings)**: Relationships between graph entities and semantic links.
- **Controls**:
  - **Left Click**: Select a point to see its original content.
  - **Right Click / Drag**: Rotate the universe.
  - **Scroll**: Zoom in/out of the knowledge cluster.
  - **Search Bar**: Type a keyword to highlight matching stars.

---

## License

This project is licensed under the Apache License 2.0.

---
*Created by Alex AI*
