
import os
import sys

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from main import Vox

def test_ai():
    print("Testing AI Question Feature...")
    vox = Vox()
    
    # Test queries
    queries = [
        "Who is Elon Musk?",
        "What is the capital of France?",
        "Tell me about the Moon"
    ]
    
    for q in queries:
        print(f"\n[User]: {q}")
        # process_command handles both processing and speaking (via self.speak)
        # Note: self.speak will print to console in this environment
        response = vox.process_command(q)
        print(f"[Vox]: {response}")

if __name__ == "__main__":
    test_ai()
