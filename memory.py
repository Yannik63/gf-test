import re
import sqlite3
from datetime import datetime, timezone


TOKEN_RE = re.compile(r'[a-zA-ZäöüÄÖÜß0-9]{3,}')


class MemoryStore:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS state(
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memories(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'fact',
                importance INTEGER NOT NULL DEFAULT 3,
                confidence REAL NOT NULL DEFAULT .8,
                created_at TEXT NOT NULL,
                last_used_at TEXT
            );
            """
        )
        self.db.commit()

    def add_message(self, role, content):
        self.db.execute(
            'INSERT INTO messages(role,content,created_at) VALUES(?,?,?)',
            (role, content, datetime.now(timezone.utc).isoformat())
        )
        self.db.commit()

    def recent(self, limit=30):
        rows = self.db.execute(
            'SELECT role,content FROM messages ORDER BY id DESC LIMIT ?',
            (limit,)
        ).fetchall()
        return list(reversed([dict(x) for x in rows]))

    def search_messages(self, query, limit=12):
        """
        Retrieve older conversation turns that are semantically relevant enough
        to help preserve continuity. This deliberately returns the original
        speaker role so the model can tell who actually said something.
        """
        tokens = set(TOKEN_RE.findall(query.lower()))
        if not tokens:
            return []

        rows = self.db.execute(
            'SELECT id,role,content,created_at FROM messages ORDER BY id DESC'
        ).fetchall()

        scored = []
        for row in rows:
            words = set(TOKEN_RE.findall(row['content'].lower()))
            overlap = len(tokens & words)
            if overlap:
                # Prefer multiple matching words and more recent messages.
                score = overlap * 3
                scored.append((score, row['id'], dict(row)))

        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [item[2] for item in scored[:limit]]

    def add_memory(self, text, kind='fact', importance=3, confidence=.8):
        if text.strip():
            self.db.execute(
                'INSERT INTO memories(text,kind,importance,confidence,created_at) VALUES(?,?,?,?,?)',
                (
                    text.strip(),
                    kind,
                    importance,
                    confidence,
                    datetime.now(timezone.utc).isoformat()
                )
            )
            self.db.commit()

    def all(self, limit=50):
        return [
            dict(x)
            for x in self.db.execute(
                'SELECT id,text,kind,importance,confidence,created_at '
                'FROM memories ORDER BY importance DESC,id DESC LIMIT ?',
                (limit,)
            ).fetchall()
        ]

    def search(self, query, limit=8):
        tokens = set(TOKEN_RE.findall(query.lower()))
        scored = []
        for r in self.db.execute(
            'SELECT id,text,kind,importance,confidence FROM memories'
        ).fetchall():
            words = set(TOKEN_RE.findall(r['text'].lower()))
            overlap = len(tokens & words)
            if overlap:
                scored.append(
                    (
                        overlap * 2 + r['importance'] * .25 + r['confidence'] * .5,
                        dict(r)
                    )
                )
        scored.sort(reverse=True, key=lambda x: x[0])
        return [x[1] for x in scored[:limit]]

    def delete_memory(self, memory_id):
        self.db.execute('DELETE FROM memories WHERE id=?', (memory_id,))
        self.db.commit()

    def get_state(self, key, default=None):
        row = self.db.execute(
            'SELECT value FROM state WHERE key=?',
            (key,)
        ).fetchone()
        return default if row is None else row['value']

    def set_state(self, key, value):
        self.db.execute(
            'INSERT INTO state(key,value) VALUES(?,?) '
            'ON CONFLICT(key) DO UPDATE SET value=excluded.value',
            (key, str(value))
        )
        self.db.commit()
