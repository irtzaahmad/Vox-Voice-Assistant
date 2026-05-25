import json
import os
import threading

class ContextMemory:
    def __init__(self, data_dir="data"):
        self.file_path = os.path.join(data_dir, "memory.json")
        self.memory = {}
        self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.memory = json.load(f)
            except Exception:
                self.memory = {}
        else:
            self.memory = {}

    def _save_async(self):
        """Professional optimization: Save in background thread to prevent blocking STT/TTS."""
        def save_worker():
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            try:
                # Copy dict to avoid thread mutation issues
                mem_copy = self.memory.copy()
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(mem_copy, f, indent=4)
            except Exception as e:
                print(f"Error saving memory: {e}")
        
        threading.Thread(target=save_worker, daemon=True).start()

    def save_fact(self, key: str, value: str) -> str:
        k = key.lower().strip()
        v = value.strip()
        if not k or not v:
            return "Please provide both what to remember and its value."
        self.memory[k] = v
        self._save_async() # Fast non-blocking save
        return f"Got it. I will remember that {k} is {v}."

    def get_fact(self, key: str) -> str:
        k = key.lower().strip()
        
        # 1. Instant Direct match (O(1))
        if k in self.memory:
            return f"You told me that {k} is {self.memory[k]}."
        
        # 2. Optimized Partial Match
        k_words = set(k.split())
        best_match = None
        highest_score = 0
        
        for mem_key, mem_val in self.memory.items():
            # Quick substring check
            if k in mem_key or mem_key in k:
                return f"I recall that {mem_key} is {mem_val}."
            
            # Word intersection scoring
            mem_words = set(mem_key.split())
            score = len(k_words.intersection(mem_words))
            if score > highest_score and score >= len(k_words) * 0.5: # 50% match
                highest_score = score
                best_match = (mem_key, mem_val)
                
        if best_match:
            return f"I think you mean {best_match[0]}, which is {best_match[1]}."
                
        return "I don't have any memory regarding that."