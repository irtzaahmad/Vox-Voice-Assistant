"""
Vox Professional v5.0 — Advanced AI Desktop Assistant
==================================================
UPGRADED:
  - Wake Word: Picovoice Porcupine
  - STT: Faster-Whisper
  - Brain: Ollama (Llama 3.2)
  - TTS: Coqui TTS
  - VAD: WebRTC VAD
"""
import sys, os, threading, time, subprocess, re, random, socket
from datetime import datetime

# ── PyAudio Monkeypatch ────────────────────────────
try:
    import pyaudiowpatch as pyaudio
    sys.modules['pyaudio'] = pyaudio
except ImportError:
    try:
        import pyaudio
    except ImportError:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import config
from core.nlp_engine      import NLPEngine, Intent
from core.always_on_voice import AlwaysOnVoiceEngine
from core.speaker         import get_speaker
from core.brain           import VoxBrain

# JARVIS Features
from modules.memory          import ContextMemory
from modules.routine_manager import RoutineManager
from modules.automation      import PCAutomation
from modules.study           import StudyAssistant

# Optional modules
try:
    from modules.database        import VoxDatabase
    from modules.face_module     import FaceModule
    from modules.whatsapp_module import WhatsAppModule
except ImportError:
    VoxDatabase = WhatsAppModule = FaceModule = None

try:
    from modules.web_module    import WebController
    from modules.file_module   import FileManager
    from modules.system_module import SystemController
    from modules.app_launcher  import AppLauncher
    from modules.downloader    import DownloadManager
    FULL = True
except ImportError as _ie:
    print(f"ℹ️  Optional modules: {_ie}")
    FULL = False

try:
    from gui.main_window import VoxWindow
    HAS_GUI = True
except ImportError:
    HAS_GUI = False


