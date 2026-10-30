"""Spatial-only conformance and the subprocess side of JS/Python agreement."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from . import carrier, spatial
from .config import load_config
from .mesh import wire
from .publication import Publisher, Reader, PublicationStore, digest
from .store import PersistentNode

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'pwa/punkti/test-vectors/publication-vectors.json').read_text())
VECTORS = {v['id']: v for v in DATA['vectors']}
CARRIER = json.loads((ROOT / 'pwa/punkti/test-vectors/carrier-vectors.json').read_text())


def observation(case):
    try:
        raw = bytes.fromhex(case['hex']) if case['kind'] == 'record' else carrier.import_json(json.dumps(case['input']).encode())
        obs = carrier.validate(raw)
        return dict(state=obs.state.value, mid=obs.address, sha256=digest(raw), h=obs.h)
    except (ValueError, TypeError, KeyError):
        return dict(state=carrier.State.STRUCTURAL.value, mid=None, sha256=None, h=None)


def read_result(reader, base, scope):
    try:
        result = reader.read_publication(base, spatial.Subscription(**scope))
        return dict(state='OK', head=result['head'], seq=result['seq'], rejected=result['rejected'],
                    valid={k: digest(v) for k, v in reader.store.valid.items()},
                    candidates={k: v.hex() for k, v in reader.store.candidates.items()})
    except ValueError as exc:
        return dict(state='ERROR', error_class=getattr(exc, 'error_class', None), reason=getattr(exc, 'reason', str(exc)))


class SpatialOnly(unittest.TestCase):
    def test_spatial_roundtrip_and_cell_size(self):
        for p in (4, 10, 12):
            for z in ('0', '23', '-18', '23.025', '-0.0000000000000001'):
                h = spatial.encode_h(55.675398, 12.561895, z, p)
                xy, exact_z = spatial.parse_h(h)
                self.assertEqual(h, xy + '_' + exact_z)
                cell = spatial.decode_xy(xy)
                self.assertEqual(spatial.encode_h(cell['lat'], cell['lon'], exact_z, p), h)
                self.assertTrue(spatial.Subscription().matches(h))
        # Canonical decimal grammar alone is insufficient: the total h cap binds.
        self.assertEqual(len(spatial.encode_h(0, 0, '-0.0000000000000001', 12)), 32)
        overlong = 's00000000000_-0.000000000000000001'
        self.assertEqual(len(overlong), 34)
        with self.assertRaisesRegex(ValueError, 'spatial address'):
            spatial.parse_h(overlong)
        with self.assertRaisesRegex(ValueError, 'spatial address'):
            spatial.encode_h(0, 0, '-0.000000000000000001', 12)
        cell = spatial.decode_xy(spatial.encode_xy(0, 0, 12))
        self.assertLess((cell['lat_max'] - cell['lat_min']) * 111320, .02)
        self.assertLess((cell['lon_max'] - cell['lon_min']) * 111320, .04)
        self.assertGreater((cell['lon_max'] - cell['lon_min']) * 111320, .02)

    def test_all_spatial_negative_vectors(self):
        data = json.loads((ROOT / 'pwa/punkti/test-vectors/spatial-vectors.json').read_text())
        for h in data['invalid_h']:
            with self.subTest(h=h), self.assertRaises(ValueError): spatial.parse_h(h)
            with self.subTest(scope_h=h), self.assertRaises(ValueError): spatial.Subscription().matches(h)

    def test_frozen_archive_bytes(self):
        for row in json.loads((ROOT / 'docs/evidence/issue-30/archive-digests.json').read_text()):
            with self.subTest(path=row['path']):
                self.assertEqual(digest((ROOT / row['path']).read_bytes()), row['sha256'])

    def test_legacy_signature_is_historical_and_rejected(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        legacy = next(c for c in VECTORS['V10']['cases'] if c['name'] == 'former-empty-record')
        raw = bytes.fromhex(legacy['hex'])
        outer = carrier.Reader(raw)
        body, sig = outer.field(), outer.field()
        outer.end()
        # Check the original signature directly without making invalid structure admissible.
        fields = carrier.Reader(body)
        for _ in range(5): fields.field()
        pk = fields.field()
        Ed25519PublicKey.from_public_bytes(pk).verify(sig, carrier.SIGN_DOMAIN + body)
        self.assertEqual(carrier.VERSION + ':' + digest(carrier.MID_DOMAIN + body), legacy['mid'])
        store = PublicationStore()
        good = bytes.fromhex(VECTORS['V4']['records'][0]['hex'])
        self.assertEqual(store.admit(good), 'VALID')
        self.assertEqual(store.admit(raw), 'INVALID-structural')
        self.assertEqual(list(store.valid.values()), [good])
        self.assertFalse(store.candidates)
        self.assertEqual(digest(raw), legacy['sha256'])
        with tempfile.TemporaryDirectory() as directory:
            publisher = Publisher(directory)
            root = publisher.publish(store)
            with self.assertRaisesRegex(ValueError, 'admitted'): publisher.publish([good, raw])
            self.assertEqual(json.loads((Path(directory) / 'root.json').read_text()), root)
            self.assertFalse(any(p.name == legacy['sha256'] for p in Path(directory).rglob('*')))

    def test_submit_and_store_reject_legacy_without_poisoning_or_rewrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cfg = root / 'config.json'
            cfg.write_text(json.dumps(dict(web=dict(enabled=False), storage=dict(data_path=str(root / 'data')))))
            node = PersistentNode(load_config(cfg, {}))
            try:
                node.start(0, '127.0.0.1')
                good = bytes.fromhex(VECTORS['V4']['records'][0]['hex'])
                self.assertTrue(node.add(good)['admitted'])
                node.republish_publication()
                old_root = (node.publication.path / 'root.json').read_bytes()
                log_before = (root / 'data/atoms.jsonl').read_bytes()
                for case in [c for c in VECTORS['V10']['cases'] if c['kind'] == 'record']:
                    raw = bytes.fromhex(case['hex'])
                    # Claim an existing valid MID too: validation must precede deduplication.
                    for mid in (case['mid'], carrier.validate(good).address):
                        item = dict(record=carrier.b64(raw), sha256=digest(raw), address=mid)
                        self.assertEqual(node.admit(item), dict(state='INVALID-structural', admitted=False))
                        request = Request(node.url + '/submit', data=json.dumps(dict(records=[item])).encode(), headers={'Content-Type': 'application/json'})
                        with self.assertRaises(HTTPError) as error: urlopen(request)
                        with error.exception as response:
                            self.assertEqual(response.code, 400)
                            self.assertIn('INVALID-structural', response.read().decode())
                    self.assertEqual(digest(raw), case['sha256'])
                self.assertEqual((root / 'data/atoms.jsonl').read_bytes(), log_before)
                self.assertEqual(len(node.store), 1)
                self.assertFalse(node.candidates)
                node.republish_publication()
                self.assertEqual((node.publication.path / 'root.json').read_bytes(), old_root)
            finally:
                node.stop()
                node.durable.close()


# One unittest per normative carrier case: counts are visible in discovery output.
for case in VECTORS['V10']['cases'] + VECTORS['V12']['cases']:
    def test(self, case=case):
        self.assertEqual(observation(case)['state'], case['expected'])
        if case['kind'] == 'record':
            self.assertEqual(digest(bytes.fromhex(case['hex'])), case['sha256'])
    setattr(SpatialOnly, 'test_' + case['name'].replace('-', '_'), test)
for name, fixture in CARRIER['fixtures'].items():
    def test(self, fixture=fixture):
        raw = carrier.unb64(fixture['R'])
        self.assertEqual(carrier.validate(raw).state.value, fixture['state'])
        self.assertEqual(carrier.record(fixture['atom']), raw)
        self.assertEqual(carrier.canonical(fixture['atom']).hex(), fixture['C'])
        self.assertEqual(digest(raw), fixture['sha256_R'])
    setattr(SpatialOnly, 'test_fixture_' + name, test)


if __name__ == '__main__':
    if sys.argv[1:] == ['--agreement']:
        print(json.dumps([observation(c) for c in json.load(sys.stdin)]))
    elif sys.argv[1:] == ['--publications']:
        rows = []
        for case in json.load(sys.stdin):
            reader = Reader(packs=case.get('packs', False), retries=0)
            if case.get('prime'): reader.read_publication(case['prime'])
            rows.append(read_result(reader, case['base'], case.get('scope', {})))
        print(json.dumps(rows))
    elif len(sys.argv) > 1 and sys.argv[1] == '--replicate':
        base, directory, scope, packs = sys.argv[2:]
        reader = Reader(packs=packs == 'true')
        result = read_result(reader, base, json.loads(scope))
        if result['state'] != 'OK': raise ValueError(result)
        Publisher(directory, packs=packs == 'true').publish(reader.store)
        print(json.dumps(result))
    else:
        unittest.main()
