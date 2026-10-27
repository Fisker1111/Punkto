"""Static GET reader. Cache only verified immutable bytes; checkpoint whole reads."""
import re
from urllib.error import HTTPError
from urllib.request import urlopen
from .carrier_io import (MAX_LEAF_DEPTH, MIN_LEAF_DEPTH, VERSION, Subscription,
                         carrier, digest, intersects, leaf_key, object_path,
                         shard_path, unpack, unpacked)

MAX_OBJECT = 64 * 1024 * 1024


def sha_ok(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('digest spelling')
    return value


def prefix_ok(prefix, depth):
    if not isinstance(prefix, str) or len(prefix) != depth or any(c not in carrier.ALPHABET for c in prefix):
        raise ValueError('prefix')


class Reader:
    def __init__(self, store, mode='A', leaf_depth=MAX_LEAF_DEPTH):
        if (mode not in ('A', 'B') or type(leaf_depth) is not int or
                not (MIN_LEAF_DEPTH <= leaf_depth <= MAX_LEAF_DEPTH)):
            raise ValueError('mode')
        self.store, self.mode, self.leaf_depth = store, mode, leaf_depth
        self.cache, self.checkpoints, self.heads = {}, {}, {}
        self.requests, self.bytes, self.paths = 0, 0, []

    def get(self, base, path, sha=None):
        if sha:
            sha_ok(sha)
            if sha in self.cache:
                return self.cache[sha]
        self.requests += 1
        self.paths.append(path)
        try:
            with urlopen(base.rstrip('/') + '/' + path, timeout=10) as response:
                raw = response.read(MAX_OBJECT + 1)
        except HTTPError as exc:
            exc.close()
            raise
        self.bytes += len(raw)
        if len(raw) > MAX_OBJECT or (sha and digest(raw) != sha):
            raise ValueError('object limit or digest mismatch')
        if sha:
            self.cache[sha] = raw
        return raw

    def read_publication(self, base, scope=None):
        """base is the URL of punkti/, including any mount prefix. Fail loudly.

        Stage all admissions until every referenced in-scope object is verified.
        A checkpoint is source+scope-specific, and never a completeness assertion.
        """
        scope = scope or Subscription()
        root = unpacked(self.get(base, 'root.json'))
        if (set(root) != {'v', 'seq', 'head', 'updated_at'} or root['v'] != VERSION or
                type(root['seq']) is not int or root['seq'] < 1 or not isinstance(root['updated_at'], str)):
            raise ValueError('root shape')
        head = sha_ok(root['head'])
        previous = self.heads.get(base)
        if previous and (root['seq'] < previous[0] or (root['seq'] == previous[0] and head != previous[1])):
            raise ValueError('stale or equivocal root')
        manifest = unpacked(self.get(base, f'manifests/{head}.json', head))
        allowed = {'v', 'seq', 'prev', 'created_at', 'depth', 'leaf_depth',
                   'index', 'record_count', 'pack_count'}
        if (set(manifest) - allowed or
                manifest['v'] != VERSION or manifest['seq'] != root['seq'] or manifest['depth'] != 2 or
                not isinstance(manifest['index'], dict) or len(manifest['index']) > 1024 or
                any(type(manifest[k]) is not int or manifest[k] < 0 for k in ('record_count', 'pack_count'))):
            raise ValueError('manifest shape')
        manifest_leaf_depth = manifest.get('leaf_depth', MAX_LEAF_DEPTH)
        if (type(manifest_leaf_depth) is not int or
                not (MIN_LEAF_DEPTH <= manifest_leaf_depth <= MAX_LEAF_DEPTH) or
                manifest_leaf_depth != self.leaf_depth):
            raise ValueError('manifest leaf depth')
        if manifest['prev'] is not None:
            sha_ok(manifest['prev'])
        pending, seen = [], set()
        record_count = pack_count = 0

        def verify(raw, entry):
            if digest(raw) != entry['sha256']:
                raise ValueError('record digest mismatch')
            observation = carrier.validate(raw)
            if observation.state in (carrier.State.STRUCTURAL, carrier.State.PROVENANCE):
                raise ValueError('invalid record: ' + observation.state.value)
            if observation.address != entry['mid'] or observation.h != entry['h']:
                raise ValueError('record index metadata mismatch')
            if scope.matches(observation.h):
                pending.append(raw)

        def walk(prefix, sha):
            nonlocal record_count, pack_count
            prefix_ok(prefix, len(prefix))
            sha_ok(sha)
            if not intersects(prefix, scope):
                return
            shard = unpacked(self.get(base, shard_path(prefix, sha), sha))
            if (set(shard) != {'v', 'prefix', 'children', 'records', 'packs'} or
                    shard['v'] != VERSION or shard['prefix'] != prefix or
                    not isinstance(shard['children'], dict) or not isinstance(shard['records'], list) or
                    not isinstance(shard['packs'], list)):
                raise ValueError('shard shape')
            if len(prefix) < manifest_leaf_depth:
                if shard['records'] or shard['packs']:
                    raise ValueError('nonleaf records')
            elif shard['children']:
                raise ValueError('leaf children')
            entries = {}
            for entry in shard['records']:
                if not isinstance(entry, dict) or set(entry) != {'mid', 'sha256', 'h'}:
                    raise ValueError('record entry')
                sha_ok(entry['sha256'])
                if not carrier.address_ok(entry['mid']) or leaf_key(entry['h'], manifest_leaf_depth) != prefix:
                    raise ValueError('record placement')
                if entry['sha256'] in entries:
                    raise ValueError('duplicate index entry')
                entries[entry['sha256']] = entry
            record_count += len(entries)
            pack_count += len(shard['packs'])
            for p in shard['packs']:
                sha_ok(p)
            needed = {s: e for s, e in entries.items() if scope.matches(e['h'])}
            if self.mode == 'B' and shard['packs'] and needed:
                extracted = {}
                for p in shard['packs']:
                    for raw in unpack(self.get(base, object_path('segments', p), p)):
                        s = digest(raw)
                        if s not in entries or s in extracted:
                            raise ValueError('pack coverage/duplicate')
                        extracted[s] = raw
                        # Verify even out-of-scope records carried by a fetched pack.
                        verify(raw, entries[s])
                if set(extracted) != set(entries):
                    raise ValueError('incomplete pack coverage')
            else:
                for s, entry in needed.items():
                    verify(self.get(base, object_path('records', s), s), entry)
            for child, child_sha in sorted(shard['children'].items()):
                prefix_ok(child, len(prefix) + 1)
                if not child.startswith(prefix):
                    raise ValueError('child prefix')
                walk(child, child_sha)

        for prefix, sha in sorted(manifest['index'].items()):
            prefix_ok(prefix, 2)
            walk(prefix, sha)
        if scope == Subscription() and (record_count != manifest['record_count'] or pack_count != manifest['pack_count']):
            raise ValueError('manifest counts')
        before = len(self.store.valid)
        for raw in pending:
            self.store.admit(raw)
        self.heads[base] = (root['seq'], head)
        self.checkpoints[(base, tuple(scope.wire().items()))] = head
        return dict(head=head, seq=root['seq'], admitted=len(self.store.valid) - before,
                    valid=len(self.store.valid), candidates=len(self.store.candidates))
