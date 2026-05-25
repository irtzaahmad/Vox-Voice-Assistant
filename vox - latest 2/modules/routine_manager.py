import json
import os
import threading
from datetime import datetime
from collections import Counter

class RoutineManager:
    def __init__(self, data_dir="data"):
        self.file_path = os.path.join(data_dir, "routine.json")
        self.routine = {}
        self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.routine = json.load(f)
            except Exception:
                self.routine = {}
        else:
            self.routine = {}

    def _save_async(self):
        """Save routine in a background thread so Vox doesn't freeze after commands."""
        def save_worker():
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            try:
                # Copy dict to avoid concurrent mutation errors
                rout_copy = self.routine.copy()
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(rout_copy, f, indent=4)
            except Exception:
                pass
                
        threading.Thread(target=save_worker, daemon=True).start()

    def record_command(self, command: str):
        if not command or len(command.split()) > 10:
            return
            
        hour = str(datetime.now().hour)
        if hour not in self.routine:
            self.routine[hour] = []
            
        self.routine[hour].append(command.lower().strip())
        
        # Keep recent history per hour
        if len(self.routine[hour]) > 50:
            self.routine[hour] = self.routine[hour][-50:]
            
        self._save_async()

    def suggest_routine(self) -> str:
        hour = str(datetime.now().hour)
        if hour in self.routine and self.routine[hour]:
            most_common = Counter(self.routine[hour]).most_common(1)
            if most_common:
                cmd = most_common[0][0]
                return f"Based on your routine, you usually '{cmd}' around this time. Would you like me to do that?"
        return "I don't have enough data to suggest a routine for this hour yet."