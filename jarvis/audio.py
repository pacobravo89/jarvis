import time,wave,tempfile,unicodedata,re
from collections import deque
from pathlib import Path
import numpy as np
import sounddevice as sd
from .config import MIC,VOICE
class Audio:
    def __init__(self):self.whisper=None;self.piper=None
    def load(self):
        from faster_whisper import WhisperModel
        from piper.voice import PiperVoice
        self.whisper=WhisperModel('base',device='cpu',compute_type='int8')
        if not VOICE.exists():raise FileNotFoundError(f'Falta voz Piper: {VOICE}')
        self.piper=PiperVoice.load(str(VOICE))
    def listen(self):
        sr=16000;size=3200;frames=[];pre=deque(maxlen=3);started=False;silence=0
        with sd.InputStream(samplerate=sr,channels=1,dtype='float32',device=MIC,blocksize=size) as stream:
            for _ in range(75):
                chunk,_=stream.read(size);level=float(np.sqrt(np.mean(chunk**2)))
                if not started:
                    pre.append(chunk.copy())
                    if level>=0.006:started=True;frames.extend(pre)
                    continue
                frames.append(chunk.copy());silence=silence+1 if level<0.004 else 0
                if silence>=9:break
        return np.concatenate(frames).reshape(-1) if frames else None
    def transcribe(self,audio):
        segments,_=self.whisper.transcribe(audio,language='es',beam_size=1,vad_filter=False,initial_prompt='Jarvis, asistente personal.')
        return ' '.join(s.text.strip() for s in segments).strip()
    def speak(self,text):
        import soundfile as sf
        path=None
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav',delete=False) as f:path=Path(f.name)
            with wave.open(str(path),'wb') as wav:self.piper.synthesize_wav(text,wav)
            a,sr=sf.read(path,dtype='float32');sd.play(a,sr);sd.wait()
        finally:
            sd.stop()
            if path:path.unlink(missing_ok=True)
def normalize(s):
    s=unicodedata.normalize('NFD',s.lower());s=''.join(c for c in s if unicodedata.category(c)!='Mn')
    return re.sub('[^a-z0-9 ]+',' ',s).strip()
def wake(s):
    s=normalize(s)
    for a in ('jarvis','yarvis','ya revis','ya de vis'):
        if s==a:return True,''
        if s.startswith(a+' '):return True,s[len(a):].strip()
    return False,''
