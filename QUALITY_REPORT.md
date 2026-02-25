# Langent v2.0.0 Repository Quality Analysis

**Date**: 2026-02-24
**Scope**: Full codebase review (~1,900 lines Python + ~560 lines JavaScript)

---

## Executive Summary

| Category | Score | Grade |
|---|---|---|
| **Architecture & Design** | 8.5/10 | A- |
| **Code Quality** | 7.5/10 | B+ |
| **Type Safety** | 7.0/10 | B |
| **Error Handling** | 5.5/10 | C+ |
| **Testing** | 3.0/10 | D |
| **Security** | 4.0/10 | D+ |
| **Documentation** | 7.5/10 | B+ |
| **CI/CD & DevOps** | 1.0/10 | F |
| **Dependency Management** | 7.0/10 | B |
| **Overall** | 5.7/10 | C+ |

---

## 1. Architecture & Design (8.5/10)

### Strengths

- **Clear modular structure**: Well-separated concerns across `brain`, `rag`, `store`, `server`, `agents`, `skills` packages
- **Adapter pattern**: `VectorStore` and `GraphStore` are cleanly abstracted, enabling provider swaps
- **Pipeline pattern**: RAG workflow (ingest -> chunk -> embed -> store -> retrieve) is well-defined
- **LangGraph integration**: State machine-based workflows (`AgentState` TypedDict) in `langent/agents/workflows.py`
- **Lazy initialization**: Heavy objects (embedding models, Neo4j driver, Langent instance) are loaded on demand
- **Dual-layer caching** in `VectorStore.get_3d_positions()`: in-memory + disk cache with cache invalidation

### Issues

- **God Class**: `Langent` class (`brain.py`, 330 lines) acts as the central orchestrator for 7+ subsystems. Should be decomposed:
  - Workspace management
  - Vector/Graph store lifecycle
  - RAG orchestration
  - Agent workflow execution
  - Skill management

- **Global state in servers**: Both `api.py:31` and `mcp_server.py:32` use module-level `_langent = None` with mutable global state. Not safe for concurrent access or testing.

```python
# api.py:31-40 — global singleton pattern
_langent = None
def get_langent():
    global _langent
    if _langent is None:
        _langent = Langent(verbose=True)
    return _langent
```

- **`sys.path` manipulation**: `api.py:13` and `mcp_server.py:22` use `sys.path.insert()` — indicates packaging issues:
```python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

---

## 2. Code Quality (7.5/10)

### Strengths

- Consistent snake_case naming throughout
- Descriptive method names: `get_nebula_data()`, `search_with_positions()`, `auto_link()`
- Clean Korean docstrings provide context alongside English code
- Good DRY principle adherence — `chunk_documents()` reuses `chunk_document()`
- Visual separators (`# ─── Section ───`) improve readability

### Issues

- **String interpolation in Cypher queries** (`graph.py:76,85-88`): Dynamic label/key injection via f-strings creates Cypher injection risk:
```python
# graph.py:76
query = f"CREATE (n:{label} {{{props_str}}}) RETURN n"
```

- **Workflow prompt uses `${}` instead of Python f-strings** (`workflows.py:95-101`):
```python
prompt = f"""...
[사용자 질문]
${query}          # Bug: should be {query}
[벡터 컨텍스트]
${context}        # Bug: should be {context}
"""
```
This is a **functional bug** — the variables won't be interpolated.

- **Unused import**: `json` imported twice in `api.py` (lines 8 and 94)

- **Hardcoded fallback path** in `mcp_server.py:40-41`:
```python
workspace = os.environ.get(
    "LANGENT_WORKSPACE",
    r"c:\Users\daewooenc\workspace\Ontology"  # Windows-specific personal path
)
```

---

## 3. Type Safety (7.0/10)

### Strengths

- Consistent use of `typing` module: `Optional`, `List`, `Dict`, `Any`, `TypedDict`
- `AgentState` is properly defined as a `TypedDict` for LangGraph
- Pydantic models for config (`LangentConfig`) and sub-agents (`SubAgent`)

### Issues

- Heavy use of `Dict[str, Any]` as a catch-all return type — loses type information at boundaries
- No `mypy` configuration or strict type checking in the project
- `workspace: str = None` in `brain.py:44` should be `Optional[str] = None`
- No runtime type validation on API request parameters (FastAPI route handlers accept raw query params without Pydantic models)

---

## 4. Error Handling (5.5/10) — Major Weakness

### Pattern: Silent exception swallowing

Multiple locations catch `Exception` and silently discard it:

| Location | Code | Impact |
|---|---|---|
| `brain.py:80-81` | `except Exception: self.graph = None` | Neo4j init failures silently ignored |
| `brain.py:217-218` | `except Exception: pass` | Graph visualization failures hidden |
| `vector.py:83-84` | `except Exception: pass` | Duplicate check failures hidden |
| `vector.py:186-187` | `except Exception: pass` | Cache read failures hidden |
| `vector.py:227-228` | `except Exception: pass` | Cache write failures hidden |
| `retriever.py:76-77` | `except Exception: continue` | Graph query failures per keyword hidden |
| `api.py:139-140` | `except Exception: pass` | WebSocket broadcast failures hidden |
| `ingest.py:109-110` | `except Exception: pass` | CSV read failures hidden |

