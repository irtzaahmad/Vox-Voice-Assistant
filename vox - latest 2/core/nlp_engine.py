"""
Vox NLP Engine v3.0
Fast regex-based intent classification — no external NLP library required.
25+ intents covering all common tasks.
"""
import re
from enum import Enum
from typing import Dict, Any


class Intent(Enum):
    GREETING        = "greeting"
    WEB_SEARCH      = "web_search"
    WEB_OPEN        = "web_open"
    WEB_OPEN_INDEX  = "web_open_index"
    YOUTUBE_PLAY    = "youtube_play"
    YOUTUBE_SEARCH  = "youtube_search"
    APP_LAUNCH      = "app_launch"
    APP_CLOSE       = "app_close"
    APP_TYPE        = "app_type"          # "type hello in notepad"
    SYSTEM_SCREENSHOT = "system_screenshot"
    SYSTEM_VOLUME   = "system_volume"
    SYSTEM_SHUTDOWN = "system_shutdown"
    SYSTEM_INFO     = "system_info"
    TIME_QUERY      = "time_query"
    DATE_QUERY      = "date_query"
    FILE_OPEN       = "file_open"
    FILE_SEARCH     = "file_search"
    FILE_CREATE     = "file_create"
    FILE_DELETE     = "file_delete"
    FILE_MOVE       = "file_move"
    WHATSAPP_SEND   = "whatsapp_send"
    WHATSAPP_OPEN   = "whatsapp_open"
    DOWNLOAD_FILE   = "download_file"
    WEATHER_QUERY   = "weather_query"
    CALCULATOR      = "calculator"
    REMINDER_SET    = "reminder_set"
    NEWS_QUERY      = "news_query"
    TRANSLATE       = "translate"
    JOKE            = "joke"
    MEMORY_SAVE     = "memory_save"
    MEMORY_QUERY    = "memory_query"
    ROUTINE_SUGGEST = "routine_suggest"
    SYSTEM_CLEAN_TEMP = "system_clean_temp"
    FOLDER_OPEN     = "folder_open"
    STUDY_QUIZ      = "study_quiz"
    AI_QUESTION     = "ai_question"
    UNKNOWN         = "unknown"


