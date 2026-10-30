from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
import unittest

from support import atom, fixture, geo
from carrier import State, b64, record, validate
from mesh import Node, digest, packed, request, wire
from spatial import Subscription


class NetworkCase(unittest.TestCase):
    def setUp(self):
        self.nodes = []

    def tearDown(self):
        for node in self.nodes:
            node.stop()

    def network(self, scopes=None):
        scopes = scopes or [None, None, None]
        for i, s in enumerate(scopes):
            self.nodes.append(Node(s, epoch=f'fixed-store-{i}').start())
        for node in self.nodes:
            node.peers.update(n.url for n in self.nodes if n is not node)
        self.assertEqual(len({n.url for n in self.nodes}), 3)
        self.assertEqual(len({id(n.store) for n in self.nodes}), 3)
        return self.nodes

    def round(self):
        a, b, c = self.nodes
        a.connect(b.url)
        b.connect(c.url)
        c.connect(a.url)

    def assert_sets(self, expected):
        expected = set(expected)
        for node in self.nodes:
            self.assertEqual(set(node.store), set(expected))
            self.assertTrue(all(validate(e.raw).state == State.VALID for e in node.store.values()))


class AcceptanceTests(NetworkCase):
    def test_01_differing_subsets(self):
        a, b, c = self.network()
        records = [fixture(i) for i in range(24)]
        for node, indexes in zip(self.nodes, (range(0, 12), range(20, 6, -1), range(23, 14, -1))):
            for i in indexes:
                node.add(records[i])
        self.round()
        self.assert_sets(validate(raw).address for raw in records)

    def test_02_discover_missing_union_and_dedup(self):
        a, b, c = self.network()
        a.peers = {b.url}
        b.peers = {a.url, c.url}
        c.peers = {b.url, a.url}
        self.assertIn(c.url, a.discover())
        for i, node in enumerate(self.nodes):
            node.add(fixture(i))
            node.add(fixture(i))
        a.connect(b.url)
        a.connect(c.url)
        b.connect(c.url)
        self.assert_sets(validate(fixture(i)).address for i in range(3))
        sizes = [len(n.log) for n in self.nodes]
        self.round()
        self.assertEqual(sizes, [len(n.log) for n in self.nodes])

    def test_03_invalid_never_valid_and_variant_does_not_poison(self):
        self.network()
        good = fixture(99)
        forged = good[:-1] + bytes([good[-1] ^ 1])
        for node in self.nodes:
            for raw, state in [(b'corrupt', State.STRUCTURAL), (forged, State.PROVENANCE)]:
                item = wire(raw, validate(good).address)
                with self.assertRaises(HTTPError) as error:
                    request(node.url, '/push', dict(records=[dict(item, state='VALID')]))
                self.assertEqual(error.exception.code, 400)
                error.exception.close()
                result = request(node.url, '/push', dict(records=[item]))
                self.assertEqual(result['results'][0]['state'], state.value)
            self.assertFalse(node.store)
        self.nodes[0].add(good)
        self.round()
        self.assert_sets([validate(good).address])
        for node in self.nodes:
            request(node.url, '/push', dict(records=[wire(forged)]))
            self.assertEqual(node.store[validate(good).address].raw, good)

    def test_04_unknown_l4_exact_record(self):
        a, b, c = self.network()
        raw = fixture(x='future-app:🛰\x00\n{"unrecognized":true}',
                      refs=[dict(target='future-type:abcd', rel='未知')], ext=b64(b'\x00\xff'))
        a.add(raw)
        self.round()
        for node in (a, b, c):
            self.assertEqual(node.store[validate(raw).address].raw, raw)

    def test_05_offline_return(self):
        a, b, c = self.network()
        a.add(fixture(0))
        self.round()
        port = c.server.server_port
        c.stop()
        a.add(fixture(1))
        b.add(fixture(2))
        a.connect(b.url)
        self.assertIn(c.url, a.sync_known())
        self.assertEqual(len(c.store), 1)
        c.start(port)
        self.round()
        self.assert_sets(validate(fixture(i)).address for i in range(3))

    def test_06_wire_spec_exists(self):
        proposals = Path(__file__).resolve().parents[3] / 'docs/proposals'
        spec = proposals / 'PUNKTI_0_6_LAYER3_RESET.md'
        text = spec.read_text()
        for term in ['PUSH', 'Range PULL', 'cursor', 'UNVERIFIABLE-alg']:
            self.assertIn(term, text)
        stub = (proposals / 'PUNKTI_0_6_MESH.md').read_text()
        for source in ['PUNKTI_0_6_LAYER3_RESET.md', 'PUNKTI_0_6_SPATIAL_XY_Z.md',
                       'PUNKTI_0_6_PUBLICATION.md', 'PUNKTI_0_6_VECTORS.md']:
            self.assertIn(f']({source})', stub)

    def test_07_single_range(self):
        s = Subscription('gggh', 'gggj')
        a, b, c = self.network([None, [s], [s]])
        inside, outside = fixture(0), fixture(1, h='zzzz00000000_0')
        a.add(inside)
        a.add(outside)
        self.round()
        self.assertEqual(set(b.store), {validate(inside).address})
        self.assertEqual(set(c.store), set(b.store))
        result = request(b.url, '/push', dict(records=[wire(outside)]))
        self.assertEqual(result['results'][0]['reason'], 'out-of-scope')

    def test_08_overlapping_subscriptions(self):
        left, right = Subscription('g', 'j'), Subscription('h', 'k')
        a, b, c = self.network([[left], [right], None])
        records = [fixture(i, h=h*12 + '_0') for i, h in enumerate('ghj')]
        for raw in records:
            c.add(raw)
        a.add(fixture(10, h='h'*12 + '_0'))
        b.add(fixture(11, h='h'*12 + '_0'))
        self.round()
        union = list(c.store.values())
        self.assertEqual(set(a.store), {e.address for e in union if left.matches(e.h)})
        self.assertEqual(set(b.store), {e.address for e in union if right.matches(e.h)})
        intersection = {e.address for e in union if left.matches(e.h) and right.matches(e.h)}
        self.assertEqual(set(a.store) & set(b.store), intersection)

    def test_09_out_of_range_not_required(self):
        s = Subscription('g', 'h')
        a, b, c = self.network([[s], [s], [Subscription('z', None)]])
        a.add(fixture(0))
        for i in range(20):
            c.add(fixture(i, h='z'*12 + '_0'))
        c.stop()  # No access to outside records is needed.
        a.connect(b.url)
        self.assertEqual(set(a.store), set(b.store))
        self.assertEqual(len(b.store), 1)

    def test_10_elevation_address_only(self):
        band = Subscription(z_min='50', z_max='150')
        a, b, c = self.network([None, [band], [band]])
        records = [fixture(i, h=geo(z), x='claims altitude 100') for i, z in enumerate([-100, 100, 500])]
        for raw in records:
            a.add(raw)
        self.round()
        expected = {validate(records[1]).address}
        self.assertEqual(set(b.store), expected)
        self.assertEqual(set(c.store), expected)

    def test_11_resume_same_scope_from_cursor(self):
        s = Subscription('g', 'h')
        a, b, c = self.network([None, [s], [s]])
        for i in range(8):
            a.add(fixture(i))
        old = b.pull(a.url, s, limit=2)
        self.assertEqual(old['after'], 8)
        port = b.server.server_port
        b.stop()
        for i in range(8, 13):
            a.add(fixture(i))
        a.add(fixture(14, h='z'*12 + '_0'))
        a.connect(c.url)
        b.start(port)
        before = a.metrics['pull_records']
        new = b.pull(a.url, s, limit=2)
        self.assertEqual(a.metrics['pull_records'] - before, 5)
        self.assertEqual(new['after'], 14)
        self.assertEqual(len(b.store), 13)
        self.assertEqual(set(b.store), set(c.store))

    def test_12_unknown_l4_in_range(self):
        s = Subscription('g', 'h')
        a, b, c = self.network([None, [s], [s]])
        inside = fixture(0, x='NairobiDot-v999:\x00not-json<>')
        outside = fixture(1, h='z'*12 + '_0', x='NairobiDot-v999:\x00not-json<>')
        a.add(inside)
        a.add(outside)
        self.round()
        for node in (b, c):
            self.assertEqual(list(node.store), [validate(inside).address])
            self.assertEqual(node.store[validate(inside).address].raw, inside)


