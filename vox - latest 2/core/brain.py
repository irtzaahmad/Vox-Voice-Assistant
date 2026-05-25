"""
Vox AI Brain Module (Upgraded)
Integrates Google Gemini (cloud), Ollama (local), and Wikipedia fallback.
Based on AIChatbot from Vox v3.2.
"""
import requests
import json
import re
import urllib.parse
from typing import Optional, Dict, List
from datetime import datetime
import config

class VoxBrain:
    def __init__(self):
        self.gemini_api_key = config.GEMINI_API_KEY
        self.ollama_enabled = config.OLLAMA_ENABLED
        self.ollama_model = config.OLLAMA_MODEL
        self.ollama_host = config.OLLAMA_HOST
        self.system_prompt = "You are Vox, a professional and efficient AI assistant. Keep your responses concise, smart, and helpful. Use a natural and human-like tone."

        self.conversation_history = []
        self.max_history = 10
        self._cache = {} # Simple high-speed response cache
        
        # Professional Optimization: Re-use TCP connections for extreme speed
        self._session = requests.Session()

        # Initialize Gemini if API key is available
        self.gemini_model = None
        if self.gemini_api_key and self.gemini_api_key != "YOUR_GEMINI_API_KEY_HERE":
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_api_key)
                
                # Professional Fallback: Try multiple model names to avoid 404
                model_names = [config.GEMINI_MODEL, "gemini-1.5-flash", "gemini-pro"]
                for mname in model_names:
                    try:
                        self.gemini_model = genai.GenerativeModel(mname)
                        # Test if this model name is valid
                        self.gemini_model.generate_content("ping", generation_config={"max_output_tokens": 1})
                        print(f"🤖 Gemini AI initialized: {mname}")
                        break
                    except Exception:
                        self.gemini_model = None
                        continue
                        
                if not self.gemini_model:
                    print("⚠️  All Gemini model names failed. Check API key/SDK version.")
            except Exception as e:
                print(f"⚠️ Gemini initialization failed: {e}")

        # Test Ollama connection
        self.ollama_available = False
        if self.ollama_enabled:
            self.ollama_available = self._check_ollama()

    def _check_ollama(self) -> bool:
        """Fast heartbeat check for Ollama availability."""
        try:
            # Check only the tags endpoint with a very short timeout
            response = self._session.get(f"{self.ollama_host}/api/tags", timeout=1.5)
            return response.status_code == 200
        except:
            return False

    def _get_ollama_response(self, prompt: str) -> Optional[str]:
        """Get response from local Ollama"""
        try:
            response = self._session.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": f"{self.system_prompt}\n\nUser: {prompt}\nVox:",
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 500}
                },
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            return None
        except Exception:
            return None

    def _get_gemini_response(self, prompt: str) -> Optional[str]:
        """Get response from Google Gemini with detailed error handling"""
        if not self.gemini_model:
            return None
        try:
            full_prompt = f"{self.system_prompt}\n\nPlease respond to this: {prompt}"
            response = self.gemini_model.generate_content(full_prompt)
            return response.text.strip()
        except Exception as e:
            err_msg = str(e)
            print(f"❌ Gemini error: {err_msg}")
            
            # Auto-fix: If model not found, it might be an SDK/Region issue
            if "404" in err_msg and "not found" in err_msg:
                print("⚠️  Gemini Model 404. Check if your API key supports this model.")
                
            return None

    def _get_wikipedia_summary(self, query: str) -> Optional[str]:
        """Fetch professional summary from Wikipedia with high-speed direct search."""
        try:
            # 1. High-Speed Subject Extraction
            q = query.lower().strip().strip('?')
            # Remove common question starters for cleaner search
            clean_q = re.sub(r'^(who|what|where|when|tell me about|search for|is|was|are|the|a|an)\s+', '', q, flags=re.I).strip()
            if not clean_q: return None
            
            headers = {'User-Agent': 'VoxAssistant/1.2 (Ultra Efficiency)'}
            
            # 2. Optimized Direct Search + Summary Request (Saves 1 network call)
            search_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(clean_q)}"
            res = self._session.get(search_url, headers=headers, timeout=3)
            
            if res.status_code == 200:
                data = res.json()
                summary = data.get('extract', '')
                if summary:
                    # Return first 3 sentences for efficiency
                    return ". ".join(summary.split(". ")[:3]) + "."
            
            # 3. Fallback to Search API if direct link fails
            search_api = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(clean_q)}&format=json&srlimit=1"
            s_res = self._session.get(search_api, headers=headers, timeout=3).json()
            results = s_res.get('query', {}).get('search', [])
            
            if results:
                title = results[0]['title']
                summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
                summary_res = self._session.get(summary_url, headers=headers, timeout=3).json()
                return summary_res.get('extract', '')

            return None
        except Exception:
            return None

    def generate_response(self, text: str) -> str:
        """Main interface with multi-tiered fallback and high-speed caching."""
        clean_text = text.lower().strip()
        
        # 0. Check Cache (Instant)
        if clean_text in self._cache:
            print("⚡ Using Cached Response")
            return self._cache[clean_text]

        self.conversation_history.append({'user': text, 'assistant': None})
        response = None
        
        # Tier 1: Gemini (Cloud)
        if self.gemini_model:
            response = self._get_gemini_response(text)
            if response: print("🤖 Using Online AI (Gemini)")

        # Tier 2: Ollama (Local)
        if not response and self.ollama_available:
            response = self._get_ollama_response(text)
            if response: print("🦙 Using Local AI (Ollama)")

        # Tier 3: Wikipedia (Info)
        ml = text.lower().strip()
        is_info = ml.startswith(('who', 'what', 'where', 'when', 'how', 'tell me about'))
        if not response and is_info:
            response = self._get_wikipedia_summary(text)
            if response: print("📚 Using Wikipedia Fallback")

        # Tier 4: Basic Offline Fallback
        if not response:
            response = "I'm having trouble connecting to my AI models. Please check your internet or Ollama connection."

        # Save to Cache
        if response:
            self._cache[clean_text] = response

        self.conversation_history[-1]['assistant'] = response
        if len(self.conversation_history) > self.max_history:
            self.conversation_history.pop(0)
        return response