class Vox:
    def __init__(self):
        print("Vox Professional v5.0 starting…")
        self.config   = config
        self.db = VoxDatabase() if VoxDatabase else None
        self.nlp      = NLPEngine()
        self.speaker  = get_speaker()
        self.brain    = VoxBrain()
        
        # Initialize JARVIS modules
        self.memory   = ContextMemory()
        self.routine  = RoutineManager()
        self.automation = PCAutomation()
        self.study    = StudyAssistant()
        
        self.whatsapp = WhatsAppModule() if WhatsAppModule else None
        self.face     = FaceModule(self.db, config.FACES_DIR) if (FaceModule and self.db) else None
        self.current_user = None
        self.gui          = None

        if FULL:
            self.web        = WebController()
            if self.db: self.web.set_db(self.db)
            self.files      = FileManager()
            self.system     = SystemController()
            self.apps       = AppLauncher()
            self.downloader = DownloadManager()
        
        self.voice_engine = AlwaysOnVoiceEngine(self)
        print("✅ Vox Professional ready")

    def set_user(self, user: dict):
        self.current_user = user

    def speak(self, text: str):
        if text: self.speaker.speak(text)

    def process_command(self, command: str) -> str:
        if not command: return "I didn't catch that."
        t0  = time.monotonic()
        uid = (self.current_user or {}).get('id', 0)
        
        # 1. Try NLP Intent detection
        res = self.nlp.process(command)
        intent, ent = res['intent'], res['entities']
        
        if intent != Intent.UNKNOWN:
            print(f"  intent={intent.value}  ent={ent}")
            response = self._run(intent, ent, command)
        else:
            # 2. Fallback to Brain (Ollama)
            print("  intent=UNKNOWN -> Using AI Brain")
            response = self.brain.generate_response(command)

        ms = int((time.monotonic() - t0) * 1000)
        if self.db:
            self.db.add_log(command, intent.value if intent else "AI", response, uid, ms)
        
        # JARVIS: Record routine
        if self.routine:
            self.routine.record_command(command)
        
        self.speak(response)
        return response

    def _run(self, intent: Intent, ent: dict, raw: str) -> str:
        def _open(url: str):
            try: subprocess.Popen(f'start "" "{url}"', shell=True)
            except Exception:
                import webbrowser
                webbrowser.open(url)

        import urllib.parse
        name = ((self.current_user or {}).get('full_name') or 'sir').split()[0]

        # JARVIS: MEMORY
        if intent == Intent.MEMORY_SAVE:
            if hasattr(self, 'memory'):
                return self.memory.save_fact(ent.get('key',''), ent.get('value',''))
        if intent == Intent.MEMORY_QUERY:
            if hasattr(self, 'memory'):
                return self.memory.get_fact(ent.get('key',''))

        # JARVIS: ROUTINE
        if intent == Intent.ROUTINE_SUGGEST:
            if hasattr(self, 'routine'):
                return self.routine.suggest_routine()

        # JARVIS: STUDY
        if intent == Intent.STUDY_QUIZ:
            if hasattr(self, 'study'):
                return self.study.run_quiz(self)

        # JARVIS: AUTOMATION
        if intent == Intent.SYSTEM_CLEAN_TEMP:
            if hasattr(self, 'automation'):
                return self.automation.clean_temp_files()
        if intent == Intent.FOLDER_OPEN:
            if hasattr(self, 'automation'):
                return self.automation.open_folder(ent.get('folder',''))

        # GREETING
        if intent == Intent.GREETING:
            h = datetime.now().hour
            g = "Good morning" if h < 12 else "Good afternoon" if h < 18 else "Good evening"
            msg = f"{g} {name}! How can I help you today?"; return msg

        # WHATSAPP
        if intent == Intent.WHATSAPP_SEND:
            contact = ent.get('contact','').strip()
            msg     = ent.get('message','').strip()
            if not contact or not msg:
                match = re.search(r"to (.*) saying (.*)", raw.lower())
                if match: contact, msg = match.groups()
                else:
                    match = re.search(r"message to (.*?) (.*)", raw.lower())
                    if match: contact, msg = match.groups()
            if contact and msg and self.whatsapp:
                ok, r = self.whatsapp.send(contact.strip(), msg.strip())
                return r
            return "Say: send WhatsApp to [number/name] saying [message]"

        if intent == Intent.WHATSAPP_OPEN:
            if self.whatsapp: self.whatsapp.open()
            return "WhatsApp opened."

        # YOUTUBE
        if intent == Intent.YOUTUBE_PLAY:
            q = ent.get('search_query','').strip()
            if not q: return "What should I play?"
            
            if config.YOUTUBE_AUTO_PLAY and hasattr(self, 'web'):
                # Play the first result directly
                threading.Thread(target=self.web.play_youtube, args=(q,), daemon=True).start()
                return f"Playing '{q}' on YouTube."
            
            _open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(q)}")
            return f"Searching YouTube for '{q}'."

        if intent == Intent.YOUTUBE_SEARCH:
            q = ent.get('search_query','').strip() or raw
            _open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(q)}")
            return f"YouTube results for '{q}'."

        # WEB SEARCH
        if intent == Intent.WEB_SEARCH:
            q = ent.get('query', raw).strip()
            if self.web: self.web.search(q)
            else: _open(f"https://www.google.com/search?q={urllib.parse.quote(q)}")
            return f"Searching for '{q}'."

        # OPEN WEBSITE
        if intent == Intent.WEB_OPEN:
            site = ent.get('website','').strip()
            if site:
                url = site if site.startswith('http') else f"https://{site}"
                msg = f"Opening {site}."; _open(url); return msg
            return "Which website?"

        # APP
        if intent == Intent.APP_LAUNCH:
            app = ent.get('app_name','').strip()
            if app:
                if self.apps:
                    ok, msg = self.apps.open_app(app); return msg
                subprocess.Popen(app, shell=True)
                return f"Opening {app}."
            return "Which application?"

        if intent == Intent.APP_CLOSE:
            app = ent.get('app_name','').strip()
            if app:
                if self.apps: return self.apps.close_app(app)[1]
                subprocess.run(f"taskkill /f /im {app}.exe", shell=True)
                return f"Closed {app}."
            return "Which application?"

        # SCREENSHOT
        if intent == Intent.SYSTEM_SCREENSHOT:
            if self.system: return self.system.take_screenshot()[1]
            try:
                import pyautogui
                fn   = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                path = os.path.join(config.SCREENSHOTS_DIR, fn)
                pyautogui.screenshot(path)
                return f"Screenshot saved: {fn}"
            except Exception as e:
                return f"Screenshot failed: {e}"

        # VOLUME
        if intent == Intent.SYSTEM_VOLUME:
            act = ent.get('action','')
            lvl = ent.get('level')
            if self.system:
                if lvl is not None: return self.system.set_volume(lvl)
                if act == 'increase': return self.system.volume_up()
                if act == 'decrease': return self.system.volume_down()
                if act == 'mute':   return self.system.mute()
                if act == 'unmute': return self.system.unmute()
            return "Volume adjusted."

        # SYSTEM INFO
        if intent == Intent.SYSTEM_INFO:
            try:
                import psutil
                cpu  = psutil.cpu_percent(interval=0.5)
                ram  = psutil.virtual_memory()
                info = f"CPU {cpu:.0f} percent, RAM {ram.percent:.0f} percent used"
                bat  = psutil.sensors_battery()
                if bat:
                    info += f", battery {bat.percent:.0f} percent"
                    if bat.power_plugged: info += " charging"
                return info
            except Exception:
                return "System info unavailable."

        # POWER
        if intent == Intent.SYSTEM_SHUTDOWN:
            rl = raw.lower()
            if 'abort' in rl or 'cancel' in rl:
                subprocess.run("shutdown /a", shell=True)
                return "Shutdown cancelled."
            if 'restart' in rl or 'reboot' in rl:
                subprocess.run("shutdown /r /t 10", shell=True)
                return "Restarting in 10 seconds."
            if 'sleep' in rl:
                subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
                return "Sleeping."
            subprocess.run("shutdown /s /t 10", shell=True)
            return "Shutting down in 10 seconds."

        # TIME / DATE
        if intent == Intent.TIME_QUERY:
            return f"It's {datetime.now().strftime('%I:%M %p')}."
        if intent == Intent.DATE_QUERY:
            return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."

        # WEATHER
        if intent == Intent.WEATHER_QUERY:
            city = (ent.get('city') or 'today').strip()
            _open(f"https://www.google.com/search?q=weather+{urllib.parse.quote(city)}")
            return f"Showing weather for {city}."

        # JOKE
        if intent == Intent.JOKE:
            jokes = [
                "Why don't scientists trust atoms? Because they make up everything!",
                "Why do programmers prefer dark mode? Because light attracts bugs!",
                "Why did the developer go broke? He used up all his cache!",
                "I asked my PC to play music. It said: Sorry, I'm on Windows!",
            ]
            return random.choice(jokes)

        # FILES
        if intent == Intent.FILE_OPEN:
            fn = ent.get('filename','').strip()
            if fn and self.files: return self.files.open_file(fn)
            return "Which file?"

        if intent == Intent.FILE_SEARCH:
            fn = ent.get('filename','').strip()
            if not fn:
                fn = raw.lower().replace("find file", "").replace("search for file", "").replace("find", "").strip()
            if fn and self.files: return self.files.search_file(fn)
            return "What file should I search for?"

        if intent == Intent.FILE_CREATE:
            n = ent.get('name','').strip()
            if n:
                if self.files: return self.files.create_folder(n)[1]
                path = os.path.join(os.path.expanduser("~"), "Desktop", n)
                os.makedirs(path, exist_ok=True)
                return f"Folder '{n}' created."
            return "What should I name it?"

        if intent == Intent.FILE_DELETE:
            fn = ent.get('filename','').strip()
            if fn:
                if self.files: return self.files.delete_file(fn)[1]
                return f"I couldn't find a file or folder named {fn}."
            return "What should I delete?"

        if intent == Intent.FILE_MOVE:
            src = ent.get('source','').strip()
            dst = ent.get('destination','').strip()
            if src and dst:
                if self.files: return self.files.move_file(src, dst)[1]
                return f"I couldn't move {src}."
            return "What should I move, and where to?"

        # DEFAULT → Fallback to Brain
        return self.brain.generate_response(raw)

    def start_voice(self):
        if self.voice_engine: self.voice_engine.start()

    def start_gui(self):
        if not HAS_GUI:
            self.start_voice()
            try:
                while True: time.sleep(10)
            except KeyboardInterrupt: self.shutdown()
            return
        self.gui = VoxWindow(Vox=self)
        threading.Thread(target=lambda: (time.sleep(1.5), self.start_voice()), daemon=True).start()
        self.gui.run()

    def shutdown(self):
        if self.voice_engine: self.voice_engine.stop()
        if self.gui: self.gui.close()
        sys.exit(0)

if __name__ == "__main__":
    vox_app = Vox()
    
    # JARVIS: Text Testing Mode
    if "--text" in sys.argv:
        print("\n" + "="*40)
        print(" 🧪 TEXT MODE ACTIVATED (JARVIS)")
        print(" Type commands below. Type 'exit' to quit.")
        print("="*40 + "\n")
        while True:
            try:
                cmd = input("You: ")
                if not cmd: continue
                if cmd.lower() in ['exit', 'quit', 'bye']: break
                vox_app.process_command(cmd)
            except KeyboardInterrupt: break
        vox_app.shutdown()

    elif "--service" in sys.argv or "--voice-test" in sys.argv:
        vox_app.start_voice()
        try:
            while True: time.sleep(10)
        except KeyboardInterrupt: vox_app.shutdown()
    else:
        vox_app.start_gui()
