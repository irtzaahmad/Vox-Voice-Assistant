"""
Vox AI Chatbot Module
Integrates Google Gemini (cloud) and Ollama (local) for intelligent conversations.
Includes high-accuracy Wikipedia fallback for informational queries.
"""
import requests
import json
import re
import urllib.parse
from typing import Optional, Dict, List
from datetime import datetime
import config

class AIChatbot:
    def __init__(self):
        self.gemini_api_key = config.GEMINI_API_KEY
        self.ollama_enabled = config.OLLAMA_ENABLED
        self.ollama_model = config.OLLAMA_MODEL
        self.ollama_host = config.OLLAMA_HOST

        self.conversation_history = []
        self.max_history = 10

        # Initialize Gemini if API key is available
        self.gemini_model = None
        if self.gemini_api_key and self.gemini_api_key != "YOUR_GEMINI_API_KEY_HERE":
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_api_key)
                # Note: Model name from config is used directly
                self.gemini_model = genai.GenerativeModel(config.GEMINI_MODEL)
                print(f"🤖 Gemini AI initialized: {config.GEMINI_MODEL}")
            except Exception as e:
                print(f"⚠️ Gemini initialization failed: {e}")

        # Test Ollama connection
        self.ollama_available = False
        if self.ollama_enabled:
            self.ollama_available = self._check_ollama()

    def _check_ollama(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=2)
            if response.status_code == 200:
                print(f"🦙 Ollama connected: {self.ollama_model}")
                return True
        except:
            pass
        return False

    def _get_ollama_response(self, prompt: str) -> Optional[str]:
        """Get response from local Ollama"""
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 500}
                },
                timeout=60
            )
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            return None
        except Exception:
            return None

    def _get_gemini_response(self, prompt: str) -> Optional[str]:
        """Get response from Google Gemini"""
        if not self.gemini_model:
            return None
        try:
            gemini_history = []
            history_slice = self.conversation_history[-(self.max_history):-1]
            for entry in history_slice:
                if entry['user']:
                    gemini_history.append({"role": "user", "parts": [entry['user']]})
                if entry['assistant']:
                    gemini_history.append({"role": "model", "parts": [entry['assistant']]})

            chat = self.gemini_model.start_chat(history=gemini_history)
            response = chat.send_message(prompt)
            return response.text.strip()
        except Exception:
            return None

    def _get_wikipedia_summary(self, query: str) -> Optional[str]:
        """Fetch a professional and accurate summary from Wikipedia"""
        try:
            # 1. Smarter Cleaning
            q = query.lower().strip().strip('?')
            patterns = [
                'who is the', 'what is the', 'who is', 'what is', 'where is', 
                'tell me about', 'who was', 'what was', 'search for', 'how many',
                'tell me something about', 'what are', 'where are'
            ]
            
            clean_q = q
            for p in sorted(patterns, key=len, reverse=True):
                if q.startswith(p):
                    clean_q = q[len(p):].strip()
                    break
            
            # Remove leading filler words
            clean_q = re.sub(r'^(is|the|a|an|was|are)\s+', '', clean_q).strip()
            if not clean_q: return None
            
            headers = {'User-Agent': 'VoxAssistant/1.0 (Professional AI)'}
            
            # 2. Search for the best matching page
            search_api = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(clean_q)}&format=json&srlimit=5"
            s_res = requests.get(search_api, headers=headers, timeout=5).json()
            
            results = s_res.get('query', {}).get('search', [])
            if not results: return None
            
            # 3. Intelligent Title Selection
            title = results[0]['title']
            if 'capital' in q:
                subject = clean_q.replace('capital of', '').replace('capital', '').strip()
                for r in results:
                    rt = r['title'].lower()
                    if ('capital' in rt and subject in rt) or (subject and subject in rt and 'punishment' not in rt):
                        title = r['title']
                        break
            
            # 4. Fetch the introduction
            summary_api = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts|pageprops&exintro&explaintext&titles={urllib.parse.quote(title)}&format=json&exsentences=3"
            p_res = requests.get(summary_api, headers=headers, timeout=5).json()
            
            pages = p_res.get('query', {}).get('pages', {})
            for pid in pages:
                if 'pageprops' in pages[pid] and 'disambiguation' in pages[pid]['pageprops']:
                    if len(results) > 1:
                        # Recursively try next search result for disambiguation
                        return self._get_wikipedia_summary(results[1]['title'])
                
                summary = pages[pid].get('extract', '').strip()
                if summary:
                    # Clean citations and whitespace
                    summary = re.sub(r'\[\d+\]', '', summary)
                    summary = re.sub(r'\s+', ' ', summary)
                    if "refer to:" not in summary:
                        return summary
            return None
        except Exception:
            return None

    def _get_fallback_response(self, prompt: str) -> str:
        """Generate fallback response for common patterns when AI is unavailable"""
        prompt_lower = prompt.lower()
        if any(word in prompt_lower for word in ['time', 'clock']):
            return f"The current time is {datetime.now().strftime('%I:%M %p')}."
        if any(word in prompt_lower for word in ['date', 'day']):
            return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."
        if any(word in prompt_lower for word in ['joke', 'funny']):
            return "Why don't scientists trust atoms? Because they make up everything!"
        if any(word in prompt_lower for word in ['help', 'can you do']):
            return "I can help you with web searches, PC control, managing files, and answering questions."
        if 'your name' in prompt_lower:
            return "I am Vox, which stands for Just A Rather Very Intelligent System."
        return "I am not sure about that. Could you please try rephrasing?"

    def chat(self, message: str) -> str:
        """Main chat interface with multi-tiered fallback"""
        self.conversation_history.append({'timestamp': datetime.now(), 'user': message, 'assistant': None})

        response = None
        # Tier 1: Gemini
        if self.gemini_model:
            response = self._get_gemini_response(message)
            if response: print("🤖 Using Gemini AI")

        # Tier 2: Ollama
        if not response and self.ollama_available:
            response = self._get_ollama_response(message)
            if response: print("🦙 Using Ollama AI")

        # Tier 3: Wikipedia (for informational questions)
        ml = message.lower().strip()
        info_keywords = ['who is', 'what is', 'where is', 'tell me about', 'who was', 'what was', 'capital of', 'population of']
        is_info = any(x in ml for x in info_keywords) or ml.startswith(('who', 'what', 'where', 'when', 'how'))
        
        if not response and is_info:
            response = self._get_wikipedia_summary(message)
            if response: print("📚 Using Wikipedia Summary")

        # Tier 4: Local Fallback
        if not response:
            response = self._get_fallback_response(message)
            print("📴 Using offline fallback")

        self.conversation_history[-1]['assistant'] = response
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
        return response

    def clear_history(self):
        self.conversation_history = []

    def get_history(self) -> List[Dict]:
        return self.conversation_history

    def is_ai_available(self) -> bool:
        return self.gemini_model is not None or self.ollama_available

if __name__ == "__main__":
    bot = AIChatbot()
    print(f"Vox Chatbot Ready. Response: {bot.chat('Who is Elon Musk?')}")