# ─────────────────────────────────────────────────────────────────
#  Pattern table  (intent, compiled_pattern, group_map)
#  group_map: dict of entity_name -> regex group name
# ─────────────────────────────────────────────────────────────────
_RAW = [
    # ── MEMORY ──
    (Intent.MEMORY_SAVE,
     r"(?:remember|save|keep\s+in\s+mind)\s+(?:that\s+)?(?P<key>.+?)\s+(?:is|are|was|were|on|at)\s+(?P<val>.+)",
     {'key': 'key', 'val': 'value'}),
    (Intent.MEMORY_QUERY,
     r"(?:do\s+you\s+remember|what\s+did\s+i\s+say\s+about|what\s+is\s+my|when\s+is\s+my|where\s+is\s+my|tell\s+me\s+about\s+my)\s+(?P<key>.+)",
     {'key': 'key'}),

    # ── ROUTINE ──
    (Intent.ROUTINE_SUGGEST,
     r"(?:what\s+should\s+i\s+do|suggest\s+a\s+routine|my\s+routine|anything\s+for\s+me|what\s+next)", {}),

    # ── STUDY ──
    (Intent.STUDY_QUIZ,
     r"(?:start\s+a\s+quiz|ask\s+me\s+a\s+question|study\s+mode|quiz\s+me|test\s+me)", {}),

    # ── PC AUTOMATION ──
    (Intent.SYSTEM_CLEAN_TEMP,
     r"(?:clean|clear|empty|delete)\s+(?:the\s+)?(?:temp|temporary)\s+(?:files|folder|junk)", {}),
    (Intent.FOLDER_OPEN,
     r"(?:open|show|go\s+to)\s+(?:my\s+)?(?P<f>downloads|documents|desktop|pictures|music|videos|downloads\s+folder|documents\s+folder|desktop\s+folder)\s*(?:folder)?",
     {'f': 'folder'}),

    # ── GREETINGS ──
    (Intent.GREETING, r"^(hey|hi|hello|good\s+(?:morning|afternoon|evening|night)|salam|assalam|howdy|what'?s?\s+up)[,\s]*(Vox)?$", {}),

    # ── WHATSAPP ──
    (Intent.WHATSAPP_SEND,
     r"(?:send|write|whatsapp|message|msg|text)\s+(?:a\s+)?(?:message\s+)?(?:to\s+)?(?P<contact>[\+\d\s\w]{1,30}?)\s+(?:saying?|say|that|:|-)\s*(?P<message>.+)",
     {'contact': 'contact', 'message': 'message'}),
    (Intent.WHATSAPP_OPEN,
     r"(?:open|launch|go\s+to)\s+whatsapp", {}),

    # ── YOUTUBE PLAY ("play X on youtube" / "play X") ──
    (Intent.YOUTUBE_PLAY,
     r"(?:play|start\s+playing)\s+(?P<q>.+?)(?:\s+on\s+youtube)?$",
     {'q': 'search_query'}),

    # ── YOUTUBE SEARCH ("X on youtube" / "search youtube for X") ──
    (Intent.YOUTUBE_SEARCH,
     r"(?:(?P<q1>.+?)\s+on\s+youtube|(?:search|find)\s+(?:youtube|on\s+youtube)\s+(?:for\s+)?(?P<q2>.+))",
     {}),

    # ── WEB SEARCH ──
    (Intent.WEB_SEARCH,
     r"(?:search|google|look\s+up|find|browse)\s+(?:for\s+)?(?P<q>.+)",
     {'q': 'query'}),

    # ── OPEN WEBSITE ──
    (Intent.WEB_OPEN,
     r"(?:open|go\s+to|launch|visit|load)\s+(?:website\s+)?(?P<site>[\w\-]+(?:\.[\w\-]+)*(?:\.[a-z]{2,})|youtube|facebook|instagram|twitter|google|gmail|github|reddit|amazon|netflix|spotify|linkedin|whatsapp|wikipedia|stackoverflow|tiktok|pinterest|discord)",
     {'site': 'website'}),

    # ── OPEN BY INDEX ──
    (Intent.WEB_OPEN_INDEX,
     r"open\s+(?:the\s+)?(?P<n>1st|2nd|3rd|4th|5th|first|second|third|fourth|fifth)\s+(?:result|link|site|one)",
     {'n': 'index'}),

    # ── TYPE COMMAND ──
    (Intent.APP_TYPE,
     r"type\s+(?P<text>.+?)(?:\s+in\s+(?P<app>.+))?$",
     {'text': 'text', 'app': 'app'}),

    # ── APPS ──
    (Intent.APP_LAUNCH,
     r"(?:open|launch|start|run)\s+(?P<app>.+)",
     {'app': 'app_name'}),
    (Intent.APP_CLOSE,
     r"(?:close|quit|exit|kill|stop)\s+(?P<app>.+)",
     {'app': 'app_name'}),

    # ── SCREENSHOT ──
    (Intent.SYSTEM_SCREENSHOT,
     r"(?:take|capture|snap)\s+(?:a\s+)?(?:screenshot|screen\s*shot|screen)", {}),

    # ── VOLUME ──
    (Intent.SYSTEM_VOLUME,
     r"(?:(?P<act>increase|raise|turn\s+up|boost|decrease|lower|turn\s+down|reduce|mute|unmute|silence)\s+(?:the\s+)?(?:volume|sound|audio)?|volume\s+(?P<dir>up|down)|set\s+volume\s+to\s+(?P<lvl>\d+))",
     {}),

    # ── POWER ──
    (Intent.SYSTEM_SHUTDOWN,
     r"(?:shutdown|shut\s+down|restart|reboot|sleep|hibernate|abort\s+shutdown|cancel\s+shutdown)\s*(?:the\s+)?(?:computer|pc|system|laptop)?",
     {}),

    # ── SYSTEM INFO ──
    (Intent.SYSTEM_INFO,
     r"(?:(?:how\s+much\s+)?(?:battery|cpu|ram|memory|disk\s+space)|system\s+info(?:rmation)?|what'?s?\s+my\s+(?:battery|cpu|ram))",
     {}),

    # ── TIME ──
    (Intent.TIME_QUERY,
     r"(?:what(?:'?s|\s+is)\s+(?:the\s+)?(?:current\s+)?time|what\s+time\s+is\s+it|tell\s+me\s+the\s+time|current\s+time)",
     {}),

    # ── DATE ──
    (Intent.DATE_QUERY,
     r"(?:what(?:'?s|\s+is)\s+(?:today'?s?\s+)?date|what\s+day\s+is\s+it|today'?s?\s+date|current\s+date)",
     {}),

    # ── FILES ──
    (Intent.FILE_OPEN,
     r"(?:open|show)\s+(?:file\s+)?(?P<fn>[\w\s\-\.]+\.\w{2,5})",
     {'fn': 'filename'}),
    (Intent.FILE_SEARCH,
     r"(?:search\s+for|find|locate|where\s+is)\s+(?:file\s+)?(?P<fn>.+)",
     {'fn': 'filename'}),
    (Intent.FILE_CREATE,
     r"(?:create|make|new)\s+(?:a\s+)?(?:folder|directory|file)\s+(?:named?\s+|called?\s+)?(?P<n>.+)",
     {'n': 'name'}),
    (Intent.FILE_DELETE,
     r"(?:delete|remove|trash|erase)\s+(?:file\s+|folder\s+|directory\s+)?(?P<fn>.+)",
     {'fn': 'filename'}),
    (Intent.FILE_MOVE,
     r"(?:move|transfer)\s+(?P<src>.+?)\s+(?:to|into)\s+(?P<dst>.+)",
     {'src': 'source', 'dst': 'destination'}),

    # ── DOWNLOAD ──
    (Intent.DOWNLOAD_FILE,
     r"download\s+(?:video\s+|audio\s+|file\s+)?(?:from\s+)?(?P<url>https?://\S+)",
     {'url': 'url'}),

    # ── WEATHER ──
    (Intent.WEATHER_QUERY,
     r"(?:weather|temperature|forecast)(?:\s+in\s+|\s+at\s+|\s+for\s+|\s+)?(?P<city>[a-zA-Z\s]{2,})?",
     {'city': 'city'}),

    # ── CALCULATOR ──
    (Intent.CALCULATOR,
     r"(?:calculate|compute|what\s+is|solve|eval)\s+(?P<expr>[\d\s\+\-\*\/\(\)\.\^%]+)",
     {'expr': 'expression'}),

    # ── REMINDER ──
    (Intent.REMINDER_SET,
     r"(?:set|create|add)\s+(?:a\s+)?reminder\s+(?:for\s+|to\s+)?(?P<task>.+?)\s+(?:at|in)\s+(?P<time>.+)",
     {'task': 'task', 'time': 'time'}),

    # ── NEWS ──
    (Intent.NEWS_QUERY,
     r"(?:(?:latest|today'?s?|current)\s+news|news\s+(?:about\s+|on\s+)?(?P<topic>.+)?|what'?s?\s+(?:happening|going\s+on))",
     {'topic': 'topic'}),

    # ── TRANSLATE ──
    (Intent.TRANSLATE,
     r"translate\s+['\"]?(?P<text>.+?)['\"]?\s+(?:to|into|in)\s+(?P<lang>\w+)",
     {'text': 'text', 'lang': 'lang'}),

    # ── JOKE ──
    (Intent.JOKE,
     r"(?:tell\s+(?:me\s+)?a?\s*joke|make\s+me\s+laugh|say\s+something\s+funny|joke)",
     {}),
]

