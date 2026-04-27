#!/usr/bin/env python3
"""
node.py — Punkto node server v0.3
Python 3 stdlib only. Listens on 127.0.0.1:8002.
Storage: DATA_DIR/atoms.ndjson (append-only NDJSON)
Cursor = byte offset (int) in atoms.ndjson
Sync: pulls /feed from each PUNKTO_PEERS peer every 60s
"""

import fcntl
import hashlib
import json
import os
import re
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

# Optional: import core library for address generation and validation.
# Falls back to inline regex if core/ is not on the path.
_core_punkto = None
try:
    _CORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    if _CORE_DIR not in sys.path:
        sys.path.insert(0, _CORE_DIR)
    from core import punkto as _core_punkto
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HOST = '127.0.0.1'
PORT = int(os.environ.get('PUNKTO_PORT', '8002'))

DATA_DIR = os.environ.get('PUNKTO_DATA_DIR', '/var/www/punkto/data')
NODE_NAME = os.environ.get('PUNKTO_NODE_NAME', 'punkto.xyz')
ATOMS_FILE = os.path.join(DATA_DIR, 'atoms.ndjson')
SYNC_STATE_FILE = os.path.join(DATA_DIR, 'sync_state.json')

PEERS_ENV = os.environ.get('PUNKTO_PEERS', '')
PEERS = [p.strip().rstrip('/') for p in PEERS_ENV.split(',') if p.strip()]

SYNC_INTERVAL = 60  # seconds

PUNKTO_RE = re.compile(r'^p:[0-9a-z]{12}(-[a-zA-Z0-9]+)?$')


def _is_valid_punkto(s: str) -> bool:
    """Validate a canonical Punkto string using core library when available."""
    if _core_punkto is not None:
        return _core_punkto.validate(s)
    return bool(PUNKTO_RE.match(s))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(ATOMS_FILE):
        with open(ATOMS_FILE, 'a'): pass


def cors_headers():
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Max-Age': '86400',
    }


