#!/usr/bin/env python3
"""
node.py — Punkto node server
Python 3 stdlib only. Listens on 127.0.0.1:8002.
Storage: /var/www/punkto/data/atoms.ndjson (append-only NDJSON)
Cursor = byte offset (int) in atoms.ndjson
"""

import fcntl
import json
import os
import re
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HOST = '127.0.0.1'
PORT = int(os.environ.get('PUNKTO_PORT', '8002'))

DATA_DIR = os.environ.get('PUNKTO_DATA_DIR', '/var/www/punkto/data')
NODE_NAME = os.environ.get('PUNKTO_NODE_NAME', 'punkto.xyz')
ATOMS_FILE = os.path.join(DATA_DIR, 'atoms.ndjson')

PUNKTO_RE = re.compile(r'^p:[0-9a-z]{12}(-[a-zA-Z0-9]+)?$')

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


def read_atoms_from_offset(offset):
    """
    Read atoms from byte offset to end of file.
    Returns (atoms_list, new_cursor).
    """
    atoms = []
    with open(ATOMS_FILE, 'rb') as f:
        # Clamp offset to file size
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
                pass  # skip corrupt lines

    return atoms, new_cursor


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
    """
    if 'punkto' not in data:
        return False, {
            'error': 'missing_field',
            'message': "Field 'punkto' is required",
        }
    if not PUNKTO_RE.match(str(data['punkto'])):
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
# Request handler
# ---------------------------------------------------------------------------

class PunktoHandler(BaseHTTPRequestHandler):
    server_version = 'PunktoNode/0.2'
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
            self.send_json(200, {
                'node': NODE_NAME,
                'version': '0.2',
                'capabilities': ['write', 'sync'],
            })
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
            if not PUNKTO_RE.match(canonical):
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

            cursor = append_atom(atom)
            self.send_json(201, {
                'status': 'accepted',
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
    server = HTTPServer((HOST, PORT), PunktoHandler)
    print(f'Punkto node listening on http://{HOST}:{PORT}')
    print(f'Storage: {ATOMS_FILE}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down.')
        server.server_close()
