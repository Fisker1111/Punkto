"""Deterministic logical-object fixtures and executable V1–V9 cases."""
import copy
import json
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
    records = [fixture(1, 'u4pruydqqv_-18'), fixture(2, 'u4pruydqqv_23.025'),
               fixture(3, 'ezs42_0'), fixture(4, ''), fixture(5, '0000_0'),
               fixture(6, 'u4pruydqqv_-0.000000000000000001')]
    normal, packed = snapshot(records), snapshot(records, True)
    catalog = {'index': normal, 'packs': packed}
    vectors = []
    def case(name, source='index', want=None, **kw):
        outcome = copy.deepcopy(want or expected(records))
        if outcome['error_class'] is None:
            root = o.parse(bytes.fromhex(catalog[source]['root']))
            outcome.update(head=root['head'], seq=root['seq'])
        return dict(name=name, source=source, expected=outcome, **kw)
    vectors.append(dict(id='V1', cases=[case('root-manifest', packs=False), case('pack-discovery', 'packs', packs=True)]))
    cases = []
    for kind in ('manifest', 'shard', 'record'):
        bad = copy.deepcopy(normal)
        sha = next(s for s, obj in bad['objects'].items() if obj['kind'] == kind)
        obj = bad['objects'][sha]
        if kind == 'shard':
            obj['prefix'] = o.parse(bytes.fromhex(obj['hex']))['prefix']
        obj['hex'] += '00'
        catalog['tamper-' + kind] = bad
        cases.append(case(kind, 'tamper-' + kind, expected([], error='corrupt object')))
    vectors.append(dict(id='V2', cases=cases))
    small = snapshot(records[:2], True)
    catalog['small-pack'] = small
    cases = [case('valid', 'small-pack', expected(records[:2]), packs=True)]
    changes = {
        'count': lambda b: b[:11] + (3).to_bytes(4, 'big') + b[15:],
        'truncation': lambda b: b[:-1],
        'trailing': lambda b: b + b'!',
        'foreign': lambda b: o.pack([fixture(99)]),
        'duplicate': lambda b: o.pack([records[0], records[0]]),
        'reversed': lambda b: o.pack(list(reversed(o.unpack(b)))),
    }
    for name, mutate in changes.items():
        def edit(node, snap, mutate=mutate):
            blob = bytes.fromhex(snap['objects'][node['packs'][0]]['hex'])
            node['packs'] = [add(snap, 'pack', mutate(blob))]
        catalog['pack-' + name] = rewrite(small, edit)
        reason = 'pack membership' if name in ('foreign', 'duplicate', 'reversed') else 'invalid object'
        cases.append(case(name, 'pack-' + name, expected([], error=reason), packs=True))
    vectors.append(dict(id='V3', cases=cases))
    vectors.append(dict(id='V4', cases=[case('exact-R-MID', 'index')],
                        records=[dict(hex=r.hex(), sha256=o.digest(r), mid=o.carrier.validate(r).address) for r in records]))
    good = records[0]
    forged = good[:-1] + bytes([good[-1] ^ 1])
    candidate = fixture(7, 'u4pruydqqv_0', 'future-alg')
    candidate2 = candidate[:-1] + bytes([candidate[-1] ^ 1])
    poison = snapshot([good, candidate, candidate2])
    def poison_leaf(node, snap):
        sha = add(snap, 'record', forged)
        node['records'].append(dict(h=o.carrier.validate(good).h, mid=o.carrier.validate(good).address, sha256=sha))
        node['records'].sort(key=lambda e: e['sha256'])
    poison = rewrite(poison, poison_leaf, lambda m: m.update(record_count=4))
    catalog['poison'] = poison
    vectors.append(dict(id='V5', cases=[case('variants', 'poison', expected([good, candidate, candidate2], rejected=1))],
                        variants=[dict(hex=r.hex(), sha256=o.digest(r), mid=o.carrier.validate(r).address,
                                       state=o.carrier.validate(r).state.value) for r in (good, forged, candidate, candidate2)]))
    vectors.append(dict(id='V6', cases=[
        case('XY', want=expected([records[0], records[1], records[5]]), scope=dict(xy_lo='u4', xy_hi='u5'),
             forbidden_records=[o.digest(r) for r in records[2:5]]),
        case('zero-cell-not-unanchored', want=expected([records[4]]), scope=dict(xy_lo='0', xy_hi='1'),
             forbidden_records=[o.digest(records[3])]),
        case('unrestricted-includes-unanchored')]))
    vectors.append(dict(id='V7', cases=[
        case('negative-exact-Z', want=expected([records[0], records[5]]), scope=dict(z_min='-18', z_max='0'),
             required_records=[o.digest(records[1])]),
        case('decimal-upper-exclusive', want=expected([records[5]]), scope=dict(xy_lo='u4', xy_hi='u5', z_min='-1', z_max='23.025'))]))
    missing = copy.deepcopy(normal)
    del missing['objects'][o.digest(records[0])]
    catalog['missing'] = missing
    newer = rewrite(normal, manifest_edit=lambda m: m.update(seq=2, prev=o.parse(bytes.fromhex(normal['root']))['head']))
    catalog['newer'] = newer
    vectors.append(dict(id='V8', cases=[
        case('missing', 'missing', expected([], error='missing object')),
        case('corrupt', 'tamper-record', expected([], error='corrupt object')),
        case('stale', want=expected(records, error='stale root'), prime='newer'),
        case('retry-idempotent', retry=True)]))
    vectors.append(dict(id='V9', cases=[case('static-index'), case('static-packs', 'packs', packs=True)]))
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
