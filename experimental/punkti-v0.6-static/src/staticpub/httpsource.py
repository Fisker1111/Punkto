"""Stdlib-only static HTTP source with optional URL mount prefix and metrics."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread


class QuietFiles(SimpleHTTPRequestHandler):
    def __init__(self, *args, mount_prefix='', **kwargs):
        self.mount_prefix = mount_prefix.rstrip('/')
        super().__init__(*args, **kwargs)

    def log_message(self, *_):
        pass

    def translate_path(self, path):
        if self.mount_prefix:
            if path == self.mount_prefix:
                path = '/'
            elif path.startswith(self.mount_prefix + '/'):
                path = path[len(self.mount_prefix):]
            else:
                return str(Path(self.directory) / '.not-found')
        return super().translate_path(path)

    def end_headers(self):
        self.server.request_count += 1
        self.server.paths.append(self.path)
        super().end_headers()

    def copyfile(self, source, outputfile):
        data = source.read()
        self.server.body_bytes += len(data)
        outputfile.write(data)


class StaticSource:
    def __init__(self, directory, port=0, mount_prefix=''):
        self.directory = str(directory)
        self.port = port
        self.mount_prefix = mount_prefix.rstrip('/')

    def __enter__(self):
        handler = partial(QuietFiles, directory=self.directory, mount_prefix=self.mount_prefix)
        self.server = ThreadingHTTPServer(('127.0.0.1', self.port), handler)
        self.server.request_count = 0
        self.server.body_bytes = 0
        self.server.paths = []
        self.url = f'http://127.0.0.1:{self.server.server_port}'
        self.thread = Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.02}, daemon=True)
        self.thread.start()
        return self

    @property
    def request_count(self):
        return self.server.request_count

    @property
    def body_bytes(self):
        return self.server.body_bytes

    @property
    def paths(self):
        return list(self.server.paths)

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
