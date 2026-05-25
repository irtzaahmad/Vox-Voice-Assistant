"""
Vox System Module
Handles system operations: volume, screenshot, shutdown, restart, sleep
Uses pyautogui, ctypes, and psutil for system control
"""
import os
import ctypes
import subprocess
import platform
from datetime import datetime
from typing import Tuple, Optional
import config

class SystemController:
    def __init__(self):
        self.system = platform.system()
        self._init_windows_api()

    def _init_windows_api(self):
        """Initialize Windows-specific APIs"""
        if self.system == "Windows":
            try:
                # Load user32.dll for volume control
                self.user32 = ctypes.windll.user32
                # Load kernel32.dll for system power functions
                self.kernel32 = ctypes.windll.kernel32
                # Load shell32.dll for system operations
                self.shell32 = ctypes.windll.shell32
            except Exception as e:
                print(f"⚠️ Error loading Windows APIs: {e}")

    # ==================== VOLUME CONTROL ====================

    def volume_up(self, step: int = None) -> Tuple[bool, str]:
        """Increase system volume"""
        try:
            if step is None:
                step = config.VOLUME_STEP

            if self.system == "Windows":
                # Simulate volume up key press (VK_VOLUME_UP = 0xAF)
                VK_VOLUME_UP = 0xAF
                # Press and release
                ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
                ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)
                return True, f"Volume increased by {step}%"
            else:
                return False, "Volume control only supported on Windows"
        except Exception as e:
            return False, f"Error increasing volume: {str(e)}"

    def volume_down(self, step: int = None) -> Tuple[bool, str]:
        """Decrease system volume"""
        try:
            if step is None:
                step = config.VOLUME_STEP

            if self.system == "Windows":
                # Simulate volume down key press (VK_VOLUME_DOWN = 0xAE)
                VK_VOLUME_DOWN = 0xAE
                ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
                ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 2, 0)
                return True, f"Volume decreased by {step}%"
            else:
                return False, "Volume control only supported on Windows"
        except Exception as e:
            return False, f"Error decreasing volume: {str(e)}"

    def mute(self) -> Tuple[bool, str]:
        """Mute system volume"""
        try:
            if self.system == "Windows":
                # Simulate mute key press (VK_VOLUME_MUTE = 0xAD)
                VK_VOLUME_MUTE = 0xAD
                ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
                ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)
                return True, "System muted"
            else:
                return False, "Mute only supported on Windows"
        except Exception as e:
            return False, f"Error muting: {str(e)}"

    def unmute(self) -> Tuple[bool, str]:
        """Unmute system volume"""
        # Same key toggles mute/unmute
        return self.mute()

    def set_volume(self, level: int) -> Tuple[bool, str]:
        """Set volume to specific level (0-100)"""
        try:
            level = max(0, min(100, level))

            if self.system == "Windows":
                try:
                    from ctypes import cast, POINTER
                    from comtypes import CLSCTX_ALL
                    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                    
                    devices = AudioUtilities.GetSpeakers()
                    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    volume = cast(interface, POINTER(IAudioEndpointVolume))
                    
                    # Set volume (0.0 to 1.0)
                    volume.SetMasterVolumeLevelScalar(level / 100, None)
                    return True, f"Volume set to {level}%"
                except Exception as e:
                    print(f"⚠️ pycaw failed, falling back to powershell: {e}")
                    # Fallback to powershell
                    cmd = f'powershell -c "$volume = {level}; $wsh = New-Object -ComObject WScript.Shell; 1..50 | ForEach-Object {{ $wsh.SendKeys([char]174) }}; 1..($volume/2) | ForEach-Object {{ $wsh.SendKeys([char]175) }}"'
                    subprocess.run(cmd, shell=True, capture_output=True)
                    return True, f"Volume set to {level}% (via fallback)"
            else:
                return False, "Volume setting only supported on Windows"
        except Exception as e:
            return False, f"Error setting volume: {str(e)}"

    # ==================== SCREENSHOT ====================

    def take_screenshot(self, filename: str = None, region: tuple = None) -> Tuple[bool, str]:
        """Take screenshot and save to file"""
        try:
            import pyautogui
            from PIL import Image

            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"

            filepath = os.path.join(config.SCREENSHOTS_DIR, filename)

            # Take screenshot
            if region:
                screenshot = pyautogui.screenshot(region=region)
            else:
                screenshot = pyautogui.screenshot()

            # Save
            screenshot.save(filepath)

            return True, f"Screenshot saved: {filepath}"
        except Exception as e:
            return False, f"Error taking screenshot: {str(e)}"

    # ==================== SYSTEM POWER ====================

    def shutdown(self, delay: int = 0) -> Tuple[bool, str]:
        """Shutdown computer"""
        try:
            if self.system == "Windows":
                if delay > 0:
                    cmd = f"shutdown /s /t {delay} /c 'Vox is shutting down the system'"
                else:
                    cmd = "shutdown /s /t 0"

                subprocess.run(cmd, shell=True, capture_output=True)
                return True, f"System shutting down in {delay} seconds"
            else:
                return False, "Shutdown only supported on Windows"
        except Exception as e:
            return False, f"Error shutting down: {str(e)}"

    def restart(self, delay: int = 0) -> Tuple[bool, str]:
        """Restart computer"""
        try:
            if self.system == "Windows":
                if delay > 0:
                    cmd = f"shutdown /r /t {delay} /c 'Vox is restarting the system'"
                else:
                    cmd = "shutdown /r /t 0"

                subprocess.run(cmd, shell=True, capture_output=True)
                return True, f"System restarting in {delay} seconds"
            else:
                return False, "Restart only supported on Windows"
        except Exception as e:
            return False, f"Error restarting: {str(e)}"

    def sleep(self) -> Tuple[bool, str]:
        """Put computer to sleep"""
        try:
            if self.system == "Windows":
                # Use rundll32 to suspend/sleep
                subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
                return True, "System going to sleep"
            else:
                return False, "Sleep only supported on Windows"
        except Exception as e:
            return False, f"Error putting system to sleep: {str(e)}"

    def abort_shutdown(self) -> Tuple[bool, str]:
        """Abort scheduled shutdown/restart"""
        try:
            if self.system == "Windows":
                subprocess.run("shutdown /a", shell=True, capture_output=True)
                return True, "Shutdown/restart aborted"
            else:
                return False, "Abort shutdown only supported on Windows"
        except Exception as e:
            return False, f"Error aborting shutdown: {str(e)}"

    # ==================== SYSTEM INFO ====================

    def get_battery_status(self) -> Tuple[bool, dict]:
        """Get battery status"""
        try:
            import psutil

            if not hasattr(psutil, "sensors_battery"):
                return False, {"error": "Battery info not available"}

            battery = psutil.sensors_battery()

            if battery is None:
                return False, {"error": "No battery detected (desktop PC)"}

            return True, {
                "percent": battery.percent,
                "is_charging": battery.power_plugged,
                "time_left": battery.secsleft if battery.secsleft > 0 else None,
                "status": "Charging" if battery.power_plugged else "Discharging"
            }
        except Exception as e:
            return False, {"error": str(e)}

    def get_cpu_usage(self) -> Tuple[bool, dict]:
        """Get CPU usage"""
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()

            return True, {
                "usage_percent": cpu_percent,
                "core_count": cpu_count,
                "frequency_mhz": cpu_freq.current if cpu_freq else None,
                "status": "High" if cpu_percent > 80 else "Normal" if cpu_percent > 50 else "Low"
            }
        except Exception as e:
            return False, {"error": str(e)}

    def get_ram_usage(self) -> Tuple[bool, dict]:
        """Get RAM usage"""
        try:
            import psutil

            memory = psutil.virtual_memory()

            return True, {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "usage_percent": memory.percent,
                "status": "High" if memory.percent > 80 else "Normal" if memory.percent > 50 else "Low"
            }
        except Exception as e:
            return False, {"error": str(e)}

    def get_system_info(self) -> dict:
        """Get comprehensive system info"""
        try:
            import psutil

            info = {
                "platform": platform.platform(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
            }

            # Disk usage
            disk = psutil.disk_usage('/')
            info["disk_total_gb"] = round(disk.total / (1024**3), 2)
            info["disk_used_gb"] = round(disk.used / (1024**3), 2)
            info["disk_free_gb"] = round(disk.free / (1024**3), 2)
            info["disk_usage_percent"] = disk.percent

            return info
        except Exception as e:
            return {"error": str(e)}

    # ==================== TIME & DATE ====================

    def get_current_time(self) -> str:
        """Get current time"""
        return datetime.now().strftime("%I:%M %p")

    def get_current_date(self) -> str:
        """Get current date"""
        return datetime.now().strftime("%A, %B %d, %Y")

# Test
if __name__ == "__main__":
    sys_ctrl = SystemController()

    print("Testing System Controller...")

    # Test system info
    print("\nSystem Info:", sys_ctrl.get_system_info())

    # Test battery
    success, battery = sys_ctrl.get_battery_status()
    if success:
        print(f"\nBattery: {battery['percent']}% - {battery['status']}")
    else:
        print(f"\nBattery: {battery.get('error', 'Unknown')}")

    # Test CPU
    success, cpu = sys_ctrl.get_cpu_usage()
    if success:
        print(f"\nCPU Usage: {cpu['usage_percent']}%")

    # Test RAM
    success, ram = sys_ctrl.get_ram_usage()
    if success:
        print(f"\nRAM Usage: {ram['usage_percent']}% ({ram['used_gb']}GB / {ram['total_gb']}GB)")

    # Test screenshot
    success, msg = sys_ctrl.take_screenshot()
    print(f"\nScreenshot: {msg}")


