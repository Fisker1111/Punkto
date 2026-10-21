"""Black-box interoperability matrix; no implementation imports in this process."""
import base64
import hashlib
import json
from pathlib import Path
import platform
import random
import subprocess
import sys
import unittest
from urllib.parse import urlencode, parse_qs, urlsplit
from driver import Adapter, Proxy, http, HERE

ROOT = HERE.parents[2]
REPORT = {}
VECTORS = []


def b64(raw):
    return base64.b64encode(raw).decode()


def spec(i=0, **kw):
    result = dict(seed=f'interop-{i}', t=1700000000000 + i, h='gggh00000000',
                  x=f'opaque-{i}', refs=[], ext='')
    result.update(kw)
    return result


def vectors():
    refs = [dict(target='unknown/a:00ff', rel='unrecognized/关系'),
            dict(target='future:abcd', rel=''), dict(target='unknown/a:00ff', rel='unrecognized/关系')]
    return [spec(0, h=''), spec(1, h='s00000000000'), spec(2, h='s00000000001'),
            spec(3, refs=refs), spec(4, x='Nairobi 🌍\u0000 e\u0301 漢字', ext=b64(bytes(range(256)))),
            spec(5, alg='future-signature')]


def item(m, raw=None, address=None):
    raw = base64.b64decode(m['R']) if raw is None else raw
    return dict(address=address or m['address'], sha256=hashlib.sha256(raw).hexdigest(), record=b64(raw))


def write_report():
    identities = {}
    for name, folder in [('ref', ROOT / 'experimental/punkti-v0.6-mesh/src'),
                         ('nb', HERE.parent / 'src')]:
        identities[name] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sorted(folder.rglob('*.py'))}
    tree_hashes = {k: hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest()
                   for k, v in identities.items()}
    totals = {s: sum(r['status'] == s for r in REPORT.values()) for s in ('PASS', 'FAIL')}
    report = dict(environment=dict(python=platform.python_version(), implementation=platform.python_implementation()),
                  implementations=identities, source_manifest_sha256=tree_hashes, arrangement='two clean-room nodes and one reference',
                  totals=totals, vectors=VECTORS, tests=REPORT,
                  divergences=[dict(test=k, failures=v['failures']) for k, v in REPORT.items() if v['status'] == 'FAIL'])
    (HERE / 'interop_report.json').write_text(json.dumps(report, indent=2, ensure_ascii=True) + '\n')
    lines = ['# NairobiDot L3 × reference Mesh interoperability', '',
             f"Python {platform.python_version()} ({platform.python_implementation()}); loopback HTTP only.",
             'Implementation identity: SHA-256 of every source file is recorded in `interop_report.json`.',
             f"Reference source manifest SHA-256: `{tree_hashes['ref']}`.",
             f"Clean-room source manifest SHA-256: `{tree_hashes['nb']}`.",
             'Convergence arrangement: two clean-room nodes and one reference.', '',
             '| Test | Result | Evidence |', '|---|---|---|']
    for name, row in sorted(REPORT.items()):
        lines.append(f"| {name} | {row['status']} | {len(row['comparisons'])} recorded comparisons; {row['summary']} |")
    lines += ['', f"Totals: {totals['PASS']} PASS, {totals['FAIL']} FAIL.", '',
              '| Vector | MID | Address |', '|---|---|---|']
    for v in VECTORS:
        lines.append(f"| {v['name']} | {v['MID']} | {v['address']} |")
    lines += ['', '## Divergences', '']
    for name, row in sorted(REPORT.items()):
        if row['status'] == 'FAIL':
            lines.append(f"- {name}: " + '; '.join(f for f in row['failures'] if not f.startswith('Traceback')).replace('\n', ' '))
    rejection = REPORT.get('rejection_consistency', {})
    for comparison in rejection.get('comparisons', []):
        if comparison['label'] == 'duplicate JSON keys raw HTTP responses':
            lines.append('- Duplicate-key request responses (reference, clean-room): `' +
                         json.dumps(comparison['actual'], sort_keys=True) + '`.')
    if not totals['FAIL']:
        lines.append('None observed in the exercised matrix.')
    lines += ['', 'Exact compared values and raw HTTP evidence are in `interop_report.json`.']
    (HERE / 'interop_matrix.md').write_text('\n'.join(lines) + '\n')


