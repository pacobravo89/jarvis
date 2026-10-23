import uvicorn
from jarvis.config import HOST,PORT
if __name__=='__main__':
    print(f'JARVIS: abre http://{HOST}:{PORT}')
    uvicorn.run('jarvis.server:app',host=HOST,port=PORT,log_level='warning')
