"""
Vox Web Module - Professional Edition (v1.2)
Handles browser automation, robust web scraping, and link caching via Database
"""
import webbrowser
import urllib.parse
import re
import threading
import json
from typing import Optional, Tuple
import config

class WebController:
    def __init__(self):
        self.common_websites = {
            'google': 'https://www.google.com',
            'youtube': 'https://www.youtube.com',
            'facebook': 'https://www.facebook.com',
            'instagram': 'https://www.instagram.com',
            'twitter': 'https://www.twitter.com',
            'github': 'https://www.github.com',
            'linkedin': 'https://www.linkedin.com',
            'reddit': 'https://www.reddit.com',
            'gmail': 'https://mail.google.com',
            'maps': 'https://maps.google.com',
            'weather': 'https://www.google.com/search?q=weather',
        }
        self.db = None

    def set_db(self, db_instance):
        self.db = db_instance

    def open_website(self, website: str) -> bool:
        try:
            website = website.lower().strip()
            for prefix in ['open ', 'go to ', 'visit ', 'website ']:
                if website.startswith(prefix):
                    website = website[len(prefix):].strip()

            if website in self.common_websites:
                webbrowser.open(self.common_websites[website])
                return True

            if website.startswith(('http://', 'https://')) or ('.' in website and ' ' not in website):
                url = website if website.startswith('http') else f"https://{website}"
                webbrowser.open(url)
                return True

            return self.search(website)
        except Exception as e:
            print(f"❌ Error opening website: {e}")
            return False

    def search(self, query: str) -> bool:
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.google.com/search?q={encoded_query}"
            
            print(f"🌐 Searching Google for: {query}")
            webbrowser.open(url)
            
            # Start background scraping
            threading.Thread(target=self._scrape_and_store_results, args=(query,), daemon=True).start()
            return True
        except Exception as e:
            print(f"❌ Search error: {e}")
            return False

    def _scrape_and_store_results(self, query: str):
        """Advanced Scraper to find real URLs from Google Results"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num=15"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                links = []
                
                # Method 1: Find all result containers
                for result in soup.select('.tF2Cxc'):
                    link = result.select_one('.yuRUbf a')['href']
                    if link and link.startswith('http'):
                        links.append(link)
                
                # Method 2 (Fallback): Find all links that look like results
                if not links:
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        if 'google.com' not in href and href.startswith('http'):
                            # Filter out social links if needed or keep top ones
                            if href not in links:
                                links.append(href)
                
                if links and self.db:
                    self.db.set_context("last_search_links", json.dumps(links[:10]))
                    print(f"✅ Professionally cached {len(links[:10])} results in Database.")
            else:
                print(f"⚠️ Google block or error: Status {response.status_code}")
        except Exception as e:
            print(f"⚠️ Scraping failed: {e}")

    def open_index(self, index_text: str) -> Tuple[bool, str]:
        try:
            if not self.db:
                return False, "Database connection missing."

            links_json = self.db.get_context("last_search_links")
            if not links_json:
                return False, "Search results not found in memory."
            
            links = json.loads(links_json)
            
            # Map words to numbers
            mapping = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "1st": 1, "2nd": 2, "3rd": 3}
            idx = None
            
            # Extract number from string like "1st" or "first"
            clean_idx = str(index_text).lower().strip()
            if clean_idx.isdigit():
                idx = int(clean_idx)
            elif clean_idx in mapping:
                idx = mapping[clean_idx]
            else:
                # Try regex to find digit
                match = re.search(r'(\d+)', clean_idx)
                if match:
                    idx = int(match.group(1))

            if idx and 1 <= idx <= len(links):
                target = links[idx-1]
                print(f"🌐 Opening Result #{idx}: {target}")
                webbrowser.open(target)
                return True, f"Opening result number {idx}"
            
            return False, f"I have {len(links)} results. You asked for {index_text}."
        except Exception as e:
            print(f"❌ Open Index Error: {e}")
            return False, f"Error opening site: {str(e)}"

    def play_youtube(self, query: str) -> bool:
        try:
            import yt_dlp
            ydl_opts = {'quiet': True, 'extract_flat': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                if 'entries' in info and info['entries']:
                    url = info['entries'][0]['url']
                    if not url.startswith('http'): url = f"https://www.youtube.com/watch?v={url}"
                    webbrowser.open(url)
                    return True
            webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")
            return True
        except:
            return False


