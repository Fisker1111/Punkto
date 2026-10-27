"""Independent all-space parser. Reuses ONLY approved carrier validation.

No reference publication helpers, Store, Publisher or Reader imports. This is
an independent parser proof, not an independent cryptographic implementation.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys
from urllib.error import HTTPError
from urllib.request import urlopen

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'punkti-v0.6-mesh' / 'src'))
import carrier

MAGIC = b'PUNKTIPACK1'


def read(base, packs=False, leaf_depth=10):
    if type(leaf_depth) is not int or not (2 <= leaf_depth <= 10):
        raise ValueError('leaf depth')
    accepted = {}

    def get(path, expected=None):
        try:
            with urlopen(base.rstrip('/') + '/' + path, timeout=10) as response:
                raw = response.read()
        except HTTPError as exc:
            exc.close()
            raise
        if expected is not None and hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('content address')
        return raw

    root = json.loads(get('root.json'))
    manifest = json.loads(get('manifests/' + root['head'] + '.json', root['head']))
    if root['v'] != 'punkti/pub/0.6-draft' or manifest['seq'] != root['seq'] or manifest['depth'] != 2:
        raise ValueError('profile')
    manifest_leaf_depth = manifest.get('leaf_depth', 10)
    if manifest_leaf_depth != leaf_depth:
        raise ValueError('leaf depth mismatch')

    def accept(raw, entries):
        sha = hashlib.sha256(raw).hexdigest()
        observation = carrier.validate(raw)
        if sha not in entries or observation.address != entries[sha]['mid'] or observation.h != entries[sha]['h']:
            raise ValueError('metadata')
        if observation.state == carrier.State.VALID:
            accepted.setdefault(observation.address, raw)
        elif observation.state not in (carrier.State.ALGORITHM, carrier.State.KEY):
            raise ValueError('invalid carrier')
        return sha

    def walk(prefix, sha):
        shard = json.loads(get('h/' + '/'.join(prefix) + '/' + sha + '.json', sha))
        if shard['prefix'] != prefix:
            raise ValueError('prefix')
        if len(prefix) < manifest_leaf_depth:
            if shard['records'] or shard['packs']:
                raise ValueError('nonleaf records')
        elif shard['children']:
            raise ValueError('leaf children')
        entries = {e['sha256']: e for e in shard['records']}
        if packs and shard['packs']:
            seen = set()
            for p in shard['packs']:
                raw = get('segments/' + p[:2] + '/' + p, p)
                if raw[:len(MAGIC)] != MAGIC or len(raw) < len(MAGIC) + 4:
                    raise ValueError('pack header')
                count, = struct.unpack('>I', raw[len(MAGIC):len(MAGIC) + 4])
                pos = len(MAGIC) + 4
                for _ in range(count):
                    if pos + 4 > len(raw):
                        raise ValueError('pack length')
                    size, = struct.unpack('>I', raw[pos:pos + 4])
                    pos += 4
                    if pos + size > len(raw):
                        raise ValueError('truncated pack')
                    seen.add(accept(raw[pos:pos + size], entries))
                    pos += size
                if pos != len(raw):
                    raise ValueError('pack suffix')
            if seen != set(entries):
                raise ValueError('pack coverage')
        else:
            for sha in entries:
                accept(get('records/' + sha[:2] + '/' + sha, sha), entries)
        for child, child_sha in shard['children'].items():
            walk(child, child_sha)

    for prefix, sha in manifest['index'].items():
        walk(prefix, sha)
    return accepted
