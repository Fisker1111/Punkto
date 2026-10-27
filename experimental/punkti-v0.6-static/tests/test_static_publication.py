import json
import copy
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(ROOT / 'src'))

from staticpub import cleanroom
from staticpub import bench
from staticpub.carrier_io import Subscription, carrier, digest, leaf_key, make_record, unpacked
from staticpub.harness import Node
from staticpub.httpsource import StaticSource


def xy_tail(number, length):
    chars = []
    alphabet = carrier.ALPHABET
    for _ in range(length):
        chars.append(alphabet[number % 32])
        number //= 32
    return ''.join(reversed(chars))


def make_h(index, prefix='u4', z='0'):
    return prefix + xy_tail(index, 10 - len(prefix)) + '_' + z


def tampered_signature(raw):
    atom, body, sig = carrier.decode(raw)
    changed = bytearray(sig)
    changed[0] ^= 1
    atom['sig'] = carrier.b64(bytes(changed))
    return carrier.record(atom)


def first_leaf_shard_with_packs(public_root):
    root = unpacked((public_root / 'punkti' / 'root.json').read_bytes())
    manifest = unpacked((public_root / 'punkti' / 'manifests' / f"{root['head']}.json").read_bytes())
    prefix, sha = sorted(manifest['index'].items())[0]
    shard_path = public_root / 'punkti' / 'h' / Path(*prefix) / f'{sha}.json'
    while True:
        shard = unpacked(shard_path.read_bytes())
        if shard['packs']:
            return shard_path, shard
        child_prefix, child_sha = sorted(shard['children'].items())[0]
        shard_path = public_root / 'punkti' / 'h' / Path(*child_prefix) / f'{child_sha}.json'


def shard_for_prefix(public_root, manifest, prefix):
    shard_sha = manifest['index'][prefix[:2]]
    shard_path = public_root / 'punkti' / 'h' / Path(*prefix[:2]) / f'{shard_sha}.json'
    while True:
        shard = unpacked(shard_path.read_bytes())
        if shard['prefix'] == prefix:
            return shard
        next_prefix = None
        for candidate in sorted(shard['children']):
            if prefix.startswith(candidate):
                next_prefix = candidate
                break
        if next_prefix is None:
            raise AssertionError('prefix not reachable')
        shard_path = public_root / 'punkti' / 'h' / Path(*next_prefix) / f"{shard['children'][next_prefix]}.json"


class StaticPublicationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def mk_node(self, name, mode='A', subscriptions=None):
        return Node(self.root / f'{name}-{mode.lower()}', mode=mode, subscriptions=subscriptions)

    def mk_depth_node(self, name, mode='A', subscriptions=None, leaf_depth=10):
        return Node(self.root / f'{name}-{mode.lower()}-d{leaf_depth}', mode=mode,
                    subscriptions=subscriptions, leaf_depth=leaf_depth)

    def add_records(self, node, records):
        for raw in records:
            node.store.admit(raw)

    def assert_mode_sets(self, checker):
        for mode in ('A', 'B'):
            with self.subTest(mode=mode):
                checker(mode)

    def records_with_prefixes(self, start, count, prefixes):
        out = []
        for i in range(count):
            prefix = prefixes[i % len(prefixes)]
            out.append(make_record(start + i, make_h(start + i, prefix=prefix, z=str((start + i) % 5 - 2))))
        return out

    def test_01_two_node_union_convergence(self):
        def checker(mode):
            node_a = self.mk_node('a', mode)
            node_b = self.mk_node('b', mode)
            records = {name: make_record(i + 1, make_h(i + 1, prefix='u4')) for i, name in enumerate('ABCDEF')}
            self.add_records(node_a, [records[k] for k in 'ABCD'])
            self.add_records(node_b, [records[k] for k in 'CDEF'])
            node_a.publish()
            node_b.publish()
            with StaticSource(node_a.path / 'public') as src_a, StaticSource(node_b.path / 'public') as src_b:
                base_a = src_a.url + '/punkti'
                base_b = src_b.url + '/punkti'
                node_a.replicate(base_b)
                node_b.replicate(base_a)
            self.assertEqual(set(node_a.store.valid), set(node_b.store.valid))
            self.assertEqual(len(node_a.store.valid), 6)

        self.assert_mode_sets(checker)

    def test_02_same_mid_invalid_variant_cannot_poison_valid(self):
        valid = make_record(11, make_h(11, prefix='u4', z='1'))
        bad = tampered_signature(valid)
        node = self.mk_node('poison', 'A')
        ok = node.store.admit(valid)
        bad_state = node.store.admit(bad)
        self.assertEqual(ok, carrier.State.VALID.value)
        self.assertEqual(bad_state, carrier.State.PROVENANCE.value)
        self.assertEqual(len(node.store.valid), 1)
        self.assertEqual(len(node.store.candidates), 0)

    def test_03_same_xy_different_z_filter(self):
        def checker(mode):
            source = self.mk_node('zsource', mode)
            node = self.mk_node('ztarget', mode)
            low = make_record(21, 'u4pruydqqv_-5')
            high = make_record(22, 'u4pruydqqv_1000.125')
            self.add_records(source, [low, high])
            source.publish()
            with StaticSource(source.path / 'public') as src:
                base = src.url + '/punkti'
                result = node.reader.read_publication(base, Subscription(xy_lo='u4', xy_hi='u5', z_min='0', z_max='2000'))
            self.assertEqual(result['admitted'], 1)
            self.assertEqual(len(node.store.valid), 1)
            admitted = list(node.store.valid.values())[0]
            self.assertEqual(carrier.validate(admitted).h, 'u4pruydqqv_1000.125')

        self.assert_mode_sets(checker)

    def test_04_xy_prefix_limited_replication_only_fetches_matching_region(self):
        def checker(mode):
            source = self.mk_node('psource', mode)
            target = self.mk_node('ptarget', mode, [Subscription(xy_lo='u4', xy_hi='u5')])
            records = self.records_with_prefixes(50, 24, ['u4', 'u5', 'u6'])
            self.add_records(source, records)
            source.publish()
            with StaticSource(source.path / 'public') as server:
                base = server.url + '/punkti'
                before = len(target.reader.paths)
                target.replicate(base)
                requested = target.reader.paths[before:]
            admitted_h = {carrier.validate(raw).h for raw in target.store.valid.values()}
            self.assertTrue(admitted_h)
            self.assertTrue(all(h.startswith('u4') for h in admitted_h))
            for raw in records:
                record_sha = digest(raw)
                path = f'records/{record_sha[:2]}/{record_sha}'
                h = carrier.validate(raw).h
                if mode == 'A' and h.startswith('u4'):
                    self.assertIn(path, requested)
                else:
                    self.assertNotIn(path, requested)
            if mode == 'B':
                self.assertTrue(any(path.startswith('segments/') for path in requested))

        self.assert_mode_sets(checker)

    def test_05_negative_and_large_z_values_preserved(self):
        def checker(mode):
            source = self.mk_node('largezsource', mode)
            target = self.mk_node('largeztarget', mode)
            values = ['-12345678901234567890', '123456789012345678901']
            records = [make_record(80 + i, make_h(80 + i, prefix='u4', z=z)) for i, z in enumerate(values)]
            self.add_records(source, records)
            source.publish()
            with StaticSource(source.path / 'public') as server:
                target.replicate(server.url + '/punkti')
            found = {carrier.validate(raw).h.split('_', 1)[1] for raw in target.store.valid.values()}
            self.assertEqual(found, set(values))

        self.assert_mode_sets(checker)

    def test_06_dumb_static_server_replication_works_after_node_stop(self):
        def checker(mode):
            source = self.mk_node('offline-source', mode)
            target = self.mk_node('offline-target', mode)
            self.add_records(source, self.records_with_prefixes(100, 10, ['u4']))
            source.publish()
            source.stop()
            with StaticSource(source.path / 'public') as server:
                target.replicate(server.url + '/punkti')
            self.assertEqual(len(target.store.valid), 10)

        self.assert_mode_sets(checker)

    def test_07_stale_root_then_refresh_detected(self):
        def checker(mode):
            source = self.mk_node('stale-source', mode)
            target = self.mk_node('stale-target', mode)
            first = make_record(120, make_h(120, prefix='u4'))
            self.add_records(source, [first])
            source.publish()
            root_path = source.path / 'public' / 'punkti' / 'root.json'
            root_old = root_path.read_bytes()
            with StaticSource(source.path / 'public') as server:
                base = server.url + '/punkti'
                target.reader.read_publication(base)
                second = make_record(121, make_h(121, prefix='u4'))
                self.add_records(source, [second])
                source.publish()
                target.reader.read_publication(base)
                root_path.write_bytes(root_old)
                with self.assertRaises(ValueError):
                    target.reader.read_publication(base)

        self.assert_mode_sets(checker)

    def test_08_missing_referenced_object_no_false_checkpoint(self):
        def checker(mode):
            source = self.mk_node('missing-source', mode)
            target = self.mk_node('missing-target', mode)
            base_records = self.records_with_prefixes(130, 6, ['u4'])
            self.add_records(source, base_records)
            source.publish()
            with StaticSource(source.path / 'public') as server:
                base = server.url + '/punkti'
                first = target.reader.read_publication(base)
                checkpoint_key = (base, tuple(Subscription().wire().items()))
                old_head = target.reader.checkpoints[checkpoint_key]
                extra = make_record(199, make_h(199, prefix='u4'))
                self.add_records(source, [extra])
                source.publish()
                extra_sha = digest(extra)
                if mode == 'A':
                    (source.path / 'public' / 'punkti' / 'records' / extra_sha[:2] / extra_sha).unlink()
                else:
                    root = unpacked((source.path / 'public' / 'punkti' / 'root.json').read_bytes())
                    manifest = unpacked((source.path / 'public' / 'punkti' / 'manifests' / f"{root['head']}.json").read_bytes())
                    prefix = leaf_key(carrier.validate(extra).h)
                    shard_sha = manifest['index'][prefix[:2]]
                    shard_path = source.path / 'public' / 'punkti' / 'h' / Path(*prefix[:2]) / f'{shard_sha}.json'
                    while True:
                        shard = unpacked(shard_path.read_bytes())
                        if shard['prefix'] == prefix:
                            break
                        next_prefix = sorted(shard['children'])[0]
                        for candidate in sorted(shard['children']):
                            if prefix.startswith(candidate):
                                next_prefix = candidate
                                break
                        shard_path = source.path / 'public' / 'punkti' / 'h' / Path(*next_prefix) / f"{shard['children'][next_prefix]}.json"
                    segment_sha = shard['packs'][0]
                    (source.path / 'public' / 'punkti' / 'segments' / segment_sha[:2] / segment_sha).unlink()
                    target.reader.cache.clear()
                with self.assertRaises(Exception):
                    target.reader.read_publication(base)
                self.assertEqual(target.reader.checkpoints[checkpoint_key], old_head)
                self.assertEqual(first['valid'], len(target.store.valid))
                source.publish()
                target.reader.read_publication(base)
            self.assertEqual(len(target.store.valid), len(base_records) + 1)

        self.assert_mode_sets(checker)

    def test_09_source_disappearance_and_reappearance_is_idempotent(self):
        def checker(mode):
            source = self.mk_node('vanish-source', mode)
            target = self.mk_node('vanish-target', mode)
            self.add_records(source, self.records_with_prefixes(220, 8, ['u4']))
            source.publish()
            with StaticSource(source.path / 'public') as server:
                base = server.url + '/punkti'
                target.reader.read_publication(base)
                port = int(server.url.rsplit(':', 1)[1])
            with self.assertRaises((ConnectionRefusedError, URLError, OSError, socket.timeout)):
                target.reader.read_publication(f'http://127.0.0.1:{port}/punkti')
            before = len(target.store.valid)
            with StaticSource(source.path / 'public', port=port) as server:
                result = target.reader.read_publication(server.url + '/punkti')
                self.assertEqual(result['admitted'], 0)
            self.assertEqual(len(target.store.valid), before)

        self.assert_mode_sets(checker)

    def test_10_three_node_partial_overlap_converges_to_union(self):
        def checker(mode):
            node_a = self.mk_node('ta', mode)
            node_b = self.mk_node('tb', mode)
            node_c = self.mk_node('tc', mode)
            records = {i: make_record(300 + i, make_h(300 + i, prefix='u4' if i % 2 else 'u5')) for i in range(9)}
            self.add_records(node_a, [records[i] for i in (0, 1, 2, 3)])
            self.add_records(node_b, [records[i] for i in (2, 3, 4, 5)])
            self.add_records(node_c, [records[i] for i in (5, 6, 7, 8)])
            node_a.publish()
            node_b.publish()
            node_c.publish()
            with StaticSource(node_a.path / 'public') as a_srv, StaticSource(node_b.path / 'public') as b_srv, StaticSource(node_c.path / 'public') as c_srv:
                a_base = a_srv.url + '/punkti'
                b_base = b_srv.url + '/punkti'
                c_base = c_srv.url + '/punkti'
                for _ in range(3):
                    node_a.replicate(b_base)
                    node_a.replicate(c_base)
                    node_b.replicate(a_base)
                    node_b.replicate(c_base)
                    node_c.replicate(a_base)
                    node_c.replicate(b_base)
            expected = set().union(node_a.store.valid, node_b.store.valid, node_c.store.valid)
            self.assertEqual(set(node_a.store.valid), expected)
            self.assertEqual(set(node_b.store.valid), expected)
            self.assertEqual(set(node_c.store.valid), expected)

        self.assert_mode_sets(checker)

    def test_11_hostile_truncated_record_rejected(self):
        source = self.mk_node('trunc-source', 'A')
        target = self.mk_node('trunc-target', 'A')
        record = make_record(500, make_h(500, prefix='u4'))
        self.add_records(source, [record])
        source.publish()
        sha = digest(record)
        path = source.path / 'public' / 'punkti' / 'records' / sha[:2] / sha
        path.write_bytes(path.read_bytes()[:-3])
        with StaticSource(source.path / 'public') as server:
            with self.assertRaises(ValueError):
                target.reader.read_publication(server.url + '/punkti')
        self.assertEqual(len(target.store.valid), 0)

    def test_12_hostile_missing_segment_in_mode_b_fails(self):
        source = self.mk_node('seg-source', 'B')
        target = self.mk_node('seg-target', 'B')
        self.add_records(source, self.records_with_prefixes(520, 9, ['u4']))
        source.publish()
        _, shard = first_leaf_shard_with_packs(source.path / 'public')
        segment_sha = shard['packs'][0]
        (source.path / 'public' / 'punkti' / 'segments' / segment_sha[:2] / segment_sha).unlink()
        with StaticSource(source.path / 'public') as server:
            with self.assertRaises(Exception):
                target.reader.read_publication(server.url + '/punkti')

    def test_13_hostile_corrupt_root_object_rejected(self):
        source = self.mk_node('corrupt-root-source', 'A')
        target = self.mk_node('corrupt-root-target', 'A')
        self.add_records(source, [make_record(540, make_h(540, prefix='u4'))])
        source.publish()
        (source.path / 'public' / 'punkti' / 'root.json').write_text('{bad-json', encoding='utf-8')
        with StaticSource(source.path / 'public') as server:
            with self.assertRaises(Exception):
                target.reader.read_publication(server.url + '/punkti')

    def test_14_hostile_mismatched_digest_rejected(self):
        source = self.mk_node('digest-source', 'A')
        target = self.mk_node('digest-target', 'A')
        self.add_records(source, [make_record(560, make_h(560, prefix='u4'))])
        source.publish()
        root = unpacked((source.path / 'public' / 'punkti' / 'root.json').read_bytes())
        manifest_path = source.path / 'public' / 'punkti' / 'manifests' / f"{root['head']}.json"
        manifest_path.write_bytes(manifest_path.read_bytes() + b'\n')
        with StaticSource(source.path / 'public') as server:
            with self.assertRaises(ValueError):
                target.reader.read_publication(server.url + '/punkti')

    def test_15_hostile_replay_duplicate_is_noop(self):
        source = self.mk_node('replay-source', 'A')
        target = self.mk_node('replay-target', 'A')
        self.add_records(source, self.records_with_prefixes(580, 12, ['u4']))
        source.publish()
        with StaticSource(source.path / 'public') as server:
            base = server.url + '/punkti'
            first = target.reader.read_publication(base)
            second = target.reader.read_publication(base)
        self.assertEqual(first['admitted'], 12)
        self.assertEqual(second['admitted'], 0)
        self.assertEqual(len(target.store.valid), 12)

    def test_16_hostile_reordered_publication_visibility(self):
        source = self.mk_node('order-source', 'A')
        target = self.mk_node('order-target', 'A')
        self.add_records(source, [make_record(600, make_h(600, prefix='u4'))])
        source.publish()
        root_path = source.path / 'public' / 'punkti' / 'root.json'
        old = unpacked(root_path.read_bytes())
        fake = dict(v=old['v'], seq=old['seq'] + 1, head='a' * 64, updated_at=old['updated_at'])
        root_path.write_text(json.dumps(fake, separators=(',', ':'), sort_keys=True), encoding='utf-8')
        with StaticSource(source.path / 'public') as server:
            base = server.url + '/punkti'
            with self.assertRaises(Exception):
                target.reader.read_publication(base)
            self.assertEqual(len(target.store.valid), 0)
        root_path.write_bytes(json.dumps(old, separators=(',', ':'), sort_keys=True).encode('utf-8'))
        self.add_records(source, [make_record(601, make_h(601, prefix='u4'))])
        source.publish()
        with StaticSource(source.path / 'public') as server:
            result = target.reader.read_publication(server.url + '/punkti')
        self.assertEqual(result['valid'], 2)

    def test_17_hostile_selective_withholding_detectable_by_comparison(self):
        reader = self.mk_node('withhold-reader', 'A')
        source_a = self.mk_node('withhold-a', 'A')
        source_b = self.mk_node('withhold-b', 'A')
        common = self.records_with_prefixes(700, 4, ['u4'])
        extra = self.records_with_prefixes(800, 2, ['u4'])
        self.add_records(source_a, common)
        self.add_records(source_b, common + extra)
        source_a.publish()
        source_b.publish()
        with StaticSource(source_a.path / 'public') as a_srv:
            reader.replicate(a_srv.url + '/punkti')
        count_after_a = len(reader.store.valid)
        with StaticSource(source_b.path / 'public') as b_srv:
            reader.replicate(b_srv.url + '/punkti')
        self.assertEqual(count_after_a, len(common))
        self.assertEqual(len(reader.store.valid), len(common) + len(extra))

    def test_18_normal_container_shaped_path_and_different_origin(self):
        source = self.mk_node('container/siteA', 'A')
        target = self.mk_node('container/siteB', 'A')
        self.add_records(source, self.records_with_prefixes(900, 6, ['u4']))
        source.publish()
        with StaticSource(self.root) as server:
            base = server.url + '/container/siteA-a/public/punkti'
            target.replicate(base)
        self.assertEqual(len(target.store.valid), 6)

    def test_19_cdn_mount_prefix_path_works(self):
        source = self.mk_node('cdn-source', 'A')
        target = self.mk_node('cdn-target', 'A')
        self.add_records(source, self.records_with_prefixes(920, 5, ['u4']))
        source.publish()
        with StaticSource(source.path / 'public', mount_prefix='/cdn') as server:
            target.replicate(server.url + '/cdn/punkti')
        self.assertEqual(len(target.store.valid), 5)

    def test_20_cleanroom_reader_matches_reference_reader(self):
        for mode in ('A', 'B'):
            with self.subTest(mode=mode):
                source = self.mk_node('cleanroom-source', mode)
                target = self.mk_node('cleanroom-target', mode)
                records = self.records_with_prefixes(950, 16, ['u4', 'u5'])
                self.add_records(source, records)
                source.publish()
                with StaticSource(source.path / 'public') as server:
                    base = server.url + '/punkti'
                    target.reader.read_publication(base)
                    parsed = cleanroom.read(base, packs=(mode == 'B'))
                self.assertEqual(set(target.store.valid), set(parsed))

    def test_21_leaf_depth_configs_4_and_6_are_readable(self):
        for mode in ('A', 'B'):
            for leaf_depth in (4, 6):
                with self.subTest(mode=mode, leaf_depth=leaf_depth):
                    source = self.mk_depth_node('depth-source', mode, leaf_depth=leaf_depth)
                    target = self.mk_depth_node('depth-target', mode, leaf_depth=leaf_depth)
                    records = self.records_with_prefixes(980, 18, ['u4', 'u5'])
                    self.add_records(source, records)
                    source.publish()
                    root = unpacked((source.path / 'public' / 'punkti' / 'root.json').read_bytes())
                    manifest = unpacked((source.path / 'public' / 'punkti' / 'manifests' / f"{root['head']}.json").read_bytes())
                    self.assertEqual(manifest['depth'], 2)
                    self.assertEqual(manifest['leaf_depth'], leaf_depth)
                    for raw in records:
                        observation = carrier.validate(raw)
                        prefix = leaf_key(observation.h, leaf_depth)
                        shard = shard_for_prefix(source.path / 'public', manifest, prefix)
                        self.assertEqual(shard['prefix'], prefix)
                        self.assertTrue(any(e['sha256'] == digest(raw) for e in shard['records']))
                    with StaticSource(source.path / 'public') as server:
                        base = server.url + '/punkti'
                        target.reader.read_publication(base)
                        parsed = cleanroom.read(base, packs=(mode == 'B'), leaf_depth=leaf_depth)
                    self.assertEqual(set(target.store.valid), set(parsed))

    def test_22_reader_leaf_depth_mismatch_rejected(self):
        source = self.mk_depth_node('mismatch-source', 'A', leaf_depth=4)
        target = self.mk_depth_node('mismatch-target', 'A', leaf_depth=10)
        self.add_records(source, self.records_with_prefixes(1200, 6, ['u4']))
        source.publish()
        with StaticSource(source.path / 'public') as server:
            with self.assertRaises(ValueError):
                target.reader.read_publication(server.url + '/punkti')


