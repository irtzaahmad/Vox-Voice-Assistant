import subprocess
import sys
import os

def install_packages():
    print("--- JARVIS/Vox Dependency Installer ---")
    
    requirements_file = "requirements.txt"
    
    if not os.path.exists(requirements_file):
        print(f"Error: {requirements_file} not found.")
        return

    print(f"Installing packages from {requirements_file}...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_file])
        print("\n✅ All dependencies installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error during installation: {e}")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    install_packages()
    input("\nPress Enter to exit...")