# Compile all patterns
_PATTERNS = []
for _intent, _pat, _gmap in _RAW:
    try:
        _PATTERNS.append((_intent, re.compile(_pat, re.IGNORECASE | re.UNICODE), _gmap))
    except re.error as _e:
        print(f"⚠️  NLP pattern error ({_intent}): {_e}")


class NLPEngine:
    def __init__(self):
        self._ordinals = {
            '1st': 1, 'first': 1, '2nd': 2, 'second': 2,
            '3rd': 3, 'third': 3, '4th': 4, 'fourth': 4,
            '5th': 5, 'fifth': 5,
        }
        self._sites = {
            'youtube':       'youtube.com',
            'facebook':      'facebook.com',
            'instagram':     'instagram.com',
            'twitter':       'twitter.com',
            'google':        'google.com',
            'gmail':         'gmail.com',
            'github':        'github.com',
            'reddit':        'reddit.com',
            'amazon':        'amazon.com',
            'netflix':       'netflix.com',
            'spotify':       'spotify.com',
            'linkedin':      'linkedin.com',
            'whatsapp':      'web.whatsapp.com',
            'wikipedia':     'wikipedia.org',
            'stackoverflow': 'stackoverflow.com',
            'tiktok':        'tiktok.com',
            'pinterest':     'pinterest.com',
            'discord':       'discord.com',
        }
        print("✅ NLP Engine v3.0 ready")

    def process(self, text: str) -> Dict[str, Any]:
        if not text:
            return {'intent': Intent.UNKNOWN, 'entities': {}, 'raw': text}

        clean = text.strip()

        for intent, pat, gmap in _PATTERNS:
            m = pat.search(clean)
            if m:
                entities = self._extract(intent, m, gmap, clean)
                return {'intent': intent, 'entities': entities, 'raw': text}

        # fallback → AI question
        return {'intent': Intent.AI_QUESTION, 'entities': {'query': text}, 'raw': text}

    def _extract(self, intent, match, gmap, raw) -> dict:
        ent = {}

        # named groups from match
        try:
            gd = match.groupdict()
            for k, v in gd.items():
                if v is not None:
                    mapped = gmap.get(k, k)
                    ent[mapped] = v.strip()
        except Exception:
            pass

        # ── intent-specific fixups ──
        if intent == Intent.YOUTUBE_SEARCH:
            q = ent.get('q1') or ent.get('q2') or ''
            ent['search_query'] = q.strip()

        elif intent == Intent.WEB_OPEN:
            site = ent.get('website', '').lower().strip()
            # map short names to full domains
            ent['website'] = self._sites.get(site, site)

        elif intent == Intent.WEB_OPEN_INDEX:
            n = ent.get('index', '').lower().strip()
            ent['index'] = self._ordinals.get(n, 1)

        elif intent == Intent.SYSTEM_VOLUME:
            raw_l = raw.lower()
            act = ent.get('act', '').lower()
            if 'up' in raw_l or any(w in act for w in ('increase','raise','boost','turn up')):
                ent['action'] = 'increase'
            elif 'down' in raw_l or any(w in act for w in ('decrease','lower','reduce','turn down')):
                ent['action'] = 'decrease'
            elif 'mute' in raw_l and 'unmute' not in raw_l:
                ent['action'] = 'mute'
            elif 'unmute' in raw_l or 'silence' not in raw_l and 'unmute' in raw_l:
                ent['action'] = 'unmute'
            lvl = ent.get('lvl')
            if lvl:
                try:
                    ent['level'] = int(lvl)
                except Exception:
                    pass

        elif intent == Intent.WHATSAPP_SEND:
            # clean trailing words from contact
            contact = ent.get('contact', '').strip()
            contact = re.sub(r'\s+(saying?|say|that|message|msg)$', '', contact, flags=re.I)
            
            # Clean leading wake words or command words that might have been caught
            contact = re.sub(r'^(hey\s+)?(vox|havoc|box|fox|folks|vox\s+)?(send\s+)?(whatsapp\s+)?(message\s+)?(to\s+)?', '', contact, flags=re.I).strip()
            
            ent['contact'] = contact

        return ent
