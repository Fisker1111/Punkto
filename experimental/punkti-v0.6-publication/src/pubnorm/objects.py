"""Revision 3 logical objects; adapted from staticpub/carrier_io.py."""
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'punkti-v0.6-mesh/src'))
import carrier
from spatial import Subscription, parse_h, xy_key

PROFILE = 'punkti/pub/0.6'
KEY_LEN, INDEX_DEPTH, LEAF_DEPTH = 12, 2, 10
ALPHABET = '0123456789bcdefghjkmnpqrstuvwxyz'
MAX_INDEX_ENTRIES = 1024
UNANCHORED = '~'
MAGIC = b'PUNKTIPACK1'
PACK_MAX = 256
DIGEST_LEN = 64
MID_PREFIX = 'punkti/0.6:'
ROOT_MEMBERS = {'head', 'seq', 'v'}
MANIFEST_MEMBERS = {'index', 'pack_count', 'prev', 'record_count', 'seq', 'v'}
SHARD_MEMBERS = {'children', 'packs', 'prefix', 'records', 'v'}
ENTRY_MEMBERS = {'h', 'mid', 'sha256'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    def check(v):
        if isinstance(v, dict):
            if any(not isinstance(k, str) for k in v):
                raise ValueError('member name')
            for x in v.values():
                check(x)
        elif isinstance(v, list):
            for x in v:
                check(x)
        elif v is not None and type(v) not in (str, int, bool):
            raise ValueError('integer numbers only')
    check(value)
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def parse(raw):
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=carrier.unique_object,
                       parse_float=carrier.reject_number, parse_constant=carrier.reject_number)
    if canonical(value) != raw:
        raise ValueError('noncanonical JSON')
    return value


def sha_ok(s):
    if not isinstance(s, str) or not re.fullmatch('[0-9a-f]{64}', s):
        raise ValueError('digest')
    return s


def prefix_ok(p, depth):
    if not isinstance(p, str) or len(p) != depth or any(c not in ALPHABET for c in p):
        raise ValueError('prefix')


def shape(v, members):
    if not isinstance(v, dict) or set(v) != members or v['v'] != PROFILE:
        raise ValueError('object shape')


def integer(n, minimum=0):
    if type(n) is not int or n < minimum:
        raise ValueError('integer')


def root(raw):
    v = parse(raw)
    shape(v, ROOT_MEMBERS)
    integer(v['seq'], 1)
    sha_ok(v['head'])
    return v


def manifest(raw):
    v = parse(raw)
    shape(v, MANIFEST_MEMBERS)
    integer(v['seq'], 1)
    for k in ('record_count', 'pack_count'):
        integer(v[k])
    if v['prev'] is not None:
        sha_ok(v['prev'])
    if (v['seq'] == 1) != (v['prev'] is None):
        raise ValueError('previous manifest')
    if not isinstance(v['index'], dict) or len(v['index']) > MAX_INDEX_ENTRIES + 1:
        raise ValueError('index')
    for p, s in v['index'].items():
        if p != UNANCHORED:
            prefix_ok(p, INDEX_DEPTH)
        sha_ok(s)
    return v


def leaf_key(h):
    parts = parse_h(h)
    return xy_key(parts[0])[:LEAF_DEPTH] if parts else UNANCHORED


def intersects(p, scope):
    if p == UNANCHORED:
        return scope == Subscription()
    return ((scope.xy_hi is None or p.ljust(KEY_LEN, '0') < xy_key(scope.xy_hi)) and
            (scope.xy_lo is None or p.ljust(KEY_LEN, 'z') >= xy_key(scope.xy_lo)))


def shard(raw, prefix):
    v = parse(raw)
    shape(v, SHARD_MEMBERS)
    if (v['prefix'] != prefix or not isinstance(v['children'], dict) or
            not isinstance(v['records'], list) or not isinstance(v['packs'], list)):
        raise ValueError('shard shape')
    if prefix != UNANCHORED:
        prefix_ok(prefix, len(prefix))
        if not INDEX_DEPTH <= len(prefix) <= LEAF_DEPTH:
            raise ValueError('depth')
    leaf = prefix == UNANCHORED or len(prefix) == LEAF_DEPTH
    if leaf:
        if v['children'] or not v['records']:
            raise ValueError('leaf shape')
    elif not v['children'] or v['records'] or v['packs']:
        raise ValueError('interior shape')
    for p, s in v['children'].items():
        prefix_ok(p, len(prefix) + 1)
        if not p.startswith(prefix):
            raise ValueError('prefix chain')
        sha_ok(s)
    for e in v['records']:
        if not isinstance(e, dict) or set(e) != ENTRY_MEMBERS:
            raise ValueError('record entry')
        sha_ok(e['sha256'])
        if not isinstance(e['mid'], str) or not e['mid'].startswith(MID_PREFIX):
            raise ValueError('MID namespace')
        sha_ok(e['mid'][len(MID_PREFIX):])
        if leaf_key(e['h']) != prefix:
            raise ValueError('record placement')
    ids = [e['sha256'] for e in v['records']]
    if ids != sorted(set(ids)):
        raise ValueError('record order/duplicate')
    for s in v['packs']:
        sha_ok(s)
    if v['packs'] != sorted(set(v['packs'])):
        raise ValueError('pack order/duplicate')
    if v['packs'] and len(v['packs']) != (len(ids) + PACK_MAX - 1) // PACK_MAX:
        raise ValueError('pack count')
    return v


def pack(records):
    if not 1 <= len(records) <= PACK_MAX or any(not r for r in records):
        raise ValueError('pack size')
    return MAGIC + struct.pack('>I', len(records)) + b''.join(carrier.lp(r) for r in records)


def unpack(raw):
    r = carrier.Reader(raw)
    if r.take(len(MAGIC)) != MAGIC:
        raise ValueError('pack magic')
    n = r.count()
    if not 1 <= n <= PACK_MAX:
        raise ValueError('pack count')
    records = [r.field() for _ in range(n)]
    r.end()
    if any(not x for x in records):
        raise ValueError('empty pack entry')
    return records


def object_path(kind, sha):
    return f'{kind}/{sha[:2]}/{sha}'


def shard_path(prefix, sha):
    return 'h/' + '/'.join(prefix) + '/' + sha + '.json'
