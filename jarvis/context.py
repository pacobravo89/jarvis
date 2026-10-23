"""Seguimiento ligero de tema sin llamadas adicionales a Ollama."""
import re
from . import storage

TOPIC_PATTERN = re.compile(r"(?:sobre|acerca de|de|del|quien (?:es|fue)|quién (?:es|fue)|hablame de|háblame de)\s+(.+)$", re.I)
FOLLOWUP = re.compile(r"\b(su|sus|ellos|ellas|él|ella|ese|esa|esos|esas|grupo|canciones|disco|album|álbum|biografía|temas|más|otra|primer|segundo|tercero)\b",re.I)
STOP = re.compile(r"[?.!]+$")

def explicit_topic(text):
    t=text.strip().lower()
    if re.search(r"\b(?:nikola|nicola)\s+tesla\b",t):return 'Nikola Tesla'
    if re.search(r"\bestopa\b",t):return 'Estopa (dúo musical español)'
    m=TOPIC_PATTERN.search(text.strip())
    if m:
        candidate=STOP.sub('',m.group(1)).strip()
        if 1<=len(candidate.split())<=5 and len(candidate)>2 and not candidate.lower().startswith(('la ','el ','los ','las ','un ','una ','qué ','que ','cuál ','cual ')):
            return candidate
    return ''

def resolve(text, history=None):
    history=storage.history(16) if history is None else history
    explicit=explicit_topic(text)
    if explicit:return text,explicit
    topic=''
    for entry in reversed(history):
        if entry['role']!='user':continue
        topic=explicit_topic(entry['content'])
        if topic:break
    if topic and FOLLOWUP.search(text):
        return f'{text.strip()} (referente de la conversación: {topic})',topic
    return text,''
