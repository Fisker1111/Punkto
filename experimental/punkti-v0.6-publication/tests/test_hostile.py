import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from support import *


class Hostile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = [fixture(100), fixture(101)]
        cls.base = snapshot(cls.records, True)

    def check_failure(self, snap, reason=None, packs=True):
        for impl in READERS:
            with self.subTest(implementation=impl.__module__):
                with tempfile.TemporaryDirectory() as tmp:
                    materialize(snap, tmp)
                    reader = impl(packs=packs)
                    with StaticSource(tmp) as server:
                        for _ in range(2):
                            with self.assertRaises(ValueError) as error:
                                reader.read_publication(server.url)
                            self.assertEqual(error.exception.error_class, 'retryable')
                            if reason:
                                self.assertEqual(error.exception.reason, reason)
                            self.assertEqual(reader.store.valid, {})
                            self.assertEqual(reader.store.candidates, {})
                            self.assertEqual(reader.heads, {})
                            self.assertEqual(reader.checkpoints, {})

    def object_failure(self, kind, mutation):
        snap = copy.deepcopy(self.base)
        if kind == 'root':
            raw = bytes.fromhex(snap['root'])
            if mutation == 'missing':
                for impl in READERS:
                    with tempfile.TemporaryDirectory() as tmp:
                        with StaticSource(tmp) as server:
                            reader = impl()
                            with self.assertRaises(ValueError):
                                reader.read_publication(server.url)
                            self.assertFalse(reader.heads)
                            self.assertFalse(reader.store.valid)
                return
            snap['root'] = (raw[:-1] if mutation == 'truncated' else b'{"bad":true}').hex()
        else:
            sha = next(s for s, obj in snap['objects'].items() if obj['kind'] == kind)
            if mutation == 'missing':
                del snap['objects'][sha]
            else:
                obj = snap['objects'][sha]
                raw = bytes.fromhex(obj['hex'])
                if kind == 'shard':
                    obj['prefix'] = o.parse(raw)['prefix']
                obj['hex'] = (raw[:-1] if mutation == 'truncated' else raw + b'!').hex()
        self.check_failure(snap, packs=kind != 'record')

    def test_interrupted_publish_all_phases(self):
        for phase in ('objects', 'shards', 'manifest'):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as tmp:
                publisher = Publisher(tmp, True)
                publisher.publish(self.records[:1])
                original = (Path(tmp) / 'root.json').read_bytes()
                with self.assertRaises(InterruptedError):
                    publisher.publish(self.records, fail_after=phase)
                self.assertEqual((Path(tmp) / 'root.json').read_bytes(), original)
                with StaticSource(tmp) as server:
                    for impl in READERS:
                        r = impl(packs=True)
                        self.assertEqual(r.read_publication(server.url)['valid'], 1)
                    publisher.publish(self.records)
                    for impl in READERS:
                        self.assertEqual(impl(packs=True).read_publication(server.url)['valid'], 2)

    def test_determinism_repair_and_no_root_rewrite(self):
        for packs in (False, True):
            with tempfile.TemporaryDirectory() as tmp:
                p = Publisher(tmp, packs)
                p.publish(self.records)
                root_path = Path(tmp) / 'root.json'
                original, stamp = root_path.read_bytes(), root_path.stat().st_mtime_ns
                record_path = Path(tmp) / o.object_path('records', o.digest(self.records[0]))
                record_path.unlink()
                p.publish(list(reversed(self.records)) + self.records)
                self.assertEqual(record_path.read_bytes(), self.records[0])
                self.assertEqual(root_path.read_bytes(), original)
                self.assertEqual(root_path.stat().st_mtime_ns, stamp)
                independent.publish(tmp, self.records, packs)
                self.assertEqual(root_path.stat().st_mtime_ns, stamp)

    def test_publisher_order_and_atomic_root(self):
        import pubnorm.publisher as module
        from pubnorm.store import durable_write
        writes = []
        def traced(path, raw):
            writes.append(Path(path).parts)
            durable_write(path, raw)
        with tempfile.TemporaryDirectory() as tmp, patch.object(module, 'durable_write', traced):
            Publisher(tmp, True).publish(self.records)
        ranks = []
        for parts in writes:
            ranks.append(next(rank for kind, rank in [('records', 0), ('segments', 1), ('h', 2), ('manifests', 3), ('root.json', 4)] if kind in parts))
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(ranks[-1], 4)

    def test_stale_equivocal_offline_rejoin(self):
        for impl in READERS:
            with tempfile.TemporaryDirectory() as tmp:
                p = Publisher(tmp)
                p.publish(self.records[:1])
                root1 = (Path(tmp) / 'root.json').read_bytes()
                reader = impl()
                with StaticSource(tmp) as server:
                    reader.read_publication(server.url)
                    # Many missed publication revisions; no time or cursor dependency.
                    for n in range(102, 112):
                        p.publish(self.records + [fixture(n)])
                    root_latest = (Path(tmp) / 'root.json').read_bytes()
                    self.assertEqual(reader.read_publication(server.url)['valid'], 3)
                    checkpoint = copy.deepcopy(reader.checkpoints)
                    for bad, reason in [(root1, 'stale root'),
                                        (o.canonical(dict(o.parse(root_latest), head='0' * 64)), 'equivocal root')]:
                        (Path(tmp) / 'root.json').write_bytes(bad)
                        with self.assertRaises(ValueError) as exc:
                            reader.read_publication(server.url)
                        self.assertEqual(exc.exception.reason, reason)
                        self.assertEqual(reader.checkpoints, checkpoint)
                        self.assertEqual(len(reader.store.valid), 3)
                    (Path(tmp) / 'root.json').write_bytes(root_latest)
                    self.assertEqual(reader.read_publication(server.url)['admitted'], 0)

    def test_root_advanced_before_objects_and_retry(self):
        for impl in READERS:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp)
                (path / 'root.json').write_bytes(bytes.fromhex(self.base['root']))
                reader = impl(packs=True)
                with StaticSource(path) as server:
                    with self.assertRaises(ValueError):
                        reader.read_publication(server.url)
                    self.assertFalse(reader.heads)
                    materialize(self.base, path)
                    self.assertEqual(reader.read_publication(server.url)['admitted'], 2)
                    self.assertEqual(reader.read_publication(server.url)['admitted'], 0)

    def test_race_bounded_and_restarts(self):
        # Static origin changes root after serving one inconsistent root response.
        from functools import partial
        from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
        from threading import Thread
        for impl in READERS:
            for recover in (False, True):
                with tempfile.TemporaryDirectory() as tmp:
                    materialize(self.base, tmp)
                    good = bytes.fromhex(self.base['root'])
                    bad = o.canonical(dict(o.parse(good), seq=2))
                    rootfile = Path(tmp) / 'root.json'
                    rootfile.write_bytes(bad)
                    class Handler(SimpleHTTPRequestHandler):
                        def log_message(self, *_):
                            pass
                        def do_GET(self):
                            super().do_GET()
                            if self.path == '/root.json':
                                self.server.roots += 1
                                if recover:
                                    rootfile.write_bytes(good)
                    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=tmp))
                    server.roots = 0
                    thread = Thread(target=server.serve_forever, kwargs={'poll_interval': .01})
                    thread.start()
                    reader = impl(packs=True, retries=2)
                    try:
                        url = f'http://127.0.0.1:{server.server_port}'
                        if recover:
                            self.assertEqual(reader.read_publication(url)['valid'], 2)
                            self.assertEqual(server.roots, 2)
                        else:
                            with self.assertRaises(ValueError) as error:
                                reader.read_publication(url)
                            self.assertEqual(error.exception.reason, 'publication race')
                            self.assertEqual(server.roots, 3)
                            self.assertFalse(reader.checkpoints)
                            self.assertFalse(reader.store.valid)
                    finally:
                        server.shutdown()
                        server.server_close()
                        thread.join()

    def test_hash_valid_structural_record_is_per_record_rejection(self):
        def edit(node, snap):
            node['records'][0]['sha256'] = add(snap, 'record', b'not a carrier')
            node['records'].sort(key=lambda e: e['sha256'])
            node['packs'] = []
        snap = rewrite(self.base, edit, lambda m: m.update(pack_count=0))
        for impl in READERS:
            with tempfile.TemporaryDirectory() as tmp:
                materialize(snap, tmp)
                with StaticSource(tmp) as server:
                    result = impl().read_publication(server.url)
                    self.assertEqual((result['valid'], result['rejected']), (1, 1))

    def test_oversized_carrier_is_resource_failure(self):
        def edit(node, snap):
            node['records'][0]['sha256'] = add(snap, 'record', b'x' * (o.carrier.RECORD_LIMIT + 1))
            node['records'].sort(key=lambda e: e['sha256'])
            node['packs'] = []
        self.check_failure(rewrite(self.base, edit, lambda m: m.update(pack_count=0)), packs=False)

    def test_multiple_packs_257_and_independent_publication(self):
        records = [fixture(i) for i in range(257)] + [fixture(1000, '')]
        for packs in (False, True):
            with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
                Publisher(a, packs).publish(records)
                independent.publish(b, list(reversed(records)), packs)
                files = lambda p: {str(f.relative_to(p)): f.read_bytes() for f in Path(p).rglob('*') if f.is_file()}
                self.assertEqual(files(a), files(b))
                with StaticSource(b) as server:
                    for impl in READERS:
                        self.assertEqual(impl(packs=packs).read_publication(server.url)['valid'], 258)

    def test_nonconsecutive_pack_partition(self):
        records = [fixture(i) for i in range(257)]
        snap = snapshot(records, True)
        def edit(node, snap):
            blobs = [bytes.fromhex(snap['objects'][e['sha256']]['hex']) for e in node['records']]
            blobs[0], blobs[-1] = blobs[-1], blobs[0]
            node['packs'] = sorted(add(snap, 'pack', o.pack(sorted(blobs[i:i + 256], key=o.digest))) for i in (0, 256))
        self.check_failure(rewrite(snap, edit), 'pack membership')

    def test_empty_publication(self):
        for packs in (False, True):
            with tempfile.TemporaryDirectory() as tmp:
                Publisher(tmp, packs).publish([])
                with StaticSource(tmp) as server:
                    for impl in READERS:
                        self.assertEqual(impl(packs=packs).read_publication(server.url)['valid'], 0)

    def test_independent_import_boundary(self):
        import ast
        tree = ast.parse((ROOT / 'src/pubnorm/independent.py').read_text())
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertEqual(node.level, 0)
                imports.append(node.module.split('.')[0])
            elif isinstance(node, ast.Import):
                imports.extend(n.name.split('.')[0] for n in node.names)
        self.assertTrue(set(imports) <= {'hashlib', 'json', 'os', 'pathlib', 're', 'sys', 'urllib', 'carrier', 'spatial'})


