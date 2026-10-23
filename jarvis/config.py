import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
DB=DATA/'jarvis.db'
MODEL=os.getenv('JARVIS_MODEL','qwen2.5:1.5b')
OLLAMA=os.getenv('JARVIS_OLLAMA','http://127.0.0.1:11434')
MIC=int(os.getenv('JARVIS_MIC','1'))
VOICE=Path(os.getenv('JARVIS_VOICE',str(ROOT/'voices'/'es_ES-davefx-medium.onnx')))
HOST=os.getenv('JARVIS_HOST','127.0.0.1')
PORT=int(os.getenv('JARVIS_PORT','8765'))
ALLOWED_DIRS=[Path(p).expanduser().resolve() for p in os.getenv('JARVIS_ALLOWED_DIRS',str(Path.home()/'Documents')).split(';') if p.strip()]
