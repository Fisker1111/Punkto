"""Stage-2 static publication tests for publisher, reader and /submit."""
import copy
import base64
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'experimental/punkti-v0.6-mesh/tests'))

from support import fixture
from punkti_node.config import load_config
from punkti_node.mesh import wire
from punkti_node.publication import Publisher, Reader, digest, root, manifest, object_path, shard_path
from punkti_node.store import PersistentNode
from punkti_node.web import StaticWeb


class _StaticSource:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.server = None
        self.thread = None
        self.url = None

    def __enter__(self):
        import http.server
        from functools import partial

        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *_):
                pass

        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(self.directory)))
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.02}, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'
        return self

    def __exit__(self, exc_type, exc, tb):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


def materialize_fixture(snapshot, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'root.json').write_bytes(bytes.fromhex(snapshot['root']))
    for sha, obj in snapshot['objects'].items():
        raw = bytes.fromhex(obj['hex'])
        kind = obj['kind']
        if kind == 'manifest':
            relative = f'manifests/{sha}.json'
        elif kind == 'shard':
            prefix = obj.get('prefix') or json.loads(raw.decode('utf-8'))['prefix']
            relative = shard_path(prefix, sha)
        else:
            relative = object_path('records' if kind == 'record' else 'segments', sha)
        target = directory / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)


class PublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vectors = json.loads((ROOT / 'experimental/punkti-v0.6-publication/vectors.json').read_text())

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
        data = dict(
            web=dict(enabled=False),
            node=dict(name=name),
            network=dict(listen_host='127.0.0.1', listen_port=0),
            storage=dict(data_path=str(self.root / name)),
        )
        for key, value in (extra or {}).items():
            if isinstance(value, dict):
                data.setdefault(key, {}).update(value)
            else:
                data[key] = value
        path = self.root / f'{name}.yml'
        path.write_text(json.dumps(data))
        return load_config(path, {})

    def node(self, name='a', extra=None):
        config = self.config(name, extra)
        node = PersistentNode(config)
        self.nodes.append(node)
        net = config['network']
        node.start(net['listen_port'], net['listen_host'])
        publication = config['publication']
        node.web = StaticWeb(None, False, {publication['serve_prefix']: publication['path']})
        return node

    def post_submit(self, node, payload):
        body = json.dumps(payload).encode('utf-8')
        request = Request(node.url + '/submit', data=body, headers={'Content-Type': 'application/json'})
        with urlopen(request, timeout=5) as response:
            return response.getcode(), json.loads(response.read())

    def test_publish_idempotent_same_root(self):
        directory = self.root / 'pub'
        publisher = Publisher(directory)
        records = [fixture(1), fixture(2)]
        first = publisher.publish(records)
        second = publisher.publish(records)
        self.assertEqual(first, second)
        self.assertEqual(root((directory / 'root.json').read_bytes()), first)

    def test_manifest_chain_progression(self):
        directory = self.root / 'pub'
        publisher = Publisher(directory)
        first = publisher.publish([fixture(1)])
        second = publisher.publish([fixture(1), fixture(2)])
        m1 = manifest((directory / f"manifests/{first['head']}.json").read_bytes())
        m2 = manifest((directory / f"manifests/{second['head']}.json").read_bytes())
        self.assertEqual(m1['seq'], 1)
        self.assertIsNone(m1['prev'])
        self.assertEqual(m2['seq'], 2)
        self.assertEqual(m2['prev'], first['head'])

    def test_root_atomicity_on_interruption(self):
        directory = self.root / 'pub'
        publisher = Publisher(directory)
        stable = publisher.publish([fixture(1)])
        with self.assertRaises(InterruptedError):
            publisher.publish([fixture(1), fixture(2)], fail_after='manifest')
        self.assertEqual(root((directory / 'root.json').read_bytes()), stable)

    def test_reader_matches_frozen_vectors(self):
        fixture_data = self.vectors['fixtures']['index']
        expected = self.vectors['vectors'][0]['cases'][0]['expected']
        materialize_fixture(fixture_data, self.root / 'publication')
        with _StaticSource(self.root / 'publication') as source:
            result = Reader().read_publication(source.url)
        self.assertEqual(result['head'], expected['head'])
        self.assertEqual(result['seq'], expected['seq'])
        self.assertEqual(result['valid'], expected['valid_count'])
        self.assertEqual(result['candidates'], expected['candidate_count'])
        self.assertEqual(result['rejected'], expected['rejected'])

    def test_submit_dedupe_and_republish(self):
        node = self.node()
        wrapper = wire(fixture(7))
        before = node.durable.log_lines
        status, first = self.post_submit(node, {'records': [wrapper]})
        self.assertEqual(status, 200)
        self.assertEqual(first['results'][0]['duplicate'], False)
        self.assertIn('head', first)
        self.assertIn('seq', first)
        self.assertEqual(node.durable.log_lines, before + 1)

        status, second = self.post_submit(node, {'records': [wrapper]})
        self.assertEqual(status, 200)
        self.assertEqual(second['results'][0]['duplicate'], True)
        self.assertEqual(node.durable.log_lines, before + 1)

    def test_submit_rejects_invalid_record(self):
        node = self.node()
        wrapper = wire(fixture(9))
        broken = copy.deepcopy(wrapper)
        raw = bytearray(base64.b64decode(wrapper['record']))
        raw[-1] ^= 1
        broken['record'] = base64.b64encode(bytes(raw)).decode('ascii')
        broken['sha256'] = digest(bytes(raw))
        request = Request(node.url + '/submit', data=json.dumps({'records': [broken]}).encode('utf-8'), headers={'Content-Type': 'application/json'})
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=5)
        self.assertEqual(caught.exception.code, 400)
        payload = json.loads(caught.exception.read())
        caught.exception.close()
        self.assertIn('INVALID-provenance', payload['error'])

    def test_static_replication_without_pull_or_sync(self):
        a = self.node('a')
        b = self.node('b')
        a.add(fixture(1))
        a.add(fixture(2))
        a.republish_publication()
        b.replicate_publication(a.url + '/publication')
        self.assertEqual({digest(entry.raw) for entry in a.store.values()}, {digest(entry.raw) for entry in b.store.values()})

    def test_restart_persists_store_and_publication(self):
        node = self.node('a')
        node.add(fixture(1))
        node.republish_publication()
        publication_root = Path(node.config['publication']['path']) / 'root.json'
        self.assertTrue(publication_root.exists())
        node.stop()
        node.durable.close()

        restarted = self.node('a')
        self.assertEqual(len(restarted.store), 1)
        self.assertTrue((Path(restarted.config['publication']['path']) / 'root.json').exists())


if __name__ == '__main__':
    unittest.main()