### No logging framework

The entire codebase uses `print()` instead of Python's `logging` module:
- `brain.py:317-319`: Custom `_log()` wraps `print()`
- `graph.py:43`: `print(f"Neo4j connection failed: {e}")`
- `ingest.py:52`: `print(f"  [Warning] Error extracting...")`

This makes debugging in production extremely difficult — no log levels, no log rotation, no structured logging.

---

## 5. Testing (3.0/10) — Critical Weakness

### Current state

- **1 test file** with meaningful content: `tests/test_smoke.py` (93 lines)
- Test structure is a **single monolithic function** `test_basic()` — not proper pytest test cases
- No use of `pytest` fixtures, parametrize, or assertions — uses `print()` for verification
- No separation between unit tests and integration tests

```python
# test_smoke.py — This is a script, not proper tests
def test_basic():
    print("1️⃣  Import test...")
    from langent.config import LangentConfig
    print("   ✓ All modules imported")  # No assertions!
```

### Missing test coverage

- No tests for: `api.py`, `mcp_server.py`, `cli.py`, `workflows.py`, `delegation.py`, `skills/loader.py`
- No error path testing
- No mock/stub usage for external dependencies (Neo4j, ChromaDB)
- No async test coverage (despite `pytest-asyncio` being in dev deps)
- No test configuration (`pytest.ini`, `conftest.py`, or `pyproject.toml [tool.pytest]`)

### Estimated coverage: **~10-15%**

---

## 6. Security (4.0/10) — Critical Weakness

### Hardcoded credentials

```python
# config.py:23 — Real password exposed in source code
class GraphStoreConfig(BaseModel):
    password: str = "yw02280228"

# graph.py:21 — Duplicated hardcoded password
class GraphStore:
    def __init__(self, ..., password: str = "yw02280228"):
```

### Cypher injection vulnerability

`graph.py:75-76,85-88,107-109`: Label and key names are interpolated directly into Cypher queries via f-strings without sanitization:
```python
def create_entity(self, label: str, properties: Dict[str, Any]) -> Dict:
    props_str = ", ".join(f"{k}: ${k}" for k in properties)
    query = f"CREATE (n:{label} {{{props_str}}}) RETURN n"
```

If `label` or key names come from user input, this allows arbitrary Cypher execution.

### CORS wide open

```python
# api.py:23-28
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### No input validation on graph queries

```python
# api.py:101-103 — Raw Cypher from user passed directly to Neo4j
@app.post("/api/graph")
async def graph_query(cypher: str):
    return get_langent().graph_query(cypher)
