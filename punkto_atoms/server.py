"""HTTP API and peer pull service for the isolated atom store."""
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import math
import os
import socket
import sqlite3
import threading
import time

import requests
from urllib.parse import parse_qs, urlsplit

from . import __version__
from .atoms_core import ValidationError

LOG = logging.getLogger(__name__)
MAX_BODY = 65536
MAX_INT = 9223372036854775807


@dataclass
class Config:
    port: int = 8020
    db: str = '/data/atoms.db'
    node: str = field(default_factory=socket.gethostname)
    peers: list = field(default_factory=list)
    sync_interval: float = 20

    @classmethod
    def from_env(cls):
        config = cls(
            port=int(os.getenv('PUNKTO_ATOMS_PORT', '8020')),
            db=os.getenv('PUNKTO_ATOMS_DB', '/data/atoms.db'),
            node=os.getenv('PUNKTO_NODE_NAME', socket.gethostname()),
            peers=[p.strip().rstrip('/') for p in os.getenv('PUNKTO_ATOMS_PEERS', '').split(',') if p.strip()],
            sync_interval=float(os.getenv('PUNKTO_ATOMS_SYNC_INTERVAL', '20')))
        if not 1 <= config.port <= 65535:
            raise ValueError('PUNKTO_ATOMS_PORT must be 1..65535')
        if not math.isfinite(config.sync_interval) or config.sync_interval <= 0:
            raise ValueError('PUNKTO_ATOMS_SYNC_INTERVAL must be positive and finite')
        for peer in config.peers:
            if urlsplit(peer).scheme not in ('http', 'https') or not urlsplit(peer).netloc:
                raise ValueError('peer must be an HTTP(S) base URL')
        return config


class AtomService:
    def __init__(self, store, config):
        self.store = store
        self.config = config
        self.stop = threading.Event()
        self.sync_lock = threading.Lock()
        self.last_sync_status = 'never'
        self.last_sync_at = None
        self.last_sync_new = 0

    def info(self):
        return dict(self.store.stats(), peer=self.config.peers[0] if self.config.peers else '',
                    peers=list(self.config.peers), last_sync_status=self.last_sync_status,
                    last_sync_at=self.last_sync_at, last_sync_new=self.last_sync_new,
                    version=__version__, cursors=self.store.cursors())

    def sync_once(self):
        """Pull using persistent cursors in each peer's own sequence space."""
        with self.sync_lock:
            added = 0
            failed = False
            for peer in list(self.config.peers):
                peer = peer.strip().rstrip('/')
                try:
                    response = requests.get(peer + '/atoms/v1/info', timeout=10)
                    response.raise_for_status()
                    head = response.json()['head_seq']
                    if type(head) is not int or head < 0:
                        raise ValueError('invalid peer head_seq')
                    since = self.store.get_cursor(peer)
                    if head > since:
                        response = requests.get(peer + '/atoms/v1/sync',
                                                params={'since': since}, timeout=10)
                        response.raise_for_status()
                        items = response.json()
                        if not isinstance(items, list):
                            raise ValueError('peer inventory must be a list')
                        # Prevalidate the entire response before inserting anything.
                        # A malformed later record must not advance the peer cursor.
                        from .atoms_core import validate_atom
                        for item in items:
                            validate_atom(item)
                        for item in items:
                            _, inserted = self.store.insert(item)
                            added += int(inserted)
                        self.store.set_cursor(peer, head)
                except (requests.RequestException, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
                    failed = True
                    LOG.warning('Peer sync failed for %s: %s', peer, exc)
            self.last_sync_status = 'error' if failed else 'ok'
            self.last_sync_at = int(time.time() * 1000)
            self.last_sync_new = added
            return added

    def sync_loop(self):
        while not self.stop.is_set():
            self.sync_once()
            self.stop.wait(self.config.sync_interval)


def make_server(service, host='0.0.0.0', port=None):
    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            self.wfile.write(body)

        def send_error(self, code, message=None, explain=None):
            self.respond(code, {'error': 'http_error', 'message': message or self.responses[code][0]})

        def do_OPTIONS(self):
            self.respond(200, {})

        def do_POST(self):
            if urlsplit(self.path).path != '/atoms/v1':
                self.send_error(404)
                return
            try:
                if self.headers.get('Transfer-Encoding'):
                    raise ValidationError('Transfer-Encoding is unsupported')
                lengths = self.headers.get_all('Content-Length', [])
                if len(lengths) != 1:
                    raise ValidationError('one Content-Length header is required')
                size = int(lengths[0])
                if size < 0:
                    raise ValidationError('negative Content-Length')
                if size > MAX_BODY:
                    self.send_error(413, 'body exceeds 64KB')
                    return
                self.connection.settimeout(10)
                raw = self.rfile.read(size)
                if len(raw) != size:
                    raise ValidationError('incomplete body')
                value = json.loads(raw)
                mid, added = service.store.insert(value)
                self.respond(201 if added else 200,
                             {'status': 'accepted' if added else 'duplicate', 'mid': mid})
            except (ValueError, UnicodeError, TimeoutError) as exc:
                self.respond(400, {'error': 'invalid_atom', 'message': str(exc)})

        def do_GET(self):
            try:
                parsed = urlsplit(self.path)
                params = parse_qs(parsed.query, keep_blank_values=True, max_num_fields=20)
                path = parsed.path

                def number(key, default, kind, low, high):
                    values = params.get(key, [str(default)])
                    if len(values) != 1:
                        raise ValueError(f'duplicate {key}')
                    value = kind(values[0])
                    if not low <= value <= high:
                        raise ValueError(f'{key} out of range')
                    return value

                if path == '/atoms/v1/health':
                    self.respond(200, {'status': 'ok', 'node': service.config.node})
                elif path == '/atoms/v1/info':
                    self.respond(200, service.info())
                elif path.startswith('/atoms/v1/mid/'):
                    item = service.store.fetch(path[len('/atoms/v1/mid/'):])
                    if item is None:
                        self.send_error(404, 'atom not found')
                    else:
                        self.respond(200, item)
                elif path == '/atoms/v1/sync':
                    since = number('since', 0, int, 0, MAX_INT)
                    self.respond(200, service.store.inventory(since))
                elif path == '/atoms/v1/feed':
                    bounds = {}
                    for dimension, bound in (('lat', 90), ('lon', 180), ('t', MAX_INT)):
                        low = 0 if dimension == 't' else -bound
                        kind = int if dimension == 't' else float
                        bounds['min_' + dimension] = number('min_' + dimension, low, kind, low, bound)
                        bounds['max_' + dimension] = number('max_' + dimension, bound, kind, low, bound)
                        if bounds['min_' + dimension] > bounds['max_' + dimension]:
                            raise ValueError(f'min_{dimension} exceeds max_{dimension}')
                    bounds['limit'] = number('limit', 100, int, 1, 10000)
                    self.respond(200, service.store.feed(**bounds))
                else:
                    self.send_error(404)
            except (ValueError, UnicodeError) as exc:
                self.respond(400, {'error': 'invalid_query', 'message': str(exc)})

    return ThreadingHTTPServer((host, service.config.port if port is None else port), Handler)