class StaticPublicationBenchTests(unittest.TestCase):
    def _write_json(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding='utf-8')

    def _fixture_root(self, static_content=None):
        tempdir = tempfile.TemporaryDirectory()
        root = Path(tempdir.name)

        docs_dir = root / 'docs'
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / 'BENCHMARK.md').write_text('', encoding='utf-8')
        (docs_dir / 'STATIC_PUBLICATION_REPORT.md').write_text('', encoding='utf-8')

        evidence_dir = root / 'evidence'
        evidence_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(evidence_dir / 'bench_mesh.json', self._minimal_mesh_data())
        self._write_json(evidence_dir / 'test_results.json', {'status': 'ok', 'returncode': 0, 'ran': 26, 'seconds': 1.0})

        static_path = evidence_dir / 'bench_static.json'
        if static_content is not None:
            if isinstance(static_content, str):
                static_path.write_text(static_content, encoding='utf-8')
            else:
                self._write_json(static_path, static_content)

        return tempdir, root, static_path

    def _minimal_static_data(self):
        return {
            'plan': 'bounded',
            'repeats': 3,
            'host': {
                'cpu_count': None,
                'memory_total_kib': None,
                'platform': None,
                'python_version': None,
            },
            'recommended_leaf_depth': {
                'leaf_depth': 6,
                'rationale': 'test',
                'ranked_candidates': [],
            },
            'matched_static': {'datasets': {}},
            'storage_and_rebuild': {},
            'concurrency': {'mode_results': {}},
            'scale_100k': None,
        }

    def _minimal_mesh_data(self):
        return {'scenarios_by_dataset': {}}

    def _evidence_payloads(self):
        evidence_dir = ROOT / 'evidence'
        static_data = json.loads((evidence_dir / 'bench_static.json').read_text(encoding='utf-8'))
        mesh_data = json.loads((evidence_dir / 'bench_mesh.json').read_text(encoding='utf-8'))
        test_data = json.loads((evidence_dir / 'test_results.json').read_text(encoding='utf-8'))
        return static_data, mesh_data, test_data

    def _publication_example_payload(self):
        evidence_dir = ROOT / 'evidence'
        return json.loads((evidence_dir / 'publication_example.json').read_text(encoding='utf-8'))

    def test_23_scale_budget_exhaustion_returns_not_completed(self):
        result = bench.run_scale_100k(recommended_leaf_depth=6, budget_seconds=0, count=5000)
        self.assertFalse(result['completed'])
        reasons = [item.get('reason') for item in result['modes'].values()]
        self.assertTrue(any(reason for reason in reasons))

    def test_24_scale_small_count_with_budget_completes(self):
        result = bench.run_scale_100k(recommended_leaf_depth=6, budget_seconds=30, count=25)
        self.assertTrue(result['completed'])
        for mode in ('A', 'B'):
            self.assertTrue(result['modes'][mode]['completed'])
            self.assertIsNotNone(result['modes'][mode]['publish'])

    def test_25_markdown_generators_tolerate_missing_and_truncated_scale(self):
        static_data = self._minimal_static_data()
        mesh_data = self._minimal_mesh_data()
        static_data['scale_100k'] = {
            'completed': False,
            'elapsed_sec': None,
            'budget_seconds': 720,
            'modes': {
                'A': {
                    'completed': False,
                    'reason': 'budget_exhausted_during_admit',
                    'publish': {'wall_sec': 0.1, 'cpu_sec': 0.05},
                    'replication': None,
                }
            },
        }
        benchmark_md = bench.generate_benchmark_markdown(static_data, mesh_data)
        self.assertIn('not completed', benchmark_md)
        self.assertIn('budget_exhausted_during_admit', benchmark_md)

        static_data_none_scale = self._minimal_static_data()
        report_md = bench.generate_static_report_markdown(
            static_data_none_scale,
            mesh_data,
            {'status': 'ok', 'returncode': 0, 'ran': 22, 'seconds': 1.0},
        )
        self.assertIn('not completed', report_md)

    def test_26_host_block_present_in_run_results(self):
        host = bench.collect_host_info()
        self.assertIn('cpu_count', host)
        self.assertIn('memory_total_kib', host)
        self.assertIn('platform', host)
        self.assertIn('python_version', host)

    def test_27_scale_only_missing_or_empty_static_exits_nonzero_without_overwrite(self):
        tempdir, root, static_path = self._fixture_root(static_content=None)
        with tempdir:
            rc_missing = bench.main(
                ['--scale-only', '--scale-budget-seconds', '1', '--scale-count', '1'],
                root=root,
            )
            self.assertNotEqual(rc_missing, 0)
            self.assertFalse(static_path.exists())

        tempdir, root, static_path = self._fixture_root(static_content='')
        with tempdir:
            before = static_path.read_text(encoding='utf-8')
            rc_empty = bench.main(
                ['--scale-only', '--scale-budget-seconds', '1', '--scale-count', '1'],
                root=root,
            )
            self.assertNotEqual(rc_empty, 0)
            self.assertEqual(static_path.read_text(encoding='utf-8'), before)

    def test_28_scale_only_preserves_non_scale_keys(self):
        static_data = self._minimal_static_data()
        static_data['custom_marker'] = {'stable': ['keep', 'all', 'fields']}
        tempdir, root, static_path = self._fixture_root(static_content=static_data)
        with tempdir:
            before = json.loads(static_path.read_text(encoding='utf-8'))
            rc = bench.main(
                ['--scale-only', '--scale-budget-seconds', '10', '--scale-count', '5'],
                root=root,
            )
            self.assertEqual(rc, 0)
            after = json.loads(static_path.read_text(encoding='utf-8'))

            before_no_scale = dict(before)
            after_no_scale = dict(after)
            before_no_scale.pop('scale_100k', None)
            after_no_scale.pop('scale_100k', None)

            self.assertEqual(after_no_scale, before_no_scale)
            self.assertIn('scale_100k', after)
            self.assertIsInstance(after['scale_100k'], dict)

    def test_29_scale_replication_includes_useful_bytes_and_maxrss(self):
        result = bench.run_scale_100k(recommended_leaf_depth=6, budget_seconds=30, count=25)
        self.assertTrue(result['completed'])
        for mode in ('A', 'B'):
            replication = result['modes'][mode]['replication']
            self.assertIn('useful_bytes', replication)
            self.assertIn('maxrss_kib', replication)
            self.assertIsInstance(replication['useful_bytes'], int)
            self.assertIsInstance(replication['maxrss_kib'], int)

    def test_30_report_contains_derived_request_ratio_and_byte_overhead(self):
        static_data, mesh_data, test_data = self._evidence_payloads()
        report_md = bench.generate_static_report_markdown(static_data, mesh_data, test_data)

        fresh5k_a = static_data['matched_static']['datasets']['5000']['A']['scenarios']['fresh_subscriber_allspace']['summary']['median']
        fresh5k_b = static_data['matched_static']['datasets']['5000']['B']['scenarios']['fresh_subscriber_allspace']['summary']['median']
        req_ratio = fresh5k_a['requests'] / fresh5k_b['requests']
        byte_overhead_pct = ((fresh5k_b['transferred_bytes'] - fresh5k_a['transferred_bytes']) / fresh5k_a['transferred_bytes']) * 100.0

        self.assertIn(f"`{bench.fmt_num(req_ratio, digits=1)}x` fewer requests", report_md)
        self.assertIn(f"(`{bench.fmt_num(byte_overhead_pct)}%`)", report_md)

    def test_31_report_contains_concurrency_rows_for_1_and_8_readers(self):
        static_data, mesh_data, test_data = self._evidence_payloads()
        report_md = bench.generate_static_report_markdown(static_data, mesh_data, test_data)

        expected_fragments = [
            'A/1 reader `1,005` req',
            'A/8 readers `8,040` req',
            'B/1 reader `11` req',
            'B/8 readers `88` req',
        ]
        for fragment in expected_fragments:
            self.assertIn(fragment, report_md)

    def test_32_report_contains_mutable_file_accounting(self):
        static_data, mesh_data, test_data = self._evidence_payloads()
        report_md = bench.generate_static_report_markdown(static_data, mesh_data, test_data)

        self.assertIn('`root.json` is the only mutable artifact', report_md)
        self.assertIn('`1` file, `150` bytes', report_md)

    def test_33_report_marks_scale_missing_and_truncated_as_not_completed(self):
        mesh_data = self._minimal_mesh_data()
        test_data = {'status': 'ok', 'returncode': 0, 'ran': 1, 'seconds': 0.1}

        static_missing = self._minimal_static_data()
        report_missing = bench.generate_static_report_markdown(static_missing, mesh_data, test_data)
        self.assertIn('100k bounded-step completion: not completed (scale_100k_missing).', report_missing)

        static_truncated = self._minimal_static_data()
        static_truncated['scale_100k'] = {
            'completed': False,
            'modes': {
                'A': {'reason': 'budget_exhausted_during_publish'},
                'B': {'reason': 'budget_exhausted_during_publish'},
            },
        }
        report_truncated = bench.generate_static_report_markdown(static_truncated, mesh_data, test_data)
        self.assertIn('100k bounded-step completion: not completed (budget_exhausted_during_publish).', report_truncated)

    def test_34_report_request_ratio_changes_when_evidence_changes(self):
        static_data, mesh_data, test_data = self._evidence_payloads()
        report_original = bench.generate_static_report_markdown(static_data, mesh_data, test_data)

        mutated = copy.deepcopy(static_data)
        mutated['matched_static']['datasets']['5000']['B']['scenarios']['fresh_subscriber_allspace']['summary']['median']['requests'] = 50
        report_mutated = bench.generate_static_report_markdown(mutated, mesh_data, test_data)

        original_ratio = static_data['matched_static']['datasets']['5000']['A']['scenarios']['fresh_subscriber_allspace']['summary']['median']['requests'] / static_data['matched_static']['datasets']['5000']['B']['scenarios']['fresh_subscriber_allspace']['summary']['median']['requests']
        mutated_ratio = static_data['matched_static']['datasets']['5000']['A']['scenarios']['fresh_subscriber_allspace']['summary']['median']['requests'] / 50

        self.assertIn(f"`{bench.fmt_num(original_ratio, digits=1)}x` fewer requests", report_original)
        self.assertIn(f"`{bench.fmt_num(mutated_ratio, digits=1)}x` fewer requests", report_mutated)
        self.assertNotIn(f"`{bench.fmt_num(original_ratio, digits=1)}x` fewer requests", report_mutated)

    def test_35_report_renders_real_publication_example_values(self):
        static_data, mesh_data, test_data = self._evidence_payloads()
        publication_example = self._publication_example_payload()

        report_md = bench.generate_static_report_markdown(
            static_data,
            mesh_data,
            test_data,
            publication_example=publication_example,
        )

        self.assertIn(publication_example['root']['head'], report_md)
        self.assertIn(publication_example['leaf_shard']['prefix'], report_md)
        self.assertIn(publication_example['record_example_path'], report_md)
        self.assertIn(publication_example['segment_example_path'], report_md)
        self.assertNotIn('{example_root_seq}', report_md)
        self.assertNotIn('publication example not recorded in evidence', report_md)

    def test_36_report_handles_missing_publication_example_file(self):
        static_data, mesh_data, test_data = self._evidence_payloads()

        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            with patch.object(bench, 'ROOT', temp_root):
                report_md = bench.generate_static_report_markdown(static_data, mesh_data, test_data)

        self.assertIn('publication example not recorded in evidence', report_md)

    def test_37_report_contains_100k_mode_request_counts_and_ratio(self):
        static_data, mesh_data, test_data = self._evidence_payloads()
        report_md = bench.generate_static_report_markdown(static_data, mesh_data, test_data)

        req_a = static_data['scale_100k']['modes']['A']['replication']['requests']
        req_b = static_data['scale_100k']['modes']['B']['replication']['requests']
        ratio = req_a / req_b

        self.assertIn(
            f"mode A `{bench.fmt_num(req_a, digits=0)}` vs mode B `{bench.fmt_num(req_b, digits=0)}` requests",
            report_md,
        )
        self.assertIn(f"(`{bench.fmt_num(ratio, digits=1)}x` fewer in mode B)", report_md)

    def test_38_report_uses_suite_fail_state_without_pass_claim(self):
        static_data, mesh_data, test_data = self._evidence_payloads()
        failed_suite = dict(test_data)
        failed_suite.update({'status': 'FAILED', 'returncode': 1})

        report_md = bench.generate_static_report_markdown(static_data, mesh_data, failed_suite)

        self.assertIn('Suite evidence from `evidence/test_results.json`: FAIL', report_md)
        self.assertNotIn('Suite evidence from `evidence/test_results.json`: PASS', report_md)


if __name__ == '__main__':
    unittest.main(verbosity=2)
