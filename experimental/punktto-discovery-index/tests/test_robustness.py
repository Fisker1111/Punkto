import copy
import json
from pathlib import Path
from unittest.mock import patch
from punkti_node import publication as pub
from punkti_node.config import load_config
from punkti_node.store import PersistentNode
from discovery import index
from discovery.client import Client
from discovery.generator import generate
from .support import Fixture


class RobustnessTests(Fixture):
    def test_deterministic(self):
        before = {str(p.relative_to(self.discovery)): p.read_bytes() for p in self.discovery.rglob('*') if p.is_file()}
        generate(self.publication)
        after = {str(p.relative_to(self.discovery)): p.read_bytes() for p in self.discovery.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_stale_snapshot_linkage_and_cross_check(self):
        self.publisher.publish(self.records[:-1])
        result = Client(self.http()).read()
        self.assertTrue(result['stale'])
        self.assertEqual(result['source']['head'], self.head['head'])
        self.assertEqual(len(result['records']), 7)
        with self.assertRaisesRegex(ValueError, 'source head differs'):
            Client(self.http()).read(cross_check=True)

    def test_atomic_root_children_order(self):
        original = pub.durable_write
        exposed = []
        def checked(path, raw):
            if Path(path).name == 'index.json':
                obj = index.validate(raw)
                def visit(node):
                    descs = list(node.get('children', {}).values())
                    if 'unanchored' in node:
                        descs.append(node['unanchored'])
                    for desc in descs:
                        data = (Path(path).parent / desc['href']).read_bytes()
                        self.assertEqual(pub.digest(data), desc['sha256'])
                        visit(index.validate(data))
                visit(obj)
                exposed.append(True)
            original(path, raw)
        with patch.object(pub, 'durable_write', checked):
            generate(self.publication, self.publication / 'new-index')
        self.assertEqual(exposed, [True])

    def test_interrupted_and_changed_head_expose_no_new_root(self):
        original = pub.durable_write
        for failure in ('interrupt', 'changed'):
            output = self.publication / failure
            calls = []
            def write(path, raw):
                original(path, raw)
                if not calls:
                    calls.append(True)
                    if failure == 'interrupt':
                        raise InterruptedError('injected interruption')
                    self.publisher.publish(self.records[:-1])
            with patch.object(pub, 'durable_write', write):
                with self.assertRaises((ValueError, InterruptedError)):
                    generate(self.publication, output)
            self.assertFalse((output / 'index.json').exists())
        # A failed refresh preserves the previously visible root byte-for-byte.
        old = (self.discovery / 'index.json').read_bytes()
        with patch.object(pub, 'durable_write', side_effect=InterruptedError):
            with self.assertRaises(InterruptedError):
                generate(self.publication)
        self.assertEqual((self.discovery / 'index.json').read_bytes(), old)

    def test_missing_corrupt_child_and_absent_index_fallback(self):
        base = self.http()
        desc = self.root['children']['9q']
        path = self.discovery / desc['href']
        raw = path.read_bytes()
        for broken in (None, b'corrupt'):
            if broken is None:
                path.unlink()
            else:
                path.write_bytes(broken)
            result = Client(base).read()
            self.assertTrue(result['fallback'])
            self.assertEqual(len(result['records']), 7)
            self.assertEqual(result['source']['head'], self.head['head'])
        path.write_bytes(raw)
        result = Client(self.http(False)).read(exact_h='bcde_0')
        self.assertTrue(result['fallback'])
        self.assertEqual(result['fallback_reason'], 'index absent')
        self.assertEqual(len(result['records']), 1)

    def test_corrupt_record_never_returned(self):
        record = next(p for p in (self.publication / 'records').rglob('*') if p.is_file())
        record.write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            Client(self.http()).read()

    def test_path_and_shape_sanitization(self):
        for bad in ['..', '/absolute', 'a/b', 'a\n', '', 'ab//c', 'abc', '0' * 13]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                index.prefix(bad)
        for bad in ['..', '/absolute', 'A' * 64, '0' * 63, '0' * 64 + '\n']:
            with self.assertRaises(ValueError):
                index.sha(bad)
        for bad in ['..', '/records/x', 'd//x', 'd/../x', '../records/../../x', 'd/\nx', 'https://evil/x']:
            for record in (False, True):
                with self.assertRaises(ValueError):
                    index.href(bad, '0' * 64, record)
        for field, value in [('atoms', True), ('addresses', -1), ('v', 'wrong')]:
            obj = copy.deepcopy(self.root)
            obj[field] = value
            with self.assertRaises(ValueError):
                index.validate(pub.canonical(obj))
        with self.assertRaises(ValueError):
            index.validate(b'{"v":1,"v":2}')
        with self.assertRaises(ValueError):
            generate(self.publication, self.directory / 'outside')
        # Source object symlinks must not escape the publication.
        entry = next(p for p in (self.publication / 'records').rglob('*') if p.is_file())
        outside = self.directory / 'outside-record'
        outside.write_bytes(entry.read_bytes())
        entry.unlink()
        entry.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'path escape'):
            generate(self.publication)

    def test_source_corruption_and_sequence(self):
        path = self.publication / 'manifests' / (self.head['head'] + '.json')
        path.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'source digest'):
            generate(self.publication)

    def test_bootstrap_optional_index_and_legacy_compatibility(self):
        legacy = dict(id='a', base='https://a.example', publication='https://a.example/publication',
                      submit='https://a.example/submit')
        for indexed in (False, True):
            entry = dict(legacy)
            if indexed:
                entry['index'] = 'https://a.example/publication/discovery/index.json'
            config_file = self.directory / 'node.json'
            config_file.write_text(json.dumps({'web': {'enabled': False}, 'bootstrap': {'nodes': [entry]}}))
            config = load_config(config_file, {})
            node = object.__new__(PersistentNode)
            node.config = config
            result = node.special_route('GET', '/nodes.json', {})
            self.assertEqual(result['v'], 'punkti/bootstrap/1')
            self.assertEqual(result['nodes'], [entry])
            self.assertEqual({k: v for k, v in result['nodes'][0].items() if k != 'index'}, legacy)
        for extra in [{'index': 'file:///bad'}, {'index': 'https://bad/'}, {'index': 'https://a.example/\n'},
                      {'index': 'https://a.example:bad/x'}, {'index': None}, {'unknown': 'x'}]:
            config_file.write_text(json.dumps({'web': {'enabled': False}, 'bootstrap': {'nodes': [dict(legacy, **extra)]}}))
            with self.assertRaises(ValueError):
                load_config(config_file, {})

    def test_child_snapshot_mismatch_falls_back(self):
        child = copy.deepcopy(self.root)
        desc = child['children']['9q']
        obj = index.validate((self.discovery / desc['href']).read_bytes())
        obj['source']['seq'] += 1
        raw = pub.canonical(obj)
        checksum = pub.digest(raw)
        desc.update(sha256=checksum, href=f'd/{checksum}.json')
        (self.discovery / desc['href']).write_bytes(raw)
        (self.discovery / 'index.json').write_bytes(pub.canonical(child))
        result = Client(self.http()).read()
        self.assertTrue(result['fallback'])
        self.assertEqual(result['fallback_reason'], 'snapshot')
        self.assertEqual(len(result['records']), 7)

    def test_missing_terminal_falls_back(self):
        obj = self.root
        while 'children' in obj:
            desc = next(iter(obj['children'].values()))
            path = self.discovery / desc['href']
            obj = index.validate(path.read_bytes())
        path.unlink()
        result = Client(self.http()).read()
        self.assertTrue(result['fallback'])
        self.assertEqual(len(result['records']), 7)

    def test_root_replace_is_same_directory_and_atomic(self):
        old = (self.discovery / 'index.json').read_bytes()
        original = pub.os.replace
        roots = []
        def replace(src, dest):
            src, dest = Path(src), Path(dest)
            if dest.name == 'index.json':
                self.assertEqual(src.parent, dest.parent)
                self.assertEqual(dest.read_bytes(), old)
                index.validate(src.read_bytes())
                roots.append(True)
            original(src, dest)
        self.publisher.publish(self.records[:-1])
        with patch.object(pub.os, 'replace', replace):
            generate(self.publication)
        self.assertEqual(roots, [True])
        self.assertNotEqual((self.discovery / 'index.json').read_bytes(), old)

    def test_output_symlink_escape_rejected(self):
        outside = self.directory / 'external'
        outside.mkdir()
        output = self.publication / 'escape-index'
        output.mkdir()
        (output / 'd').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'discovery path escape'):
            generate(self.publication, output)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((output / 'index.json').exists())

    def test_source_sequence_mismatch_exposes_no_root(self):
        root = dict(self.head, seq=self.head['seq'] + 1)
        (self.publication / 'root.json').write_bytes(pub.canonical(root))
        output = self.publication / 'sequence-index'
        with self.assertRaisesRegex(ValueError, 'source sequence'):
            generate(self.publication, output)
        self.assertFalse((output / 'index.json').exists())

    def test_malicious_href_is_not_fetched(self):
        obj = copy.deepcopy(self.root)
        obj['children']['9q']['href'] = '../outside'
        (self.discovery / 'index.json').write_bytes(pub.canonical(obj))
        client = Client(self.http())
        result = client.read()
        self.assertTrue(result['fallback'])
        self.assertEqual(result['fallback_reason'], 'href')
        self.assertFalse(any('outside' in url for url in client.http.paths))
