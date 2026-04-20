import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Django Folder Nameclear
django_dir = os.path.join(BASE_DIR)
print ("Django Directory:", django_dir)

# Flask Folder Name
flask_dir = os.path.join(BASE_DIR, "Codes")

django_cmd = [sys.executable, "manage.py", "runserver", "0.0.0.0:8000"]
flask_cmd = [sys.executable, "app.py"]

django_proc = subprocess.Popen(django_cmd, cwd=django_dir)
flask_proc = subprocess.Popen(flask_cmd, cwd=flask_dir)

try:
    input("\n✅ Django + Flask running.\nPress ENTER to stop...\n")
finally:
    django_proc.terminate()
    flask_proc.terminate()
