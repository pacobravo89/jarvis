import threading,time,asyncio
from pathlib import Path
from fastapi import FastAPI,HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from . import storage,engine,tools
from .config import ROOT
app=FastAPI(title='JARVIS Local')
class Query(BaseModel):text:str
class Action(BaseModel):tool:str;args:dict
listeners=set();state={'voice':'off','last':'','error':''};voice_thread=None;stop_event=threading.Event()
def broadcast(event):
    # thread-safe polling queue is used by the frontend instead of websocket
    state.update(event)
@app.on_event('startup')
def startup():storage.init()
@app.get('/')
def index():return FileResponse(ROOT/'web'/'index.html')
@app.get('/app.js')
def js():return FileResponse(ROOT/'web'/'app.js',media_type='application/javascript')
@app.get('/style.css')
def css():return FileResponse(ROOT/'web'/'style.css',media_type='text/css')
@app.get('/api/status')
def status():return state
@app.post('/api/chat')
def chat(q:Query):
    if not q.text.strip():raise HTTPException(400,'Escribe un mensaje')
    return engine.handle(q.text[:2000])
@app.get('/api/history')
def history():return storage.history(40)
@app.get('/api/tasks')
def tasks():return storage.tasks()
@app.get('/api/memories')
def memories():return storage.memories()
@app.post('/api/action')
def action(q:Action):
    if q.tool not in ('open_app','open_url'):raise HTTPException(403,'Acción no permitida')
    allowed=set(tools.SCHEMA[q.tool]);args={k:v for k,v in q.args.items() if k in allowed and isinstance(v,str)}
    try:return tools.TOOLS[q.tool](**args)
    except Exception as exc:raise HTTPException(400,str(exc))
@app.post('/api/voice/start')
def start_voice():
    global voice_thread
    if voice_thread and voice_thread.is_alive():return {'ok':True,'state':'running'}
    stop_event.clear();voice_thread=threading.Thread(target=voice_loop,daemon=True);voice_thread.start()
    return {'ok':True,'state':'starting'}
@app.post('/api/voice/stop')
def stop_voice():
    stop_event.set();state['voice']='stopping';return {'ok':True}
def voice_loop():
    from .audio import Audio,wake,normalize
    state['voice']='loading';a=Audio();followup=0
    try:
        a.load();state['voice']='listening'
        while not stop_event.is_set():
            clip=a.listen()
            if clip is None:continue
            phrase=a.transcribe(clip)
            if not phrase:continue
            activated,cmd=wake(phrase)
            if activated:
                followup=time.monotonic()+20
                if not cmd:
                    state['voice']='speaking';a.speak('Te escucho');state['voice']='listening';continue
            elif time.monotonic()<followup:cmd=phrase
            else:continue
            if normalize(cmd) in ('termina','salir','adios','hasta luego'):
                state['voice']='speaking';a.speak('Hasta luego');break
            state['voice']='thinking';out=engine.handle(cmd)
            state['last']=cmd;state['answer']=out['answer'];state['result']=out
            state['voice']='speaking';a.speak(out['answer']);followup=time.monotonic()+20
            state['voice']='listening'
    except Exception as exc:state['error']=str(exc);state['voice']='error'
    finally:
        if state['voice']!='error':state['voice']='off'
