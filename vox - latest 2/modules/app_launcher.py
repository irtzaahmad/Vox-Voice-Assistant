"""
Vox Application Launcher Module
Handles opening and closing applications
"""
import subprocess
import os
import shutil
from typing import Tuple, Optional
import config

class AppLauncher:
    def __init__(self):
        self.common_apps = {
            # Browsers
            'chrome': ['chrome', 'google chrome', 'google-chrome', 'chrome.exe'],
            'firefox': ['firefox', 'firefox.exe', 'mozilla firefox'],
            'edge': ['edge', 'microsoft edge', 'msedge', 'msedge.exe'],
            'opera': ['opera', 'opera.exe'],
            'brave': ['brave', 'brave.exe'],

            # Office
            'notepad': ['notepad', 'notepad.exe'],
            'word': ['winword', 'word', 'microsoft word', 'winword.exe'],
            'excel': ['excel', 'microsoft excel', 'excel.exe'],
            'powerpoint': ['powerpnt', 'powerpoint', 'microsoft powerpoint', 'powerpnt.exe'],
            'outlook': ['outlook', 'microsoft outlook', 'outlook.exe'],

            # Media
            'vlc': ['vlc', 'vlc media player', 'vlc.exe'],
            'spotify': ['spotify', 'spotify.exe'],
            'itunes': ['itunes', 'itunes.exe'],
            'windows media player': ['wmplayer', 'windows media player', 'wmplayer.exe'],
            'photos': ['ms-photos:', 'photos', 'microsoft photos'],

            # System
            'calculator': ['calc', 'calculator', 'calc.exe'],
            'paint': ['mspaint', 'paint', 'microsoft paint', 'mspaint.exe'],
            'settings': ['ms-settings:', 'settings', 'windows settings'],
            'file explorer': ['explorer', 'file explorer', 'windows explorer'],
            'task manager': ['taskmgr', 'task manager', 'taskmgr.exe'],
            'control panel': ['control', 'control panel'],
            'command prompt': ['cmd', 'command prompt', 'cmd.exe'],
            'powershell': ['powershell', 'powershell.exe', 'windows powershell'],
            'terminal': ['wt', 'windows terminal', 'wt.exe'],

            # Development
            'visual studio code': ['code', 'vscode', 'visual studio code', 'code.exe'],
            'visual studio': ['devenv', 'visual studio', 'devenv.exe'],
            'notepad++': ['notepad++', 'notepad++.exe'],
            'pycharm': ['pycharm', 'pycharm.exe'],
            'sublime text': ['sublime_text', 'sublime text', 'subl.exe'],

            # Communication
            'discord': ['discord', 'discord.exe'],
            'teams': ['teams', 'microsoft teams', 'teams.exe'],
            'zoom': ['zoom', 'zoom.exe'],
            'skype': ['skype', 'skype.exe'],
            'whatsapp': ['whatsapp', 'whatsapp.exe'],
            'telegram': ['telegram', 'telegram.exe'],

            # Utilities
            'snipping tool': ['snippingtool', 'snipping tool', 'snippingtool.exe'],
            'sticky notes': ['stikynot', 'sticky notes', 'stikynot.exe'],
            'calendar': ['outlookcal:', 'calendar', 'windows calendar'],
            'mail': ['outlookmail:', 'mail', 'windows mail'],
            'store': ['ms-windows-store:', 'microsoft store', 'windows store'],
            'xbox': ['xbox', 'xbox.exe'],
        }

        self.running_processes = {}

    def _find_executable(self, app_name: str) -> Optional[str]:
        """Professional fuzzy-matching executable finder."""
        query = app_name.lower().strip()
        
        # 1. Fuzzy match aliases
        match_alias = None
        for key, aliases in self.common_apps.items():
            if query in key or any(query in a for a in aliases):
                match_alias = aliases[0] # Use primary alias
                break
        
        target = match_alias or query
        
        # 2. Check system PATH
        exe_path = shutil.which(target)
        if not exe_path:
            exe_path = shutil.which(f"{target}.exe")
            
        if exe_path: return exe_path

        # 3. Check common Windows installation paths
        if os.name == 'nt':
            search_paths = [
                os.path.expandvars(r"%ProgramFiles%"),
                os.path.expandvars(r"%ProgramFiles(x86)%"),
                os.path.expandvars(r"%LocalAppData%\Programs"),
                r"C:\Windows\System32",
            ]
            
            for base in search_paths:
                if not os.path.exists(base): continue
                # Look for .exe in base or one level deep
                for root, dirs, files in os.walk(base):
                    # Only check first level for speed
                    if root.count(os.sep) - base.count(os.sep) > 1:
                        break
                    for f in files:
                        if f.lower() == f"{target}.exe" or f.lower() == f"{target}":
                            return os.path.join(root, f)
        return None

    def open_app(self, app_name: str) -> Tuple[bool, str]:
        """Professional application opener using os.startfile (Windows native)."""
        try:
            # Clean name
            target = app_name.lower().replace("open", "").replace("launch", "").strip()
            
            # Find path
            exe_path = self._find_executable(target)

            if exe_path:
                os.startfile(exe_path)
                return True, f"Opening {target.capitalize()}"
            
            # Fallback: try direct command
            try:
                os.startfile(target)
                return True, f"Opening {target}"
            except:
                return False, f"I couldn't find the application: {target}"

        except Exception as e:
            return False, f"Error opening {app_name}: {str(e)}"

    def close_app(self, app_name: str) -> Tuple[bool, str]:
        """Close an application by name"""
        try:
            import psutil

            # Handle common typos or variations
            app_name_lower = app_name.lower().strip()
            if 'chrome' in app_name_lower:
                app_name_lower = 'chrome'
            
            closed = False
            processes_killed = 0

            # Try to find and kill process by name
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    proc_name = proc.info['name'].lower()

                    # Check if process name matches
                    if app_name_lower in proc_name or proc_name in app_name_lower:
                        try:
                            proc.terminate()
                            processes_killed += 1
                        except:
                            proc.kill()
                            processes_killed += 1
                        closed = True

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if closed:
                return True, f"Closed {app_name} ({processes_killed} processes)"
            else:
                # Try taskkill on Windows as a final fallback
                if os.name == 'nt':
                    # Try with and without .exe
                    subprocess.run(f"taskkill /f /im {app_name_lower}.exe", shell=True, capture_output=True)
                    subprocess.run(f"taskkill /f /im {app_name_lower}", shell=True, capture_output=True)
                    return True, f"Attempted to close {app_name} using system taskkill"

                return False, f"Could not find running instance of {app_name}"

        except Exception as e:
            return False, f"Error closing {app_name}: {str(e)}"

    def list_running_apps(self) -> list:
        """List currently running applications"""
        try:
            import psutil

            apps = []
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if proc.info['exe']:  # Only show apps with executable paths
                        apps.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'exe': proc.info['exe']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return apps
        except Exception as e:
            return []

    def get_available_apps(self) -> list:
        """Get list of available applications"""
        return list(self.common_apps.keys())

# Test
if __name__ == "__main__":
    launcher = AppLauncher()

    print("Testing App Launcher...")
    print("\nAvailable apps:", launcher.get_available_apps()[:10], "...")

    # Test opening notepad
    success, msg = launcher.open_app("notepad")
    print(f"\nOpen Notepad: {msg}")

    # Test opening calculator
    success, msg = launcher.open_app("calculator")
    print(f"Open Calculator: {msg}")


