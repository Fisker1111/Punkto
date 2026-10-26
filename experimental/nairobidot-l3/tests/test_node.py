"""Mesh loopback admission, pagination, reconnect and multi-hop convergence."""
import copy
import hashlib
import json
from pathlib import Path
import select
import socket
import subprocess
import sys
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from vectors import atom
from nairobidot.carrier import ResourceError, StructuralError, b64, dumps, from_atom
from nairobidot.node import MAX_HTTP, Node, PeerError, request


def item(index=0, h='', **kwargs):
    return from_atom(atom(index, h, **kwargs)).item()


def candidate(index=0):
    a = atom(index, alg='future-signature')
    a['sig'] = b64(index.to_bytes(4, 'big') + b'opaque')
    return from_atom(a).item()


def opaque(index=0):
    raw = f'opaque future {index}'.encode()
    return {'address': f'future:{index:04x}', 'sha256': hashlib.sha256(raw).hexdigest(),
            'record': b64(raw)}


class NodeTests(unittest.TestCase):
    def setUp(self):
        self.nodes = []

    def tearDown(self):
        for node in self.nodes:
            node.stop()

    def node(self, scopes=None):
        node = Node([{}] if scopes is None else scopes).start()
        self.nodes.append(node)
        return node

    def pair(self):
        a, b = self.node(), self.node()
        a.peers.add(b.url)
        b.peers.add(a.url)
        return a, b

    def http_error(self, node, path, body, code):
        with self.assertRaises(HTTPError) as caught:
            urlopen(Request(node.url + path, data=dumps(body),
                            headers={'Content-Type': 'application/json'}), timeout=5)
        self.assertEqual(caught.exception.code, code)
        value = json.loads(caught.exception.read())
        caught.exception.close()
        return value

    def test_admission_and_bad_variant_never_poisons(self):
        n = self.node()
        good = item()
        bad = atom()
        bad['sig'] = b64(bytes(64))
        forged = from_atom(bad).item()
        self.http_error(n, '/push', {'records': [dict(forged, state='VALID')]}, 400)
        results = request(n.url, '/push', {'records': [forged, good, good, forged]})['results']
        self.assertEqual([r['state'] for r in results],
                         ['INVALID-provenance', 'VALID', 'VALID', 'INVALID-provenance'])
        self.assertEqual([r['admitted'] for r in results], [False, True, False, False])
        self.assertEqual(len(n.store), 1)
        self.assertEqual(n.store[good['address']].item(), good)
        damaged = copy.deepcopy(good)
        damaged['sha256'] = '0' * 64
        with self.assertRaises(StructuralError):
            n.add(damaged)
        damaged = copy.deepcopy(good)
        damaged['address'] = 'punkti/0.6:' + '0' * 64
        with self.assertRaises(StructuralError):
            n.add(damaged)
        raw = b'not a canonical R'
        malformed = {'address': good['address'], 'record': b64(raw),
                     'sha256': hashlib.sha256(raw).hexdigest()}
        self.assertEqual(n.add(malformed)['state'], 'INVALID-structural')
        self.assertEqual(len(n.log), 1)

    def test_candidate_retention_and_scope(self):
        a, b = self.pair()
        c, future = candidate(), opaque()
        self.assertEqual(a.add(c), {'state': 'UNVERIFIABLE-alg', 'admitted': True})
        self.assertEqual(a.add(future), {'state': 'OPAQUE-version', 'admitted': True})
        self.assertFalse(a.store)
        a.connect(b.url)
        self.assertEqual(set(a.candidates), set(b.candidates))
        self.assertEqual(b.candidates[c['sha256']].item(), c)
        self.assertEqual(b.candidates[future['sha256']].item(), future)
        limited = self.node([{'z_min': '-1000'}])
        self.assertEqual(limited.add(future)['reason'], 'out-of-scope')
        self.assertEqual(limited.add(item())['reason'], 'out-of-scope')
        self.assertTrue(limited.add(item(h='000000000000_-18'))['admitted'])
        self.assertFalse(self.node([]).add(item())['admitted'])

    def test_wire_queries_and_strict_json_requests(self):
        n = self.node()
        n.add(item(h='s00000000000_23'))
        def query(raw):
            return '/pull?' + urlencode({'q': raw})
        with self.assertRaises(HTTPError) as caught:
            urlopen(n.url + query('{"scope":{"z_min":-0}}'), timeout=5)
        self.assertEqual(caught.exception.code, 400)
        for raw, status in [('{"limit":33}', 413), ('{"limit":0}', 400),
                            ('{"limit":1,"limit":2}', 400), ('{"cursor":{}}', 400)]:
            with self.assertRaises(HTTPError) as caught:
                urlopen(n.url + query(raw), timeout=5)
            self.assertEqual(caught.exception.code, status)
            caught.exception.close()
        with self.assertRaises(HTTPError) as caught:
            urlopen(Request(n.url + '/push', data=b'{"records":[],"records":[]}'), timeout=5)
        self.assertEqual(caught.exception.code, 400)
        caught.exception.close()
        legacy = opaque()
        legacy['address'] = 'punkti/0.5.1:' + '0' * 64
        self.assertEqual(n.add(legacy)['reason'], 'legacy-adapter-unavailable')

    def test_candidate_capacity_does_not_promote_or_evict(self):
        n = Node([{}])
        for i in range(128):
            self.assertTrue(n.add(opaque(i))['admitted'])
        self.assertFalse(n.add(opaque())['admitted'])
        with self.assertRaises(ResourceError):
            n.add(candidate())
        self.assertTrue(n.add(item())['admitted'])
        self.assertEqual(len(n.log), 129)

    def test_spatial_cursor_gaps_resume_and_binding(self):
        n = self.node()
        for i, h in enumerate(('000000000000_-18', '', 's00000000000_23', '', 's00000000001_23.025')):
            n.add(item(i, h))
        scope = {'xy_lo': 's'}
        first = n.page({'scope': scope, 'limit': 1})
        self.assertFalse(first['end'])
        self.assertEqual(first['cursor']['after'], 3)
        n.add(item(5, 's00000000000_23'))
        second = n.page({'scope': scope, 'limit': 2, 'cursor': first['cursor']})
        self.assertTrue(second['end'])
        self.assertEqual(second['cursor']['after'], 5)
        self.assertEqual(len(second['records']), 1)
        third = n.page({'scope': scope, 'cursor': second['cursor']})
        self.assertTrue(third['end'])
        self.assertEqual(len(third['records']), 1)
        self.assertEqual(third['cursor']['after'], 6)
        n.add(item(6))
        empty = n.page({'scope': scope, 'cursor': third['cursor']})
        self.assertEqual(empty['records'], [])
        self.assertEqual(empty['cursor']['after'], 7)
        with self.assertRaises(StructuralError):
            n.page({'scope': {}, 'cursor': third['cursor']})
        with self.assertRaises(StructuralError):
            self.node().page({'scope': scope, 'cursor': third['cursor']})
        for field, value in [('after', True), ('ceiling', 999), ('after', -1)]:
            cursor = dict(third['cursor'], **{field: value})
            with self.assertRaises(StructuralError):
                n.page({'scope': scope, 'cursor': cursor})

    def test_mid_variants_ceiling_and_new_sweep(self):
        n = self.node()
        a = atom(0, alg='unknown')
        records = []
        for sig in (b'a', b'b', b'c'):
            a['sig'] = b64(sig)
            records.append(from_atom(a).item())
        for r in reversed(records):
            n.add(r)
        first = n.page({'mode': 'mid', 'limit': 1})
        n.add(item(9))
        page, seen = first, list(first['records'])
        while not page['end']:
            page = n.page({'mode': 'mid', 'limit': 1, 'cursor': page['cursor']})
            seen.extend(page['records'])
        self.assertEqual(seen, sorted(records, key=lambda r: (r['address'], r['sha256'])))
        self.assertEqual(n.page({'mode': 'mid', 'cursor': page['cursor']})['records'], [])
        self.assertEqual(len(n.page({'mode': 'mid'})['records']), 4)
        bound = records[0]['address']
        with self.assertRaises(StructuralError):
            n.page({'mode': 'mid', 'lo': bound, 'hi': bound})
        self.assertEqual(len(n.page({'mode': 'mid', 'lo': bound})['records']),
                         sum(e.address >= bound for e in n.log))
        with self.assertRaises(StructuralError):
            n.page({'mode': 'mid', 'lo': bound, 'cursor': first['cursor']})

    def test_page_response_byte_cap(self):
        n = Node([{}])
        for i in range(8):
            n.add(item(i, x='x' * 900000))
        first = n.page({'limit': 32})
        self.assertLessEqual(len(dumps(first)), MAX_HTTP)
        self.assertFalse(first['end'])
        second = n.page({'cursor': first['cursor']})
        self.assertTrue(second['end'])
        self.assertEqual(len(first['records']) + len(second['records']), 8)

    def test_reconnect_retains_state_and_catches_up(self):
        a, b = self.pair()
        for i in range(40):
            a.add(item(i))
        b.add(candidate())
        a.connect(b.url)
        self.assertEqual(set(a.store), set(b.store))
        self.assertTrue(a._pull_checkpoints)
        old_epoch, old_url = b.epoch, b.url
        b.stop()
        a.add(item(50))
        b.add(item(51))
        self.assertNotEqual(a.sync_known()[b.url], 'ok')
        b.start()
        self.assertEqual((b.epoch, b.url), (old_epoch, old_url))
        a.connect(b.url)
        self.assertEqual(set(a.store), set(b.store))
        self.assertEqual(len(a.store), 42)
        before = len(a.log), len(b.log)
        a.connect(b.url)
        self.assertEqual((len(a.log), len(b.log)), before)

    def test_new_incarnation_and_subscription_change_force_catchup(self):
        a, b = self.pair()
        a.add(item())
        a.connect(b.url)
        port = b._port
        b.stop()
        replacement = Node([{}], peers=[a.url], port=port).start()
        self.nodes.append(replacement)
        a.connect(replacement.url)
        self.assertEqual(set(a.store), set(replacement.store))
        self.assertNotEqual(b.epoch, replacement.epoch)
        c = self.node([])
        a.peers.add(c.url)
        c.peers.add(a.url)
        a.connect(c.url)
        self.assertFalse(c.store)
        c.subscriptions = [{}]
        a.connect(c.url)
        self.assertEqual(set(a.store), set(c.store))

    def test_different_orders_subsets_and_multihop_converge(self):
        a, b, c = self.node(), self.node(), self.node()
        a.peers.add(b.url)
        b.peers.update([a.url, c.url])
        c.peers.add(b.url)
        records = [item(i, h='000000000000_-18' if i % 2 else '') for i in range(12)]
        for n, indices in ((a, range(6)), (b, range(8, 2, -1)), (c, range(11, 6, -1))):
            for i in indices:
                n.add(records[i])
        for _ in range(2):
            a.connect(b.url)
            b.connect(c.url)
        expected = {r['address'] for r in records}
        for n in (a, b, c):
            self.assertEqual(set(n.store), expected)
            self.assertEqual({e.raw for e in n.log}, {e.raw for e in a.log})
        hints = a.discover(b.url)
        self.assertIn(c.url, hints)
        self.assertNotIn(c.url, a.peers)

    def test_http_errors_limits_and_callback_authorization(self):
        n = self.node()
        hello = request(n.url, '/hello')
        self.assertEqual(hello['protocol'], 'punkti-mesh/0.6-draft')
        self.assertEqual(hello['limits']['candidates'], 128)
        self.http_error(n, '/push', {'records': 'wrong'}, 400)
        self.assertEqual(self.http_error(n, '/push', {'records': [item()] * 33}, 413)['kind'], 'resource')
        self.http_error(n, '/sync', {'peer': 'http://127.0.0.1:1', 'phase': 'push'}, 400)
        # Reserve a loopback port without listening: callback must be unreachable.
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            peer = f'http://127.0.0.1:{s.getsockname()[1]}'
            n.peers.add(peer)
            self.http_error(n, '/sync', {'peer': peer, 'phase': 'push'}, 502)
        with self.assertRaises(ResourceError):
            n.page({'limit': 33})
        for query in ({'limit': True}, {'limit': 0}, {'mode': 'application'}, {'scope': {'xy_lo': 'i'}}):
            with self.assertRaises(StructuralError):
                n.page(query)
        self.assertEqual(self.http_error(n, '/push', {'records': [item(), {}]}, 400)['kind'], 'request')
        self.assertEqual(len(n.store), 0)  # descriptor validation precedes all admissions
        # Oversized declaration is rejected before a body is read.
        with socket.create_connection(('127.0.0.1', n._port), timeout=5) as s:
            s.sendall(f'POST /push HTTP/1.0\r\nContent-Length: {MAX_HTTP + 1}\r\n\r\n'.encode())
            self.assertIn(b'413', s.recv(1024).split(b'\r\n')[0])

    def test_resource_refusal_does_not_advance_checkpoint(self):
        a, b = self.pair()
        for i in range(128):
            b.add(opaque(i))
        a.add(candidate())
        with self.assertRaises(ResourceError):
            a._push_to(b.url)
        self.assertEqual(a._push_checkpoints, {})
        receiver = self.node()
        for i in range(128):
            receiver.add(opaque(i))
        with self.assertRaises(ResourceError):
            receiver._pull_from(a.url)
        self.assertEqual(receiver._pull_checkpoints, {})

    def test_cli_subprocess(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            config = Path(tmp) / 'config.json'
            config.write_text(json.dumps({'subscriptions': [{}], 'peers': [], 'port': 0}))
            proc = subprocess.Popen([sys.executable, '-m', 'nairobidot.serve', '--config', str(config)],
                                    cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                ready, _, _ = select.select([proc.stdout], [], [], 10)
                self.assertTrue(ready, 'CLI failed to publish readiness')
                info = json.loads(proc.stdout.readline())
                self.assertEqual(request(info['url'], '/hello')['epoch'], info['epoch'])
                self.assertTrue(request(info['url'], '/push', {'records': [item()]})['results'][0]['admitted'])
            finally:
                proc.terminate()
                proc.communicate(timeout=10)
            self.assertEqual(proc.returncode, 0)