def compute_atom_id(atom):
    """
    SHA-256 of canonical JSON bytes.
    canonical = sort_keys, no whitespace, UTF-8.
    atom_id is always computed locally, never trusted from external input.
    """
    canonical = json.dumps(atom, sort_keys=True, separators=(',', ':'),
                           ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(canonical).hexdigest()


def read_atoms_from_offset(offset):
    """
    Read atoms from byte offset to end of file.
    Returns (atoms_list, new_cursor).
    """
    atoms = []
    with open(ATOMS_FILE, 'rb') as f:
        f.seek(0, 2)
        file_size = f.tell()
        offset = max(0, min(offset, file_size))
        f.seek(offset)
        data = f.read()
        new_cursor = offset + len(data)

    for line in data.decode('utf-8').splitlines():
        line = line.strip()
        if line:
            try:
                atoms.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    return atoms, new_cursor


def load_all_atom_ids():
    """
    Read all atoms.ndjson and return a set of atom_id strings.
    Used for deduplication.
    """
    ids = set()
    if not os.path.exists(ATOMS_FILE):
        return ids
    with open(ATOMS_FILE, 'rb') as f:
        data = f.read()
    for line in data.decode('utf-8').splitlines():
        line = line.strip()
        if line:
            try:
                atom = json.loads(line)
                ids.add(compute_atom_id(atom))
            except (json.JSONDecodeError, TypeError):
                pass
    return ids


def append_atom(atom):
    """
    Append a validated atom dict to atoms.ndjson.
    Returns new cursor (byte offset after write).
    """
    line = json.dumps(atom, separators=(',', ':')) + '\n'
    encoded = line.encode('utf-8')
    with open(ATOMS_FILE, 'ab') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(encoded)
            f.flush()
            cursor = f.tell()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    return cursor


def validate_atom(data):
    """
    Validate atom dict. Returns (True, None) or (False, error_dict).
    Required fields for /atom POST: punkto, t
    (f and x are optional but encouraged; sync validates all four)
    """
    if 'punkto' not in data:
        return False, {
            'error': 'missing_field',
            'message': "Field 'punkto' is required",
        }
    if not _is_valid_punkto(str(data["punkto"])):
        return False, {
            'error': 'invalid_punkto',
            'message': (
                "Field 'punkto' must match p:[0-9a-z]{12}(-[a-zA-Z0-9]+)? "
                f"— got: {data['punkto']!r}"
            ),
        }
    if 't' not in data:
        return False, {
            'error': 'missing_field',
            'message': "Field 't' (timestamp) is required",
        }
    t = data['t']
    if not isinstance(t, int) or not (1_000_000_000_000 <= t <= 9_999_999_999_999):
        return False, {
            'error': 'invalid_timestamp',
            'message': "Field 't' must be a 13-digit Unix millisecond timestamp",
        }
    return True, None


# ---------------------------------------------------------------------------
# Sync state (per-peer byte-offset cursors)
# ---------------------------------------------------------------------------

_sync_lock = threading.Lock()


def load_sync_state():
    """Load {peer_url: cursor_int} from sync_state.json."""
    if not os.path.exists(SYNC_STATE_FILE):
        return {}
    try:
        with open(SYNC_STATE_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_sync_state(state):
    """Persist sync state atomically."""
    tmp = SYNC_STATE_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f)
    os.replace(tmp, SYNC_STATE_FILE)


def sync_from_peer(peer_url):
    """
    Pull new atoms from a single peer node.
    Returns number of new atoms appended.
    """
    with _sync_lock:
        state = load_sync_state()
        cursor = int(state.get(peer_url, 0))

    feed_url = f'{peer_url}/feed?since={cursor}'
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] [sync] pulling {feed_url}')

    try:
        req = urllib.request.Request(feed_url, headers={'User-Agent': 'PunktoSync/0.3'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode('utf-8')
            data = json.loads(body)
    except Exception as exc:
        ts = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f'[{ts}] [sync] error fetching {feed_url}: {exc}')
        return 0

    new_cursor = data.get('cursor', cursor)
    remote_atoms = data.get('atoms', [])

    if not remote_atoms:
        with _sync_lock:
            state = load_sync_state()
            state[peer_url] = new_cursor
            save_sync_state(state)
        return 0

    # Load known IDs for deduplication
    known_ids = load_all_atom_ids()
    appended = 0

    for atom in remote_atoms:
        if not isinstance(atom, dict):
            continue
        # Validate required fields
        if not all(k in atom for k in ('punkto', 't', 'f', 'x')):
            continue
        # Validate punkto format
        if not _is_valid_punkto(str(atom.get('punkto', ''))):
            continue
        # Validate timestamp
        t = atom.get('t')
        if not isinstance(t, int) or not (1_000_000_000_000 <= t <= 9_999_999_999_999):
            continue
        # Compute atom_id locally (never trust external)
        atom_id = compute_atom_id(atom)
        if atom_id in known_ids:
            continue
        # Append new atom
        append_atom(atom)
        known_ids.add(atom_id)
        appended += 1

    # Save updated cursor
    with _sync_lock:
        state = load_sync_state()
        state[peer_url] = new_cursor
        save_sync_state(state)

    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] [sync] {peer_url}: +{appended} new atoms, cursor={new_cursor}')
    return appended


def sync_loop():
    """Background thread: sync from all peers every SYNC_INTERVAL seconds."""
    # Initial delay to let the server start
    time.sleep(5)
    while True:
        if PEERS:
            for peer_url in PEERS:
                try:
                    sync_from_peer(peer_url)
                except Exception as exc:
                    ts = time.strftime('%Y-%m-%d %H:%M:%S')
                    print(f'[{ts}] [sync] unexpected error for {peer_url}: {exc}')
        time.sleep(SYNC_INTERVAL)


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------

