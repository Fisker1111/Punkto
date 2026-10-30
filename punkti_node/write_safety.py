"""Provider-side public /submit admission guard (not part of the Punkti protocol).

Protects hosted submission without rewriting/weakening the signed atom contract.
All policy is node-local. It is NOT an authentication or anti-Sybil mechanism.
"""
from contextlib import contextmanager
import ipaddress
import os
import threading
import time


class AdmissionRejected(Exception):
    def __init__(self, message, http_status=429, retry_after=1):
        super().__init__(message)
        self.http_status = http_status
        self.retry_after = retry_after


def _dir_bytes(root):
    total = 0
    for folder, dirs, files in os.walk(root, followlinks=False):
        for name in files:
            path = os.path.join(folder, name)
            if not os.path.islink(path):
                total += os.stat(path, follow_symlinks=False).st_size
    return total


class WriteSafety:
    """In-process token buckets + admission concurrency + disk headroom gate.

    Public IP is extracted from a proxy-injected header ONLY when the immediate
    socket peer belongs to an operator-configured trusted proxy network.
    Untrusted XFF/real-IP headers are ignored, never promoted to identity.
    """

    MAX_CLIENTS = 4096

    def __init__(self, config):
        self.enabled = config['enabled']
        self.rate = float(config['per_ip_rate'])
        self.burst = float(config['per_ip_burst'])
        self.global_rate = float(config['global_rate'])
        self.global_burst = float(config['global_burst'])
        self.max_in_flight = config['max_in_flight']
        self.max_batch = config['max_batch']
        self.max_http_bytes = config['max_http_bytes']
        self.max_data_bytes = config['max_data_bytes']
        self.min_free_bytes = config['min_free_bytes']
        self.proxy_networks = [ipaddress.ip_network(cidr, strict=False)
                               for cidr in config['trusted_proxy_cidrs']]
        self.lock = threading.Lock()
        self.clients = {}
        self.global_tokens = self.global_burst
        self.global_updated = time.monotonic()
        self.in_flight = 0

    def _client(self, peer, headers):
        try:
            address = ipaddress.ip_address(peer)
        except ValueError as exc:
            raise AdmissionRejected('invalid connection source', 403, 0) from exc
        if any(address in net for net in self.proxy_networks):
            # The trusted proxy MUST overwrite this header with its actual
            # validated client IP; never accept a comma-separated chain.
            claimed = headers.get('X-Punkto-Client-IP')
            if not claimed or ',' in claimed or claimed != claimed.strip():
                raise AdmissionRejected('trusted proxy client IP missing/invalid', 403, 0)
            try:
                address = ipaddress.ip_address(claimed)
            except ValueError as exc:
                raise AdmissionRejected('invalid trusted proxy client IP', 403, 0) from exc
        return str(address)

    def _reserve(self, client):
        now = time.monotonic()
        with self.lock:
            if self.in_flight >= self.max_in_flight:
                raise AdmissionRejected('submit concurrency limit', 503, 1)
            global_tokens = min(self.global_burst,
                                self.global_tokens + max(0, now - self.global_updated) * self.global_rate)
            state = self.clients.get(client)
            tokens = (min(self.burst, state[0] + max(0, now - state[1]) * self.rate)
                      if state else self.burst)
            if global_tokens < 1 or tokens < 1:
                raise AdmissionRejected('submit rate limit', 429, 1)
            if client not in self.clients and len(self.clients) >= self.MAX_CLIENTS:
                expiry = max(60.0, 2 * self.burst / self.rate)
                self.clients = {ip: state for ip, state in self.clients.items()
                                if now - state[1] < expiry}
                if len(self.clients) >= self.MAX_CLIENTS:
                    raise AdmissionRejected('submit rate limit', 429, 1)
            self.clients[client] = (tokens - 1, now)
            self.global_tokens = global_tokens - 1
            self.global_updated = now
            self.in_flight += 1

    def _free(self):
        with self.lock:
            self.in_flight -= 1

    def check_storage(self, data_path, request_size):
        """Check conservative budget before admission; external writes need
        separate operator disk monitoring and a tested emergency shutoff.
        """
        try:
            stats = os.statvfs(data_path)
            free = stats.f_bavail * stats.f_frsize
            # Append log, indices, manifests and previous immutable versions
            # amplify wire bytes; keep a conservative reserve.
            incoming = max(1048576, request_size * 8)
            if free < self.min_free_bytes + incoming:
                raise AdmissionRejected('insufficient free storage', 507, 0)
            if self.max_data_bytes:
                used = _dir_bytes(data_path)
                if used + incoming > self.max_data_bytes:
                    raise AdmissionRejected('node data budget exhausted', 507, 0)
        except OSError as exc:
            raise AdmissionRejected('storage budget unavailable', 503, 1) from exc

    @contextmanager
    def admit(self, peer, headers, data_path):
        if not self.enabled:
            yield
            return
        length_header = headers.get('Content-Length', '')
        try:
            length = int(length_header)
        except (ValueError, TypeError) as exc:
            raise AdmissionRejected('Content-Length required', 411, 0) from exc
        if length < 0:
            raise AdmissionRejected('Content-Length required', 411, 0)
        if length > self.max_http_bytes:
            raise AdmissionRejected('submit request size limit', 413, 0)
        client = self._client(peer, headers)
        self._reserve(client)
        try:
            self.check_storage(data_path, length)
            yield
        finally:
            self._free()
