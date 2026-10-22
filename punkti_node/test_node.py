"""Standalone operational acceptance suite using the original signing fixtures."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'experimental/punkti-v0.6-mesh/tests'))
from support import fixture, geo
from punkti_node.carrier import unb64, validate
from punkti_node.config import load_config
from punkti_node.mesh import peer_url, request, wire
from punkti_node.store import PersistentNode


class NodeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.nodes = []
        self.addCleanup(self.close_nodes)

    def close_nodes(self):
        for node in self.nodes:
            node.stop()
            node.durable.close()

    def config(self, name='a', extra=None):
        data = dict(web=dict(enabled=False), node=dict(name=name), network=dict(listen_host='127.0.0.1', listen_port=0),
                    storage=dict(data_path=str(self.root / name)))
        for key, value in (extra or {}).items():
            if isinstance(value, dict):
                data.setdefault(key, {}).update(value)
            else:
                data[key] = value
        path = self.root / (name + '.yml')
        path.write_text(json.dumps(data))
        return load_config(path, {})

    def node(self, name='a', extra=None):
        config = self.config(name, extra)
        node = PersistentNode(config)
        self.nodes.append(node)
        net = config['network']
        return node.start(net['listen_port'], net['listen_host'])

    def test_yaml(self):
        c = self.config(extra={'network': {'peers': ['https://example.org'], 'listen_port': 1234},
                               'subscriptions': [{'h_lo': 'g', 'h_hi': 'h'}]})
        self.assertEqual(c['node']['name'], 'a')
        self.assertEqual(c['network']['listen_host'], '127.0.0.1')
        self.assertEqual(c['network']['listen_port'], 1234)
        self.assertEqual(c['network']['peers'], ['https://example.org'])
        self.assertEqual(c['storage']['data_path'], str(self.root / 'a'))
        self.assertEqual(c['subscriptions'][0]['h_lo'], 'g')

    def test_environment(self):
        self.config()
        c = load_config('/does/not/exist', {'PUNKTO_NODE_CONFIG': str(self.root / 'a.yml'),
            'PUNKTO_HOST': '0.0.0.0', 'PUNKTO_PORT': '4321', 'PUNKTO_NODE_NAME': 'override',
            'PUNKTO_PEERS': 'http://one:80, https://two', 'PUNKTO_DATA_DIR': '/new',
            'PUNKTO_SYNC_INTERVAL': '12', 'PUNKTO_LOG_LEVEL': 'debug'})
        self.assertEqual(c['node']['name'], 'override')
        self.assertEqual(c['network'], dict(listen_host='0.0.0.0', listen_port=4321,
            advertise_url='', peers=['http://one:80', 'https://two'], sync_interval_seconds=12))
        self.assertEqual(c['storage']['data_path'], '/new')
        self.assertEqual(c['logging']['level'], 'debug')

    def test_empty_subscriptions(self):
        node = self.node(extra={'subscriptions': []})
        self.assertFalse(node.add(fixture())['admitted'])
        self.assertFalse(node.store)

    def test_default_global(self):
        node = self.node()
        self.assertTrue(node.add(fixture())['admitted'])
        self.assertEqual(len(node.subscriptions), 1)

    def test_invalid_subscription(self):
        for sub in [{'h_lo': 'INVALID'}, {'z_min': 5, 'z_max': 2}, {'extra': 0}]:
            with self.subTest(sub=sub), self.assertRaisesRegex(ValueError, 'invalid subscription'):
                self.config(extra={'subscriptions': [sub]})

    def test_invalid_config(self):
        for extra in [{'network': {'listen_port': True}}, {'network': {'sync_interval_seconds': 0}},
                      {'logging': {'level': 'verbose'}}, {'network': {'peers': ['ftp://example']}}]:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                self.config(extra=extra)

    def test_peer_origins(self):
        for origin in ['https://example.org', 'http://node-b:8000', 'http://127.0.0.1:1']:
            self.assertEqual(peer_url(origin), origin)
        for origin in ['ftp://example', 'https://u:p@example', 'http://example/',
                       'http://example?q=1', 'http://example#f', 'relative', 'http://example:bad']:
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                peer_url(origin)

    def test_durable_restart_pull_bytes(self):
        node = self.node()
        raw = fixture()
        node.add(raw)
        epoch = node.epoch
        node.after_sync()
        node.stop()
        node.durable.close()
        again = self.node()
        result = request(again.url, '/pull?' + urlencode({'q': '{}'}))
        self.assertEqual(unb64(result['records'][0]['record']), raw)
        self.assertEqual(again.epoch, epoch)
        self.assertEqual(again.durable.meta, node.durable.meta)

    def test_two_node_sync(self):
        a, b = self.node('a'), self.node('b')
        self.assertNotEqual(a.url, b.url)
        a.peers.add(b.url)
        b.peers.add(a.url)
        raw = fixture(42)
        request(a.url, '/push', {'records': [wire(raw)]})
        a.connect(b.url)
        self.assertEqual(b.store[validate(raw).address].raw, raw)

    def test_spatial_filtering(self):
        node = self.node(extra={'subscriptions': [{'h_lo': 'g', 'h_hi': 'h'}]})
        self.assertTrue(node.add(fixture())['admitted'])
        self.assertFalse(node.add(fixture(1, h='z'*12))['admitted'])
        altitude = self.node('altitude', {'subscriptions': [{'z_min': 50, 'z_max': 150}]})
        self.assertTrue(altitude.add(fixture(h=geo(100)))['admitted'])
        self.assertFalse(altitude.add(fixture(h=geo(500)))['admitted'])

    def test_unknown_l4_sync(self):
        a, b = self.node('a'), self.node('b')
        raw = fixture(x='future-app:🛰\x00\nunknown<>')
        a.add(raw)
        b.pull(a.url)
        self.assertEqual(b.store[validate(raw).address].raw, raw)

    def test_operational_routes(self):
        node = self.node()
        self.assertEqual(request(node.url, '/health')['status'], 'ok')
        self.assertEqual(request(node.url, '/ready')['status'], 'ready')
        info = request(node.url, '/node/info')
        self.assertEqual(info['protocol'], 'punkti-mesh/0.6-draft')
        self.assertEqual(info['node']['name'], 'a')
        self.assertEqual(info['config_path'], 'a.yml')
        self.assertTrue(info['config_loaded'])
        self.assertNotIn(str(self.root), json.dumps(info))
        self.assertNotIn('operator_contact', json.dumps(info))

    def test_write_failure_not_ready(self):
        node = self.node()
        with patch('punkti_node.store.os.fsync', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                node.add(fixture())
        with self.assertRaises(HTTPError) as caught:
            request(node.url, '/ready')
        self.assertEqual(caught.exception.code, 503)
        self.assertIn('durable write failure', json.load(caught.exception)['reasons'])
        self.assertEqual(request(node.url, '/health')['status'], 'ok')

    def test_candidate_replay_and_corruption(self):
        node = self.node()
        unknown = fixture(alg='future-pq')
        opaque = wire(b'future\x00\xff', 'punkti/9:abcd')
        node.add(unknown)
        node.admit(opaque)
        node.stop()
        node.durable.close()
        path = self.root / 'a' / 'atoms.jsonl'
        with path.open('ab') as f:
            f.write(json.dumps(opaque).encode() + b'\n')
            f.write(b'broken\n{"torn":')
        again = self.node()
        self.assertEqual({e.raw for e in again.candidates.values()}, {unknown, b'future\x00\xff'})
        self.assertEqual(again.counts()['corrupt_lines'], 2)
        self.assertEqual(again.counts()['duplicate_lines'], 1)
        again.add(fixture(99))
        again.stop()
        again.durable.close()
        third = self.node()
        self.assertEqual(len(third.store), 1)
        self.assertEqual(len(third.candidates), 2)

    def test_cursor_restart(self):
        a, b = self.node('a'), self.node('b')
        a.add(fixture())
        b.pull(a.url)
        b.push_to(a.url)
        expected = b.cursors.copy(), b.push_cursors.copy()
        b.stop()
        b.durable.close()
        b = self.node('b')
        self.assertEqual((b.cursors, b.push_cursors), expected)
        a.add(fixture(1))
        b.pull(a.url)
        self.assertEqual(len(b.store), 2)

    def test_cursor_write_failure_not_ready(self):
        node = self.node()
        with patch('punkti_node.store.os.replace', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                node.after_sync()
        with self.assertRaises(HTTPError) as caught:
            request(node.url, '/ready')
        self.assertEqual(caught.exception.code, 503)
        caught.exception.close()

    def test_invalid_cursor_file_restarts_from_null(self):
        node = self.node()
        node.add(fixture())
        node.stop()
        node.durable.close()
        (self.root / 'a/cursors.json').write_text(json.dumps({
            'cursors': [[['http://peer', 'scope'], {'epoch': 'e', 'scope': 's', 'after': -1, 'ceiling': 0}]],
            'push_cursors': []}))
        node = self.node()
        self.assertEqual(node.cursors, {})
        self.assertEqual(len(node.store), 1)

    def test_replay_after_subscription_change(self):
        a = self.node()
        a.add(fixture())
        a.stop()
        a.durable.close()
        a = self.node(extra={'subscriptions': []})
        self.assertEqual(len(a.store), 1)
        self.assertFalse(a.add(fixture(1))['admitted'])

    def test_start_bind_and_advertise(self):
        node = PersistentNode(self.config())
        self.nodes.append(node)
        node.start(host='0.0.0.0')
        self.assertTrue(node.url.startswith('http://127.0.0.1:'))
        node.stop()
        node.start(host='127.0.0.1', advertise_url='https://alice.example')
        self.assertEqual(node.url, 'https://alice.example')

    def test_runtime_sigterm_with_unavailable_peer(self):
        self.config(extra={'network': {'peers': ['http://127.0.0.1:1'], 'sync_interval_seconds': 0.1}})
        with tempfile.TemporaryFile(mode='w+') as output:
            process = subprocess.Popen([sys.executable, '-m', 'punkti_node', '--config', str(self.root / 'a.yml')],
                                       cwd=ROOT, stdout=output, stderr=output)
            try:
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    output.seek(0)
                    if 'sync peers unavailable' in output.read():
                        break
                    if process.poll() is not None:
                        self.fail('runtime exited before signal')
                    time.sleep(0.05)
                else:
                    self.fail('runtime did not attempt sync')
                process.send_signal(signal.SIGTERM)
                self.assertEqual(process.wait(timeout=8), 0)
                self.assertTrue((self.root / 'a/cursors.json').exists())
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(NodeTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f'{passed}/{result.testsRun} tests passed')
    raise SystemExit(0 if result.wasSuccessful() else 1)
