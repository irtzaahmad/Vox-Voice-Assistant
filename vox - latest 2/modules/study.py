import json
import os
import random
import time

class StudyAssistant:
    def __init__(self, data_dir="data"):
        self.file_path = os.path.join(data_dir, "mcqs.json")
        self._create_default_mcqs()

    def _create_default_mcqs(self):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            default_data = [
                {"q": "What is the capital of France?", "a": "paris", "options": ["Paris", "London", "Berlin"]},
                {"q": "What is 5 plus 7?", "a": "12", "options": ["10", "11", "12", "13"]},
                {"q": "Which planet is known as the Red Planet?", "a": "mars", "options": ["Earth", "Jupiter", "Mars", "Venus"]},
                {"q": "What does CPU stand for?", "a": "central processing unit", "options": ["Central Processing Unit", "Computer Personal Unit", "Central Processor Utility"]}
            ]
            try:
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(default_data, f, indent=4)
            except Exception:
                pass

    def run_quiz(self, vox_app) -> str:
        """Runs a synchronous voice quiz by pausing the background listener."""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                mcqs = json.load(f)
        except Exception:
            return "Failed to load question bank."
            
        if not mcqs:
            return "I don't have any questions in my bank."

        question = random.choice(mcqs)
        text = question['q'] + " Your options are: " + ", ".join(question['options'])
        
        # Stop background first
        was_running = False
        if vox_app.voice_engine and vox_app.voice_engine.running:
            was_running = True
            vox_app.voice_engine.stop() # Complete stop for reliability
            time.sleep(0.5)

        vox_app.speak(text)
        time.sleep(1.0) # Give more time for TTS to finish
            
        vox_app.speak("What is your answer?")
        time.sleep(0.5)
        
        # Use simple SpeechRecognition for the answer to keep it light
        import speech_recognition as sr
        answer = ""
        try:
            r = sr.Recognizer()
            with sr.Microphone(device_index=vox_app.config.MIC_INDEX) as source:
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio = r.listen(source, timeout=8)
                answer = r.recognize_google(audio)
                print(f"👂 Answer heard: {answer}")
        except:
            pass
            
        if was_running:
            threading.Thread(target=vox_app.voice_engine.start, daemon=True).start()

        if not answer:
            return "I didn't hear an answer. Quiz cancelled."

        # Check answer
        if question['a'].lower() in answer.lower():
            return "That is correct!"
        else:
            return f"Sorry, the correct answer was {question['a']}."