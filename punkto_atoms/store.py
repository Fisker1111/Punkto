"""Thread-safe, append-only SQLite atom persistence."""
import json
from pathlib import Path
import sqlite3
import threading

from .atoms_core import validate_atom


class AtomStore:
    def __init__(self, path):
        if str(path) != ':memory:':
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS atoms (
                seq INTEGER PRIMARY KEY, mid TEXT NOT NULL UNIQUE,
                t INTEGER NOT NULL, lat REAL NOT NULL, lon REAL NOT NULL,
                alt REAL NOT NULL, atom BLOB NOT NULL);
            CREATE TABLE IF NOT EXISTS sync_cursors (
                peer TEXT PRIMARY KEY,
                last_seq INTEGER NOT NULL DEFAULT 0);
            CREATE INDEX IF NOT EXISTS atoms_t ON atoms(t);
            CREATE INDEX IF NOT EXISTS atoms_position ON atoms(lat, lon);
            CREATE TRIGGER IF NOT EXISTS atoms_no_update BEFORE UPDATE ON atoms
                BEGIN SELECT RAISE(ABORT, 'atoms are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS atoms_no_delete BEFORE DELETE ON atoms
                BEGIN SELECT RAISE(ABORT, 'atoms are append-only'); END;
        ''')

    def insert(self, value):
        atom, mid, point = validate_atom(value)
        payload = json.dumps(atom, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        with self.lock, self.db:
            result = self.db.execute('''INSERT INTO atoms(mid,t,lat,lon,alt,atom)
                VALUES(?,?,?,?,?,?) ON CONFLICT(mid) DO NOTHING''',
                (mid, atom['t'], point.lat, point.lon, point.alt, payload))
            return mid, result.rowcount == 1

    @staticmethod
    def _item(row, spatial=False):
        item = json.loads(row['atom'])
        item['mid'] = row['mid']
        if spatial:
            item.update({k: row[k] for k in ('lat', 'lon', 'alt')})
        return item

    def fetch(self, mid):
        with self.lock:
            row = self.db.execute('SELECT * FROM atoms WHERE mid=?', (mid,)).fetchone()
            return self._item(row) if row else None

    def inventory(self, since=0):
        with self.lock:
            return [self._item(r) for r in self.db.execute(
                'SELECT * FROM atoms WHERE seq>? ORDER BY seq', (since,))]

    def stats(self):
        with self.lock:
            row = self.db.execute('SELECT COUNT(*), COALESCE(MAX(seq),0) FROM atoms').fetchone()
            return {'count': row[0], 'head_seq': row[1]}

    def get_cursor(self, peer):
        with self.lock:
            row = self.db.execute('SELECT last_seq FROM sync_cursors WHERE peer=?',
                                  (peer.strip().rstrip('/'),)).fetchone()
            return row[0] if row else 0

    def set_cursor(self, peer, last_seq):
        with self.lock, self.db:
            self.db.execute('''INSERT INTO sync_cursors(peer,last_seq) VALUES(?,?)
                ON CONFLICT(peer) DO UPDATE SET last_seq=excluded.last_seq''',
                (peer.strip().rstrip('/'), last_seq))

    def cursors(self):
        with self.lock:
            return dict(self.db.execute('SELECT peer,last_seq FROM sync_cursors'))

    def feed(self, min_lat=-90, max_lat=90, min_lon=-180, max_lon=180,
             min_t=0, max_t=9223372036854775807, limit=100):
        with self.lock:
            return [self._item(r, spatial=True) for r in self.db.execute('''
                SELECT * FROM atoms WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?
                AND t BETWEEN ? AND ? ORDER BY t DESC, mid LIMIT ?''',
                (min_lat, max_lat, min_lon, max_lon, min_t, max_t, limit))]

    def close(self):
        with self.lock:
            self.db.close()
