"""Read-only local readiness check."""
import importlib.metadata
import json
import shutil
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
print('Research Desk readiness')
print('Python:', sys.version.split()[0])
for executable in ['node', 'npm', 'tesseract', 'ollama']:
    print(executable + ':', shutil.which(executable) or 'not installed')
for package in ['fastapi', 'pypdf', 'scikit-learn', 'pillow', 'pytesseract']:
    try:
        print(package + ':', importlib.metadata.version(package))
    except importlib.metadata.PackageNotFoundError:
        print(package + ': missing; install requirements.txt in the virtual environment')
print('Frontend build:', 'ready' if (ROOT / 'frontend/dist/index.html').exists() else 'run scripts/start.sh')
try:
    with urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=2) as response:
        models = json.load(response).get('models', [])
    print('Ollama models:', ', '.join(model['name'] for model in models) or 'none installed')
except OSError:
    print('Ollama server: offline; startup will attempt to launch it if installed')
