"""Offline deny-list, HTTP forwarding and CONNECT tests using loopback only."""
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
from pathlib import Path
import socket
import tempfile
import threading
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'independent_origin_block_proxy.py'
spec = importlib.util.spec_from_file_location('block_proxy', SCRIPT)
proxy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proxy)


class ProxyTests(unittest.TestCase):
    def setUp(self):
        class Origin(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Length', '12')
                self.end_headers()
                self.wfile.write(b'origin bytes')

            def log_message(self, *args):
                pass

        self.origin = ThreadingHTTPServer(('127.0.0.1', 0), Origin)
        self.proxy = proxy.Proxy(('127.0.0.1', 0), {'blocked.example', '127.0.0.2', '::1'})
        for server in (self.origin, self.proxy):
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(thread.join)
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)

    def request(self, url):
        connection = http.client.HTTPConnection('127.0.0.1', self.proxy.server_port, timeout=3)
        self.addCleanup(connection.close)
        connection.request('GET', url)
        return connection.getresponse()

    def test_blocked_host_no_http_response(self):
        with self.assertRaises(http.client.RemoteDisconnected):
            self.request('http://BLOCKED.example.:1234/record')

    def test_blocked_literal_ip(self):
        with self.assertRaises(http.client.RemoteDisconnected):
            self.request('http://127.0.0.2:1234/record')

    def test_allowed_http_forwarded(self):
        response = self.request(f'http://127.0.0.1:{self.origin.server_port}/record?x=1')
        self.assertEqual(response.status, 200)
        self.assertEqual(response.read(), b'origin bytes')

    def connect(self, authority):
        sock = socket.create_connection(('127.0.0.1', self.proxy.server_port), timeout=3)
        self.addCleanup(sock.close)
        sock.sendall(f'CONNECT {authority} HTTP/1.1\r\nHost: {authority}\r\n\r\n'.encode())
        return sock

    def test_connect_blocked_no_http_response(self):
        self.assertEqual(self.connect('blocked.example:443').recv(4096), b'')

    def test_connect_blocked_ipv6(self):
        self.assertEqual(self.connect('[::1]:443').recv(4096), b'')

    def test_connect_allowed_transports_bytes(self):
        sock = self.connect(f'127.0.0.1:{self.origin.server_port}')
        head = b''
        while not head.endswith(b'\r\n\r\n'):
            head += sock.recv(1)
        self.assertIn(b'200 Connection Established', head)
        sock.sendall(b'GET / HTTP/1.0\r\nHost: localhost\r\n\r\n')
        body = b''
        while chunk := sock.recv(4096):
            body += chunk
        self.assertIn(b'200 OK', body)
        self.assertTrue(body.endswith(b'origin bytes'))

    def test_inventory_hosts_and_ports(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'origins'
            path.write_text('https://Blocked.example:443\nhttp://127.0.0.2:8080\nhttps://[::1]:444\n')
            self.assertEqual(proxy.load_hosts(path), {'blocked.example', '127.0.0.2', '::1'})

    def test_invalid_or_empty_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'origins'
            for value in ('', 'not-an-origin', 'https://host:bad', 'https://user@host',
                          'http://host/path'):
                with self.subTest(value=value):
                    path.write_text(value)
                    with self.assertRaises(ValueError):
                        proxy.load_hosts(path)


if __name__ == '__main__':
    unittest.main()
