"""
Vox v3.0 - Silent Launcher
Double-click to start Vox with NO console window visible.
"""
import os, sys, subprocess

project_dir = os.path.dirname(os.path.abspath(__file__))
main_script = os.path.join(project_dir, "main.py")

# find pythonw.exe automatically
py_exe  = sys.executable
pythonw = py_exe.replace("python.exe", "pythonw.exe")
if not os.path.exists(pythonw):
    pythonw = os.path.join(os.path.dirname(py_exe), "pythonw.exe")
if not os.path.exists(pythonw):
    pythonw = py_exe   # fallback

subprocess.Popen(
    [pythonw, main_script],
    cwd=project_dir,
    creationflags=subprocess.CREATE_NO_WINDOW
)