class Interop(unittest.TestCase):
    def setUp(self):
        self.row = dict(status='PASS', summary=self._testMethodDoc or '', comparisons=[], failures=[])
        REPORT[self._testMethodName.removeprefix('test_')] = self.row

    def tearDown(self):
        # Retain failures even when an unexpected exception interrupts a row.
        result = self._outcome.result
        for test, trace in result.errors + result.failures:
            if test is self or getattr(test, 'test_case', None) is self:
                self.row['status'] = 'FAIL'
                self.row['failures'].append(trace)
        write_report()

    def eq(self, label, actual, expected):
        self.row['comparisons'].append(dict(label=label, actual=actual, expected=expected))
        if actual != expected:
            self.row['status'] = 'FAIL'
            self.row['failures'].append(f'{label}: actual={actual!r}; expected={expected!r}')
        self.assertEqual(actual, expected, label)

    def adapter(self, kind, scopes=None, serve=True):
        a = Adapter(kind, dict(subscriptions=[{}] if scopes is None else scopes, peers=[], port=0) if serve else None)
        self.addCleanup(a.close)
        isolation = a.rpc('isolation')
        forbidden = ('punkti-v0.6-mesh' if kind == 'nb' else 'nairobidot-l3/src')
        self.eq(kind + ' isolated sys.path', [p for p in isolation['path'] if forbidden in p], [])
        if kind == 'nb':
            self.eq('no reference modules loaded', sorted(k for k in isolation['modules'] if k in ('carrier', 'mesh', 'spatial')), [])
        self.eq('adapter survives invalid command', a.rpc('invalid-command').get('ok'), False)
        self.eq('adapter remains responsive', 'modules' in a.rpc('isolation'), True)
        return a

    def call(self, a, cmd, **args):
        r = a.rpc(cmd, **args)
        self.eq(f'{a.kind} {cmd} RPC error', r.get('error'), None)
        return r

    def seed(self, a, s):
        r = self.call(a, 'add', spec=s)
        self.eq('local seed admission', r['admission']['admitted'], True)
        return r

    def addresses(self, a):
        return sorted(e['address'] for e in self.call(a, 'state')['valid'])

    def configure(self, *nodes):
        for a in nodes:
            self.call(a, 'configure', peers=[b.url for b in nodes if b is not a])

    def pullpage(self, a, scope=None):
        status, page = http(a.url, '/pull?' + urlencode({'q': json.dumps(dict(mode='spatial', scope=scope or {}))}))
        self.eq('pull HTTP status', status, 200)
        return page

    def test_vector_parity(self):
        """Six deterministic vectors compare all canonical and framed bytes."""
        a, b = self.adapter('ref', serve=False), self.adapter('nb', serve=False)
        VECTORS.clear()
        for name, s in zip(('unanchored', 'XY', 'XYZ', 'refs-order-duplicates', 'unicode-ext', 'unknown-alg'), vectors()):
            left, right = self.call(a, 'mint', spec=s), self.call(b, 'mint', spec=s)
            for key in ('C', 'S', 'MID', 'address', 'R', 'sig'):
                self.eq(name + ':' + key, left[key], right[key])
            self.eq(name + ':state', left['state'], 'UNVERIFIABLE-alg' if s.get('alg') else 'VALID')
            self.eq(name + ':state parity', right['state'], left['state'])
            VECTORS.append(dict(name=name, MID=left['MID'], address=left['address']))

    def test_decode_parity(self):
        """Both standalone adapters decode the other implementation's records."""
        a, b = self.adapter('ref', serve=False), self.adapter('nb', serve=False)
        for s in vectors():
            for sender, receiver in ((a, b), (b, a)):
                m = self.call(sender, 'mint', spec=s)
                d = self.call(receiver, 'decode', record=m['R'])
                for key in ('C', 'S', 'MID', 'address', 'state'):
                    self.eq(sender.kind + '→' + receiver.kind + ':' + key, d[key], m[key])
                self.eq('expected validation', d['state'], 'UNVERIFIABLE-alg' if s.get('alg') else 'VALID')

    def transfer(self, sender, receiver, s):
        m = self.seed(sender, s)
        status, response = http(receiver.url, '/push', {'records': [item(m)]})
        self.eq('push status', status, 200)
        self.eq('receiver classification', response['results'][0]['state'], m['state'])
        self.eq('receiver admission', response['results'][0]['admitted'], True)
        state = self.call(receiver, 'state')
        entries = state['valid'] if m['state'] == 'VALID' else state['candidates']
        self.eq('stored digest', next(e['sha256'] for e in entries if e['address'] == m['address']), m['sha256'])
        pulled = next(r for r in self.pullpage(receiver)['records'] if r['address'] == m['address'])
        self.eq('exact R round trip', pulled, item(m))
        decoded = self.call(receiver, 'decode', record=pulled['record'])
        for key in ('x', 'ext', 'refs'):
            self.eq('opaque ' + key, decoded['atom'][key], s[key])

    def test_push_both_directions(self):
        """Both HTTP push directions admit VALID and return identical R/digests."""
        a, b = self.adapter('ref'), self.adapter('nb')
        self.transfer(a, b, spec(10))
        self.transfer(b, a, spec(11))

    def test_connect_both_initiators(self):
        """Each implementation initiates full reciprocal connect over mixed atoms."""
        for kind in ('ref', 'nb'):
            a, b = self.adapter(kind), self.adapter('nb' if kind == 'ref' else 'ref')
            self.configure(a, b)
            expected = []
            for i, s in enumerate(vectors()[:5]):
                expected.append(self.seed(a if i % 2 else b, s)['address'])
            self.call(a, 'connect', peer=b.url)
            self.eq(kind + ' initiator store', self.addresses(a), sorted(expected))
            self.eq(kind + ' receiver store', self.addresses(b), sorted(expected))

    def test_spatial_range_selection(self):
        """Literal half-open h bounds filter push admission and peer PULL."""
        scope = dict(h_lo='gggh', h_hi='gggj')
        for kind in ('ref', 'nb'):
            source = self.adapter('nb' if kind == 'ref' else 'ref')
            target = self.adapter(kind, [scope])
            expected = []
            for i, h in enumerate(('', 'ggggzzzzzzzz', 'gggh00000000', 'ggghzzzzzzzz', 'gggj00000000')):
                m = self.seed(source, spec(20 + i, h=h))
                admitted = i in (2, 3)
                status, body = http(target.url, '/push', {'records': [item(m)]})
                self.eq('spatial push HTTP', status, 200)
                self.eq('spatial admission ' + h, body['results'][0]['admitted'], admitted)
                if admitted:
                    expected.append(m['address'])
                else:
                    self.eq('spatial rejection reason', body['results'][0]['reason'], 'out-of-scope')
            self.call(target, 'pull', peer=source.url)
            self.eq('subscribed store', self.addresses(target), sorted(expected))
            self.eq('source scoped PULL', sorted(r['address'] for r in self.pullpage(source, scope)['records']), sorted(expected))
            self.eq('target PULL', sorted(r['address'] for r in self.pullpage(target)['records']), sorted(expected))

    def test_xy_z_selection(self):
        """Fixed XY bits with varying Z agree at exact altitude boundaries."""
        alphabet = '0123456789bcdefghjkmnpqrstuvwxyz'
        zs = [0, 1, 2, 3, 100]
        hs = []
        for z in zs:
            bits = ''.join('00' + bit for bit in f'{z:020b}')
            hs.append(''.join(alphabet[int(bits[i:i+5], 2)] for i in range(0, 60, 5)))
        altitude = lambda z: -500 + (z + .5) * 9000 / 2**20
        scope = dict(z_min=altitude(1), z_max=altitude(3))
        all_nodes = [self.adapter(k) for k in ('ref', 'nb')]
        expected = []
        for a in all_nodes:
            addresses = [self.seed(a, spec(30+i, h=h))['address'] for i, h in enumerate(hs)]
            expected = sorted(addresses[1:3])
            self.eq('Z bounded PULL ' + a.kind, sorted(r['address'] for r in self.pullpage(a, scope)['records']), expected)
            for i, z in enumerate(zs):
                self.eq('z_min only ' + str(z), sorted(r['address'] for r in self.pullpage(a, {'z_min': altitude(z)})['records']), sorted(addresses[i:]))
        for i, kind in enumerate(('ref', 'nb')):
            target = self.adapter(kind, [scope])
            self.call(all_nodes[1-i], 'push_to', peer=target.url)
            self.call(target, 'pull', peer=all_nodes[1-i].url)
            self.eq('Z subscribed store ' + kind, self.addresses(target), expected)

    def test_unknown_l4_byte_preservation(self):
        """Unicode, JSON-looking text, unknown refs/ext/alg survive exact transfer."""
        a, b = self.adapter('ref'), self.adapter('nb')
        rng = random.Random(606)
        for index, (sender, receiver) in enumerate(((a, b), (b, a))):
            for j, x in enumerate(('🌍\u0000漢字 e\u0301', '{"looks":"json","duplicate":1,"duplicate":2}')):
                s = spec(40 + index*10+j, x=x, refs=vectors()[3]['refs'],
                         ext=b64(bytes(rng.randrange(256) for _ in range(128))))
                self.transfer(sender, receiver, s)
            self.transfer(sender, receiver, spec(42 + index*10, alg='unknown/l4', x='[opaque]', ext=b64(bytes(range(256)))))

    def test_disconnect_rejoin_cursor_catchup(self):
        """Both initiators survive refused proxy, reuse cursor, pull only new records."""
        for kind in ('ref', 'nb'):
            a, b = self.adapter(kind), self.adapter('nb' if kind == 'ref' else 'ref')
            proxy = Proxy(b.url)
            self.addCleanup(proxy.stop)
            self.call(a, 'configure', peers=[proxy.url])
            self.call(b, 'configure', peers=[a.url])
            old = [self.seed(b, spec(60+i))['address'] for i in range(3)]
            self.call(a, 'sync_known')
            self.eq('initial sync', self.addresses(a), sorted(old))
            proxy.stop()
            failed = self.call(a, 'sync_known')['result']
            self.eq('connection refusal observed', failed != {proxy.url: 'ok'} and failed != [], True)
            new = [self.seed(b, spec(70+i))['address'] for i in range(2)]
            proxy.exchanges.clear()
            proxy.start()
            self.call(a, 'sync_known')
            proxy.stop()  # Complete captures before inspecting them.
            self.eq('rejoined store', self.addresses(a), sorted(old + new))
            pulls = []
            for request, response in proxy.exchanges:
                path = request.split(b' ', 2)[1].decode()
                if path.startswith('/pull?'):
                    query = json.loads(parse_qs(urlsplit(path).query)['q'][0])
                    body = json.loads(response.split(b'\r\n\r\n', 1)[1])
                    pulls.append(dict(query=query, response=body))
            self.row['comparisons'].append(dict(label='captured proxy PULL exchanges ' + kind, actual=pulls, expected='resumed after=3; exactly 2 new records'))
            self.eq('nonempty cursor reused', [p['query']['cursor']['after'] for p in pulls], [3])
            self.eq('only new records transferred by PULL', sorted(r['address'] for p in pulls for r in p['response']['records']), sorted(new))

    def test_convergence_orders_and_subsets(self):
        """Two clean-room plus one reference converge after two fair sync rounds."""
        nodes = [self.adapter('nb', [{'h_lo': 'g', 'h_hi': 'u'}]),
                 self.adapter('nb', [{'h_lo': 'f', 'h_hi': 't'}]),
                 self.adapter('ref', [{'h_lo': 'g', 'h_hi': 't'}])]
        self.configure(*nodes)
        specs = [spec(80+i, h=('gggh00000000' if i % 2 else 's00000000000')) for i in range(6)]
        expected = set()
        for node, indices in zip(nodes, ((0, 2, 4), (5, 3, 1), (2, 1, 4))):
            for i in indices:
                expected.add(self.seed(node, specs[i])['address'])
        for _ in range(2):
            for a in nodes:
                for b in nodes:
                    if a is not b:
                        self.call(a, 'connect', peer=b.url)
        for a in nodes:
            self.eq('converged ' + a.kind, self.addresses(a), sorted(expected))

    def test_rejection_consistency(self):
        """Malformed/forged records stay out of main store; valid later wins."""
        nodes = [self.adapter('ref'), self.adapter('nb')]
        m = self.call(nodes[0], 'mint', spec=spec(100))
        raw = base64.b64decode(m['R'])
        forged = raw[:-1] + bytes([raw[-1] ^ 1])
        flipped = bytearray(raw)
        flipped[0] ^= 128
        unknown = self.call(nodes[0], 'mint', spec=spec(101, alg='future-alg'))
        cases = [('forged signature', item(m, forged), 'INVALID-provenance', False),
                 ('byte-flipped R', item(m, bytes(flipped)), 'INVALID-structural', False),
                 ('trailing R', item(m, raw+b'!'), 'INVALID-structural', False),
                 ('truncated R', item(m, raw[:-4]), 'INVALID-structural', False),
                 ('unsupported alg', item(unknown), 'UNVERIFIABLE-alg', True),
                 ('future wrapper', item(m, b'future opaque bytes', 'punkti/9:00ff'), 'OPAQUE-version', True)]
        for name, payload, state, admitted in cases:
            with self.subTest(case=name):
                results = []
                for a in nodes:
                    status, body = http(a.url, '/push', {'records': [payload]})
                    self.eq(name + ' status', status, 200)
                    result = body['results'][0]
                    results.append(result['state'])
                    self.eq(name + ' classification ' + a.kind, result['state'], state)
                    self.eq(name + ' admission ' + a.kind, result['admitted'], admitted)
                    self.eq('main store remains empty', self.addresses(a), [])
                    state_snapshot = self.call(a, 'state')
                    self.eq(name + ' candidate retention',
                            any(e['sha256'] == payload['sha256'] for e in state_snapshot['candidates']), admitted)
                    if name != 'future wrapper':
                        decoded = self.call(a, 'decode', record=payload['record'])
                        self.eq(name + ' decoder classification ' + a.kind, decoded['state'], state)
                self.eq(name + ' classification parity', results[0], results[1])
        for a in nodes:
            with self.subTest(valid_after_forged=a.kind):
                status, body = http(a.url, '/push', {'records': [item(m)]})
                self.eq('later valid HTTP', status, 200)
                self.eq('later valid admission', body['results'][0]['admitted'], True)
                self.eq('later valid store', self.addresses(a), [m['address']])
        # Fresh nodes keep a malformed request's effects independent of other cases.
        duplicate = ('{"records":[],"records":' + json.dumps([item(m)]) + '}').encode()
        noncanonical = item(m)
        noncanonical['record'] += '\n'
        for name, body in [('duplicate JSON keys', duplicate), ('noncanonical base64', {'records': [noncanonical]})]:
            fresh = [self.adapter('ref'), self.adapter('nb')]
            responses = [http(a.url, '/push', body) for a in fresh]
            stores = [self.addresses(a) for a in fresh]
            self.row['comparisons'].append(dict(label=name + ' raw HTTP responses', actual=responses, expected='HTTP 400; empty main stores'))
            self.row['comparisons'].append(dict(label=name + ' stores (ref, nb)', actual=stores, expected=[[], []]))
            for a, (status, response), addresses in zip(fresh, responses, stores):
                with self.subTest(case=name, implementation=a.kind, check='status'):
                    self.eq(name + ' HTTP rejection ' + a.kind, status, 400)
                with self.subTest(case=name, implementation=a.kind, check='store'):
                    self.eq(name + ' main store ' + a.kind, addresses, [])

    def test_no_reference_imports(self):
        """Static scan and isolated import prove clean-room source independence."""
        folder = HERE.parent / 'src'
        for p in sorted((folder / 'nairobidot').rglob('*.py')):
            text = p.read_text()
            for forbidden in ('import carrier', 'import mesh', 'import spatial', 'punkti-v0.6-mesh'):
                self.eq(str(p.relative_to(ROOT)) + ':' + forbidden, forbidden in text, False)
        code = ('import sys; sys.path.insert(0, ' + repr(str(folder)) + '); '
                'import nairobidot, nairobidot.carrier, nairobidot.node; '
                'assert not any(k in sys.modules for k in ("carrier", "mesh", "spatial")); '
                'print(nairobidot.__file__)')
        result = subprocess.run([sys.executable, '-I', '-c', code], capture_output=True, text=True)
        self.eq('isolated package import exit', result.returncode, 0)
        self.eq('isolated package path', result.stdout.strip(), str(folder / 'nairobidot/__init__.py'))
        self.adapter('nb', serve=False)
        self.adapter('ref', serve=False)
        self.eq('harness imported no implementation', [k for k in sys.modules if k in ('carrier', 'mesh', 'spatial') or k.startswith('nairobidot')], [])


if __name__ == '__main__':
    unittest.main()
