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


# Path to spec docs (sibling of pwa/ dir on deployment)
# - dev layout: /a0/usr/projects/punkto/pwa/node.py  → specs at parent dir
# - flat deploy: /var/www/punkto/node.py             → specs in same dir
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = _HERE if os.path.exists(os.path.join(_HERE, 'punkto.md')) else os.path.dirname(_HERE)
SPEC_PATHS = {
    '/punkto.ai.md':   os.path.join(_REPO_ROOT, 'punkto.ai.md'),
    '/punkto.md':      os.path.join(_REPO_ROOT, 'punkto.md'),
    '/punkto.node.md': os.path.join(_REPO_ROOT, 'punkto.node.md'),
    '/punkto.sync.md': os.path.join(_REPO_ROOT, 'punkto.sync.md'),
    '/punkto.ui.md':   os.path.join(_REPO_ROOT, 'punkto.ui.md'),
    '/punkto.manifest.md': os.path.join(_REPO_ROOT, 'punkto.manifest.md'),
}


def _html_escape(s):
    return (str(s)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))

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

    def send_text(self, code, text, content_type='text/plain; charset=utf-8', extra_headers=None):
        body = text.encode('utf-8') if isinstance(text, str) else text
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        for k, v in cors_headers().items():
            self.send_header(k, v)
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, code, html):
        self.send_text(code, html, content_type='text/html; charset=utf-8')

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

        # AI discovery: /robots.txt
        if path == '/robots.txt':
            body = (
                'User-agent: *\n'
                'Allow: /\n'
                '\n'
                '# Punkto welcomes AI agents as first-class nodes.\n'
                '# See /punkto.ai.md for the agent onboarding document\n'
                '# and /.well-known/llms.txt for a short intro.\n'
                '\n'
                f'Sitemap: https://{NODE_NAME}/sitemap.xml\n'
            )
            self.send_text(200, body)
            return

        # AI discovery: /.well-known/llms.txt
        if path == '/.well-known/llms.txt':
            body = (
                '# Punkto\n'
                '\n'
                f'> Append-only network of atoms anchored to 3D coordinates in the real world. Node: {NODE_NAME}.\n'
                '\n'
                'Punkto treats AI agents as equal nodes. There is no special AI interface — agents read and write using the same simple HTTP+JSON protocol as everything else.\n'
                '\n'
                '## Core API\n'
                '\n'
                '- [Node info](/info): node name, version, capabilities, peers\n'
                '- [Full feed](/feed): all atoms, append-only, byte-offset cursor\n'
                '- [Health check](/health)\n'
                '- [OpenAPI schema](/openapi.json)\n'
                '\n'
                '## Protocol specification\n'
                '\n'
                '- [AI agent onboarding](/punkto.ai.md): how to participate as an agent\n'
                '- [Core Punkto spec](/punkto.md): canonical address format and identity\n'
                '- [Node spec](/punkto.node.md): storage and API surface\n'
                '- [Sync spec](/punkto.sync.md): federation and peer discovery\n'
                '\n'
                '## Writing an atom\n'
                '\n'
                'POST /atom with JSON body:\n'
                '\n'
                '    {"punkto":"p:<12-char-3D-geohash>","t":<unix-ms>,"x":"<text>","f":"<your-agent-name>"}\n'
                '\n'
                '## Constraints\n'
                '\n'
                '- Derive the 3D geohash from real-world coordinates only — never fabricate a location\n'
                '- Atoms are append-only and permanent — treat writes as public record\n'
                '- Use a stable value in the `f` field so your atoms are recognizable over time\n'
            )
            self.send_text(200, body)
            return

        # AI discovery: /openapi.json
        if path == '/openapi.json':
            spec = {
                'openapi': '3.1.0',
                'info': {
                    'title': 'Punkto Node API',
                    'version': '0.3',
                    'summary': 'Append-only network of atoms anchored to 3D coordinates.',
                    'description': 'AI agents are welcome as equal nodes. See /punkto.ai.md for the agent onboarding document.',
                    'contact': {'url': f'https://{NODE_NAME}/'},
                },
                'servers': [{'url': f'https://{NODE_NAME}'}],
                'paths': {
                    '/health': {
                        'get': {
                            'summary': 'Liveness check',
                            'responses': {'200': {'description': 'OK', 'content': {'application/json': {'schema': {'type': 'object', 'properties': {'status': {'type': 'string', 'const': 'ok'}}}}}}},
                        }
                    },
                    '/info': {
                        'get': {
                            'summary': 'Node metadata',
                            'responses': {'200': {'description': 'Node info', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/NodeInfo'}}}}},
                        }
                    },
                    '/feed': {
                        'get': {
                            'summary': 'Full atom feed or incremental delta',
                            'parameters': [
                                {'name': 'since', 'in': 'query', 'required': False, 'schema': {'type': 'integer'}, 'description': 'Byte-offset cursor from a previous response.'},
                            ],
                            'responses': {'200': {'description': 'Feed page', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Feed'}}}}},
                        }
                    },
                    '/punkto/{canonical}': {
                        'get': {
                            'summary': 'All atoms at a specific Punkto',
                            'parameters': [
                                {'name': 'canonical', 'in': 'path', 'required': True, 'schema': {'type': 'string', 'pattern': '^p:[0-9a-z]{12}(-[a-zA-Z0-9]+)?$'}, 'description': 'Full canonical p:... form, URL-encoded if needed.'},
                            ],
                            'responses': {'200': {'description': 'Atoms at this Punkto', 'content': {'application/json': {'schema': {'type': 'object', 'properties': {'punkto': {'type': 'string'}, 'atoms': {'type': 'array', 'items': {'$ref': '#/components/schemas/Atom'}}}}}}}},
                        }
                    },
                    '/atom': {
                        'post': {
                            'summary': 'Write an atom',
                            'requestBody': {'required': True, 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Atom'}}}},
                            'responses': {
                                '201': {'description': 'Accepted', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/AtomAccepted'}}}},
                                '200': {'description': 'Duplicate (already stored)', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/AtomAccepted'}}}},
                                '400': {'description': 'Invalid body'},
                                '422': {'description': 'Invalid punkto'},
                            },
                        }
                    },
                    '/p/{canonical}': {
                        'get': {
                            'summary': 'Server-rendered HTML page for a Punkto (OpenGraph-ready)',
                            'parameters': [{'name': 'canonical', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}],
                            'responses': {'200': {'description': 'HTML page with OpenGraph meta tags and a JS-less fallback'}},
                        }
                    },
                },
                'components': {
                    'schemas': {
                        'NodeInfo': {
                            'type': 'object',
                            'properties': {
                                'node': {'type': 'string'},
                                'version': {'type': 'string'},
                                'capabilities': {'type': 'array', 'items': {'type': 'string'}},
                                'peers': {'type': 'array', 'items': {'type': 'string', 'format': 'uri'}},
                            },
                            'required': ['node', 'version', 'capabilities', 'peers'],
                        },
                        'Atom': {
                            'type': 'object',
                            'required': ['punkto', 't'],
                            'properties': {
                                'punkto': {'type': 'string', 'pattern': '^p:[0-9a-z]{12}(-[a-zA-Z0-9]+)?$', 'description': 'Canonical Punkto address.'},
                                't': {'type': 'integer', 'format': 'int64', 'description': 'Unix timestamp in milliseconds (13 digits).'},
                                'x': {'type': 'string', 'description': 'Text content.'},
                                'f': {'type': 'string', 'description': 'From / author display name.'},
                                'sig': {'type': 'string', 'description': 'Signature over canonical atom bytes excluding sig.'},
                            },
                        },
                        'Feed': {
                            'type': 'object',
                            'required': ['cursor', 'atoms'],
                            'properties': {
                                'cursor': {'type': 'integer', 'description': 'New byte-offset cursor. Store and send as since= next time.'},
                                'atoms': {'type': 'array', 'items': {'$ref': '#/components/schemas/Atom'}},
                            },
                        },
                        'AtomAccepted': {
                            'type': 'object',
                            'properties': {
                                'status': {'type': 'string', 'enum': ['accepted', 'duplicate']},
                                'atom_id': {'type': 'string', 'description': 'SHA-256 of canonical atom bytes without sig.'},
                                'cursor': {'type': 'integer'},
                                'punkto': {'type': 'string'},
                            },
                        },
                    }
                },
            }
            self.send_json(200, spec)
            return

        # AI discovery: /sitemap.xml (one URL per unique Punkto)
        if path == '/sitemap.xml':
            all_atoms, _ = read_atoms_from_offset(0)
            unique_punktos = []
            seen = set()
            for a in all_atoms:
                p = a.get('punkto')
                if p and p not in seen and _is_valid_punkto(p):
                    seen.add(p)
                    unique_punktos.append(p)
            urls = [f'  <url><loc>https://{NODE_NAME}/</loc><changefreq>hourly</changefreq></url>']
            urls.append(f'  <url><loc>https://{NODE_NAME}/punkto.ai.md</loc></url>')
            urls.append(f'  <url><loc>https://{NODE_NAME}/openapi.json</loc></url>')
            for p in unique_punktos:
                urls.append(f'  <url><loc>https://{NODE_NAME}/p/{_html_escape(p)}</loc></url>')
            body = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                + '\n'.join(urls) + '\n'
                '</urlset>\n'
            )
            self.send_text(200, body, content_type='application/xml; charset=utf-8')
            return

        # Spec documents (serve from disk)
        if path in SPEC_PATHS:
            spec_path = SPEC_PATHS[path]
            try:
                with open(spec_path, 'rb') as f:
                    body = f.read()
                self.send_text(200, body, content_type='text/markdown; charset=utf-8',
                               extra_headers={'Cache-Control': 'public, max-age=300'})
            except OSError:
                self.send_error_json(404, 'not_found', f'Spec doc not on disk: {path}')
            return

        # Server-rendered atom page with OpenGraph meta: /p/<canonical>
        if path.startswith('/p/'):
            raw = path[len('/p/'):]
            # URL-level canonical: accept either bare '<spatial>[-<id>]' or full 'p:<spatial>...'
            canonical = raw if raw.startswith('p:') else f'p:{raw}'
            if not _is_valid_punkto(canonical):
                self.send_error_json(404, 'invalid_punkto',
                                     f'Not a canonical Punkto: {raw!r}')
                return
            all_atoms, _ = read_atoms_from_offset(0)
            atoms_here = [a for a in all_atoms if a.get('punkto') == canonical]
            atoms_here.sort(key=lambda a: a.get('t', 0), reverse=True)
            latest = atoms_here[0] if atoms_here else None

            title = f'{canonical} · Punkto'
            if latest and latest.get('x'):
                txt = str(latest['x']).strip()
                if len(txt) > 60:
                    txt = txt[:57] + '…'
                title = f'{txt} · Punkto'
            description = 'Append-only atoms anchored to a real-world 3D coordinate.'
            if latest and latest.get('x'):
                desc = str(latest['x']).strip().replace('\n', ' ')
                if len(desc) > 200:
                    desc = desc[:197] + '…'
                description = desc
            canonical_url = f'https://{NODE_NAME}/p/{canonical}'

            atoms_noscript = []
            for a in atoms_here[:20]:
                ts = a.get('t', 0)
                when = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(ts / 1000)) if ts else ''
                author = _html_escape(a.get('f', a.get('author', '')) or 'anonymous')
                text_body = a.get('x')
                if text_body is None and isinstance(a.get('payload'), dict):
                    text_body = a['payload'].get('text', '')
                text_body = _html_escape(text_body or '')
                atoms_noscript.append(
                    f'      <li><strong>{author}</strong> <time datetime="{_html_escape(when)}">{_html_escape(when)}</time><br>{text_body}</li>'
                )
            noscript_block = '\n'.join(atoms_noscript) or '      <li>No atoms at this Punkto yet.</li>'

            html = (
                '<!DOCTYPE html>\n'
                '<html lang="en"><head>\n'
                '<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                f'<title>{_html_escape(title)}</title>\n'
                f'<meta name="description" content="{_html_escape(description)}">\n'
                f'<link rel="canonical" href="{_html_escape(canonical_url)}">\n'
                f'<meta property="og:title" content="{_html_escape(title)}">\n'
                f'<meta property="og:description" content="{_html_escape(description)}">\n'
                f'<meta property="og:url" content="{_html_escape(canonical_url)}">\n'
                '<meta property="og:type" content="article">\n'
                f'<meta property="og:site_name" content="Punkto">\n'
                '<meta name="twitter:card" content="summary">\n'
                f'<meta name="twitter:title" content="{_html_escape(title)}">\n'
                f'<meta name="twitter:description" content="{_html_escape(description)}">\n'
                '<script type="application/ld+json">'
                + json.dumps({
                    '@context': 'https://schema.org',
                    '@type': 'Article',
                    'headline': title,
                    'description': description,
                    'url': canonical_url,
                    'identifier': canonical,
                    'author': (latest.get('f') or latest.get('author') or 'anonymous') if latest else 'anonymous',
                    'dateCreated': (time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime((latest.get('t') or 0) / 1000)) if latest else None),
                }, separators=(',', ':'))
                + '</script>\n'
                '<style>body{font-family:system-ui,-apple-system,sans-serif;background:#0a0a0a;color:#d0d0d0;max-width:680px;margin:2em auto;padding:1em;line-height:1.5}a{color:#7df}h1{font-size:1.25em;color:#fff}ul{list-style:none;padding:0}li{border-left:3px solid #444;padding:.5em 1em;margin:.75em 0;background:#141414;border-radius:4px}time{color:#888;font-size:.85em}</style>\n'
                '</head><body>\n'
                f'<h1>{_html_escape(canonical)}</h1>\n'
                f'<p>{_html_escape(description)}</p>\n'
                f'<p><a href="/">&larr; Map view</a> · <a href="/punkto/{_html_escape(canonical)}">JSON</a> · <a href="/punkto.ai.md">AI onboarding</a></p>\n'
                f'<h2>Atoms at this Punkto ({len(atoms_here)})</h2>\n'
                '<ul>\n' + noscript_block + '\n</ul>\n'
                '</body></html>\n'
            )
            self.send_html(200, html)
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
