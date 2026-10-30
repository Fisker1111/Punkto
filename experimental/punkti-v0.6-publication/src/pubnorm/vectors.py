"""Deterministic logical-object fixtures and executable V1–V9 cases."""
import copy
import json
import re
from pathlib import Path
import tempfile
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from . import objects as o
from .publisher import Publisher


def fixture(i, h='u4pruydqqv_0', alg='ed25519'):
    key = Ed25519PrivateKey.from_private_bytes(o.hashlib.sha256(b'static-test-key').digest())
    atom = dict(v=o.carrier.VERSION, t=i, h=h, x=f'fixture-{i}', alg=alg,
                pk=o.carrier.b64(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)),
                refs=[], ext='', sig=o.carrier.b64(bytes(64)))
    atom['sig'] = o.carrier.b64(key.sign(o.carrier.SIGN_DOMAIN + o.carrier.canonical(atom)))
    return o.carrier.record(atom)


def snapshot(records, packs=False):
    with tempfile.TemporaryDirectory() as tmp:
        Publisher(tmp, packs).publish(records)
        root = b''
        objects = {}
        for file in sorted(Path(tmp).rglob('*')):
            if not file.is_file():
                continue
            raw = file.read_bytes()
            if file.name == 'root.json':
                root = raw
            else:
                kind = {'h': 'shard', 'manifests': 'manifest', 'records': 'record', 'segments': 'pack'}[file.relative_to(tmp).parts[0]]
                objects[o.digest(raw)] = dict(kind=kind, hex=raw.hex())
        return dict(root=root.hex(), objects=objects)


def add(snap, kind, raw):
    sha = o.digest(raw)
    snap['objects'][sha] = dict(kind=kind, hex=raw.hex())
    return sha


def rewrite(snap, leaf_edit=None, manifest_edit=None):
    """Readdress changed logical fixtures, keeping malicious bytes hash-valid."""
    snap = copy.deepcopy(snap)
    root = o.parse(bytes.fromhex(snap['root']))
    m = o.parse(bytes.fromhex(snap['objects'][root['head']]['hex']))
    def walk(sha):
        node = o.parse(bytes.fromhex(snap['objects'][sha]['hex']))
        original_prefix = node['prefix']
        if node['children']:
            node['children'] = {p: walk(s) for p, s in node['children'].items()}
        elif leaf_edit:
            leaf_edit(node, snap)
        address = add(snap, 'shard', o.canonical(node))
        if node['prefix'] != original_prefix:
            snap['objects'][address]['prefix'] = original_prefix
        return address
    m['index'] = {p: walk(s) for p, s in m['index'].items()}
    if manifest_edit:
        manifest_edit(m)
    root['head'] = add(snap, 'manifest', o.canonical(m))
    root['seq'] = m['seq']
    snap['root'] = o.canonical(root).hex()
    return snap


