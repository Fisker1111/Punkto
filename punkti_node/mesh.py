"""In-memory reference Mesh with real bounded HTTP PUSH and paginated Range PULL."""
import hashlib
import json
import threading
import uuid
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from carrier import (BODY_LIMIT, RECORD_LIMIT, ResourceLimit, State, VERSION,
                     address_ok, b64, unb64, validate)
from spatial import Subscription

MAX_PAGE = 32
MAX_HTTP = 4 * RECORD_LIMIT
MAX_CANDIDATES = 128


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def packed(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def wire(raw, address=None):
    observation = validate(raw) if address is None else None
    return dict(address=address or observation.address, sha256=digest(raw), record=b64(raw))


def request(url, path, payload=None):
    data = None if payload is None else packed(payload)
    req = Request(url + path, data=data, headers={'Content-Type': 'application/json'})
    with urlopen(req, timeout=5) as response:
        raw = response.read(MAX_HTTP + 1)
    if len(raw) > MAX_HTTP:
        raise ResourceLimit('HTTP response limit')
    return json.loads(raw)


def peer_url(url):
    parsed = urlparse(url)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname or
            parsed.path or parsed.query or parsed.fragment or
            parsed.username is not None or parsed.password is not None or
            any(c.isspace() for c in url) or '?' in url or '#' in url):
        raise ValueError('absolute http(s) peer origin required')
    parsed.port  # Validate an explicit port, if present.
    return url


@dataclass(frozen=True)
class Entry:
    raw: bytes
    address: str
    h: str | None
    state: State
    seq: int

    def wire(self):
        return dict(address=self.address, sha256=digest(self.raw), record=b64(self.raw))


