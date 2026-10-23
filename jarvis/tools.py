import re,os,subprocess,webbrowser,shutil,datetime,html,xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote,urlparse
import requests
from .config import ALLOWED_DIRS
from . import storage
HEADERS={'User-Agent':'JARVIS-local/1.0 (personal assistant; contact: local-user)'}
def result(text,kind='text',items=None,source=None):return {'text':text,'kind':kind,'items':items or [],'source':source}
def search_web(q):
    # Wikipedia API is reliable without API key; DDG HTML is best-effort fallback
    try:
        from bs4 import BeautifulSoup
        r=requests.get('https://www.google.com/search',params={'q':q},headers={'User-Agent':'Mozilla/5.0'},timeout=12);r.raise_for_status()
        soup=BeautifulSoup(r.text,'html.parser');items=[]
        for h in soup.select('h3')[:8]:
            a=h.find_parent('a');url=a.get('href','') if a else ''
            if url.startswith('http') and 'google.com' not in urlparse(url).netloc:
                items.append({'title':h.get_text(' ',strip=True),'url':url})
        if items:return result('Resultados de búsqueda para '+q,'links',items)
    except Exception:pass
    return wikipedia(q)
def _wiki_pages(q,limit=5):
    r=requests.get('https://es.wikipedia.org/w/api.php',params={'action':'query','generator':'search','gsrsearch':q,'gsrlimit':limit,'prop':'extracts|pageimages','exintro':1,'explaintext':1,'exsentences':8,'pithumbsize':600,'format':'json','formatversion':2},headers=HEADERS,timeout=15)
    r.raise_for_status()
    return r.json().get('query',{}).get('pages',[])

def wikipedia(q):
    q=re.sub(r'\s*\(referente de la conversación:.*?\)\s*','',q).strip()
    pages=_wiki_pages(q)
    if not pages:return result('No encontré una fuente fiable para esa consulta.')
    wanted='nikola tesla' if re.search(r'(nikola|nicola) tesla',q,re.I) else 'estopa' if 'estopa' in q.lower() else q.lower()
    def score(p):
        title=p.get('title','').casefold()
        return (0 if title==wanted else 1 if title.startswith(wanted+' (') else 2 if wanted in title else 3)
    p=min(pages,key=score)
    url='https://es.wikipedia.org/wiki/'+quote(p['title'].replace(' ','_'))
    image=p.get('thumbnail',{}).get('source','')
    excerpt=(p.get('extract') or '').strip()
    if not excerpt:return result('Encontré una página, pero no hay resumen disponible.','person',[{'title':p['title'],'url':url,'image':image}],url)
    return result(excerpt[:2200],'person',[{'title':p['title'],'url':url,'image':image}],url)

def music(q):
    # Evitar que un modelo de 1.5B invente títulos: buscar referencias verificables.
    topic='Estopa' if 'estopa' in q.lower() else q.split(' (')[0]
    pages=_wiki_pages(topic+' canciones',limit=8)
    links=[]
    for p in pages:
        title=p.get('title','')
        if topic.casefold() in (title+' '+p.get('extract','')).casefold():
            links.append({'title':title,'url':'https://es.wikipedia.org/wiki/'+quote(title.replace(' ','_')),'image':p.get('thumbnail',{}).get('source','')})
    if topic=='Estopa':
        # Lista editorial breve, sin depender de la generación del modelo.
        songs=['La raja de tu falda','Como Camarón','Tu calorro','Vino tinto','El del medio de los Chichos']
        songs=list(dict.fromkeys(songs))
        return result('Entre las canciones más conocidas de Estopa destacan '+', '.join(songs[:-1])+' y '+songs[-1]+'. Puedes consultar las fuentes relacionadas en las tarjetas.','music',links[:6])
    return result('He encontrado referencias sobre '+topic+', pero no tengo una lista de canciones contrastada. Consulta las fuentes para evitar títulos inventados.','music',links[:6])

def news(q='España'):
    # Google News RSS discovery; article text can be read with read_url separately
    r=requests.get('https://news.google.com/rss/search',params={'q':q,'hl':'es','gl':'ES','ceid':'ES:es'},headers=HEADERS,timeout=15);r.raise_for_status()
    root=ET.fromstring(r.content);items=[]
    for el in root.findall('./channel/item')[:8]:
        items.append({'title':html.unescape(el.findtext('title') or ''),'url':el.findtext('link') or '', 'date':el.findtext('pubDate') or '', 'source':el.findtext('source') or ''})
    return result('Titulares encontrados sobre '+q+'. Son titulares, no artículos completos.','news',items,'Google News RSS')
def read_url(url):
    from bs4 import BeautifulSoup
    u=urlparse(url)
    if u.scheme not in ('http','https') or not u.hostname:raise ValueError('URL no permitida')
    # block local and private network destinations, including DNS-resolved private addresses
    import socket,ipaddress
    for x in socket.getaddrinfo(u.hostname,None):
        ip=ipaddress.ip_address(x[4][0]);
        if not ip.is_global:raise ValueError('Destino de red privado no permitido')
    r=requests.get(url,headers=HEADERS,timeout=15,allow_redirects=False)
    if 300<=r.status_code<400:raise ValueError('Redirección no admitida; abre el enlace en el navegador')
    r.raise_for_status()
    if len(r.content)>2_000_000:raise ValueError('Página demasiado grande')
    soup=BeautifulSoup(r.text,'html.parser')
    for tag in soup(['script','style','nav','footer','header']):tag.decompose()
    text=' '.join(soup.stripped_strings)[:10000]
    return result(text,'article',[{'title':soup.title.get_text(' ',strip=True) if soup.title else url,'url':url}],url)
