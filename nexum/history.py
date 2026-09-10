from __future__ import annotations
import json, sqlite3
from contextlib import closing
from pathlib import Path

class HistoryStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS calculations(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                module TEXT NOT NULL,
                inputs TEXT NOT NULL,
                result TEXT NOT NULL
            )""")
    def add(self, module: str, inputs: dict, result: dict):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO calculations(module,inputs,result) VALUES(?,?,?)",
                       (module, json.dumps(inputs, ensure_ascii=False), json.dumps(result, ensure_ascii=False)))
    def latest(self, limit=100):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.row_factory = sqlite3.Row
            return [dict(r) for r in db.execute("SELECT * FROM calculations ORDER BY id DESC LIMIT ?", (limit,))]
