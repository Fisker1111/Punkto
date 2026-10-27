"""Isolated JSON-lines processes and restartable loopback TCP forwarding."""
import json
import os
from pathlib import Path
import select
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent


def http(url, path, body=None):
    assert urlsplit(url).hostname == '127.0.0.1'
    raw = body if isinstance(body, bytes) else (None if body is None else json.dumps(body).encode())
    req = Request(url + path, data=raw, headers={'Content-Type': 'application/json'})
    try:
        with urlopen(req, timeout=10) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        with exc:
            return exc.code, json.load(exc)


class Adapter:
    def __init__(self, kind, config=None):
        self.kind = kind
        self.temp = tempfile.TemporaryDirectory(prefix='punkti-interop-')
        self.stderr = tempfile.TemporaryFile(mode='w+')
        args = [sys.executable, '-E', str(HERE / f'{kind}_adapter.py')]
        if config is None:
            args += ['--stdin']
        else:
            path = Path(self.temp.name) / 'config.json'
            path.write_text(json.dumps(config))
            args += ['--serve', str(path)]
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        self.process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=self.stderr, text=True, bufsize=1, env=env, cwd=self.temp.name)
        self.url = None
        if config is not None:
            ready = self.read()
            self.url, self.epoch = ready['url'], ready['epoch']

    def read(self):
        if not select.select([self.process.stdout], [], [], 20)[0]:
            raise TimeoutError('adapter response timeout')
        line = self.process.stdout.readline()
        if not line:
            self.stderr.seek(0)
            raise RuntimeError('adapter exited: ' + self.stderr.read())
        return json.loads(line)

    def rpc(self, cmd, **args):
        self.process.stdin.write(json.dumps(dict(cmd=cmd, **args)) + '\n')
        self.process.stdin.flush()
        return self.read()

    def close(self):
        try:
            if self.process.poll() is None:
                self.rpc('shutdown')
                self.process.wait(timeout=5)
        finally:
            if self.process.poll() is None:
                self.process.kill()
                self.process.wait()
            self.process.stdin.close()
            self.process.stdout.close()
            self.stderr.close()
            self.temp.cleanup()


class Proxy:
    """Raw TCP relay; captures complete HTTP requests/responses as evidence."""
    def __init__(self, target):
        self.target = urlsplit(target)
        assert self.target.hostname == '127.0.0.1'
        self.port = 0
        self.exchanges = []
        self.start()

    @property
    def url(self):
        return f'http://127.0.0.1:{self.port}'

    def start(self):
        proxy = self
        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                sent, received = bytearray(), bytearray()
                with socket.create_connection(('127.0.0.1', proxy.target.port), timeout=5) as upstream:
                    try:
                        while True:
                            ready, _, _ = select.select([self.request, upstream], [], [], 10)
                            if not ready:
                                break
                            for source in ready:
                                data = source.recv(65536)
                                if not data:
                                    return
                                if source is self.request:
                                    sent.extend(data)
                                    upstream.sendall(data)
                                else:
                                    received.extend(data)
                                    self.request.sendall(data)
                    finally:
                        proxy.exchanges.append((bytes(sent), bytes(received)))
        class Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True
        self.server = Server(('127.0.0.1', self.port), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .02}, daemon=True)
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join()
            self.server = None
