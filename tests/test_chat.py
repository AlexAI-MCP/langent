"""
Test Agent Chat logic
"""
import sys
import os

sys.path.insert(0, ".")

def test_chat():
    from langent.brain import Langent
    
    print("Initializing Langent...")
    agent = Langent(neo4j=False, llm_mode="fake")
    
    print("\n💬 Sending message: '강남에 있는 치킨집 찾아줘'")
    result = agent.chat("강남에 있는 치킨집 찾아줘")
    
    print("\nResult Answer:")
    print(result.get("answer"))
    
    print("\nExecution Steps:")
    for i, step in enumerate(result.get("steps", [])):
        print(f"  {i+1}. {step}")

if __name__ == "__main__":
    test_chat()
