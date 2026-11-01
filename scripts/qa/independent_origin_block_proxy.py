#!/usr/bin/env python3
"""Disposable loopback HTTP proxy for a coordinator-supplied founder deny list.

Denied hosts are disconnected without an HTTP response. HTTPS remains end-to-end
TLS: CONNECT only transports bytes and never terminates or disables TLS.
"""
import argparse
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
from pathlib import Path
import select
import socket
import sys
from urllib.parse import urlsplit


def normalized_host(host):
    host = host.rstrip('.').lower()
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        return host.encode('idna').decode('ascii')


def load_hosts(path):
    hosts = set()
    for origin in Path(path).read_text().splitlines():
        parsed = urlsplit(origin)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname or
                parsed.username is not None or parsed.password is not None or
                parsed.path not in ('', '/') or parsed.query or parsed.fragment):
            raise ValueError(f'invalid inventory origin: {origin!r}')
        _ = parsed.port  # Validate explicit ports too.
        hosts.add(normalized_host(parsed.hostname))
    if not hosts:
        raise ValueError('complete nonempty founder-origin inventory required')
    return hosts


class Proxy(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, blocked_hosts):
        self.blocked_hosts = {normalized_host(h) for h in blocked_hosts}
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    # No HTTP refusal response: any HTTP status must fail the negative control.
    def denied(self, host):
        if normalized_host(host) in self.server.blocked_hosts:
            self.log_message('DENY %s', host)
            self.close_connection = True
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            return True
        return False

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.scheme != 'http' or not parsed.hostname or parsed.username is not None:
            self.send_error(400, 'absolute HTTP URL required')
            return
        if self.denied(parsed.hostname):
            return
        upstream = None
        try:
            upstream = http.client.HTTPConnection(parsed.hostname, parsed.port or 80, timeout=10)
            excluded = {'host', 'connection', 'proxy-connection', 'proxy-authorization',
                        'keep-alive', 'transfer-encoding', 'te', 'trailer', 'upgrade'}
            excluded.update(h.strip().lower() for h in self.headers.get('Connection', '').split(','))
            headers = {k: v for k, v in self.headers.items() if k.lower() not in excluded}
            path = parsed.path or '/'
            if parsed.query:
                path += '?' + parsed.query
            upstream.request('GET', path, headers=headers)
            response = upstream.getresponse()
            body = response.read()
            self.send_response(response.status, response.reason)
            excluded.update(h.strip().lower() for h in response.getheader('Connection', '').split(','))
            for key, value in response.getheaders():
                if key.lower() not in excluded | {'content-length'}:
                    self.send_header(key, value)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (OSError, ValueError, http.client.HTTPException):
            self.send_error(502, 'upstream unavailable')
        finally:
            if upstream is not None:
                upstream.close()

    def do_CONNECT(self):
        try:
            parsed = urlsplit('//' + self.path)
            if (not parsed.hostname or parsed.port is None or parsed.username is not None or
                    parsed.path or parsed.query or parsed.fragment):
                raise ValueError('host:port required')
            host, port = parsed.hostname, parsed.port
        except ValueError:
            self.send_error(400, 'host:port required')
            return
        if self.denied(host):
            return
        try:
            upstream = socket.create_connection((host, port), timeout=10)
        except OSError:
            self.send_error(502, 'upstream unavailable')
            return
        with upstream:
            self.send_response(200, 'Connection Established')
            self.end_headers()
            self.wfile.flush()
            self.close_connection = True
            # The client starts TLS after receiving 200; its hostname/cert checks
            # are unchanged. This proxy never sees decrypted HTTPS content.
            sockets = [self.connection, upstream]
            try:
                while True:
                    readable, _, _ = select.select(sockets, [], [], 30)
                    if not readable:
                        return
                    for source in readable:
                        data = source.recv(65536)
                        if not data:
                            return
                        (upstream if source is self.connection else self.connection).sendall(data)
            except OSError:
                return


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origins', required=True)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args(argv)
    try:
        with Proxy(('127.0.0.1', args.port), load_hosts(args.origins)) as server:
            print(f'Listening on 127.0.0.1:{server.server_port}', flush=True)
            server.serve_forever()
    except (OSError, ValueError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
