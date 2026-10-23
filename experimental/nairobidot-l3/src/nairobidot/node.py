"""Mesh HTTP operations, local admission and reciprocal scoped catch-up."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from http.client import HTTPException
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen
import uuid

from .carrier import (MAX_C, MAX_R, Record, ResourceError, State, StructuralError,
                      address_ok, b64, decode_record, dumps, loads, unb64, validate)
from .spatial import matches, normalize, subscribed

MAX_HTTP = 8 * 1024 * 1024
MAX_PAGE = 32
MAX_CANDIDATES = 128
MAX_QUERY = 16384
LIMITS = {'body': MAX_C, 'record': MAX_R, 'page': MAX_PAGE,
          'http': MAX_HTTP, 'candidates': MAX_CANDIDATES}


class PeerError(RuntimeError):
    """An unreachable peer or failed peer operation; never a checkpoint."""


def origin(value: str) -> str:
    """The experimental Mesh transport accepts loopback HTTP origins only."""
    if not isinstance(value, str):
        raise StructuralError('peer-origin')
    try:
        parts = urlsplit(value)
        if (parts.scheme != 'http' or parts.hostname != '127.0.0.1' or
                parts.username is not None or parts.password is not None or
                parts.path not in ('', '/') or parts.query or parts.fragment or
                parts.port is None or not 1 <= parts.port <= 65535):
            raise ValueError()
        return f'http://127.0.0.1:{parts.port}'
    except ValueError as exc:
        raise StructuralError('peer-origin') from exc


def request(peer: str, path: str, body: dict | None = None, *, timeout: int = 5) -> dict:
    """Bounded standard-library HTTP client; resource errors retain their kind."""
    data = None if body is None else dumps(body)
    if data is not None and len(data) > MAX_HTTP:
        raise ResourceError('http-body-limit')
    req = Request(origin(peer) + path, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read(MAX_HTTP + 1)
            length = response.headers.get('Content-Length')
            if length is not None and len(raw) < int(length) and len(raw) <= MAX_HTTP:
                raise PeerError('truncated HTTP response')
            if len(raw) > MAX_HTTP:
                raise ResourceError('http-response-limit')
            result = loads(raw)
            if not isinstance(result, dict):
                raise PeerError('peer-response-shape')
            return result
    except ResourceError:
        raise
    except HTTPError as exc:
        exc.close()
        if exc.code == 413:
            raise ResourceError('peer-resource-refusal') from exc
        raise PeerError(f'peer-http-{exc.code}') from exc
    except (URLError, TimeoutError, OSError, ValueError, HTTPException) as exc:
        raise PeerError('peer-unreachable-or-malformed') from exc


@dataclass(frozen=True)
class Entry:
    address: str
    digest: str
    raw: bytes
    h: str | None
    state: State
    sequence: int

    def item(self) -> dict:
        return {'address': self.address, 'sha256': self.digest, 'record': b64(self.raw)}


class Node:
    """Mesh in-memory incarnation; stop/start retains entries and checkpoints."""
    def __init__(self, subscriptions: list[dict], peers: list[str] | None = None,
                 port: int = 0):
        if not isinstance(subscriptions, list):
            raise StructuralError('subscriptions')
        self.subscriptions = [normalize(s) for s in subscriptions]
        self.peers = {origin(p) for p in (peers or [])}
        self.epoch = uuid.uuid4().hex
        self.store: dict[str, Entry] = {}
        self.candidates: dict[str, Entry] = {}
        self.log: list[Entry] = []
        self._lock = threading.RLock()
        self._sync_lock = threading.RLock()
        self._port = port
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._push_checkpoints: dict[tuple, int] = {}
        self._pull_checkpoints: dict[tuple, dict] = {}

    @property
    def url(self) -> str:
        return f'http://127.0.0.1:{self._port}'

    def hello(self) -> dict:
        return {'protocol': 'punkti-mesh/0.6-draft', 'epoch': self.epoch,
                'subscriptions': self.subscriptions, 'peers': sorted(self.peers),
                'capabilities': ['push', 'range-mid', 'range-spatial', 'opaque-wrapper'],
                'limits': dict(LIMITS)}

    def add(self, raw: bytes | str | dict | Record, *, _validate_only: bool = False) -> dict:
        """Locally verify imports or wire items before deduplication (Mesh admission)."""
        if isinstance(raw, dict) and 'record' in raw:
            item = raw
            if set(item) != {'address', 'sha256', 'record'}:
                raise StructuralError('item-fields')
            address = item['address']
            if not address_ok(address):
                raise StructuralError('item-address')
            record_raw = unb64(item['record'])
            if len(record_raw) > MAX_R:
                raise ResourceError('record-limit')
            digest = hashlib.sha256(record_raw).hexdigest()
            if item['sha256'] != digest:
                raise StructuralError('transport-digest')
            namespace = address.split(':', 1)[0]
            if namespace != 'punkti/0.6':
                if namespace == 'punkti/0.5.1':
                    return {'state': State.STRUCTURAL.value, 'admitted': False,
                            'reason': 'legacy-adapter-unavailable'}
                state, h = State.VERSION, None
            else:
                # R is never heuristically interpreted as JSON on the wire.
                try:
                    result = validate(decode_record(record_raw))
                except StructuralError as exc:
                    return {'state': State.STRUCTURAL.value, 'admitted': False, 'reason': str(exc)}
                if result.record is not None and result.record.address != address:
                    raise StructuralError('address-mismatch')
                if result.state not in (State.VALID, State.ALGORITHM):
                    return {'state': result.state.value, 'admitted': False, 'reason': result.reason}
                state, h = result.state, result.record.atom['h']
        else:
            result = validate(raw)
            if result.state not in (State.VALID, State.ALGORITHM):
                return {'state': result.state.value, 'admitted': False, 'reason': result.reason}
            rec = result.record
            address, digest, record_raw = rec.address, rec.digest, rec.R
            state, h = result.state, rec.atom['h']
        if _validate_only:
            return {'state': state.value, 'admitted': False}
        with self._lock:
            if not subscribed(h, self.subscriptions):
                return {'state': state.value, 'admitted': False, 'reason': 'out-of-scope'}
            target, key = (self.store, address) if state == State.VALID else (self.candidates, digest)
            if key in target:
                return {'state': state.value, 'admitted': False, 'reason': 'duplicate'}
            if state != State.VALID and len(self.candidates) >= MAX_CANDIDATES:
                raise ResourceError('candidate-limit')
            entry = Entry(address, digest, record_raw, h, state, len(self.log) + 1)
            target[key] = entry
            self.log.append(entry)
            return {'state': state.value, 'admitted': True}

    def push(self, body: dict) -> dict:
        if not isinstance(body, dict) or not isinstance(body.get('records'), list):
            raise StructuralError('push-shape')
        if len(body['records']) > MAX_PAGE:
            raise ResourceError('batch-limit')
        results = []
        for item in body['records']:
            if not isinstance(item, dict) or set(item) != {'address', 'sha256', 'record'}:
                raise StructuralError('item-fields')
            self.add(item, _validate_only=True)
        for item in body['records']:
            results.append(self.add(item))
        return {'results': results}

    def page(self, query: dict) -> dict:
        """Mesh §Subscriptions and cursors: snapshot pages and spatial resumption."""
        if not isinstance(query, dict) or set(query) - {'mode', 'scope', 'lo', 'hi', 'cursor', 'limit'}:
            raise StructuralError('query-fields')
        mode = query.get('mode', 'spatial')
        if mode not in ('spatial', 'mid'):
            raise StructuralError('query-mode')
        scope = normalize(query.get('scope', {}))
        lo, hi = query.get('lo'), query.get('hi')
        if any(v is not None and not address_ok(v) for v in (lo, hi)):
            raise StructuralError('mid-bound')
        if mode == 'mid' and lo is not None and hi is not None and lo >= hi:
            raise StructuralError('equal or reversed bounds')
        limit = query.get('limit', MAX_PAGE)
        if type(limit) is not int or limit < 1:
            raise StructuralError('page-limit')
        if limit > MAX_PAGE:
            raise ResourceError('page-limit')
        binding = hashlib.sha256(dumps(dict(mode=mode, scope=scope, lo=lo, hi=hi))).hexdigest()
        token = query.get('cursor')
        with self._lock:
            high = len(self.log)
            if token is None:
                after, ceiling = (0 if mode == 'spatial' else None), high
            else:
                if (not isinstance(token, dict) or set(token) != {'epoch', 'scope', 'after', 'ceiling'}
                        or token['epoch'] != self.epoch or token['scope'] != binding):
                    raise StructuralError('cursor-binding')
                after, ceiling = token['after'], token['ceiling']
                if type(ceiling) is not int or not 0 <= ceiling <= high:
                    raise StructuralError('cursor-ceiling')
                if mode == 'spatial':
                    if type(after) is not int or not 0 <= after <= ceiling:
                        raise StructuralError('cursor-after')
                    if after == ceiling:
                        ceiling = high
                elif after is not None:
                    if (not isinstance(after, list) or len(after) != 2 or not address_ok(after[0])
                            or not isinstance(after[1], str) or len(after[1]) != 64
                            or any(c not in '0123456789abcdef' for c in after[1])):
                        raise StructuralError('cursor-after')
            entries = [e for e in self.log if e.sequence <= ceiling
                       and matches(e.h, scope) and (lo is None or e.address >= lo)
                       and (hi is None or e.address < hi)]
            if mode == 'spatial':
                entries = [e for e in entries if e.sequence > after]
            else:
                entries.sort(key=lambda e: (e.address, e.digest))
                if after is not None:
                    entries = [e for e in entries if (e.address, e.digest) > tuple(after)]
            records = []
            # Reserve bytes for the bounded token and response punctuation.
            used = 2048
            last = after
            for entry in entries[:limit]:
                item = entry.item()
                size = len(dumps(item)) + 1
                if used + size > MAX_HTTP:
                    break
                records.append(item)
                used += size
                last = entry.sequence if mode == 'spatial' else [entry.address, entry.digest]
            end = len(records) == len(entries)
            if end and mode == 'spatial':
                last = ceiling
            return {'records': records, 'cursor': {'epoch': self.epoch, 'scope': binding,
                    'after': last, 'ceiling': ceiling}, 'end': end}

    def pull(self, peer: str, *, mode: str = 'spatial', scope: dict | None = None,
             lo: str | None = None, hi: str | None = None, cursor: dict | None = None,
             limit: int = MAX_PAGE) -> dict:
        """Fetch and process one page; return its cursor only after all admissions."""
        q = dict(mode=mode, scope={} if scope is None else scope, lo=lo, hi=hi,
                 cursor=cursor, limit=limit)
        page = request(peer, '/pull?' + urlencode({'q': dumps(q).decode('utf-8')}))
        if (not isinstance(page.get('records'), list) or len(page['records']) > MAX_PAGE
                or type(page.get('end')) is not bool or not isinstance(page.get('cursor'), dict)):
            raise PeerError('pull-response-shape')
        for item in page['records']:
            if not isinstance(item, dict) or set(item) != {'address', 'sha256', 'record'}:
                raise PeerError('pull-item-shape')
            try:
                result = self.add(item, _validate_only=True)
            except StructuralError as exc:
                raise PeerError('pull-invalid-descriptor') from exc
            if result['state'] not in (State.VALID.value, State.ALGORITHM.value, State.VERSION.value):
                raise PeerError('pull-invalid-record')
        for item in page['records']:
            self.add(item)
        return page

    def _hello(self, peer: str) -> dict:
        info = request(peer, '/hello')
        if (info.get('protocol') != 'punkti-mesh/0.6-draft' or not isinstance(info.get('epoch'), str)
                or not isinstance(info.get('subscriptions'), list)):
            raise PeerError('hello-shape')
        info['subscriptions'] = [normalize(s) for s in info['subscriptions']]
        return info

    def _push_to(self, peer: str) -> None:
        info = self._hello(peer)
        scopes = info['subscriptions']
        key = (peer, info['epoch'], dumps(scopes), self.epoch)
        with self._lock:
            start = self._push_checkpoints.get(key, 0)
            high = len(self.log)
            entries = [e for e in self.log[start:high] if subscribed(e.h, scopes)]
        batch: list[dict] = []
        size = 32
        def deliver() -> None:
            if not batch:
                return
            response = request(peer, '/push', {'records': batch})
            results = response.get('results')
            if not isinstance(results, list) or len(results) != len(batch):
                raise PeerError('push-response-shape')
            for result in results:
                if (not isinstance(result, dict) or result.get('state') not in
                        (State.VALID.value, State.ALGORITHM.value, State.VERSION.value)
                        or type(result.get('admitted')) is not bool):
                    raise PeerError('push-rejected')
        for entry in entries:
            item = entry.item()
            amount = len(dumps(item)) + 1
            if len(batch) == MAX_PAGE or size + amount > MAX_HTTP:
                deliver()
                batch, size = [], 32
            batch.append(item)
            size += amount
        deliver()
        self._push_checkpoints[key] = high

    def _pull_from(self, peer: str) -> None:
        info = self._hello(peer)
        for scope in self.subscriptions:
            key = (peer, info['epoch'], dumps(scope))
            cursor = self._pull_checkpoints.get(key)
            while True:
                page = self.pull(peer, scope=scope, cursor=cursor)
                cursor = page['cursor']
                self._pull_checkpoints[key] = cursor
                if page['end']:
                    break

    def connect(self, peer: str) -> None:
        """Mesh §Discovery: local PUSH, reciprocal PUSH, local PULL, reciprocal PULL."""
        peer = origin(peer)
        if peer not in self.peers:
            raise StructuralError('unconfigured-peer')
        with self._sync_lock:
            self._push_to(peer)
            request(peer, '/sync', {'peer': self.url, 'phase': 'push'}, timeout=300)
            self._pull_from(peer)
            request(peer, '/sync', {'peer': self.url, 'phase': 'pull'}, timeout=300)

    def discover(self, peer: str) -> list[str]:
        """Return hints for explicit selection, without configuring or crawling them."""
        try:
            info = request(peer, '/hello')
            if (info.get('protocol') != 'punkti-mesh/0.6-draft'
                    or not isinstance(info.get('peers'), list)):
                return []
        except (PeerError, ResourceError, StructuralError, OSError):
            return []
        hints = set()
        for hint in info['peers']:
            try:
                hints.add(origin(hint))
            except StructuralError:
                continue
        return sorted(hints - {self.url})

    def sync_known(self) -> dict[str, str]:
        results = {}
        for peer in sorted(self.peers):
            try:
                self.connect(peer)
                results[peer] = 'ok'
            except (PeerError, ResourceError, StructuralError) as exc:
                results[peer] = str(exc)
        return results

    def start(self) -> Node:
        if self._server is not None:
            return self
        node = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.0'

            def log_message(self, format: str, *args: Any) -> None:
                pass

            def reply(self, status: int, value: dict) -> None:
                raw = dumps(value)
                self.send_response(status)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def handle_request(self) -> None:
                try:
                    url = urlsplit(self.path)
                    if self.command == 'GET' and url.path == '/hello':
                        result = node.hello()
                    elif self.command == 'GET' and url.path == '/pull':
                        if len(self.path) > MAX_QUERY:
                            raise ResourceError('query-limit')
                        params = parse_qs(url.query, strict_parsing=True)
                        if set(params) != {'q'} or len(params['q']) != 1:
                            raise StructuralError('pull-query')
                        result = node.page(loads(params['q'][0]))
                    elif self.command == 'POST' and url.path in ('/push', '/sync'):
                        if self.headers.get('Transfer-Encoding') is not None:
                            raise StructuralError('transfer-encoding')
                        lengths = self.headers.get_all('Content-Length', [])
                        if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit():
                            raise StructuralError('content-length')
                        length = int(lengths[0])
                        if length > MAX_HTTP:
                            raise ResourceError('http-body-limit')
                        self.connection.settimeout(5)
                        body_raw = self.rfile.read(length)
                        if len(body_raw) != length:
                            raise StructuralError('truncated-http-body')
                        body = loads(body_raw)
                        if not isinstance(body, dict):
                            raise StructuralError('request-object')
                        if url.path == '/push':
                            result = node.push(body)
                        else:
                            peer = origin(body.get('peer'))
                            if peer not in node.peers:
                                raise StructuralError('unconfigured-callback')
                            if body.get('phase') == 'push':
                                node._push_to(peer)
                            elif body.get('phase') == 'pull':
                                node._pull_from(peer)
                            else:
                                raise StructuralError('sync-phase')
                            result = {'ok': True}
                    else:
                        raise StructuralError('unknown-operation')
                    self.reply(200, result)
                except ResourceError as exc:
                    self.reply(413, {'kind': 'resource', 'reason': str(exc)})
                except PeerError as exc:
                    self.reply(502, {'kind': 'peer', 'reason': str(exc)})
                except (StructuralError, ValueError, TimeoutError) as exc:
                    self.reply(400, {'kind': 'request', 'reason': str(exc)})

            do_GET = handle_request
            do_POST = handle_request

        self._server = ThreadingHTTPServer(('127.0.0.1', self._port), Handler)
        self._port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        kwargs={'poll_interval': 0.05}, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._thread.join()
            self._server = None
            self._thread = None
