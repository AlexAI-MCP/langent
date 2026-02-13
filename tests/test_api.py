import urllib.request, json

# Test search
resp = urllib.request.urlopen("http://localhost:8000/api/query?q=AI&top_k=3")
data = json.loads(resp.read().decode())
print("=== Search Results for 'AI' ===")
for r in data:
    print(f"  [{r['score']:.3f}] {r['source']}")
    print(f"    {r['preview'][:80]}...")
    print()

# Test status
resp2 = urllib.request.urlopen("http://localhost:8000/api/status")
status = json.loads(resp2.read().decode())
print(f"=== Status ===")
print(f"  Vectors: {status['vector_count']}")
print(f"  Collections: {status['collections']}")
print(f"  Graph: {status['graph_connected']}")
