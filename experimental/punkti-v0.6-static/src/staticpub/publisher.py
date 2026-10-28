"""Single-writer bottom-up immutable publication, atomic root commit."""
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from .carrier_io import (MAX_LEAF_DEPTH, MIN_LEAF_DEPTH, VERSION, carrier,
                         digest, leaf_key, object_path, pack, packed,
                         shard_path, unpacked)
from .store import durable_write


class Publisher:
    def __init__(self, directory, mode='A', pack_size=256, leaf_depth=MAX_LEAF_DEPTH):
        if (mode not in ('A', 'B') or pack_size < 1 or type(leaf_depth) is not int or
                not (MIN_LEAF_DEPTH <= leaf_depth <= MAX_LEAF_DEPTH)):
            raise ValueError('publication mode/pack size')
        self.path = Path(directory) / 'punkti'
        self.mode, self.pack_size, self.leaf_depth = mode, pack_size, leaf_depth

    def _put(self, path, raw):
        target = self.path / path
        if not target.exists() or target.read_bytes() != raw:
            durable_write(target, raw)

    def publish(self, store, *, fail_after=None):
        """Failure injection marks durable phases for recovery tests only."""
        groups, pack_count = defaultdict(list), 0
        for mid, raw in sorted(store.valid.items()):
            observation = carrier.validate(raw)
            if observation.state != carrier.State.VALID or observation.address != mid:
                raise ValueError('store contains invalid record')
            sha = digest(raw)
            self._put(object_path('records', sha), raw)
            groups[leaf_key(observation.h, self.leaf_depth)].append((dict(mid=mid, sha256=sha, h=observation.h), raw))
        leaves = {}
        for prefix, items in sorted(groups.items()):
            packs = []
            if self.mode == 'B':
                for start in range(0, len(items), self.pack_size):
                    raw = pack([r for _, r in items[start:start + self.pack_size]])
                    sha = digest(raw)
                    self._put(object_path('segments', sha), raw)
                    packs.append(sha)
                    pack_count += 1
            leaves[prefix] = dict(v=VERSION, prefix=prefix, children={},
                                  records=[e for e, _ in items], packs=packs)
        if fail_after == 'objects':
            raise InterruptedError('objects durable')
        level = leaves
        index = {}
        for depth in range(self.leaf_depth, 1, -1):
            parents = {}
            for prefix, shard in sorted(level.items()):
                raw = packed(shard)
                sha = digest(raw)
                self._put(shard_path(prefix, sha), raw)
                if depth == 2:
                    index[prefix] = sha
                else:
                    parent = prefix[:-1]
                    parents.setdefault(parent, dict(v=VERSION, prefix=parent, children={}, records=[], packs=[]))['children'][prefix] = sha
            level = parents
        if fail_after == 'shards':
            raise InterruptedError('shards durable')
        root_path = self.path / 'root.json'
        old = unpacked(root_path.read_bytes()) if root_path.exists() else None
        previous = unpacked((self.path / 'manifests' / (old['head'] + '.json')).read_bytes()) if old else None
        state = dict(v=VERSION, depth=2, leaf_depth=self.leaf_depth, index=index,
                     record_count=len(store.valid), pack_count=pack_count)
        if previous and all(previous.get(k) == v for k, v in state.items()):
            return old  # Includes repairing missing objects before the no-op.
        seq = old['seq'] + 1 if old else 1
        # A stable per-state timestamp is needed for interrupted retry determinism.
        # Derive from max signed atom timestamp (milliseconds), never wall clock.
        millis = max((carrier.decode(r)[0]['t'] for r in store.valid.values()), default=0)
        # Carrier timestamps extend beyond datetime; use epoch for unrepresentable dates.
        try:
            created = datetime.fromtimestamp(millis / 1000, timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        except (ValueError, OverflowError, OSError):
            created = '1970-01-01T00:00:00.000Z'
        manifest = dict(state, seq=seq, prev=old['head'] if old else None, created_at=created)
        raw = packed(manifest)
        head = digest(raw)
        self._put(f'manifests/{head}.json', raw)
        if fail_after == 'manifest':
            raise InterruptedError('manifest durable')
        root = dict(v=VERSION, seq=seq, head=head, updated_at=created)
        durable_write(root_path, packed(root))
        return root