class WireTests(NetworkCase):
    def test_mid_bounds_pagination_and_sweep(self):
        a, b, c = self.network()
        raws = sorted([fixture(i) for i in range(16)], key=lambda r: validate(r).address)
        # Omit an atom lexicographically behind the first cursor.
        for raw in raws[1:]:
            a.add(raw)
        query = dict(mode='mid', limit=3)
        first = request(a.url, '/pull?' + urlencode({'q': packed(query).decode()}))
        self.assertFalse(first['end'])
        for item in first['records']:
            b.admit(item)
        a.add(raws[0])
        query['cursor'] = first['cursor']
        while True:
            page = request(a.url, '/pull?' + urlencode({'q': packed(query).decode()}))
            for item in page['records']:
                b.admit(item)
            if page['end']:
                break
            query['cursor'] = page['cursor']
        self.assertEqual(len(b.store), 15)
        b.pull(a.url, mode='mid', limit=3)
        self.assertEqual(set(a.store), set(b.store))
        lo, hi = map(lambda r: validate(r).address, (raws[3], raws[9]))
        c.pull(a.url, mode='mid', lo=lo, hi=hi, limit=2)
        self.assertEqual(set(c.store), {validate(raw).address for raw in raws[3:9]})

    def test_cursor_scope_epoch_and_page_validation(self):
        a, b, c = self.network()
        a.add(fixture())
        cursor = b.pull(a.url)
        for query in [dict(cursor=cursor, scope=dict(xy_lo='z')), dict(cursor=dict(cursor, epoch='wrong')),
                      dict(limit=0), dict(limit=33), dict(cursor=dict(cursor, after=-1))]:
            with self.assertRaises(HTTPError) as error:
                request(a.url, '/pull?' + urlencode({'q': packed(query).decode()}))
            self.assertEqual(error.exception.code, 413 if query.get('limit') == 33 else 400)
            error.exception.close()
        # Store replacement invalidates saved cursor; pull automatically starts afresh.
        a.epoch = 'new-store'
        a.add(fixture(2))
        b.pull(a.url)
        self.assertEqual(set(a.store), set(b.store))

    def test_unverified_and_opaque_preservation(self):
        a, b, c = self.network()
        unknown = record(atom(alg='future-pq'))
        a.add(unknown)
        opaque = b'future bytes\x00\xff'
        wrapped = wire(opaque, 'punkti/9:abcd')
        a.admit(wrapped)
        self.round()
        for node in self.nodes:
            self.assertFalse(node.store)
            self.assertEqual({e.state for e in node.candidates.values()}, {State.ALGORITHM, State.VERSION})
            self.assertEqual({e.raw for e in node.candidates.values()}, {unknown, opaque})

    def test_integrity_address_and_callback_checks(self):
        a, b, c = self.network()
        for changed in [dict(sha256='0'*64), dict(address='punkti/0.6:' + '0'*64)]:
            with self.assertRaises(HTTPError):
                request(a.url, '/push', dict(records=[dict(wire(fixture()), **changed)]))
        a.peers.remove(b.url)
        with self.assertRaises(HTTPError):
            request(a.url, '/sync', dict(peer=b.url, phase='push'))
        self.assertFalse(a.store)

    def test_push_precedes_pull_both_directions(self):
        a, b, c = self.network()
        a.add(fixture(0))
        b.add(fixture(1))
        a.connect(b.url)
        # Catch-up receives records already delivered by the two immediate PUSHes.
        self.assertEqual(len(a.store), 2)
        self.assertEqual(len(b.store), 2)
        self.assertGreater(a.metrics['push_records'], 0)
        self.assertGreater(b.metrics['push_records'], 0)
        self.assertGreater(a.metrics['pull_requests'], 0)
        self.assertGreater(b.metrics['pull_requests'], 0)
        previous = sum(n.metrics['push_records'] for n in (a, b))
        a.connect(b.url)
        self.assertEqual(sum(n.metrics['push_records'] for n in (a, b)), previous + 1)
        # At most one echo newly admitted during the previous connection; then idle.
        a.connect(b.url)
        self.assertEqual(sum(n.metrics['push_records'] for n in (a, b)), previous + 1)