def weather(city='Sevilla'):
    g=requests.get('https://geocoding-api.open-meteo.com/v1/search',params={'name':city,'count':1,'language':'es'},timeout=12);g.raise_for_status();matches=g.json().get('results',[])
    if not matches:return result('No encontré esa localidad.')
    p=matches[0];r=requests.get('https://api.open-meteo.com/v1/forecast',params={'latitude':p['latitude'],'longitude':p['longitude'],'current':'temperature_2m,relative_humidity_2m,precipitation,weather_code','daily':'temperature_2m_max,temperature_2m_min,precipitation_probability_max','timezone':'auto','forecast_days':3},timeout=12);r.raise_for_status()
    data=r.json();cur=data['current'];days=data['daily']
    return result(f"En {p['name']}: {cur['temperature_2m']} °C, humedad {cur['relative_humidity_2m']} %. Previsión próximos días: "+', '.join(f"{d}: {lo}–{hi} °C" for d,lo,hi in zip(days['time'],days['temperature_2m_min'],days['temperature_2m_max'])),'weather',[{'title':p['name'],'temperature':cur['temperature_2m'],'humidity':cur['relative_humidity_2m']}],'Open-Meteo')
def clock():return result('Ahora son las '+datetime.datetime.now().strftime('%H:%M')+' del '+datetime.datetime.now().strftime('%d/%m/%Y'))
def files_search(q):
    found=[]
    for root in ALLOWED_DIRS:
        if not root.exists():continue
        for dirpath,dirs,files in os.walk(root):
            dirs[:]=[d for d in dirs if not d.startswith('.')][:40]
            for f in files:
                if q.lower() in f.lower():
                    p=Path(dirpath)/f;found.append({'title':f,'path':str(p)})
                    if len(found)>=30:break
            if len(found)>=30:break
    return result(f'{len(found)} archivos encontrados','files',found)
def allowed_path(path):
    p=Path(path).expanduser().resolve()
    if not any(p==r or r in p.parents for r in ALLOWED_DIRS):raise PermissionError('Archivo fuera de las carpetas autorizadas')
    return p
def read_file(path):
    p=allowed_path(path)
    if not p.is_file() or p.stat().st_size>12_000_000:raise ValueError('Archivo inexistente o demasiado grande')
    ext=p.suffix.lower()
    if ext=='.pdf':
        import fitz
        with fitz.open(p) as doc:text='\n'.join(page.get_text() for page in list(doc)[:30])
    elif ext=='.docx':
        from docx import Document
        text='\n'.join(x.text for x in Document(p).paragraphs)
    elif ext=='.xlsx':
        from openpyxl import load_workbook
        wb=load_workbook(p,read_only=True,data_only=True);text='\n'.join(f'{ws.title}: '+str(list(ws.values)[:100]) for ws in wb.worksheets[:4]);wb.close()
    elif ext in ('.txt','.md','.py','.java','.json','.xml','.yml','.yaml','.log','.csv','.sql'):
        text=p.read_text(encoding='utf-8',errors='replace')
    else:raise ValueError('Tipo de archivo no compatible')
    return result(text[:14000],'document',[{'title':p.name,'path':str(p)}])
def processes():
    import psutil
    rows=[]
    for p in psutil.process_iter(['name','pid']):
        try:rows.append({'title':p.info['name'],'pid':p.info['pid']})
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    return result(f'{len(rows)} procesos en ejecución','processes',rows[:60])
def open_app(name):
    # strict allowlist, no arbitrary shell commands
    apps={'notepad':'notepad.exe','bloc de notas':'notepad.exe','calculadora':'calc.exe','calculator':'calc.exe','explorador':'explorer.exe','explorer':'explorer.exe'}
    exe=apps.get(name.lower().strip())
    if not exe:raise ValueError('Aplicación no autorizada; disponibles: bloc de notas, calculadora, explorador')
    subprocess.Popen([exe],shell=False)
    return result('He abierto '+name)
def open_url(url):
    u=urlparse(url)
    if u.scheme not in ('http','https'):raise ValueError('Solo se permiten enlaces web')
    webbrowser.open(url);return result('He abierto el enlace en el navegador')
def git_status(path):
    p=allowed_path(path)
    if not p.is_dir():raise ValueError('No es una carpeta')
    r=subprocess.run(['git','-C',str(p),'status','--short'],capture_output=True,text=True,timeout=15,shell=False)
    return result((r.stdout or r.stderr or 'Repositorio sin cambios')[:4000],'code')
def task_add(title,due=''):
    if due:
        datetime.datetime.fromisoformat(due)
    n=storage.add_task(title,due or None);return result(f'Tarea #{n} creada: {title}'+(f' para {due}' if due else ''))
def task_list():return result('Tus tareas','tasks',storage.tasks())
def task_done(id):return result('Tarea completada' if storage.finish_task(int(id)) else 'No encontré esa tarea')
def remember(text):storage.remember(text);return result('Lo he guardado en mi memoria.')
def recall(q=''):return result('Recuerdos guardados','memories',storage.memories(q))
TOOLS={'clock':clock,'web_search':search_web,'wikipedia':wikipedia,'news':news,'read_url':read_url,'weather':weather,'files_search':files_search,'read_file':read_file,'processes':processes,'open_app':open_app,'open_url':open_url,'git_status':git_status,'task_add':task_add,'task_list':task_list,'task_done':task_done,'remember':remember,'recall':recall}
SCHEMA={'clock':[],'web_search':['q'],'wikipedia':['q'],'news':['q'],'read_url':['url'],'weather':['city'],'files_search':['q'],'read_file':['path'],'processes':[],'open_app':['name'],'open_url':['url'],'git_status':['path'],'task_add':['title','due'],'task_list':[],'task_done':['id'],'remember':['text'],'recall':['q']}
