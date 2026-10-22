"""Subprocess adapters, deterministic fixtures and implementation-owned store checks."""
import base64
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[4]
HOME = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experimental/nairobidot-l3/interop'))
from driver import Adapter as BaseAdapter, http  # plumbing only; neither implementation is imported here
from hostile.faultproxy import FaultProxy


class Adapter(BaseAdapter):
    """Preserve existing adapter protocol, clean up even when readiness fails."""
    def __init__(self, *args, **kwargs):
        self._ready = False
        try:
            super().__init__(*args, **kwargs)
        except Exception:
            if hasattr(self, 'process'):
                if self.process.poll() is None:
                    self.process.kill()
                    self.process.wait(timeout=5)
                self.close()
            raise

    def read(self):
        result = super().read()
        if not self._ready:
            if 'url' not in result:
                raise RuntimeError('adapter readiness failed: ' + repr(result))
            self._ready = True
        return result


def spec(i):
    return dict(seed=f'hostile-{i}', t=1700000000000 + i, h='gggh00000000',
                x=f'hostile opaque {i}', refs=[], ext='')


def item(m):
    return dict(address=m['address'], record=m['R'], sha256=m['sha256'])


def body(exchange, key='upstream_response'):
    return json.loads(exchange[key].split(b'\r\n\r\n', 1)[1])


def query(exchange):
    return json.loads(parse_qs(urlsplit(exchange['path']).query)['q'][0])


def serial(value):
    if isinstance(value, bytes):
        return {'base64': base64.b64encode(value).decode(), 'length': len(value)}
    if isinstance(value, dict):
        return {k: serial(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serial(v) for v in value]
    return value


class Runner:
    def __init__(self, case, direction='ref'):
        self.case, self.direction = case, direction
        self.nodes, self.proxies, self.errors = [], [], []
        self.retries = 0
        self.notes = {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        for proxy in reversed(self.proxies):
            proxy.close()
        for node in reversed(self.nodes):
            node.close()

    def node(self, kind=None, port=0):
        node = Adapter(kind or self.direction, dict(subscriptions=[{}], peers=[], port=port))
        self.nodes.append(node)
        return node

    def proxy(self, node):
        proxy = FaultProxy(node.url)
        self.proxies.append(proxy)
        return proxy

    def pair(self):
        a = self.node()
        b = self.node('nb' if self.direction == 'ref' else 'ref')
        p = self.proxy(b)
        self.call(a, 'configure', peers=[p.url])
        self.call(b, 'configure', peers=[a.url])
        return a, b, p

    def call(self, node, command, **args):
        result = node.rpc(command, **args)
        assert 'error' not in result, result
        return result

    def fail(self, operation):
        try:
            result = operation()
        except (OSError, ValueError) as exc:
            result = dict(ok=False, error=f'{type(exc).__name__}: {exc}')
        assert result.get('ok') is False, result
        self.errors.append(result)
        return result

    def pull(self, node, peer):
        # The clean-room public pull is one page. Its real reciprocal pull phase
        # owns the persisted checkpoint and full sweep, as reference pull does.
        if node.kind == 'ref':
            return node.rpc('pull', peer=peer)
        self.call(node, 'configure', peers=[peer])
        status, result = http(node.url, '/sync', dict(peer=peer, phase='pull'))
        return dict(ok=status == 200, **({'error': result} if status != 200 else {}))

    def seed(self, node, start, count):
        records = [self.call(node, 'add', spec=spec(i)) for i in range(start, start + count)]
        assert all(m['admission']['admitted'] for m in records)
        return records

    def state(self, node):
        return self.call(node, 'state')

    def equal(self, nodes, records):
        expected = sorted(m['address'] for m in records)
        assert len(expected) == len(set(expected))
        for node in nodes:
            state = self.state(node)
            assert sorted(e['address'] for e in state['valid']) == expected
            assert state['candidates'] == [], state
            assert len(state['log']) == len(expected), state
            assert [e['seq'] for e in state['log']] == list(range(1, len(expected) + 1))
            assert {e['address']: e['sha256'] for e in state['valid']} == {
                m['address']: m['sha256'] for m in records}
        return expected

    def retry_pull(self, a, p):
        self.retries += 1
        assert self.pull(a, p.url)['ok']

    def pulls(self, p):
        p.idle()
        return [e for e in p.exchanges if e['path'].startswith('/pull?')]

    def finish(self, nodes, records):
        addresses = self.equal(nodes, records)
        proxies = []
        for p in self.proxies:
            stats = p.stats()
            exchanges = list(p.exchanges)
            proxies.append(dict(stats=stats, exchanges=exchanges))
        exchanges = [e for p in proxies for e in p['exchanges']]
        return dict(status='PASS', scenario=self.case, initiator=self.direction,
                    admitted_set_equality=True, addresses=addresses,
                    store_sizes=[len(self.state(n)['valid']) for n in nodes],
                    candidate_sizes=[len(self.state(n)['candidates']) for n in nodes],
                    http_requests=sum(bool(e['method']) for e in exchanges),
                    upstream_requests=sum(2 if e['fault'] == 'duplicate' else
                                          bool(e['upstream_request_bytes']) for e in exchanges),
                    wire_bytes=sum(e[k] for e in exchanges for k in
                                   ('request_bytes', 'response_bytes', 'upstream_request_bytes', 'upstream_response_bytes')),
                    measurement_scope='instrumented proxy links, both TCP legs; callback/control HTTP excluded',
                    retries=self.retries, errors=self.errors, notes=self.notes, proxies=proxies)


def report(name, rows):
    folder = HOME / 'evidence'
    folder.mkdir(exist_ok=True)
    (folder / (name + '.json')).write_text(json.dumps(serial(rows), indent=2) + '\n')
    print(f'\n{name}: scenario | direction | result | stores | requests | wire bytes | retries')
    for row in rows:
        print(f"{row['scenario']} | {row['initiator']} | {row['status']} | "
              f"{row.get('store_sizes')} | {row.get('http_requests')} | "
              f"{row.get('wire_bytes')} | {row.get('retries')}")