for kind in ('root', 'manifest', 'shard', 'record', 'pack'):
    for mutation in ('truncated', 'corrupt', 'missing'):
        def test(self, kind=kind, mutation=mutation):
            self.object_failure(kind, mutation)
        setattr(Hostile, f'test_{kind}_{mutation}', test)


def leaf_mutation(name, fn):
    def test(self):
        def edit(node, snap):
            fn(node)
        self.check_failure(rewrite(self.base, edit))
    setattr(Hostile, 'test_leaf_' + name, test)


leaf_mutation('duplicate_entry', lambda n: n['records'].append(n['records'][0]))
leaf_mutation('unsorted_entries', lambda n: n['records'].reverse())
leaf_mutation('wrong_mid', lambda n: n['records'][0].update(mid='punkti/0.6:' + '0' * 64))
leaf_mutation('wrong_h', lambda n: n['records'][0].update(h='u4pruydqqv_1'))
leaf_mutation('wrong_namespace', lambda n: n['records'][0].update(mid='other:' + '0' * 64))
leaf_mutation('unanchored_mixed', lambda n: n['records'][0].update(h=''))
leaf_mutation('wrong_prefix', lambda n: n.update(prefix='u4pruydqqw'))
leaf_mutation('empty', lambda n: n.update(records=[], packs=[]))
leaf_mutation('extra_member', lambda n: n.update(extra=1))
leaf_mutation('duplicate_pack', lambda n: n['packs'].append(n['packs'][0]))
leaf_mutation('oversized_h', lambda n: n['records'][0].update(h='u' * 100000))
leaf_mutation('oversized_digest', lambda n: n['records'][0].update(sha256='0' * 100000))