class PunktoHandler(BaseHTTPRequestHandler):
    server_version = 'PunktoNode/0.3'
    sys_version = ''

    def log_message(self, fmt, *args):
        ts = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f'[{ts}] {self.address_string()} {fmt % args}')

    # ------------------------------------------------------------------ send

    def send_json(self, code, obj):
        body = json.dumps(obj, separators=(',', ':')).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, code, error_key, message):
        self.send_json(code, {'error': error_key, 'message': message})

    # --------------------------------------------------------------- OPTIONS

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    # -------------------------------------------------------------------- GET

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')
        qs = parse_qs(parsed.query)

        # /health
        if path == '/health':
            self.send_json(200, {'status': 'ok'})
            return

        # /info
        if path == '/info':
            info = {
                'node': NODE_NAME,
                'version': '0.3',
                'capabilities': ['write', 'sync'],
                'peers': PEERS,
            }
            self.send_json(200, info)
            return

        # /feed  or  /feed?since=<cursor>
        if path == '/feed':
            try:
                offset = int(qs['since'][0]) if 'since' in qs else 0
            except (ValueError, IndexError):
                self.send_error_json(400, 'invalid_cursor',
                                     "'since' must be an integer byte offset")
                return
            atoms, cursor = read_atoms_from_offset(offset)
            self.send_json(200, {'cursor': cursor, 'atoms': atoms})
            return

        # /punkto/<canonical>
        if path.startswith('/punkto/'):
            canonical = path[len('/punkto/'):]
            if not _is_valid_punkto(canonical):
                self.send_error_json(400, 'invalid_punkto',
                                     f'Invalid canonical form: {canonical!r}')
                return
            all_atoms, _ = read_atoms_from_offset(0)
            filtered = [a for a in all_atoms if a.get('punkto') == canonical]
            self.send_json(200, {'punkto': canonical, 'atoms': filtered})
            return

        self.send_error_json(404, 'not_found', f'No endpoint: {path}')

    # ------------------------------------------------------------------- POST

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        if path == '/atom':
            # Read body
            length = int(self.headers.get('Content-Length', 0))
            if length > 65_536:
                self.send_error_json(413, 'payload_too_large',
                                     'Request body exceeds 64 KB limit')
                return
            raw = self.rfile.read(length)
            try:
                atom = json.loads(raw.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                self.send_error_json(400, 'invalid_json',
                                     f'Could not parse JSON body: {exc}')
                return

            if not isinstance(atom, dict):
                self.send_error_json(400, 'invalid_json',
                                     'Atom must be a JSON object')
                return

            ok, err = validate_atom(atom)
            if not ok:
                status = 400
                if err['error'] == 'invalid_punkto':
                    status = 422
                self.send_json(status, err)
                return

            # Deduplication: compute atom_id and check if already stored
            atom_id = compute_atom_id(atom)
            known_ids = load_all_atom_ids()
            if atom_id in known_ids:
                self.send_json(200, {
                    'status': 'duplicate',
                    'atom_id': atom_id,
                    'punkto': atom['punkto'],
                })
                return

            cursor = append_atom(atom)
            self.send_json(201, {
                'status': 'accepted',
                'atom_id': atom_id,
                'cursor': cursor,
                'punkto': atom['punkto'],
            })
            return

        self.send_error_json(404, 'not_found', f'No endpoint: {path}')


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    ensure_data_dir()

    # Start background sync thread
    if PEERS:
        t = threading.Thread(target=sync_loop, daemon=True, name='sync-loop')
        t.start()
        print(f'Sync thread started. Peers: {PEERS}')
    else:
        print('No peers configured (PUNKTO_PEERS not set).')

    server = HTTPServer((HOST, PORT), PunktoHandler)
    print(f'Punkto node listening on http://{HOST}:{PORT}')
    print(f'Storage: {ATOMS_FILE}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down.')
        server.server_close()