```

### No authentication/authorization on any API endpoint

All endpoints are publicly accessible without any auth mechanism.

---

## 7. Documentation (7.5/10)

### Strengths

- Comprehensive `README.md` with installation, usage, architecture, and MCP integration docs
- YouTube demo link included
- Visual screenshots of the 3D nebula
- Korean + English bilingual documentation
- All modules have descriptive docstrings
- `.env.example` provides clear configuration template

### Issues

- No API documentation (no OpenAPI/Swagger customization beyond FastAPI defaults)
- No `CONTRIBUTING.md` or development setup guide
- No `CHANGELOG.md` for version tracking
- README references `python server/api.py` instead of `langent serve`
- `README.md:54`: Typo "raw raw files"

---

## 8. CI/CD & DevOps (1.0/10) — Critical Gap

### Completely absent

- No `.github/workflows/` or any CI configuration
- No `Dockerfile` or container setup
- No `Makefile` or task runner
- No pre-commit hooks (`.pre-commit-config.yaml`)
- No linting configuration (no `ruff.toml`, `.flake8`, `mypy.ini`, etc.)
- No code formatting tool configured (no `black`, `isort`, `ruff format`)
- No dependency lockfile (`requirements.txt` or `poetry.lock`)

---

## 9. Dependency Management (7.0/10)

### Strengths

- Well-organized `pyproject.toml` with categorized comments
- Reasonable version pinning (minimum versions specified)
- Dev dependencies separated via `[project.optional-dependencies]`
- Hatchling build system is modern and well-suited

### Issues

- No upper bounds on dependencies — major version bumps could break the project
- `requests` is used in `llm_proxy.py:74` but not declared in dependencies
- No lockfile for reproducible builds
- Heavy dependency chain: `sentence-transformers` + `torch` adds ~2GB to install size but there's no mention of this in README

---

## 10. Specific Bugs Found

| # | File | Line | Severity | Description |
|---|---|---|---|---|
| 1 | `workflows.py` | 95-101 | **High** | `${query}` / `${context}` / `${graph_str}` uses shell-style interpolation inside f-string — variables not substituted |
| 2 | `config.py` | 23 | **High** | Hardcoded password `"yw02280228"` committed to repo |
| 3 | `graph.py` | 21 | **High** | Same hardcoded password duplicated |
| 4 | `mcp_server.py` | 40-41 | **Medium** | Windows personal path as fallback |
| 5 | `mcp_server.py` | 137 | **Medium** | `agent.graph.query()` should be `agent.graph_query()` — will crash at runtime |
| 6 | `api.py` | 94 | **Low** | Duplicate `import json` |
| 7 | `api.py` | 13 | **Low** | `sys.path.insert()` hack |

---

## 11. Recommendations (Priority Order)

### P0 — Immediate

1. **Remove hardcoded credentials** from `config.py:23` and `graph.py:21` — use environment variables only
2. **Fix the `${}` interpolation bug** in `workflows.py:95-101`
3. **Fix `mcp_server.py:137`** method call: `agent.graph.query()` -> `agent.graph_query()`

### P1 — Short-term

4. **Add logging framework**: Replace all `print()` with `logging.getLogger(__name__)`
5. **Add proper test suite**: Convert smoke test to proper pytest cases with fixtures and assertions
6. **Add input validation**: Pydantic request models for FastAPI endpoints
7. **Sanitize Cypher queries**: Validate label/key names against allowlists in `GraphStore`
8. **Add API authentication**: At minimum, API key middleware for production use

### P2 — Medium-term

9. **Set up CI/CD**: GitHub Actions for lint + test + build
10. **Add linting**: `ruff` for linting and formatting
11. **Add type checking**: `mypy` with strict mode
12. **Refactor `Langent` class**: Extract subsystem managers
13. **Remove `sys.path` manipulation**: Fix package structure
14. **Add `Dockerfile`** for reproducible deployments
15. **Replace global singletons** with FastAPI dependency injection

### P3 — Long-term

16. **Add structured logging** with correlation IDs
17. **Add integration test suite** with Docker Compose (ChromaDB + Neo4j)
18. **Add API rate limiting** and request validation
19. **Implement proper error types** instead of returning `{"error": "..."}` dicts
20. **Add health check endpoints** and graceful shutdown handling

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│              langent serve (CLI)                 │
│              langent ingest                      │
│              langent query                       │
├─────────────┬───────────────┬───────────────────┤
│  FastAPI     │  MCP Server   │  CLI (Click)      │
│  + WebSocket │  (stdio)      │                   │
├─────────────┴───────────────┴───────────────────┤
│               Langent Brain                      │
│        (Central Orchestrator — God Class)         │
├──────────┬──────────┬──────────┬────────────────┤
│ RAG      │ Stores   │ Agents   │ Skills         │
│ Pipeline │          │          │                │
│ ┌──────┐ │ ┌──────┐ │ ┌──────┐ │ ┌────────────┐│
│ │Ingest│ │ │Vector│ │ │Work- │ │ │SkillLoader ││
│ │or    │ │ │Store │ │ │flows │ │ │(SKILL.md)  ││
│ ├──────┤ │ │Chroma│ │ │Lang- │ │ └────────────┘│
│ │Chunk-│ │ │DB    │ │ │Graph │ │                │
│ │er    │ │ ├──────┤ │ ├──────┤ │                │
│ ├──────┤ │ │Graph │ │ │Sub-  │ │                │
│ │Retri-│ │ │Store │ │ │Agent │ │                │
│ │ever  │ │ │Neo4j │ │ │Mgr   │ │                │
│ └──────┘ │ └──────┘ │ └──────┘ │                │
├──────────┴──────────┴──────────┴────────────────┤
│             LLM Proxy Layer                      │
│     fake | ollama | mcp | proxy modes            │
└─────────────────────────────────────────────────┘
```

---

## File-by-File Quality Scores

| File | Lines | Score | Key Concern |
|---|---|---|---|
| `brain.py` | 331 | 7/10 | God class, silent exceptions |
| `config.py` | 91 | 6/10 | Hardcoded password |
| `store/vector.py` | 273 | 8/10 | Good caching, silent exceptions |
| `store/graph.py` | 168 | 6/10 | Cypher injection, hardcoded password |
| `rag/ingest.py` | 112 | 9/10 | Multi-encoding, robust extraction |
| `rag/chunker.py` | 104 | 8/10 | Good algorithm, clean code |
| `rag/retriever.py` | 128 | 8/10 | Clean RRF implementation |
| `agents/workflows.py` | 110 | 6/10 | Variable interpolation bug |
| `agents/delegation.py` | 51 | 7/10 | Simplistic keyword matching |
| `skills/loader.py` | 77 | 8/10 | Clean, extensible design |
| `server/api.py` | 155 | 6/10 | No auth, CORS *, global state |
| `server/mcp_server.py` | 175 | 6/10 | Method call bug, hardcoded path |
| `server/cli.py` | 56 | 8/10 | Clean Click usage |
| `llm_proxy.py` | 94 | 7/10 | Good LangChain integration |
| `tests/test_smoke.py` | 93 | 4/10 | Not proper tests, no assertions |

---

*Analysis performed by reviewing all 15 source files and configuration in the Langent v2.0.0 repository.*