for name, fn in {
    'extra': lambda m: m.update(extra=1),
    'negative_count': lambda m: m.update(record_count=-1),
    'boolean_count': lambda m: m.update(pack_count=True),
    'wrong_count': lambda m: m.update(record_count=999),
    'wrong_index_depth': lambda m: m.update(index={'u': next(iter(m['index'].values()))}),
    'dangling_shard': lambda m: m['index'].update(zz='0' * 64),
    'wrong_prev': lambda m: m.update(prev='0' * 64),
}.items():
    def test(self, fn=fn):
        self.check_failure(rewrite(self.base, manifest_edit=fn))
    setattr(Hostile, 'test_manifest_shape_' + name, test)


for name, raw in {
    'duplicate': b'{"head":"' + b'0' * 64 + b'","seq":1,"seq":1,"v":"punkti/pub/0.6"}',
    'float': b'{"head":"' + b'0' * 64 + b'","seq":1.0,"v":"punkti/pub/0.6"}',
    'exponent': b'{"head":"' + b'0' * 64 + b'","seq":1e0,"v":"punkti/pub/0.6"}',
    'NaN': b'{"head":"' + b'0' * 64 + b'","seq":NaN,"v":"punkti/pub/0.6"}',
    'boolean': b'{"head":"' + b'0' * 64 + b'","seq":true,"v":"punkti/pub/0.6"}',
    'negative_zero': b'{"head":"' + b'0' * 64 + b'","seq":-0,"v":"punkti/pub/0.6"}',
    'BOM': b'\xef\xbb\xbf{}',
    'newline': b'{}\n',
    'surrogate': b'{"v":"\\ud800"}',
}.items():
    def test(self, raw=raw):
        snap = copy.deepcopy(self.base)
        snap['root'] = raw.hex()
        self.check_failure(snap)
    setattr(Hostile, 'test_json_' + name, test)


