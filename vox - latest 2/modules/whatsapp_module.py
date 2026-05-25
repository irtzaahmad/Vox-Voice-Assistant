"""
Vox WhatsApp Module v4.5 — STANDALONE STABLE VERSION
====================================================
Professional automation with PyWhatKit.
"""
import urllib.parse
import webbrowser
import time
import threading
import sys
import os

try:
    import pywhatkit as kit
except ImportError:
    kit = None

class WhatsAppModule:
    def __init__(self):
        print("📱 WhatsApp Module initialized.")

    def open(self):
        webbrowser.open("https://web.whatsapp.com")
        return True, "Opening WhatsApp Web."

    def send(self, contact: str, message: str):
        if not contact or not message:
            return False, "⚠️ Error: Contact or message missing."

        # Clean the contact string
        # Removing "hey vox", "send", "whatsapp", etc. in case parsing was messy
        clean_contact = contact.lower()
        for word in ["to", "send", "whatsapp", "message", "hey", "vox"]:
            clean_contact = clean_contact.replace(word, "")
        
        clean_contact = clean_contact.replace('+','').replace(' ','').replace('-','').strip()
        
        print(f"🔍 Processing WhatsApp Send:")
        print(f"   - Target: {clean_contact}")
        print(f"   - Message: {message}")

        # 1. Automated Sending (Phone Numbers)
        if clean_contact.isdigit() and len(clean_contact) >= 10:
            phone = "+" + clean_contact if not clean_contact.startswith('+') else clean_contact
            
            if kit:
                try:
                    print(f"🚀 Launching PyWhatKit Automation (Wait: 25s)...")
                    # PyWhatKit automation runs in a separate thread to prevent Vox from freezing
                    def run_automation():
                        try:
                            kit.sendwhatmsg_instantly(phone, message, wait_time=25, tab_close=True)
                            print(f"✅ PyWhatKit: Command sent to browser for {phone}")
                        except Exception as e:
                            print(f"❌ PyWhatKit Thread Error: {e}")

                    threading.Thread(target=run_automation, daemon=True).start()
                    return True, f"I am sending the message to {phone}. Please keep the browser window focused."
                except Exception as e:
                    print(f"❌ PyWhatKit Core Error: {e}")

            # Manual Fallback URL
            url = f"https://web.whatsapp.com/send?phone={clean_contact}&text={urllib.parse.quote(message)}"
            webbrowser.open(url)
            return True, "Automation library failed. Opening manual link."

        # 2. Name Based (Search Fallback)
        url = f"https://web.whatsapp.com/send?text={urllib.parse.quote(message)}"
        webbrowser.open(url)
        return True, f"WhatsApp Web opened. Search for '{contact}' to send the message."
