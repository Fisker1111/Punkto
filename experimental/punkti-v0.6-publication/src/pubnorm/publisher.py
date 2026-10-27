"""Single-writer bottom-up publication, adapted from staticpub/publisher.py."""
from collections import defaultdict
from pathlib import Path
from . import objects as o
from .store import durable_write


class Publisher:
    def __init__(self, directory, packs=False):
        self.path, self.packs = Path(directory), packs

    def _put(self, path, raw):
        target = self.path / path
        if not target.exists() or target.read_bytes() != raw:
            durable_write(target, raw)

    def publish(self, records, *, fail_after=None):
        """Publish exact admitted variants; fail_after is a test interruption hook."""
        if hasattr(records, 'valid'):
            records = list(records.valid.values()) + list(records.candidates.values())
        groups = defaultdict(list)
        unique = {o.digest(r): r for r in records}
        for sha, raw in sorted(unique.items()):
            obs = o.carrier.validate(raw)
            if obs.state not in (o.carrier.State.VALID, o.carrier.State.ALGORITHM, o.carrier.State.KEY):
                raise ValueError('publisher requires admitted records')
            groups[o.leaf_key(obs.h)].append((dict(h=obs.h, mid=obs.address, sha256=sha), raw))
        for sha, raw in sorted(unique.items()):
            self._put(o.object_path('records', sha), raw)
        leaves, pack_count = {}, 0
        for prefix, items in sorted(groups.items()):
            packs = []
            if self.packs:
                for start in range(0, len(items), o.PACK_MAX):
                    raw = o.pack([r for _, r in items[start:start + o.PACK_MAX]])
                    sha = o.digest(raw)
                    self._put(o.object_path('segments', sha), raw)
                    packs.append(sha)
            pack_count += len(packs)
            leaves[prefix] = dict(v=o.PROFILE, prefix=prefix, children={},
                                  records=[e for e, _ in items], packs=sorted(packs))
        if fail_after == 'objects':
            raise InterruptedError('objects durable')
        index = {}
        if o.UNANCHORED in leaves:
            raw = o.canonical(leaves.pop(o.UNANCHORED))
            sha = o.digest(raw)
            self._put(o.shard_path(o.UNANCHORED, sha), raw)
            index[o.UNANCHORED] = sha
        level = leaves
        for depth in range(o.LEAF_DEPTH, o.INDEX_DEPTH - 1, -1):
            parents = {}
            for prefix, shard in sorted(level.items()):
                raw = o.canonical(shard)
                sha = o.digest(raw)
                self._put(o.shard_path(prefix, sha), raw)
                if depth == o.INDEX_DEPTH:
                    index[prefix] = sha
                else:
                    parent = prefix[:-1]
                    parents.setdefault(parent, dict(v=o.PROFILE, prefix=parent, children={},
                                                    records=[], packs=[]))['children'][prefix] = sha
            level = parents
        if fail_after == 'shards':
            raise InterruptedError('shards durable')
        root_path = self.path / 'root.json'
        old = o.root(root_path.read_bytes()) if root_path.exists() else None
        previous = None
        if old:
            raw = (self.path / 'manifests' / (old['head'] + '.json')).read_bytes()
            if o.digest(raw) != old['head']:
                raise ValueError('previous manifest digest')
            previous = o.manifest(raw)
            if previous['seq'] != old['seq']:
                raise ValueError('previous sequence')
        state = dict(index=index, record_count=len(unique), pack_count=pack_count)
        if previous and all(previous[k] == v for k, v in state.items()):
            return old
        seq = old['seq'] + 1 if old else 1
        raw = o.canonical(dict(state, v=o.PROFILE, seq=seq, prev=old['head'] if old else None))
        head = o.digest(raw)
        self._put(f'manifests/{head}.json', raw)
        if fail_after == 'manifest':
            raise InterruptedError('manifest durable')
        root = dict(v=o.PROFILE, seq=seq, head=head)
        durable_write(root_path, o.canonical(root))
        return root
