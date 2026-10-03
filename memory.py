import re
import sqlite3
from datetime import datetime, timezone

class MemoryStore:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL, importance INTEGER NOT NULL DEFAULT 3, created_at TEXT NOT NULL);
        ''')
        self.db.commit()

    def add_message(self, role, content):
        self.db.execute('INSERT INTO messages(role,content,created_at) VALUES(?,?,?)', (role, content, datetime.now(timezone.utc).isoformat()))
        self.db.commit()

    def recent(self, limit=12):
        rows = self.db.execute('SELECT role,content FROM messages ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
        return list(reversed([dict(x) for x in rows]))

    def add_memory(self, text, importance=3):
        if text.strip():
            self.db.execute('INSERT INTO memories(text,importance,created_at) VALUES(?,?,?)', (text.strip(), importance, datetime.now(timezone.utc).isoformat()))
            self.db.commit()

    def all(self, limit=50):
        rows = self.db.execute('SELECT id,text,importance,created_at FROM memories ORDER BY importance DESC,id DESC LIMIT ?', (limit,)).fetchall()
        return [dict(x) for x in rows]

    def search(self, query, limit=8):
        tokens = set(re.findall(r'[a-zA-ZäöüÄÖÜß0-9]{4,}', query.lower()))
        scored = []
        for r in self.db.execute('SELECT id,text,importance FROM memories').fetchall():
            words = set(re.findall(r'[a-zA-ZäöüÄÖÜß0-9]{4,}', r['text'].lower()))
            overlap = len(tokens & words)
            if overlap:
                scored.append((overlap * 2 + r['importance'] * .2, dict(r)))
        scored.sort(reverse=True, key=lambda x: x[0])
        return [x[1] for x in scored[:limit]]