def materialize(snap, directory):
    """Reference layout is a test transport adapter, not part of vector identity."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'root.json').write_bytes(bytes.fromhex(snap['root']))
    for sha, obj in snap['objects'].items():
        raw = bytes.fromhex(obj['hex'])
        kind = obj['kind']
        if kind == 'manifest':
            path = f'manifests/{sha}.json'
        elif kind == 'shard':
            # The original prefix is retained when hostile bytes cannot be parsed.
            p = obj.get('prefix') or o.parse(raw)['prefix']
            path = o.shard_path(p, sha)
        else:
            path = o.object_path('records' if kind == 'record' else 'segments', sha)
        target = directory / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)


def expected(records, rejected=0, error=None):
    valid, candidates = {}, {}
    for raw in records:
        obs = o.carrier.validate(raw)
        if obs.state == o.carrier.State.VALID:
            valid[obs.address] = o.digest(raw)
        elif obs.state in (o.carrier.State.ALGORITHM, o.carrier.State.KEY):
            candidates[o.digest(raw)] = raw.hex()
    return dict(valid=valid, candidates=candidates, valid_count=len(valid),
                candidate_count=len(candidates), admitted=0 if error else len(valid), rejected=rejected,
                error_class='retryable' if error else None, reason=error)


def generate():
    """Build logical objects from the pinned Stage A records and expectations."""
    normative = Path(__file__).resolve().parents[4] / 'docs/proposals/PUNKTI_0_6_VECTORS.md'
    vectors = [json.loads(block) for block in re.findall(r'```json\n(.*?)\n```', normative.read_text(), re.S)]
    by_id = {v['id']: v for v in vectors}
    records = [bytes.fromhex(r['hex']) for r in by_id['V4']['records']]
    normal, packed = snapshot(records), snapshot(records, True)
    catalog = dict(index=normal, packs=packed, **{'small-pack': snapshot(records[:2], True)})
    for kind in ('manifest', 'shard', 'record'):
        bad = copy.deepcopy(normal)
        sha = min(s for s, obj in bad['objects'].items() if obj['kind'] == kind)
        obj = bad['objects'][sha]
        raw = bytes.fromhex(obj['hex'])
        if kind == 'shard': obj['prefix'] = o.parse(raw)['prefix']
        obj['hex'] = (bytes([raw[0] ^ 1]) + raw[1:]).hex()
        catalog['tamper-' + kind] = bad
    changes = {
        'count': lambda b: b[:11] + (3).to_bytes(4, 'big') + b[15:],
        'truncation': lambda b: b[:-1],
        'trailing': lambda b: b + b'\0',
        'foreign': lambda b: o.pack(sorted(o.unpack(b) + [records[2]], key=o.digest)),
        'duplicate': lambda b: o.pack([o.unpack(b)[0]] * 2),
        'reversed': lambda b: o.pack(list(reversed(o.unpack(b)))),
    }
    for name, mutate in changes.items():
        def edit(node, snap, mutate=mutate):
            blob = bytes.fromhex(snap['objects'][node['packs'][0]]['hex'])
            node['packs'] = [add(snap, 'pack', mutate(blob))]
        catalog['pack-' + name] = rewrite(catalog['small-pack'], edit)
    variants = [bytes.fromhex(r['hex']) for r in by_id['V5']['variants']]
    good = [r for r in variants if o.carrier.validate(r).state != o.carrier.State.PROVENANCE]
    forged = next(r for r in variants if o.carrier.validate(r).state == o.carrier.State.PROVENANCE)
    def poison_leaf(node, snap):
        obs = o.carrier.validate(forged)
        if node['prefix'] == o.leaf_key(obs.h):
            sha = add(snap, 'record', forged)
            node['records'].append(dict(h=obs.h, mid=obs.address, sha256=sha))
            node['records'].sort(key=lambda e: e['sha256'])
    catalog['poison'] = rewrite(snapshot(good), poison_leaf, lambda m: m.update(record_count=4))
    missing = copy.deepcopy(normal)
    del missing['objects'][min(o.digest(r) for r in records)]
    catalog['missing'] = missing
    catalog['newer'] = rewrite(packed, manifest_edit=lambda m: m.update(seq=2, prev=o.parse(bytes.fromhex(normal['root']))['head']))
    # Hash-valid geographical mutations: no digest error can mask the bad key.
    for case in by_id['V11']['cases']:
        snap = copy.deepcopy(normal)
        rt = o.parse(bytes.fromhex(snap['root']))
        m = o.parse(bytes.fromhex(snap['objects'][rt['head']]['hex']))
        if case['mutation'] == 'index-key':
            m['index']['~'] = m['index']['u4']
        else:
            node = o.parse(bytes.fromhex(snap['objects'][m['index']['u4']]['hex']))
            if case['mutation'] == 'shard-prefix': node['prefix'] = '~'
            else: node['children']['~'] = node['children'][sorted(node['children'])[0]]
            sha = add(snap, 'shard', o.canonical(node))
            snap['objects'][sha]['prefix'] = 'u4'
            m['index']['u4'] = sha
        rt['head'] = add(snap, 'manifest', o.canonical(m))
        snap['root'] = o.canonical(rt).hex()
        catalog[case['name']] = snap
        case['source'] = case['name']
    return dict(profile=o.PROFILE, fixtures=catalog, vectors=vectors)


def write_artifacts(directory):
    directory = Path(directory)
    data = generate()
    raw = json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + '\n'
    (directory / 'vectors.json').write_text(raw, encoding='utf-8')
    lines = ['# Normative publication vectors', '',
             'Generated by `scripts/generate_vectors.py`; inputs and outcomes are logical bytes, not paths.',
             'Fixture signing seed literal: `static-test-key` (SHA-256 → Ed25519 private seed).',
             'All hex payloads and immutable object digests are in `vectors.json`.',
             'Success verifies referenced objects at read time; no global completeness or freshness claim.', '']
    for vector in data['vectors']:
        lines += ['## ' + vector['id'], '', '```json', json.dumps(vector, sort_keys=True, indent=2), '```', '']
    (directory / 'docs/NORMATIVE_VECTORS.md').write_text('\n'.join(lines), encoding='utf-8')
    return data
