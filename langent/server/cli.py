import click
import uvicorn
import os
from langent.brain import Langent

@click.group()
def main():
    """Langent v2 CLI - RAG Agentic Framework"""
    pass

@main.command()
@click.option("--port", default=8000, help="Port to run the server on")
@click.option("--host", default="0.0.0.0", help="Host to run the server on")
@click.option("--workspace", default=None, help="Path to the workspace")
def serve(port, host, workspace):
    """Start the Langent Nebula server"""
    if workspace:
        os.environ["LANGENT_WORKSPACE"] = workspace
    
    # We import app here to avoid loading everything just for --help
    from langent.server.api import app
    click.echo(f"Starting Langent Nebula server on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)

@main.command()
@click.option("--workspace", default=None, help="Path to the workspace to ingest")
def ingest(workspace):
    """Ingest workspace files into vector store"""
    agent = Langent(workspace=workspace)
    click.echo("📥 Starting workspace ingestion...")
    result = agent.ingest()
    click.echo(f"✅ Ingestion complete: {result['files_scanned']} files, {result['vectors_added']} vectors added.")

@main.command()
def link():
    """Link vector chunks and graph entities"""
    agent = Langent()
    click.echo("🔗 Starting knowledge linking...")
    result = agent.auto_link()
    click.echo(f"✅ Linking complete: {result.get('chunks_linked', 0)} chunks linked.")

@main.command()
@click.argument("question")
def query(question):
    """Query the Langent knowledge base"""
    agent = Langent()
    click.echo(f"🔍 Searching for: {question}")
    results = agent.query(question)
    for i, r in enumerate(results):
        click.echo(f"\n[{i+1}] Score: {r.get('score', 0):.4f}")
        click.echo(f"Source: {r.get('metadata', {}).get('source', 'unknown')}")
        click.echo(f"Content: {r.get('document', '')[:200]}...")

if __name__ == "__main__":
    main()
