"""Store/cursor checks supplement (never substitute for) the loopback tests."""
import unittest
from support import atom, fixture
from carrier import State, ResourceLimit, record, validate
from mesh import Node, wire
from spatial import Subscription


class StoreTests(unittest.TestCase):
    def test_subscription_history_resume_and_scope_binding(self):
        node = Node(epoch='test')
        for i in range(7):
            node.add(fixture(i, h=('g' if i % 2 else 'z') * 12))
        scope = Subscription('g', 'h').wire()
        query = dict(scope=scope, limit=2)
        page = node.page(query)
        self.assertFalse(page['end'])
        self.assertEqual(len(page['records']), 2)
        node.add(fixture(8, h='g'*12))
        query['cursor'] = page['cursor']
        page = node.page(query)
        self.assertTrue(page['end'])
        self.assertEqual(len(page['records']), 1)
        self.assertEqual(page['cursor']['after'], 7)
        query['cursor'] = page['cursor']
        page = node.page(query)
        self.assertEqual(len(page['records']), 1)
        self.assertEqual(page['cursor']['after'], 8)
        with self.assertRaises(ValueError):
            node.page(dict(query, scope={}))

    def test_mid_snapshot_requires_fresh_sweep(self):
        node = Node(epoch='test')
        records = sorted([fixture(i) for i in range(10)], key=lambda r: validate(r).address)
        for raw in records[1:]:
            node.add(raw)
        first = node.page(dict(mode='mid', limit=2))
        node.add(records[0])
        seen = first['records']
        page = first
        while not page['end']:
            page = node.page(dict(mode='mid', cursor=page['cursor'], limit=2))
            seen += page['records']
        self.assertEqual(len(seen), 9)
        self.assertEqual(len(node.page(dict(mode='mid'))['records']), 10)

    def test_reject_variants_and_preserve_candidates(self):
        node = Node()
        good = fixture()
        bad = good[:-1] + bytes([good[-1] ^ 1])
        self.assertEqual(node.add(bad)['state'], State.PROVENANCE)
        self.assertTrue(node.add(good)['admitted'])
        self.assertFalse(node.add(bad)['admitted'])
        self.assertEqual(node.store[validate(good).address].raw, good)
        raw = record(atom(alg='unknown'))
        node.add(raw)
        node.add(raw[:-1] + bytes([raw[-1] ^ 1]))
        self.assertEqual(len(node.candidates), 2)
        self.assertEqual(len(node.store), 1)
        records = node.page(dict(mode='mid', limit=1))
        count = len(records['records'])
        while not records['end']:
            records = node.page(dict(mode='mid', limit=1, cursor=records['cursor']))
            count += len(records['records'])
        self.assertEqual(count, 3)

    def test_spatial_scope_does_not_trust_opaque_claims(self):
        node = Node([Subscription('g', 'h')])
        item = wire(b'future raw', 'punkti/9:aa')
        item['h'] = 'g'*12
        with self.assertRaises(ValueError):
            node.admit(item)
        del item['h']
        self.assertFalse(node.admit(item)['admitted'])
        self.assertFalse(node.candidates)
        self.assertFalse(node.add(fixture(h='z'*12))['admitted'])
        self.assertTrue(node.add(fixture())['admitted'])

    def test_transport_and_resource_refusals(self):
        node = Node()
        item = wire(fixture())
        with self.assertRaises(ValueError):
            node.admit(dict(item, sha256='0'*64))
        with self.assertRaises(ValueError):
            node.admit(dict(item, address='punkti/0.6:'+'0'*64))
        for i in range(128):
            node.admit(wire(str(i).encode(), f'future:{i:04x}'))
        with self.assertRaises(ResourceLimit):
            node.admit(wire(b'overflow', 'future:aaaa'))
        self.assertTrue(node.add(fixture())['admitted'])
