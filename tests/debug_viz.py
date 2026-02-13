"""
Debug 3D Point Generation
"""
import sys
import os

sys.path.insert(0, ".")

def debug_points():
    from langent.brain import Langent
    print("Initializing Langent...")
    agent = Langent(neo4j=False, verbose=False)
    
    print(f"Vector Count: {agent.vector.count()}")
    
    print("\nGenerating 3D points...")
    try:
        data = agent.get_nebula_data(limit=100)
        points = data.get("points", [])
        print(f"Successfully generated {len(points)} points")
        
        if points:
            p = points[0]
            print(f"Sample Point: ID={p['id']}, X={p['x']:.2f}, Y={p['y']:.2f}, Z={p['z']:.2f}")
            print(f"Metadata: {p.get('metadata')}")
        else:
            print("❌ No points generated! Check if embeddings exist.")
            
            # Check embeddings directly
            all_emb = agent.vector.get_all_embeddings(limit=5)
            emb = all_emb.get("embeddings")
            print(f"Embeddings raw check: {type(emb)}")
            if emb is not None:
                print(f"Embedding count: {len(emb)}")
                if len(emb) > 0:
                    print(f"First embedding size: {len(emb[0])}")
            else:
                print("❌ No embeddings found in ChromaDB!")

    except Exception as e:
        print(f"❌ Error during point generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_points()