class Node:
    def __init__(self, subscriptions=None, peers=(), epoch=None):
        self.subscriptions = tuple([Subscription()] if subscriptions is None else subscriptions)
        self.peers = set(map(peer_url, peers))
        self.epoch = epoch or uuid.uuid4().hex  # Store incarnation, never atom ordering.
        self.api_prefix = '/api'  # Deployment alias; not a mesh protocol change.
        self.web = None
        self.store = {}
        self.candidates = {}  # Transport-digest keyed unverified variants, bounded.
        self.log = []
        self.cursors = {}
        self.push_cursors = {}
        self.lock = threading.RLock()
        self.server = None
        self.url = None
        self.metrics = dict(push_requests=0, push_records=0, pull_requests=0, pull_records=0)

    def api_path(self, path):
        prefix = self.api_prefix
        return path[len(prefix):] if prefix and path.startswith(prefix + '/') else path

    def wants(self, h):
        if h is None:  # Unknown carrier cannot authenticate any spatial address.
            return Subscription() in self.subscriptions
        return any(s.matches(h) for s in self.subscriptions)

    def admit(self, item):
        if not isinstance(item, dict):
            raise ValueError('record wrapper required')
        raw = unb64(item['record'])
        if len(raw) > RECORD_LIMIT:
            raise ResourceLimit('record limit')
        if digest(raw) != item['sha256']:
            raise ValueError('transport digest mismatch')
        address = item['address']
        if address is not None and not address_ok(address):
            raise ValueError('declared address')
        namespace = address.split(':')[0] if address else VERSION
        if namespace == VERSION:
            observation = validate(raw)
            state, h = observation.state, observation.h
            if observation.address is not None and address != observation.address:
                raise ValueError('address mismatch')
        elif namespace == 'punkti/0.5.1':
            raise ValueError('legacy adapter not supported')
        else:
            state, h = State.VERSION, None
        # Never use a claimed state, or dedup before local verification.
        if state in (State.STRUCTURAL, State.PROVENANCE):
            return dict(state=state.value, admitted=False)
        if not self.wants(h):
            return dict(state=state.value, admitted=False, reason='out-of-scope')
        with self.lock:
            key = address if state == State.VALID else digest(raw)
            target = self.store if state == State.VALID else self.candidates
            if key in target:
                return dict(state=state.value, admitted=False, reason='duplicate')
            if state != State.VALID and len(target) >= MAX_CANDIDATES:
                raise ResourceLimit('candidate capacity')
            entry = Entry(raw, address, h, state, len(self.log) + 1)
            target[key] = entry
            self.log.append(entry)
            self.persisted(entry)
        return dict(state=state.value, admitted=True)

    def persisted(self, entry):
        pass

    def after_sync(self):
        pass

    def special_route(self, method, path, query):
        return None

    def add(self, raw):
        return self.admit(wire(raw))

    def hello(self):
        return dict(protocol='punkti-mesh/0.6-draft', epoch=self.epoch,
                    subscriptions=[s.wire() for s in self.subscriptions], peers=sorted(self.peers),
                    capabilities=['push', 'range-mid', 'range-spatial', 'opaque-wrapper'],
                    limits=dict(body=BODY_LIMIT, record=RECORD_LIMIT, page=MAX_PAGE,
                                http=MAX_HTTP, candidates=MAX_CANDIDATES))

    def page(self, query):
        if not isinstance(query, dict):
            raise ValueError('query object required')
        mode = query.get('mode', 'spatial')
        size = query.get('limit', MAX_PAGE)
        if type(size) is not int or not 1 <= size <= MAX_PAGE:
            raise ValueError('page size')
        scope = Subscription(**query.get('scope', {}))
        lo, hi = query.get('lo'), query.get('hi')
        if mode not in ('mid', 'spatial'):
            raise ValueError('range mode')
        if mode == 'mid' and (any(v is not None and not address_ok(v) for v in (lo, hi)) or
                              (lo is not None and hi is not None and lo >= hi)):
            raise ValueError('MID bounds')
        binding = digest(packed(dict(mode=mode, scope=scope.wire(), lo=lo, hi=hi)))
        cursor = query.get('cursor')
        with self.lock:
            top = len(self.log)
            if cursor is not None:
                if not isinstance(cursor, dict) or cursor.get('epoch') != self.epoch or cursor.get('scope') != binding:
                    raise ValueError('cursor store/scope mismatch; restart from null')
                after, ceiling = cursor['after'], cursor['ceiling']
                if type(ceiling) is not int or not 0 <= ceiling <= top:
                    raise ValueError('cursor high-water')
                if mode == 'spatial':
                    if type(after) is not int or not 0 <= after <= ceiling:
                        raise ValueError('sequence cursor')
                    if after == ceiling:
                        ceiling = top  # Resume a finished subscription at a new high-water.
                elif not isinstance(after, list) or len(after) != 2 or not all(isinstance(v, str) for v in after):
                    raise ValueError('address cursor')
            else:
                after, ceiling = (0 if mode == 'spatial' else ['', '']), top
            history = self.log[after:ceiling] if mode == 'spatial' else self.log[:ceiling]
            entries = [e for e in history if
                       (scope.matches(e.h) if e.h is not None else scope == Subscription()) and
                       (lo is None or e.address >= lo) and (hi is None or e.address < hi)]
            key = (lambda e: e.seq) if mode == 'spatial' else (lambda e: [e.address, digest(e.raw)])
            entries = sorted((e for e in entries if key(e) > after), key=key)
            selected, byte_count = [], 0
            for entry in entries[:size]:
                cost = len(packed(entry.wire()))
                if selected and byte_count + cost > MAX_HTTP - 4096:
                    break
                selected.append(entry)
                byte_count += cost
            end = len(selected) == len(entries)
            next_after = key(selected[-1]) if selected else after
            if end and mode == 'spatial':
                next_after = ceiling
            token = dict(epoch=self.epoch, scope=binding, after=next_after, ceiling=ceiling)
            self.metrics['pull_requests'] += 1
            self.metrics['pull_records'] += len(selected)
            return dict(records=[e.wire() for e in selected], cursor=token, end=end)

    def pull(self, peer, scope=None, mode='spatial', lo=None, hi=None, limit=MAX_PAGE, resume=True):
        scope = scope or Subscription()
        query = dict(mode=mode, scope=scope.wire(), lo=lo, hi=hi, limit=limit)
        cache_key = (peer, digest(packed(query)))
        cursor = self.cursors.get(cache_key) if resume and mode == 'spatial' else None
        info = request(peer, '/hello')
        if info['protocol'] != 'punkti-mesh/0.6-draft':
            raise ValueError('unsupported Mesh protocol')
        if cursor and cursor['epoch'] != info['epoch']:
            cursor = None
        while True:
            query['cursor'] = cursor
            result = request(peer, '/pull?' + urlencode({'q': packed(query).decode()}))
            for item in result['records']:
                self.admit(item)
            cursor = result['cursor']
            self.cursors[cache_key] = cursor  # Only advance after processing the entire page.
            if result['end']:
                self.after_sync()
                return cursor

    def push_to(self, peer):
        info = request(peer, '/hello')
        if info['protocol'] != 'punkti-mesh/0.6-draft':
            raise ValueError('unsupported Mesh protocol')
        scopes = [Subscription(**s) for s in info['subscriptions']]
        cache_key = (peer, info['epoch'], digest(packed(info['subscriptions'])))
        with self.lock:
            after = self.push_cursors.get(cache_key, 0)
            top = len(self.log)
            entries = [e for e in self.log if after < e.seq <= top and
                       (any(s.matches(e.h) for s in scopes) if e.h is not None else Subscription() in scopes)]
        # One record/request bounds transfer even at the maximum record size.
        for entry in entries:
            request(peer, '/push', {'records': [entry.wire()]})
        self.push_cursors[cache_key] = top
        self.after_sync()

    def catchup(self, peer):
        for scope in self.subscriptions:
            self.pull(peer, scope)

    def connect(self, peer):
        peer_url(peer)
        self.peers.add(peer)
        # Both immediate PUSH directions precede both Range PULL directions.
        self.push_to(peer)
        request(peer, '/sync', dict(peer=self.url, phase='push'))
        self.catchup(peer)
        request(peer, '/sync', dict(peer=self.url, phase='pull'))

    def discover(self):
        """Read peer hints; callers explicitly choose which origins to connect to."""
        hints = set()
        for peer in sorted(self.peers):
            try:
                hints.update(peer_url(p) for p in request(peer, '/hello')['peers'])
            except (OSError, ValueError):
                continue
        return hints - {self.url}

    def sync_known(self):
        failures = []
        for peer in sorted(self.peers):
            try:
                self.connect(peer)
            except OSError:
                failures.append(peer)
        return failures

    def start(self, port=0, host='127.0.0.1', advertise_url=None):
        node = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def reply(self, status, payload):
                raw = packed(payload)
                self.send_response(getattr(payload, 'http_status', status))
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def dispatch(self):
                parsed = urlparse(self.path)
                # Deployment aliases preserve the native peer protocol surface.
                parsed = parsed._replace(path=node.api_path(parsed.path))
                special = node.special_route(self.command, parsed.path, parsed.query)
                if special is not None:
                    return special
                if self.command == 'GET':
                    if parsed.path == '/hello':
                        return node.hello()
                    if parsed.path == '/pull':
                        return node.page(json.loads(parse_qs(parsed.query)['q'][0]))
                elif self.command == 'POST':
                    length = int(self.headers.get('Content-Length', '-1'))
                    if not 0 <= length <= MAX_HTTP:
                        raise ResourceLimit('request size')
                    data = json.loads(self.rfile.read(length))
                    if not isinstance(data, dict):
                        raise ValueError('request object required')
                    if parsed.path == '/push':
                        records = data['records']
                        if not isinstance(records, list) or not 1 <= len(records) <= MAX_PAGE:
                            raise ValueError('push batch size')
                        node.metrics['push_requests'] += 1
                        node.metrics['push_records'] += len(records)
                        return {'results': [node.admit(item) for item in records]}
                    if parsed.path == '/sync':
                        peer = peer_url(data['peer'])
                        if peer not in node.peers:
                            raise ValueError('callback peer must be configured locally')
                        if data['phase'] == 'push':
                            node.push_to(peer)
                        elif data['phase'] == 'pull':
                            node.catchup(peer)
                        else:
                            raise ValueError('sync phase')
                        return {'ok': True}
                # Static fallback uses the original path so unknown API routes stay errors.
                if node.web and node.web.serve(self, urlparse(self.path).path):
                    return None
                raise ValueError('unknown operation')

            def handle_request(self):
                try:
                    result = self.dispatch()
                    if result is not None:
                        self.reply(200, result)
                except ResourceLimit as exc:
                    self.reply(413, {'error': str(exc), 'kind': 'resource'})
                except (ValueError, KeyError, TypeError, IndexError) as exc:
                    self.reply(400, {'error': str(exc)})
                except OSError as exc:
                    self.reply(502, {'error': str(exc)})

            do_GET = do_POST = do_HEAD = handle_request

        self.server = ThreadingHTTPServer((host, port), Handler)
        url_host = '127.0.0.1' if host == '0.0.0.0' else host
        self.url = advertise_url or f'http://{url_host}:{self.server.server_port}'
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.02}, daemon=True)
        self.thread.start()
        return self

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join()
            self.server = None
