import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DJANGO_DIR = os.path.join(BASE_DIR, "email-generator")
APP_DIR = os.path.join(BASE_DIR, "APP")

DJANGO_REQUIREMENTS = os.path.join(DJANGO_DIR, "requirements.txt")

# -------------------------
# INSTALL REQUIREMENTS
# -------------------------
def install_requirements(req_file):
    if os.path.exists(req_file):
        print(f"📦 Installing requirements from {req_file} ...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", req_file
        ])
    else:
        print(f"⚠️ requirements.txt not found at {req_file}")

install_requirements(DJANGO_REQUIREMENTS)

# -------------------------
# COMMANDS
# -------------------------
django_cmd = [sys.executable, "manage.py", "runserver", "0.0.0.0:8000"]
flask_cmd = [sys.executable, "tool_old.py"]
new_tool_cmd = [sys.executable, "new_tool.py"]

# -------------------------
# START PROCESSES
# -------------------------
print("🚀 Starting Django...")
django_proc = subprocess.Popen(django_cmd, cwd=DJANGO_DIR)

print("🚀 Starting Flask (old_tool.py)...")
flask_proc = subprocess.Popen(flask_cmd, cwd=APP_DIR)

print("🚀 Starting new_tool.py...")
new_tool_proc = subprocess.Popen(new_tool_cmd, cwd=APP_DIR)

try:
    input("\n✅ All services running.\nPress ENTER to stop...\n")
finally:
    print("\n🛑 Stopping all services...")
    django_proc.terminate()
    flask_proc.terminate()
    new_tool_proc.terminate()