class StagingAndGeometry(unittest.TestCase):
    setUpClass = classmethod(Hostile.setUpClass.__func__)
    check_failure = Hostile.check_failure
    def test_late_missing_record_preserves_both_stores_and_checkpoint(self):
        records = [fixture(300), fixture(301, alg='future'), fixture(302, 'zzzz_0')]
        snap = snapshot(records)
        missing = copy.deepcopy(snap)
        del missing['objects'][o.digest(records[-1])]
        for impl in READERS:
            with tempfile.TemporaryDirectory() as tmp:
                materialize(missing, tmp)
                reader = impl()
                with StaticSource(tmp) as server:
                    with self.assertRaises(ValueError):
                        reader.read_publication(server.url)
                    # Both staged valid and candidate were fetched before failure.
                    for raw in records[:2]:
                        self.assertIn(o.object_path('records', o.digest(raw)), reader.paths)
                    self.assertFalse(reader.store.valid)
                    self.assertFalse(reader.store.candidates)
                    self.assertFalse(reader.checkpoints)
                    materialize(snap, tmp)
                    result = reader.read_publication(server.url)
                    self.assertEqual((result['valid'], result['candidates']), (2, 1))
                    checkpoint = copy.deepcopy(reader.checkpoints)
                    (Path(tmp) / o.object_path('records', o.digest(records[-1]))).unlink()
                    with self.assertRaises(ValueError):
                        reader.read_publication(server.url)
                    self.assertEqual(reader.checkpoints, checkpoint)
                    self.assertEqual((len(reader.store.valid), len(reader.store.candidates)), (2, 1))

    def test_scope_can_skip_withheld_unselected_subtree(self):
        records = [fixture(310, '0000_0'), fixture(311, 'zzzz_0'), fixture(312, '')]
        snap = snapshot(records)
        del snap['objects'][o.digest(records[1])]
        del snap['objects'][o.digest(records[2])]
        for impl in READERS:
            with tempfile.TemporaryDirectory() as tmp:
                materialize(snap, tmp)
                with StaticSource(tmp) as server:
                    reader = impl()
                    result = reader.read_publication(server.url, o.Subscription(xy_hi='1'))
                    self.assertEqual(result['valid'], 1)
                    self.assertFalse(any('/z/' in p or '/~/' in p for p in reader.paths))
                    before = copy.deepcopy(reader.checkpoints)
                    with self.assertRaises(ValueError):
                        reader.read_publication(server.url)
                    self.assertEqual(reader.checkpoints, before)

    def test_prefix_chain_and_empty_interior(self):
        for mutation in ('chain', 'empty', 'leaf-too-early'):
            snap = copy.deepcopy(self.base)
            root = o.parse(bytes.fromhex(snap['root']))
            m = o.parse(bytes.fromhex(snap['objects'][root['head']]['hex']))
            address = m['index']['u4']
            node = o.parse(bytes.fromhex(snap['objects'][address]['hex']))
            if mutation == 'chain':
                node['children'] = {'u5p': next(iter(node['children'].values()))}
            elif mutation == 'empty':
                node['children'] = {}
            else:
                node['children'] = {}
                node['records'] = [dict(h='u4pruydqqv_0', mid=o.carrier.validate(self.records[0]).address,
                                        sha256=o.digest(self.records[0]))]
            m['index']['u4'] = add(snap, 'shard', o.canonical(node))
            root['head'] = add(snap, 'manifest', o.canonical(m))
            snap['root'] = o.canonical(root).hex()
            self.check_failure(snap, 'invalid object')

    def test_coarse_and_12_character_bounds(self):
        records = [fixture(320, 'u3bu_0'), fixture(321, 'u3butz7k9q7v_0'), fixture(322, 'u3butz7k9q7w_0')]
        snap = snapshot(records)
        for impl in READERS:
            with tempfile.TemporaryDirectory() as tmp:
                materialize(snap, tmp)
                with StaticSource(tmp) as server:
                    for scope, chosen in [(o.Subscription(xy_lo='u3bu', xy_hi='u3bu000001'), records[:1]),
                                          (o.Subscription(xy_lo='u3butz7k9q7v', xy_hi='u3butz7k9q7w'), records[1:2])]:
                        reader = impl()
                        reader.read_publication(server.url, scope)
                        self.assertEqual(set(reader.store.valid), {o.carrier.validate(r).address for r in chosen})

    def test_root_change_during_read_keeps_immutable_snapshot_readable(self):
        from functools import partial
        from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
        from threading import Thread
        for impl in READERS:
            with tempfile.TemporaryDirectory() as tmp:
                p = Publisher(tmp)
                p.publish(self.records[:1])
                old = (Path(tmp) / 'root.json').read_bytes()
                p.publish(self.records)
                new = (Path(tmp) / 'root.json').read_bytes()
                (Path(tmp) / 'root.json').write_bytes(old)
                class Handler(SimpleHTTPRequestHandler):
                    def log_message(self, *_):
                        pass
                    def do_GET(self):
                        super().do_GET()
                        if self.path.startswith('/manifests/'):
                            (Path(tmp) / 'root.json').write_bytes(new)
                server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=tmp))
                thread = Thread(target=server.serve_forever, kwargs={'poll_interval': .01})
                thread.start()
                try:
                    reader = impl()
                    url = f'http://127.0.0.1:{server.server_port}'
                    self.assertEqual(reader.read_publication(url)['valid'], 1)
                    self.assertEqual(reader.read_publication(url)['valid'], 2)
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join()
