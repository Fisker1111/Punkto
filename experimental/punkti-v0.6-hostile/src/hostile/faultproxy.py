"""Bounded, deterministic HTTP/1.x impairments over real loopback TCP sockets."""
from collections import Counter, deque
import json
import select
import socket
import socketserver
import threading
import time
from urllib.parse import urlsplit

CAPTURE = 4 * 1024 * 1024
MESSAGE = 8 * 1024 * 1024 + 65536


def read_message(sock):
    """Read Content-Length framing with select; never buffer an unbounded peer."""
    data = bytearray()
    total = None
    while total is None or len(data) < total:
        if not select.select([sock], [], [], 5)[0]:
            raise TimeoutError('proxy upstream/read timeout')
        chunk = sock.recv(min(65536, MESSAGE + 1 - len(data)))
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > MESSAGE:
            raise ValueError('proxy message budget exceeded')
        if total is None and b'\r\n\r\n' in data:
            header, body = data.split(b'\r\n\r\n', 1)
            lengths = [int(line.split(b':', 1)[1]) for line in header.split(b'\r\n')[1:]
                       if line.lower().startswith(b'content-length:')]
            total = len(header) + 4 + (lengths[0] if lengths else 0)
            if total > MESSAGE:
                raise ValueError('proxy message budget exceeded')
    return bytes(data)


class FaultProxy:
    """One directive per request, default pass; plans are consumed under a lock.

    Captures share a 4 MiB budget per exchange; at most 4096 exchanges retained.
    Counters include evicted exchanges. Original and actually forwarded bytes are
    separate, including duplicate responses. Socket errors are evidence, not
    unhandled server-thread exceptions. close() wakes delays and joins workers.
    """
    def __init__(self, target_url, seed=7):
        self.target = urlsplit(target_url)
        if self.target.scheme != 'http' or self.target.hostname != '127.0.0.1' or not self.target.port:
            raise ValueError('loopback HTTP origin required')
        self.seed = seed
        self.exchanges = deque(maxlen=4096)
        self._plan = deque()
        self._counts = Counter()
        self._condition = threading.Condition()
        self._active = 0
        self._blocked = False
        self._closed = threading.Event()
        self.fired = threading.Event()
        self._seen = set()
        self._gate = threading.Event()
        self._gate.set()
        self._held_fault = None
        proxy = self

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                proxy._handle(self.request)

        class Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = False

        self.server = Server(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.server.server_address[1]}'
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={'poll_interval': .01}, daemon=True)
        self.thread.start()

    def plan(self, directives):
        for directive in directives:
            parts = directive.split(':')
            name = parts[0]
            arity = {'pass': 1, 'drop_before': 1, 'drop_after': 1, 'corrupt': 1,
                     'duplicate': 1, 'shuffle': 1, 'delay': 2, 'truncate': 2,
                     'stall': 2, 'slowdrip': 3}
            if name not in arity or len(parts) != arity[name]:
                raise ValueError('unknown fault directive')
            if any(float(x) < 0 for x in parts[1:]):
                raise ValueError('negative fault parameter')
            if name == 'slowdrip' and int(parts[1]) < 1:
                raise ValueError('positive chunk required')
        with self._condition:
            self._plan = deque(directives)
            self.fired.clear()

    def hold_fault(self, name):
        self._held_fault = name
        self._gate.clear()

    def release_fault(self):
        self._gate.set()

    def wait_fault(self, name, timeout=10):
        with self._condition:
            return self._condition.wait_for(lambda: name in self._seen, timeout)

    def partition(self, blocked):
        with self._condition:
            self._blocked = bool(blocked)

    def stats(self):
        self.idle()
        with self._condition:
            return dict(self._counts)

    def idle(self):
        with self._condition:
            if not self._condition.wait_for(lambda: self._active == 0, timeout=12):
                raise TimeoutError('proxy workers did not finish')

    def close(self):
        self._closed.set()
        self._gate.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def _handle(self, client):
        start = time.monotonic()
        row = dict(method='', path='', fault='partition', request_bytes=0, response_bytes=0,
                   upstream_request_bytes=0, upstream_response_bytes=0)
        captures = {}
        budget = CAPTURE

        def capture(key, raw):
            nonlocal budget
            captures[key] = raw[:budget]
            budget -= len(captures[key])

        def upstream(raw):
            with socket.create_connection(('127.0.0.1', self.target.port), timeout=5) as peer:
                peer.sendall(raw)
                row['upstream_request_bytes'] += len(raw)
                response = read_message(peer)
                row['upstream_response_bytes'] += len(response)
                return response

        def send(raw):
            # Count bytes actually accepted by the client socket, including partial writes.
            view = memoryview(raw)
            while view:
                size = client.send(view)
                if not size:
                    raise ConnectionError('closed client')
                row['response_bytes'] += size
                view = view[size:]

        with self._condition:
            self._active += 1
            blocked = self._blocked
        try:
            if blocked:
                return
            client.settimeout(5)
            raw = read_message(client)
            if not raw:
                return
            row['request_bytes'] = len(raw)
            capture('request', raw)
            row['method'], row['path'], _ = raw.split(b'\r\n', 1)[0].decode().split(' ', 2)
            with self._condition:
                fault = self._plan.popleft() if self._plan else 'pass'
            row['fault'] = fault
            name, *params = fault.split(':')
            if name == 'drop_before':
                return
            if name == 'stall':
                self.fired.set()
                self._closed.wait(float(params[0]))
                return
            if name == 'shuffle':
                head, body = raw.split(b'\r\n\r\n', 1)
                obj = json.loads(body)
                obj['records'].reverse()  # deterministic even for a one-element batch
                body = json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()
                lines = [line for line in head.split(b'\r\n')
                         if not line.lower().startswith(b'content-length:')]
                raw = b'\r\n'.join(lines) + f'\r\nContent-Length: {len(body)}\r\n\r\n'.encode() + body
            capture('forwarded_request', raw)
            response = upstream(raw)
            capture('upstream_response', response)
            if name == 'duplicate':
                capture('duplicate_response', upstream(raw))
            self.fired.set()
            with self._condition:
                self._seen.add(name)
                self._condition.notify_all()
            if name == self._held_fault and not self._gate.wait(10):
                raise TimeoutError('fault barrier not released')
            if name == 'drop_after':
                return
            if name == 'delay':
                self._closed.wait(float(params[0]) / 1000)
            elif name == 'truncate':
                response = response[:int(params[0])]
            elif name == 'corrupt':
                offset = response.index(b'\r\n\r\n') + 4
                # Flip exactly one JSON body byte; retain Content-Type and length.
                changed = bytearray(response)
                changed[offset] ^= 1
                row['corrupt_offset'] = offset
                response = bytes(changed)
            capture('response', response)
            if name == 'slowdrip':
                size, delay = int(params[0]), float(params[1]) / 1000
                for offset in range(0, len(response), size):
                    send(response[offset:offset + size])
                    if self._closed.wait(delay):
                        break
            else:
                send(response)
        except (OSError, ValueError, KeyError, IndexError) as exc:
            row['error'] = f'{type(exc).__name__}: {exc}'
        finally:
            row['elapsed_ms'] = round((time.monotonic() - start) * 1000, 3)
            row.update(captures)
            with self._condition:
                self.exchanges.append(row)
                self._counts[row['fault'].split(':')[0]] += 1
                self._active -= 1
                self._condition.notify_all()
