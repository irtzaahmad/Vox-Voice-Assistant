import requests
import re
import time
import urllib.parse
from typing import Optional, Dict, List
import config


class VoxBrain:
    def __init__(self):
        self._groq_api_key = config.GROQ_API_KEY
        self._groq_llm_model = config.GROQ_LLM_MODEL
        self.ollama_enabled = config.OLLAMA_ENABLED
        self.ollama_model = config.OLLAMA_MODEL
        self.ollama_host = config.OLLAMA_HOST
        self.system_prompt = "You are Vox, a professional voice assistant. Only respond in English. Keep responses concise, smart, and helpful. If you receive a command that sounds like a misheard app or web command (e.g. 'not bad' for 'notepad', 'you tube' for 'youtube'), politely suggest the correction. If you cannot understand the request, ask the user to clarify what they meant. Never respond with Urdu or any non-English text."

        self.conversation_history = []
        self.max_history = 10
        self._max_history_tokens = 600
        self._max_message_chars = 600
        self._cache = {}

        self._session = requests.Session()

        if self._groq_api_key:
            print(f"Groq LLM configured (model: {self._groq_llm_model})")
        else:
            print("No Groq API key — LLM will use Ollama or online search")

        self.ollama_available = False
        if self.ollama_enabled:
            self.ollama_available = self._check_ollama()

        self.duckduckgo_available = False
        if config.ENABLE_DUCKDUCKGO:
            self.duckduckgo_available = self._check_duckduckgo()

    def _check_ollama(self) -> bool:
        try:
            response = self._session.get(f"{self.ollama_host}/api/tags", timeout=1.5)
            return response.status_code == 200
        except:
            return False

    def _check_duckduckgo(self) -> bool:
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text("ping", max_results=1))
            return True
        except Exception:
            return False

    def _build_messages(self, prompt: str) -> list:
        messages = [{"role": "system", "content": self.system_prompt}]
        recent = self.conversation_history[-self.max_history:-1] if len(self.conversation_history) > 1 else []

        total_chars = 0
        included = []
        for turn in reversed(recent):
            u_text = (turn['user'] or '')[:self._max_message_chars]
            a_text = (turn['assistant'] or '')[:self._max_message_chars] if turn['assistant'] else ''
            turn_chars = len(u_text) + len(a_text)
            if total_chars + turn_chars > self._max_history_tokens * 4:
                break
            included.insert(0, (u_text, a_text))
            total_chars += turn_chars

        for u_text, a_text in included:
            messages.append({"role": "user", "content": u_text})
            if a_text:
                messages.append({"role": "assistant", "content": a_text})

        messages.append({"role": "user", "content": prompt})
        return messages

    def _post_groq(self, messages, max_tokens: int) -> Optional[object]:
        """POST to Groq chat completions. Returns response object or None on network error."""
        try:
            return self._session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json={
                    "model": self._groq_llm_model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": max_tokens
                },
                headers={"Authorization": f"Bearer {self._groq_api_key}"},
                timeout=30
            )
        except Exception as e:
            print(f"Groq LLM network error: {e}")
            return None

    @staticmethod
    def _extract_content(resp) -> Optional[str]:
        try:
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            return None

    def _get_groq_response(self, prompt: str) -> Optional[str]:
        if not self._groq_api_key:
            return None

        resp = self._post_groq(self._build_messages(prompt), 300)
        if resp is None:
            return None
        if resp.status_code == 200:
            return self._extract_content(resp)

        # Failure → retry once with minimal context (system + prompt only)
        reason = resp.status_code
        detail = resp.text[:150].replace('\n', ' ')
        print(f"Groq LLM {reason}: {detail} — retrying with minimal context...")

        # 429 rate limit: brief wait when Retry-After is short (TPM), skip long waits (TPD)
        if reason == 429:
            try:
                wait = int(resp.headers.get('Retry-After', '2'))
            except Exception:
                wait = 2
            if wait <= 5:
                print(f"Groq LLM rate limit: waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"Groq LLM daily token limit hit (Retry-After {wait}s) — using fallback.")
                return None

        minimal = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        retry = self._post_groq(minimal, 200)
        if retry is None:
            return None
        if retry.status_code == 200:
            return self._extract_content(retry)

        print(f"Groq LLM retry failed: {retry.status_code} {retry.text[:150]}")
        return None

    def _get_ollama_response(self, prompt: str) -> Optional[str]:
        try:
            messages = self._build_messages(prompt)
            response = self._session.post(
                f"{self.ollama_host}/api/chat",
                json={
                    "model": self.ollama_model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 500}
                },
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get("message", {}).get("content", "").strip()
            return None
        except Exception:
            return None

    def _needs_live_search(self, text: str) -> bool:
        clean = text.lower().strip()
        live_keywords = [
            "latest", "news", "today", "current", "recent", "breaking",
            "update", "headlines", "weather", "temperature", "forecast",
            "stock", "price", "cricket score", "football score",
            "schedule", "match", "result", "election", "covid",
            "coronavirus", "pandemic", "earthquake", "flood",
            "live", "now", "this week", "this month", "2024", "2025", "2026",
            "palestine", "israel", "ukraine", "russia", "gaza",
            "who is", "what is", "tell me about", "information about",
        ]
        for kw in live_keywords:
            if kw in clean:
                return True
        return False

    def _get_duckduckgo_response(self, query: str) -> Optional[str]:
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))

            if not results:
                return None

            snippets = []
            for r in results:
                title = r.get("title", "")
                body = r.get("body", "")
                if title and body:
                    snippets.append(f"{title}: {body}")
                elif body:
                    snippets.append(body)

            if not snippets:
                return None

            combined = "\n".join(snippets[:3])
            return f"Here's what I found online:\n{combined}"
        except Exception as e:
            print(f"DuckDuckGo search error: {e}")
            return None

    def _get_wikipedia_summary(self, query: str) -> Optional[str]:
        try:
            q = query.lower().strip().strip('?')

            prefixes = r'^(who|what|where|when|tell me about|search for|is|was|are|the|a|an|about|around)\s+'
            last_q = None
            while q != last_q:
                last_q = q
                q = re.sub(prefixes, '', q, flags=re.I).strip()

            clean_q = q
            if not clean_q:
                return None

            print(f"Wikipedia Search: '{clean_q}'")
            headers = {'User-Agent': 'VoxAssistant/1.2'}

            search_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(clean_q.replace(' ', '_'))}"
            res = self._session.get(search_url, headers=headers, timeout=3)

            if res.status_code == 200:
                data = res.json()
                summary = data.get('extract', '')
                if summary:
                    return ". ".join(summary.split(". ")[:3]) + "."

            search_api = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(clean_q)}&format=json&srlimit=1"
            s_res = self._session.get(search_api, headers=headers, timeout=3).json()
            results = s_res.get('query', {}).get('search', [])

            if results:
                title = results[0]['title']
                summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title.replace(' ', '_'))}"
                summary_res = self._session.get(summary_url, headers=headers, timeout=3).json()
                extract = summary_res.get('extract', '')
                if extract:
                    return ". ".join(extract.split(". ")[:3]) + "."

            return None
        except Exception as e:
            print(f"Wikipedia error: {e}")
            return None

    def generate_response(self, text: str) -> str:
        clean_text = text.lower().strip()
        clean_text = re.sub(r'^[a-z]\s+', '', clean_text)

        if clean_text in self._cache:
            print("Using Cached Response")
            return self._cache[clean_text]

        self.conversation_history.append({'user': text, 'assistant': None})
        response = None

        if self._groq_api_key:
            response = self._get_groq_response(text)
            if response:
                print("Using Groq Cloud AI")

        if not response and self.ollama_available:
            response = self._get_ollama_response(text)
            if response:
                print("Using Local AI (Ollama)")

        if not response and self.duckduckgo_available and self._needs_live_search(clean_text):
            response = self._get_duckduckgo_response(text)
            if response:
                print("Using DuckDuckGo Search")

        info_keywords = ('who', 'what', 'where', 'when', 'how', 'tell me', 'search', 'find')
        if not response and any(clean_text.startswith(kw) for kw in info_keywords):
            response = self._get_wikipedia_summary(clean_text)
            if response:
                print("Using Wikipedia Fallback")

        if not response:
            if not self._groq_api_key and not self.ollama_available:
                response = "I'm having trouble connecting to my AI models. Please check your internet or Ollama connection."
            else:
                response = "I couldn't find a good answer for that. Can you try rephrasing?"

        if response:
            self._cache[clean_text] = response

        self.conversation_history[-1]['assistant'] = response
        if len(self.conversation_history) > self.max_history:
            self.conversation_history.pop(0)
        return response
