"""Motor: ruta rápida para consultas públicas, fuentes antes que generación."""
import json,re
from . import llm,storage,tools,context

ROUTER=('Elige una herramienta. Devuelve exclusivamente JSON con tool y args. '
        'No inventes argumentos. Si el usuario solo conversa, usa chat. Herramientas: '
        +json.dumps(tools.SCHEMA,ensure_ascii=False))

def _json_object(s):
    if isinstance(s,dict):return s
    try:return json.loads(s)
    except (TypeError,ValueError):
        m=re.search(r'\{.*\}',str(s),re.S)
        if m:
            try:return json.loads(m.group())
            except ValueError:pass
    return {}

def _store(user,answer):
    storage.add_message('user',user);storage.add_message('assistant',answer)

def _public_route(text,topic):
    t=text.casefold()
    if re.search(r'\b(canciones|temas musicales|discograf[ií]a|[aá]lbumes|discos|hits|[eé]xitos)\b',t) and topic:
        return 'music',{'q':topic}
    if re.search(r'\b(h[aá]blame|informaci[oó]n|qui[eé]n (?:es|fue)|biograf[ií]a|cu[eé]ntame|conocer|saber)\b',t) and topic:
        return 'wikipedia',{'q':topic}
    return None,None

def handle(text):
    original=text.strip()
    if not original:return {'answer':'¿Qué necesitas?','tool':'chat','view':{'kind':'text','items':[]}}
    try:
        history=storage.history(16)
        resolved,topic=context.resolve(original,history)
        name,args=_public_route(original,topic)
        if not name:
            raw=llm.chat([{'role':'system','content':ROUTER},{'role':'user','content':resolved}],max_tokens=120,json_mode=True)
            obj=_json_object(raw);name=obj.get('tool','chat');args=obj.get('args',{})
        if name=='chat' or name not in tools.TOOLS and name!='music':
            answer=llm.answer(original,resolved_query=resolved)
            return {'answer':answer,'tool':'chat','view':{'kind':'text','items':[]},'resolved_query':resolved}
        if not isinstance(args,dict):args={}
        expected=tools.SCHEMA.get(name,[])
        args={k:v for k,v in args.items() if k in expected and isinstance(v,(str,int))} if name!='music' else args
        if name in ('wikipedia','web_search','news','music'):
            args['q']=topic or str(args.get('q') or resolved)
        elif name in ('files_search','recall') and not args.get('q'):
            args['q']=resolved
        if name in ('open_app','open_url'):
            return {'answer':'Confirma la acción desde la interfaz.','tool':name,'pending':args,'view':{'kind':'confirmation','items':[]}}
        if name=='music':
            out=tools.music(topic)
        else:
            missing=[k for k in expected if k not in args and k not in {'due','city'}]
            if missing:return {'answer':'Me falta un dato para realizar esa acción: '+', '.join(missing),'tool':name,'view':{'kind':'text','items':[]}}
            out=tools.TOOLS[name](**args)
        # Para consultas factuales no dejar al modelo pequeño reescribir los hechos.
        # Mostrar directamente el texto recuperado y sus enlaces/imágenes.
        if name in ('wikipedia','music','web_search','news','weather','clock','read_url','read_file','files_search','processes','git_status','task_list','recall','task_add','task_done','remember'):
            answer=out['text'];_store(original,answer)
        else:
            answer=llm.answer(original,context=json.dumps(out,ensure_ascii=False)[:3500],resolved_query=resolved)
        return {'answer':answer,'tool':name,'view':out,'resolved_query':resolved}
    except Exception as exc:
        return {'answer':'No he podido completar la consulta. '+str(exc)[:180], 'tool':'error','view':{'kind':'text','items':[]}}
