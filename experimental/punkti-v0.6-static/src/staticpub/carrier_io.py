"""Use the approved, unmodified carrier and spatial codec through flat imports."""
import hashlib
import json
from pathlib import Path
import struct
import sys

sys.dont_write_bytecode = True  # Do not write into the read-only mesh experiment.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'punkti-v0.6-mesh' / 'src'))
import carrier
from spatial import Subscription, parse_h, xy_key
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

VERSION = 'punkti/pub/0.6-draft'
MAGIC = b'PUNKTIPACK1'
MIN_LEAF_DEPTH = 2
MAX_LEAF_DEPTH = 10


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def packed(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def unpacked(raw):
    return json.loads(raw, object_pairs_hook=carrier.unique_object,
                      parse_constant=carrier.reject_number)


def make_record(i, h='u4pruydqqv_0'):
    """Deterministic Ed25519 fixture; never an operational identity."""
    key = Ed25519PrivateKey.from_private_bytes(hashlib.sha256(b'static-test-key').digest())
    atom = dict(v=carrier.VERSION, t=i, h=h, x=f'fixture-{i}', alg='ed25519',
                pk=carrier.b64(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)),
                refs=[], ext='', sig=carrier.b64(bytes(64)))
    atom['sig'] = carrier.b64(key.sign(carrier.SIGN_DOMAIN + carrier.canonical(atom)))
    return carrier.record(atom)


def pack(records):
    return MAGIC + struct.pack('>I', len(records)) + b''.join(carrier.lp(r) for r in records)


def unpack(raw):
    r = carrier.Reader(raw)
    if r.take(len(MAGIC)) != MAGIC:
        raise ValueError('pack magic')
    count = r.count()
    if count > len(raw) // 4:
        raise ValueError('pack count')
    records = [r.field() for _ in range(count)]
    r.end()
    return records


def shard_path(prefix, sha):
    return 'h/' + '/'.join(prefix) + '/' + sha + '.json'


def object_path(kind, sha):
    return f'{kind}/{sha[:2]}/{sha}'


def leaf_key(h, depth=MAX_LEAF_DEPTH):
    if type(depth) is not int or not (MIN_LEAF_DEPTH <= depth <= MAX_LEAF_DEPTH):
        raise ValueError('leaf depth')
    parts = parse_h(h)
    return (parts[0] if parts else '').ljust(MAX_LEAF_DEPTH, '0')[:depth]


def intersects(prefix, scope):
    low, high = prefix.ljust(12, '0'), prefix.ljust(12, 'z')
    return ((scope.xy_lo is None or high >= xy_key(scope.xy_lo)) and
            (scope.xy_hi is None or low < xy_key(scope.xy_hi)))
