"""
Langent v3 — RAG Agentic Framework
====================================
Workspace -> ChromaDB -> 3D Nebula -> MCP/API

Usage:
    from langent import Langent
    agent = Langent(workspace="./my_data")
    agent.ingest()
    agent.query("Find related documents about AI")
"""
__version__ = "3.0.0"

from langent.brain import Langent

__all__ = ["Langent"]
