import sqlite3
from datetime import datetime
from .config import DB

def connect():
    db=sqlite3.connect(DB,timeout=10)
    db.row_factory=sqlite3.Row
    return db

def init():
    with connect() as db:
        db.executescript('''CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, role TEXT, content TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY, content TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY, title TEXT NOT NULL, due TEXT, done INTEGER DEFAULT 0, notified INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);''')

def history(limit=12):
    with connect() as db:
        return [dict(role=r['role'],content=r['content']) for r in reversed(db.execute('SELECT role,content FROM messages ORDER BY id DESC LIMIT ?', (limit,)).fetchall())]

def add_message(role,content):
    with connect() as db: db.execute('INSERT INTO messages(role,content) VALUES (?,?)',(role,content))

def remember(text):
    with connect() as db: db.execute('INSERT INTO memories(content) VALUES (?)',(text[:2000],))

def memories(query='',limit=8):
    with connect() as db:
        if query:
            words=[w for w in query.lower().split() if len(w)>3][:6]
            rows=db.execute('SELECT * FROM memories ORDER BY id DESC LIMIT 150').fetchall()
            ranked=sorted(rows,key=lambda r:sum(w in r['content'].lower() for w in words),reverse=True)
            return [dict(r) for r in ranked[:limit]]
        return [dict(r) for r in db.execute('SELECT * FROM memories ORDER BY id DESC LIMIT ?',(limit,))]

def add_task(title,due=None):
    with connect() as db:
        c=db.execute('INSERT INTO tasks(title,due) VALUES (?,?)',(title[:300],due));return c.lastrowid

def tasks():
    with connect() as db: return [dict(r) for r in db.execute('SELECT * FROM tasks ORDER BY done,due,id DESC LIMIT 100')]

def finish_task(id):
    with connect() as db: return db.execute('UPDATE tasks SET done=1 WHERE id=?',(id,)).rowcount

def due_tasks():
    with connect() as db:
        rows=db.execute("SELECT * FROM tasks WHERE done=0 AND notified=0 AND due IS NOT NULL AND due<=?",(datetime.now().isoformat(timespec='minutes'),)).fetchall()
        for r in rows:db.execute('UPDATE tasks SET notified=1 WHERE id=?',(r['id'],))
        return [dict(r) for r in rows]
