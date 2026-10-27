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
    result = dict(seed=f'interop-{i}', t=1700000000000 + i, h='gggh00000000_0',
                  x=f'opaque-{i}', refs=[], ext='')
    result.update(kw)
    return result


def vectors():
    refs = [dict(target='unknown/a:00ff', rel='unrecognized/关系'),
            dict(target='future:abcd', rel=''), dict(target='unknown/a:00ff', rel='unrecognized/关系')]
    return [spec(0, h=''), spec(1, h='s00000000000_23'), spec(2, h='s00000000001_23.025'),
            spec(3, refs=refs), spec(4, x='Nairobi 🌍\u0000 e\u0301 漢字', ext=b64(bytes(range(256)))),
            spec(5, alg='future-signature')]


def item(m, raw=None, address=None):
    raw = base64.b64decode(m['R']) if raw is None else raw
    return dict(address=address or m['address'], sha256=hashlib.sha256(raw).hexdigest(), record=b64(raw))


def evidence(value):
    """Copy recorded values, hiding runtime epochs without changing assertions."""
    if isinstance(value, dict):
        return {key: '<epoch>' if key == 'epoch' and isinstance(item, str) else evidence(item)
                for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [evidence(item) for item in value]
    return value


def write_report():
    identities = {}
    for name, folder in [('ref', ROOT / 'experimental/punkti-v0.6-mesh/src'),
                         ('nb', HERE.parent / 'src')]:
        identities[name] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sorted(folder.rglob('*.py'))}
    tree_hashes = {k: hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest()
                   for k, v in identities.items()}
    totals = {s: sum(r['status'] == s for r in REPORT.values()) for s in ('PASS', 'FAIL')}
    divergences = [dict(test=name, explanation=row['divergence'],
                        reference_behaviour=row['reference_behaviour'],
                        clean_room_behaviour=row['clean_room_behaviour'])
                   for name, row in sorted(REPORT.items()) if 'divergence' in row]
    report = dict(environment=dict(python=platform.python_version(), implementation=platform.python_implementation()),
                  implementations=identities, source_manifest_sha256=tree_hashes, arrangement='two clean-room nodes and one reference',
                  totals=totals, vectors=VECTORS, tests=REPORT,
                  divergences=divergences)
    (HERE / 'interop_report.json').write_text(json.dumps(report, indent=2, ensure_ascii=True) + '\n')
    lines = ['# NairobiDot L3 × reference Mesh interoperability', '',
             f"Python {platform.python_version()} ({platform.python_implementation()}); loopback HTTP only.",
             'Implementation identity: SHA-256 of every source file is recorded in `interop_report.json`.',
             f"Reference source manifest SHA-256: `{tree_hashes['ref']}`.",
             f"Clean-room source manifest SHA-256: `{tree_hashes['nb']}`.",
             'Convergence arrangement: two clean-room nodes and one reference.', '',
             '| Test | Result | Evidence |', '|---|---|---|']
    for name, row in sorted(REPORT.items()):
        result = "PASS (documented divergence)" if row['status'] == 'PASS' and 'divergence' in row else row['status']
        lines.append(f"| {name} | {result} | {len(row['comparisons'])} recorded comparisons; {row['summary']} |")
    lines += ['', f"Totals: {totals['PASS']} PASS, {totals['FAIL']} FAIL.", '',
              '| Vector | MID | Address |', '|---|---|---|']
    for v in VECTORS:
        lines.append(f"| {v['name']} | {v['MID']} | {v['address']} |")
    lines += ['', '## Divergences', '']
    for name, row in sorted(REPORT.items()):
        if row['status'] == 'FAIL':
            lines.append(f"- {name}: " + '; '.join(f for f in row['failures'] if not f.startswith('Traceback')).replace('\n', ' '))
    for divergence in divergences:
        lines.append(f"- {divergence['test']}: {divergence['explanation']}")
        for line in REPORT[divergence['test']].get('divergence_lines', []):
            lines.append(f"  - {line}")
        for label, key in [('Reference', 'reference_behaviour'), ('Clean-room', 'clean_room_behaviour')]:
            lines.append(f"  - {label}: `" + json.dumps(divergence[key], sort_keys=True) + "`.")
    if not totals['FAIL'] and not divergences:
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

    def record_comparison(self, label, actual, expected):
        self.row['comparisons'].append(evidence(dict(label=label, actual=actual, expected=expected)))

    def eq(self, label, actual, expected):
        self.record_comparison(label, actual, expected)
        if actual != expected:
            self.row['status'] = 'FAIL'
            self.row['failures'].append(f'{label}: actual={evidence(actual)!r}; expected={evidence(expected)!r}')
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
        """Padded lower-edge XY bounds filter push admission and peer PULL."""
        scope = dict(xy_lo='gggh', xy_hi='gggj')
        for kind in ('ref', 'nb'):
            source = self.adapter('nb' if kind == 'ref' else 'ref')
            target = self.adapter(kind, [scope])
            expected = []
            for i, h in enumerate(('', 'ggggzzzzzzzz_0', 'gggh00000000_0', 'ggghzzzzzzzz_0', 'gggj00000000_0')):
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

    def test_xy_z_profile_vectors(self):
        """Every deterministic XY_Z vector runs on both process-isolated codecs."""
        sys.path.insert(0, str(ROOT / 'experimental/punkti-v0.6-freeze/src'))
        from vector_suite import HOME, Runner
        document = json.loads((HOME / 'vectors.json').read_text())
        for vector in document['vectors']:
            if vector['id'] in ('V11', 'V12', 'V13'):
                self.eq(vector['id'] + ' parity', Runner('ref',document).run(vector),
                        Runner('nb',document).run(vector))

    def test_xy_z_selection(self):
        """Same XY with separate decimal Z agrees at exact height boundaries."""
        zs = [0, 1, 2, 3, 100]
        hs = ['u3butz7k9q_' + str(z) for z in zs]
        altitude = str
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
            self.record_comparison('captured proxy PULL exchanges ' + kind, pulls, 'resumed after=3; exactly 2 new records')
            self.eq('nonempty cursor reused', [p['query']['cursor']['after'] for p in pulls], [3])
            self.eq('only new records transferred by PULL', sorted(r['address'] for p in pulls for r in p['response']['records']), sorted(new))

    def test_convergence_orders_and_subsets(self):
        """Two clean-room plus one reference converge after two fair sync rounds."""
        nodes = [self.adapter('nb', [{'xy_lo': 'g', 'xy_hi': 'u'}]),
                 self.adapter('nb', [{'xy_lo': 'f', 'xy_hi': 't'}]),
                 self.adapter('ref', [{'xy_lo': 'g', 'xy_hi': 't'}])]
        self.configure(*nodes)
        specs = [spec(80+i, h=('gggh00000000_0' if i % 2 else 's00000000000_23')) for i in range(6)]
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
        """Carrier/data-level rejection agrees; valid records later win."""
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
        noncanonical = item(m)
        noncanonical['record'] += '\n'
        for name, body in [('noncanonical base64', {'records': [noncanonical]})]:
            fresh = [self.adapter('ref'), self.adapter('nb')]
            responses = [http(a.url, '/push', body) for a in fresh]
            stores = [self.addresses(a) for a in fresh]
            self.record_comparison(name + ' raw HTTP responses', responses, 'HTTP 400; empty main stores')
            self.record_comparison(name + ' stores (ref, nb)', stores, [[], []])
            for a, (status, response), addresses in zip(fresh, responses, stores):
                with self.subTest(case=name, implementation=a.kind, check='status'):
                    self.eq(name + ' HTTP rejection ' + a.kind, status, 400)
                with self.subTest(case=name, implementation=a.kind, check='store'):
                    self.eq(name + ' main store ' + a.kind, addresses, [])

    def test_http_duplicate_key_divergence(self):
        """Duplicate HTTP envelope keys are accepted only by the reference."""
        reference, clean_room = self.adapter('ref'), self.adapter('nb')
        m = self.call(reference, 'mint', spec=spec(100))
        address = 'punkti/0.6:' + m['MID']
        self.eq('canonical record address', m['address'], address)
        duplicate = ('{"records":[],"records":' + json.dumps([item(m)]) + '}').encode()
        behaviours = []
        for node, key in ((reference, 'reference_behaviour'), (clean_room, 'clean_room_behaviour')):
            status, response = http(node.url, '/push', duplicate)
            state = self.call(node, 'state')
            behaviour = dict(http_status=status, response=response,
                             addresses=sorted(e['address'] for e in state['valid']),
                             candidates=state['candidates'], log=state['log'])
            self.row[key] = evidence(behaviour)
            behaviours.append(behaviour)
        self.row['divergence'] = ('HTTP envelope duplicate JSON keys: reference keeps the last records key '
                                  'and admits the record; clean-room rejects with HTTP 400 and stores nothing.')
        ref, nb = behaviours
        self.eq('reference HTTP acceptance', ref['http_status'], 200)
        self.eq('reference admission', ref['response']['results'][0]['admitted'], True)
        self.eq('reference classification', ref['response']['results'][0]['state'], 'VALID')
        self.eq('reference stored address', ref['addresses'], [address])
        self.eq('reference stored record', self.pullpage(reference)['records'], [item(m)])
        self.eq('clean-room HTTP rejection', nb['http_status'], 400)
        self.eq('clean-room main store empty', nb['addresses'], [])
        self.eq('clean-room candidates empty', nb['candidates'], [])
        self.eq('clean-room log empty', nb['log'], [])
        self.eq('HTTP outcomes differ', ref['http_status'] != nb['http_status'], True)
        self.eq('stored addresses differ', ref['addresses'] != nb['addresses'], True)

    def test_request_validation_divergences(self):
        """Pin four revised agreements and two out-of-scope request differences."""
        reference, clean_room = self.adapter('ref'), self.adapter('nb')
        m = self.call(reference, 'mint', spec=spec(110))
        for node in (reference, clean_room):
            self.eq('wrong-address fixture VALID ' + node.kind,
                    self.call(node, 'decode', record=m['R'])['state'], 'VALID')
        wrong_address = 'punkti/0.6:' + ('0' if m['MID'][0] != '0' else '1') + m['MID'][1:]
        cases = [
            ('equal XY bounds', dict(mode='spatial', scope=dict(xy_lo='g', xy_hi='g')), None,
             400, {'error': 'equal or reversed bounds: xy'}, 400, {'kind': 'request', 'reason': 'equal or reversed bounds'},
             "GET /pull scope {xy_lo:'g',xy_hi:'g'}: reference HTTP 400, error 'equal or reversed bounds: xy'; clean-room HTTP 400, reason 'equal or reversed bounds'. Revised contract agrees."),
            ('reversed elevation', dict(mode='spatial', scope=dict(z_min='100', z_max='-100')), None,
             400, {'error': 'equal or reversed bounds: z'}, 400, {'kind': 'request', 'reason': 'equal or reversed bounds'},
             "GET /pull scope {z_min:'100',z_max:'-100'}: reference HTTP 400, error 'equal or reversed bounds: z'; clean-room HTTP 400, reason 'equal or reversed bounds'. Revised contract agrees."),
            ('equal elevation', dict(mode='spatial', scope=dict(z_min='1', z_max='1')), None,
             400, {'error': 'equal or reversed bounds: z'}, 400, {'kind': 'request', 'reason': 'equal or reversed bounds'},
             "GET /pull scope {z_min:'1',z_max:'1'}: reference HTTP 400, error 'equal or reversed bounds: z'; clean-room HTTP 400, reason 'equal or reversed bounds'. Revised contract agrees."),
            ('unknown query member', dict(mode='spatial', extra=1), None,
             200, {'records': [], 'end': True}, 400, {'kind': 'request', 'reason': 'query-fields'},
             "GET /pull query {mode:'spatial',extra:1}: reference HTTP 200, member ignored; clean-room HTTP 400, kind='request', reason='query-fields'."),
            ('wrong address for VALID record', None, {'records': [item(m, address=wrong_address)]},
             400, {'error': 'address mismatch'}, 400,
             {'kind': 'request', 'reason': 'address-mismatch'},
             "POST /push wrong address for a VALID record: reference HTTP 400 for the whole request, error 'address mismatch'; clean-room HTTP 400, reason='address-mismatch'. Revised descriptor tier agrees."),
            ('empty push batch', None, {'records': []},
             400, {'error': 'push batch size'}, 200, {'results': []},
             "POST /push {records:[]}: reference HTTP 400, error 'push batch size'; clean-room HTTP 200, {results:[]}."),
        ]
        self.row['divergence'] = 'Two remaining out-of-scope request-validation divergences: unknown query member and empty push batch. Revised interval bounds and wrong-address tiers agree.'
        self.row['divergence_lines'] = [case[-1] for case in cases if case[0] in ('unknown query member', 'empty push batch')]
        self.row['reference_behaviour'] = {}
        self.row['clean_room_behaviour'] = {}
        for label, query, payload, ref_status, ref_body, nb_status, nb_body, _ in cases:
            path = '/pull?' + urlencode({'q': json.dumps(query)}) if query is not None else '/push'
            for node, key, expected_status, expected_body in (
                    (reference, 'reference_behaviour', ref_status, ref_body),
                    (clean_room, 'clean_room_behaviour', nb_status, nb_body)):
                with self.subTest(case=label, implementation=node.kind):
                    status, response = http(node.url, path, payload)
                    self.row[key][label] = evidence(dict(http_status=status, response=response))
                    self.eq(label + ' HTTP status ' + node.kind, status, expected_status)
                    for field, expected in expected_body.items():
                        self.eq(label + ' ' + field + ' ' + node.kind, response.get(field), expected)
                    if label == 'empty push batch' and node is clean_room:
                        self.eq(label + ' exact response nb', response, {'results': []})
                    if label == 'unknown query member' and node is reference:
                        self.eq(label + ' ignored by reference', response, self.pullpage(reference))

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
