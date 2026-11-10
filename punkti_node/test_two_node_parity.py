"""Hermetic two-node parity: no network beyond loopback, no proxy."""
import json
import socket
import sys
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'experimental/punkti-v0.6-mesh/tests'))
from support import fixture
from punkti_node import runtime
from punkti_node.carrier import validate, State
from punkti_node.mesh import wire
from punkti_node.publication import Publisher, Reader, PublicationReadError, digest, root, manifest, object_path
from punkti_node import test_publication as helpers
from punkti_node.test_publication import _StaticSource


class TwoNodeParityTests(unittest.TestCase):
    # Reuse setup helpers, not the other suite's tests.
    setUp = helpers.PublicationTests.setUp
    close_nodes = helpers.PublicationTests.close_nodes
    config = helpers.PublicationTests.config
    node = helpers.PublicationTests.node

    def setUp(self):
        helpers.PublicationTests.setUp(self)
        original = socket.getaddrinfo
        connect = socket.socket.connect

        def resolve(host, *args, **kwargs):
            if host not in ('127.0.0.1', 'localhost', '::1'):
                raise AssertionError('non-loopback DNS: ' + str(host))
            return original(host, *args, **kwargs)

        def local_connect(sock, address):
            if address[0] not in ('127.0.0.1', '::1'):
                raise AssertionError('non-loopback connection: ' + str(address))
            return connect(sock, address)

        for target, replacement in [('socket.getaddrinfo', resolve),
                                    ('socket.socket.connect', local_connect),
                                    ('urllib.request._opener', build_opener(ProxyHandler({})))]:
            mock = patch(target, replacement)
            mock.start()
            self.addCleanup(mock.stop)

    def records(self, node):
        for entry in node.store.values():
            self.assertEqual(validate(entry.raw).state, State.VALID)
        return {(mid, digest(e.raw)) for mid, e in node.store.items()}

    def expected(self, raws):
        return {(validate(raw).address, digest(raw)) for raw in raws}

    def seed(self, node, raws):
        for raw in raws:
            node.submit_records([wire(raw)])
        node.after_sync()

    def cycle(self, a, b):
        a.replicate_publication(b.url + '/publication')
        b.replicate_publication(a.url + '/publication')

    def snapshot(self, node):
        return {str(p.relative_to(node.durable.path)): p.read_bytes()
                for p in node.durable.path.rglob('*') if p.is_file()}

    def runtime_cycles(self, node, cycles=1, before=None):
        """Run the real lifecycle/worker in-process with deterministic wakeups."""
        node.stop()
        done = threading.Event()
        errors = []

        class Wakeups:
            count = 0
            def wait(self, timeout=None):
                if timeout is None:
                    if not done.wait(15):
                        raise AssertionError('runtime worker timed out')
                    return True
                if self.count >= cycles:
                    done.set()
                    return True
                if before:
                    before(self.count)
                self.count += 1
                return False
            def set(self):
                done.set()

        def thread(*args, **kwargs):
            target = kwargs['target']
            def guarded():
                try:
                    target()
                except BaseException as exc:
                    errors.append(exc)
                    done.set()
            kwargs['target'] = guarded
            return threading.Thread(*args, **kwargs)

        shim = types.SimpleNamespace(Event=Wakeups, Thread=thread)
        with patch.object(runtime, 'PersistentNode', return_value=node), patch.object(runtime, 'threading', shim):
            runtime.run(node.config)
        if errors:
            raise errors[0]

    def test_static_peer_config(self):
        self.assertEqual(self.config()['replication']['static_peers'], [])
        from punkti_node.config import load_config
        config = load_config(environ={'PUNKTO_WEB_ENABLED': 'false',
            'PUNKTO_STATIC_PEERS': ' http://127.0.0.1:123/pub, https://localhost/pub '})
        self.assertEqual(len(config['replication']['static_peers']), 2)
        for peers in [None, {}, 'http://localhost', [1], ['/pub'], ['ftp://localhost'],
                      ['http://localhost/'], ['http://u:p@localhost'], ['http://@localhost'],
                      ['http://localhost?q'], ['http://localhost#'], ['http://localhost:bad']]:
            with self.subTest(peers=peers), self.assertRaises(ValueError):
                self.config(extra={'replication': {'static_peers': peers}})

    def test_bidirectional_signed_atom_replication(self):
        a, b = self.node('a'), self.node('b')
        raws = [fixture(1), fixture(2)]
        self.seed(a, raws[:1])
        self.seed(b, raws[1:])
        self.cycle(a, b)
        for node in (a, b):
            self.assertEqual(self.records(node), self.expected(raws))
            reader = Reader()
            reader.read_publication(node.url + '/publication')
            self.assertEqual(self.expected(reader.store.valid.values()), self.expected(raws))

    def test_union_convergence(self):
        a, b = self.node('a'), self.node('b')
        raws = [fixture(i) for i in range(6)]
        self.seed(a, raws[:4])
        self.seed(b, raws[2:])
        self.cycle(a, b)
        self.assertEqual(self.records(a), self.expected(raws))
        self.assertEqual(self.records(b), self.expected(raws))
        # Independent peer checkpoints, with one source at a lower sequence.
        with _StaticSource(b.config['publication']['path']) as alternate:
            a.replicate_publication(alternate.url)
        self.assertEqual(len(a._publication_heads), 2)

    def test_repeated_sync_is_idempotent(self):
        a, b = self.node('a'), self.node('b')
        self.seed(a, [fixture(1)])
        self.seed(b, [fixture(2)])
        self.cycle(a, b)
        before = [self.snapshot(n) for n in (a, b)]
        for _ in range(3):
            self.cycle(a, b)
        self.assertEqual(before, [self.snapshot(n) for n in (a, b)])

    def test_static_replication_survives_source_daemon_stop(self):
        a, b = self.node('a'), self.node('b')
        raw = fixture(7)
        self.seed(a, [raw])
        a.stop()
        a.durable.close()
        with _StaticSource(a.config['publication']['path']) as source:
            b.config['replication']['static_peers'] = [source.url]
            self.runtime_cycles(b)
        self.assertEqual(self.records(b), self.expected([raw]))
        with _StaticSource(b.config['publication']['path']) as source:
            reader = Reader()
            reader.read_publication(source.url)
            self.assertEqual(self.expected(reader.store.valid.values()), self.expected([raw]))

    def test_peer_unavailable_then_restore_converges(self):
        a, b = self.node('a'), self.node('b')
        raws = [fixture(1), fixture(2)]
        self.seed(a, raws[:1])
        self.seed(b, raws[1:])
        with _StaticSource(a.config['publication']['path']) as source:
            def before(cycle):
                # A missing publication first; same origin restored next cycle.
                b.config['replication']['static_peers'] = [source.url + '/missing',
                    source.url + '/unavailable' if cycle == 0 else source.url]
            with self.assertLogs('punkti_node.runtime', level='WARNING') as logs:
                self.runtime_cycles(b, 2, before)
            self.assertTrue(any('static replication failed' in line for line in logs.output))
        with _StaticSource(b.config['publication']['path']) as source:
            a.replicate_publication(source.url)
        self.assertEqual(self.records(a), self.expected(raws))
        self.assertEqual(self.records(b), self.expected(raws))

    def test_invalid_signature_same_mid_is_rejected(self):
        a, b = self.node('a'), self.node('b')
        raw = fixture(8)
        self.seed(a, [raw])
        broken = raw[:-1] + bytes([raw[-1] ^ 1])
        self.assertEqual(validate(broken).address, validate(raw).address)
        before = self.snapshot(b)
        for item in [wire(broken), {**wire(raw), 'sha256': '0' * 64}]:
            with self.assertRaises(ValueError):
                b.submit_records([item])
            self.assertEqual(self.snapshot(b), before)
        self.assertFalse(b.store)
        # A hostile origin can publish a hash-consistent graph containing a
        # broken signature. Only construction bypasses validation; reception
        # uses the real verifier and must not admit it.
        hostile = self.root / 'hostile'
        observation = validate(raw)
        with patch('punkti_node.publication.carrier.validate', return_value=observation):
            Publisher(hostile).publish([broken])
        with _StaticSource(hostile) as source:
            b.replicate_publication(source.url)
            self.assertEqual(self.snapshot(b), before)
            (hostile / object_path('records', digest(broken))).write_bytes(raw)
            with self.assertRaisesRegex(PublicationReadError, 'corrupt object'):
                b.replicate_publication(source.url)
            self.assertEqual(self.snapshot(b), before)

    def test_publication_race_and_stale_head_are_safe(self):
        a, b = self.node('a'), self.node('b')
        self.seed(a, [fixture(1)])
        path = Path(a.config['publication']['path']) / 'root.json'
        old = path.read_bytes()
        get = Reader.get
        changed = False
        def racing(reader, base, relative, sha=None):
            nonlocal changed
            if relative.startswith('manifests/') and not changed:
                changed = True
                self.seed(a, [fixture(2)])
            return get(reader, base, relative, sha)
        before = self.snapshot(b)
        with patch.object(Reader, 'get', racing), self.assertRaisesRegex(PublicationReadError, 'publication race'):
            b.replicate_publication(a.url + '/publication')
        self.assertEqual(self.snapshot(b), before)
        self.assertFalse(b._publication_heads)
        b.replicate_publication(a.url + '/publication')
        stable = self.snapshot(b)
        path.write_bytes(old)
        with self.assertRaisesRegex(PublicationReadError, 'stale root'):
            b.replicate_publication(a.url + '/publication')
        self.assertEqual(self.snapshot(b), stable)
        self.assertEqual(self.records(b), self.expected([fixture(1), fixture(2)]))

    def test_mixed_spatial_scopes_and_exact_z(self):
        a = self.node('a')
        b = self.node('b', {'subscriptions': [dict(xy_lo='g', xy_hi='h', z_min='0.1', z_max='0.2')]})
        hs = ['gggh00000000_0.1', 'gzzz00000000_0.19999999999999999',
              'gggh00000000_0.2', 'gggh00000000_0.09999999999999999',
              'hhhh00000000_0.1', 'ffff00000000_0.1']
        raws = [fixture(i, h=h) for i, h in enumerate(hs)]
        self.seed(a, raws)
        b.replicate_publication(a.url + '/publication')
        self.assertEqual(self.records(b), self.expected(raws[:2]))
        # XY/Z upper bounds are exclusive; lower bounds are inclusive.
        self.assertEqual(b.durable.log_lines, 2)

    def test_publication_content_addressed_objects_unchanged(self):
        a, b = self.node('a'), self.node('b')
        self.seed(a, [fixture(1)])
        self.cycle(a, b)
        for node in (a, b):
            directory = Path(node.config['publication']['path'])
            current = root((directory / 'root.json').read_bytes())
            self.assertEqual(current['v'], 'punkti/pub/0.6')
            published = manifest((directory / 'manifests' / (current['head'] + '.json')).read_bytes())
            self.assertEqual(published['record_count'], 1)
            kinds = set()
            for path in directory.rglob('*'):
                if not path.is_file() or path.name == 'root.json':
                    continue
                parts = path.relative_to(directory).parts
                kinds.add(parts[0])
                self.assertEqual(path.stem, digest(path.read_bytes()))
                if parts[0] == 'records':
                    self.assertEqual(parts, ('records', path.name[:2], path.name))
                elif parts[0] == 'h':
                    doc = json.loads(path.read_bytes())
                    self.assertEqual(parts[1:-1], tuple(doc['prefix']))
                    self.assertEqual(doc['v'], 'punkti/pub/0.6')
                else:
                    self.assertEqual(parts[0], 'manifests')
                    self.assertEqual(len(parts), 2)
            self.assertEqual(kinds, {'records', 'h', 'manifests'})


if __name__ == '__main__':
    unittest.main()
