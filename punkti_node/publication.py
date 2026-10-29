"""Static publication publisher and reader for Punkti 0.6."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import struct
import tempfile
from urllib.error import URLError
from urllib.request import urlopen

from . import carrier
from .spatial import Subscription, parse_h, xy_key

PROFILE = 'punkti/pub/0.6'
KEY_LEN = 12
INDEX_DEPTH = 2
LEAF_DEPTH = 10
ALPHABET = '0123456789bcdefghjkmnpqrstuvwxyz'
MAGIC = b'PUNKTIPACK1'
PACK_MAX = 256
MID_PREFIX = 'punkti/0.6:'
ROOT_MEMBERS = {'head', 'seq', 'v'}
MANIFEST_MEMBERS = {'index', 'pack_count', 'prev', 'record_count', 'seq', 'v'}
SHARD_MEMBERS = {'children', 'packs', 'prefix', 'records', 'v'}
ENTRY_MEMBERS = {'h', 'mid', 'sha256'}
MAX_OBJECT = 64 * 1024 * 1024


class PublicationReadError(ValueError):
    error_class = 'retryable'

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    def check(node):
        if isinstance(node, dict):
            if any(not isinstance(k, str) for k in node):
                raise ValueError('member name')
            for child in node.values():
                check(child)
        elif isinstance(node, list):
            for child in node:
                check(child)
        elif node is not None and type(node) not in (str, int, bool):
            raise ValueError('integer numbers only')
    check(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False,
        allow_nan=False,
    ).encode('utf-8')


def parse(raw):
    value = json.loads(
        raw.decode('utf-8'),
        object_pairs_hook=carrier.unique_object,
        parse_float=carrier.reject_number,
        parse_constant=carrier.reject_number,
    )
    if canonical(value) != raw:
        raise ValueError('noncanonical JSON')
    return value


def _sha_ok(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('digest')
    return value


def _prefix_ok(prefix, depth):
    if not isinstance(prefix, str) or len(prefix) != depth or any(c not in ALPHABET for c in prefix):
        raise PublicationReadError('non-conforming geographical key')


def _shape(value, members):
    if not isinstance(value, dict) or set(value) != members or value['v'] != PROFILE:
        raise ValueError('object shape')


def _integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError('integer')


def root(raw):
    value = parse(raw)
    _shape(value, ROOT_MEMBERS)
    _integer(value['seq'], 1)
    _sha_ok(value['head'])
    return value


def manifest(raw):
    value = parse(raw)
    _shape(value, MANIFEST_MEMBERS)
    _integer(value['seq'], 1)
    for key in ('record_count', 'pack_count'):
        _integer(value[key])
    if value['prev'] is not None:
        _sha_ok(value['prev'])
    if (value['seq'] == 1) != (value['prev'] is None):
        raise ValueError('previous manifest')
    if not isinstance(value['index'], dict) or len(value['index']) > 1024:
        raise ValueError('index')
    for prefix, shard_sha in value['index'].items():
        _prefix_ok(prefix, INDEX_DEPTH)
        _sha_ok(shard_sha)
    return value


def leaf_key(h):
    parts = parse_h(h)
    return xy_key(parts[0])[:LEAF_DEPTH]


def intersects(prefix, scope):
    return (
        (scope.xy_hi is None or prefix.ljust(KEY_LEN, '0') < xy_key(scope.xy_hi)) and
        (scope.xy_lo is None or prefix.ljust(KEY_LEN, 'z') >= xy_key(scope.xy_lo))
    )


def shard(raw, prefix):
    value = parse(raw)
    _shape(value, SHARD_MEMBERS)
    if not isinstance(value['prefix'], str):
        raise PublicationReadError('non-conforming geographical key')
    _prefix_ok(value['prefix'], len(value['prefix']))
    if (
        value['prefix'] != prefix
        or not isinstance(value['children'], dict)
        or not isinstance(value['records'], list)
        or not isinstance(value['packs'], list)
    ):
        raise ValueError('shard shape')
    if not isinstance(value['prefix'], str):
        raise PublicationReadError('non-conforming geographical key')
    _prefix_ok(value['prefix'], len(value['prefix']))
    _prefix_ok(prefix, len(prefix))
    if not INDEX_DEPTH <= len(prefix) <= LEAF_DEPTH:
        raise PublicationReadError('non-conforming geographical key')
    leaf = len(prefix) == LEAF_DEPTH
    if leaf:
        if value['children'] or not value['records']:
            raise ValueError('leaf shape')
    elif not value['children'] or value['records'] or value['packs']:
        raise ValueError('interior shape')
    for child, child_sha in value['children'].items():
        _prefix_ok(child, len(prefix) + 1)
        if not child.startswith(prefix):
            raise ValueError('prefix chain')
        _sha_ok(child_sha)
    for entry in value['records']:
        if not isinstance(entry, dict) or set(entry) != ENTRY_MEMBERS:
            raise ValueError('record entry')
        _sha_ok(entry['sha256'])
        if not isinstance(entry['mid'], str) or not entry['mid'].startswith(MID_PREFIX):
            raise ValueError('MID namespace')
        _sha_ok(entry['mid'][len(MID_PREFIX):])
        if leaf_key(entry['h']) != prefix:
            raise ValueError('record placement')
    ids = [entry['sha256'] for entry in value['records']]
    if ids != sorted(set(ids)):
        raise ValueError('record order/duplicate')
    for pack_sha in value['packs']:
        _sha_ok(pack_sha)
    if value['packs'] != sorted(set(value['packs'])):
        raise ValueError('pack order/duplicate')
    if value['packs'] and len(value['packs']) != (len(ids) + PACK_MAX - 1) // PACK_MAX:
        raise ValueError('pack count')
    return value


def pack(records):
    if not 1 <= len(records) <= PACK_MAX or any(not r for r in records):
        raise ValueError('pack size')
    return MAGIC + struct.pack('>I', len(records)) + b''.join(carrier.lp(r) for r in records)


def unpack(raw):
    reader = carrier.Reader(raw)
    if reader.take(len(MAGIC)) != MAGIC:
        raise ValueError('pack magic')
    count = reader.count()
    if not 1 <= count <= PACK_MAX:
        raise ValueError('pack count')
    records = [reader.field() for _ in range(count)]
    reader.end()
    if any(not entry for entry in records):
        raise ValueError('empty pack entry')
    return records


def object_path(kind, sha):
    return f'{kind}/{sha[:2]}/{sha}'


def shard_path(prefix, sha):
    return 'h/' + '/'.join(prefix) + '/' + sha + '.json'


def _fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def durable_write(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _fsync_dir(path.parent)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


class PublicationStore:
    """Single-writer dedupe store: valid by MID, candidates by transport digest."""

    def __init__(self):
        self.valid = {}
        self.candidates = {}

    def admit(self, raw):
        observation = carrier.validate(raw)
        if observation.state == carrier.State.VALID:
            target, key = self.valid, observation.address
        elif observation.state in (carrier.State.ALGORITHM, carrier.State.KEY):
            target, key = self.candidates, digest(raw)
        else:
            return observation.state.value
        target.setdefault(key, raw)
        return observation.state.value


class Publisher:
    def __init__(self, directory, packs=False):
        self.path = Path(directory)
        self.packs = packs

    def _put(self, relative_path, raw):
        target = self.path / relative_path
        if not target.exists() or target.read_bytes() != raw:
            durable_write(target, raw)

    def publish(self, records, *, fail_after=None):
        if hasattr(records, 'valid'):
            records = list(records.valid.values()) + list(records.candidates.values())
        self.path.mkdir(parents=True, exist_ok=True)
        grouped = {}
        unique = {digest(raw): raw for raw in records}
        for sha, raw in sorted(unique.items()):
            observation = carrier.validate(raw)
            if observation.state not in (carrier.State.VALID, carrier.State.ALGORITHM, carrier.State.KEY):
                raise ValueError('publisher requires admitted records')
            grouped.setdefault(leaf_key(observation.h), []).append((
                dict(h=observation.h, mid=observation.address, sha256=sha),
                raw,
            ))

        for sha, raw in sorted(unique.items()):
            self._put(object_path('records', sha), raw)

        leaves = {}
        pack_count = 0
        for prefix, items in sorted(grouped.items()):
            packs = []
            if self.packs:
                for start in range(0, len(items), PACK_MAX):
                    packed = pack([raw for _, raw in items[start:start + PACK_MAX]])
                    pack_sha = digest(packed)
                    self._put(object_path('segments', pack_sha), packed)
                    packs.append(pack_sha)
            pack_count += len(packs)
            leaves[prefix] = dict(
                v=PROFILE,
                prefix=prefix,
                children={},
                records=[entry for entry, _ in items],
                packs=sorted(packs),
            )

        if fail_after == 'objects':
            raise InterruptedError('objects durable')

        index = {}

        level = leaves
        for depth in range(LEAF_DEPTH, INDEX_DEPTH - 1, -1):
            parents = {}
            for prefix, node in sorted(level.items()):
                raw = canonical(node)
                sha = digest(raw)
                self._put(shard_path(prefix, sha), raw)
                if depth == INDEX_DEPTH:
                    index[prefix] = sha
                else:
                    parent = prefix[:-1]
                    parent_node = parents.setdefault(parent, dict(v=PROFILE, prefix=parent, children={}, records=[], packs=[]))
                    parent_node['children'][prefix] = sha
            level = parents

        if fail_after == 'shards':
            raise InterruptedError('shards durable')

        root_file = self.path / 'root.json'
        old = root(root_file.read_bytes()) if root_file.exists() else None
        previous = None
        if old:
            manifest_raw = (self.path / 'manifests' / f"{old['head']}.json").read_bytes()
            if digest(manifest_raw) != old['head']:
                raise ValueError('previous manifest digest')
            previous = manifest(manifest_raw)
            if previous['seq'] != old['seq']:
                raise ValueError('previous sequence')

        state = dict(index=index, record_count=len(unique), pack_count=pack_count)
        if previous and all(previous[key] == value for key, value in state.items()):
            return old

        seq = old['seq'] + 1 if old else 1
        manifest_raw = canonical(dict(state, v=PROFILE, seq=seq, prev=old['head'] if old else None))
        head = digest(manifest_raw)
        self._put(f'manifests/{head}.json', manifest_raw)

        if fail_after == 'manifest':
            raise InterruptedError('manifest durable')

        root_object = dict(v=PROFILE, seq=seq, head=head)
        durable_write(root_file, canonical(root_object))
        return root_object


class Reader:
    def __init__(self, packs=False, store=None, retries=2):
        self.packs = packs
        self.store = store or PublicationStore()
        self.retries = retries
        self.heads = {}
        self.checkpoints = {}
        self.paths = []

    def get(self, base, path, sha=None):
        self.paths.append(path)
        try:
            with urlopen(base.rstrip('/') + '/' + path, timeout=10) as response:
                raw = response.read(MAX_OBJECT + 1)
        except (URLError, OSError) as exc:
            if hasattr(exc, 'close'):
                exc.close()
            raise PublicationReadError('missing object') from exc
        if len(raw) > MAX_OBJECT:
            raise PublicationReadError('resource limit')
        if sha is not None and digest(raw) != sha:
            raise PublicationReadError('corrupt object')
        return raw

    def read_publication(self, base, scope=None):
        scope = scope or Subscription()
        for attempt in range(self.retries + 1):
            try:
                return self._attempt(base.rstrip('/'), scope)
            except PublicationReadError as exc:
                if exc.reason == 'publication race' and attempt < self.retries:
                    continue
                raise
            except carrier.ResourceLimit as exc:
                raise PublicationReadError('resource limit') from exc
            except (ValueError, TypeError, KeyError, RecursionError, OverflowError) as exc:
                raise PublicationReadError('invalid object') from exc

    def _attempt(self, base, scope):
        current_root = root(self.get(base, 'root.json'))
        seq = current_root['seq']
        head = current_root['head']
        previous = self.heads.get(base)
        if previous and seq < previous[0]:
            raise PublicationReadError('stale root')
        if previous and seq == previous[0] and head != previous[1]:
            raise PublicationReadError('equivocal root')

        current_manifest = manifest(self.get(base, f'manifests/{head}.json', head))
        if current_manifest['seq'] != seq:
            raise PublicationReadError('publication race')

        pending = []
        rejected = 0
        record_count = 0
        pack_count = 0

        def verify(raw, entry):
            nonlocal rejected
            if digest(raw) != entry['sha256']:
                raise PublicationReadError('corrupt object')
            observation = carrier.validate(raw)
            if observation.address is not None and (observation.address != entry['mid'] or observation.h != entry['h']):
                raise PublicationReadError('record metadata')
            if observation.state in (carrier.State.STRUCTURAL, carrier.State.PROVENANCE):
                rejected += 1
                return
            if scope.matches(observation.h):
                pending.append(raw)

        def walk(prefix, shard_sha):
            nonlocal record_count, pack_count
            if not intersects(prefix, scope):
                return
            current = shard(self.get(base, shard_path(prefix, shard_sha), shard_sha), prefix)
            entries = {entry['sha256']: entry for entry in current['records']}
            record_count += len(entries)
            pack_count += len(current['packs'])
            if self.packs and current['packs']:
                ids = list(entries)
                groups = [ids[i:i + PACK_MAX] for i in range(0, len(ids), PACK_MAX)]
                seen = set()
                for pack_sha in current['packs']:
                    records = unpack(self.get(base, object_path('segments', pack_sha), pack_sha))
                    actual = [digest(record) for record in records]
                    if actual not in groups or any(item in seen for item in actual):
                        raise PublicationReadError('pack membership')
                    seen.update(actual)
                    for raw, sha in zip(records, actual):
                        verify(raw, entries[sha])
                if seen != set(entries):
                    raise PublicationReadError('pack membership')
            else:
                for sha, entry in entries.items():
                    verify(self.get(base, object_path('records', sha), sha), entry)
            for child, child_sha in current['children'].items():
                walk(child, child_sha)

        for prefix, shard_sha in current_manifest['index'].items():
            walk(prefix, shard_sha)

        if scope == Subscription() and (
            record_count != current_manifest['record_count'] or pack_count != current_manifest['pack_count']
        ):
            raise PublicationReadError('manifest counts')

        before = len(self.store.valid)
        for raw in pending:
            self.store.admit(raw)

        self.heads[base] = (seq, head)
        self.checkpoints[(base, tuple(scope.wire().items()))] = head
        return dict(
            head=head,
            seq=seq,
            admitted=len(self.store.valid) - before,
            valid=len(self.store.valid),
            candidates=len(self.store.candidates),
            rejected=rejected,
        )

