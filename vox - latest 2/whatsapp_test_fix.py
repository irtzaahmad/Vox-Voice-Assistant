"""
Vox - WhatsApp Diagnostic & Fix Tool
=====================================
Run this to see why WhatsApp is not sending.
"""
import sys
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

def test_imports():
    print("\n1. Checking Libraries...")
    try:
        import pywhatkit
        print("✅ pywhatkit is installed.")
    except ImportError:
        print("❌ pywhatkit is MISSING. Run: pip install pywhatkit")
        return False
    return True

def test_parsing(text):
    print(f"\n2. Testing Parsing for: '{text}'")
    # This simulates how Vox extracts info
    match = re.search(r"to (.*) saying (.*)", text.lower())
    if match:
        contact, msg = match.groups()
        print(f"✅ Extracted Contact: '{contact}'")
        print(f"✅ Extracted Message: '{msg}'")
        return contact, msg
    else:
        print("❌ Regex failed to find 'to ... saying ...'")
        return None, None

def test_automation(number, message):
    print(f"\n3. Testing Browser Automation...")
    import pywhatkit as kit
    import threading
    
    phone = "+" + number if not number.startswith('+') else number
    print(f"   Target: {phone}")
    print(f"   Wait Time: 25 seconds")
    print("   ⚠️  IMPORTANT: Browser will open. DO NOT move the mouse.")
    
    try:
        kit.sendwhatmsg_instantly(phone, message, wait_time=25, tab_close=True)
        print("✅ Automation command sent. If the message didn't type, check if WhatsApp Web is logged in.")
    except Exception as e:
        print(f"❌ Automation failed: {e}")

if __name__ == "__main__":
    print("=== Vox WhatsApp Fixer ===")
    if test_imports():
        # You can change these to test your own number
        test_text = "hey vox send whatsapp to 923001234567 saying hello this is a test"
        contact, msg = test_parsing(test_text)
        
        if contact and msg:
            choice = input("\nDo you want to run a REAL browser test now? (y/n): ")
            if choice.lower() == 'y':
                num = input("Enter a phone number to test (with country code, e.g. 923...): ")
                test_automation(num, "Hello! This is a test from Vox.")
    
    input("\nPress Enter to exit...")
