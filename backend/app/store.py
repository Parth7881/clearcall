import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

class Store:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / 'clearcall.sqlite3'
        with self.connect() as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1, 2):
                raise RuntimeError('This database needs a newer version of Clearcall.')
            db.execute('''CREATE TABLE IF NOT EXISTS transcripts (
                id TEXT PRIMARY KEY, digest TEXT NOT NULL UNIQUE, filename TEXT NOT NULL,
                expert TEXT NOT NULL, role TEXT NOT NULL, market TEXT NOT NULL,
                raw BLOB NOT NULL, passages TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            )''')
            db.execute('''CREATE TABLE IF NOT EXISTS analysis_jobs (
                id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT NOT NULL
                DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')))''')
            db.execute('''CREATE TABLE IF NOT EXISTS analysis_cache (
                cache_key TEXT PRIMARY KEY, payload TEXT NOT NULL)''')
            db.execute('PRAGMA user_version = 2')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def ingest(self, items: list) -> dict:
        added = 0
        with self.connect() as db:
            for filename, raw, parsed in items:
                cursor = db.execute('''INSERT OR IGNORE INTO transcripts
                    (id,digest,filename,expert,role,market,raw,passages) VALUES (?,?,?,?,?,?,?,?)''',
                    (uuid.uuid4().hex, hashlib.sha256(raw).hexdigest(), filename,
                     parsed['expert'], parsed['role'], parsed['market'], raw,
                     json.dumps(parsed['passages'], ensure_ascii=False)))
                added += cursor.rowcount
        return {'added': added, 'duplicates': len(items) - added}

    def all(self):
        with self.connect() as db:
            rows = db.execute('SELECT id,filename,expert,role,market,created_at FROM transcripts ORDER BY created_at,rowid').fetchall()
            return [dict(r) for r in rows]

    def get(self, transcript_id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM transcripts WHERE id=?', (transcript_id,)).fetchone()
            return dict(row) if row else None

    def save_job(self, job):
        with self.connect() as db:
            db.execute('''INSERT INTO analysis_jobs(id,payload) VALUES(?,?)
                ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,
                updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')''', (job['id'],json.dumps(job,ensure_ascii=False)))

    def jobs(self, limit=30):
        with self.connect() as db:
            return [json.loads(r['payload']) for r in db.execute('SELECT payload FROM analysis_jobs ORDER BY updated_at DESC,rowid DESC LIMIT ?', (limit,))]

    def job(self, job_id):
        with self.connect() as db:
            row = db.execute('SELECT payload FROM analysis_jobs WHERE id=?',(job_id,)).fetchone()
            return json.loads(row['payload']) if row else None

    def cached(self, key):
        with self.connect() as db:
            row = db.execute('SELECT payload FROM analysis_cache WHERE cache_key=?',(key,)).fetchone()
            return json.loads(row['payload']) if row else None

    def cache(self, key, result):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO analysis_cache(cache_key,payload) VALUES(?,?)',(key,json.dumps(result,ensure_ascii=False)))
