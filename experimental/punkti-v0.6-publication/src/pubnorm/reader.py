"""Static GET and whole-attempt staging, adapted from staticpub/reader.py."""
from urllib.error import URLError
from urllib.request import urlopen
from . import objects as o
from .store import Store

# Explicit local resource policy, not a protocol validity limit.
MAX_OBJECT = 64 * 1024 * 1024


class ReadError(ValueError):
    error_class = 'retryable'

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class Reader:
    def __init__(self, packs=False, store=None, retries=2):
        self.packs, self.store, self.retries = packs, store or Store(), retries
        self.heads, self.checkpoints, self.paths = {}, {}, []

    def get(self, base, path, sha=None):
        self.paths.append(path)
        try:
            with urlopen(base + '/' + path, timeout=10) as response:
                raw = response.read(MAX_OBJECT + 1)
        except (URLError, OSError) as exc:
            if hasattr(exc, 'close'):
                exc.close()
            raise ReadError('missing object') from exc
        if len(raw) > MAX_OBJECT:
            raise ReadError('resource limit')
        if sha is not None and o.digest(raw) != sha:
            raise ReadError('corrupt object')
        return raw

    def read_publication(self, base, scope=None):
        base = base.rstrip('/')
        scope = scope or o.Subscription()
        for attempt in range(self.retries + 1):
            try:
                return self._attempt(base, scope)
            except ReadError as exc:
                if exc.reason == 'publication race' and attempt < self.retries:
                    continue
                raise
            except o.carrier.ResourceLimit as exc:
                raise ReadError('resource limit') from exc
            except (ValueError, TypeError, KeyError, RecursionError, OverflowError) as exc:
                raise ReadError('invalid object') from exc

    def _attempt(self, base, scope):
        root = o.root(self.get(base, 'root.json'))
        seq, head = root['seq'], root['head']
        old = self.heads.get(base)
        if old and seq < old[0]:
            raise ReadError('stale root')
        if old and seq == old[0] and head != old[1]:
            raise ReadError('equivocal root')
        manifest = o.manifest(self.get(base, f'manifests/{head}.json', head))
        if manifest['seq'] != seq:
            raise ReadError('publication race')
        pending, rejected = [], 0
        record_count = pack_count = 0

        def verify(raw, entry):
            nonlocal rejected
            if o.digest(raw) != entry['sha256']:
                raise ReadError('corrupt object')
            obs = o.carrier.validate(raw)
            if obs.address is not None and (obs.address != entry['mid'] or obs.h != entry['h']):
                raise ReadError('record metadata')
            if obs.state in (o.carrier.State.STRUCTURAL, o.carrier.State.PROVENANCE):
                rejected += 1
                return
            if scope.matches(obs.h):
                pending.append(raw)

        def walk(prefix, sha):
            nonlocal record_count, pack_count
            if not o.intersects(prefix, scope):
                return
            shard = o.shard(self.get(base, o.shard_path(prefix, sha), sha), prefix)
            entries = {e['sha256']: e for e in shard['records']}
            record_count += len(entries)
            pack_count += len(shard['packs'])
            if self.packs and shard['packs']:
                ids = list(entries)
                groups = [ids[i:i + o.PACK_MAX] for i in range(0, len(ids), o.PACK_MAX)]
                seen = set()
                for p in shard['packs']:
                    records = o.unpack(self.get(base, o.object_path('segments', p), p))
                    actual = [o.digest(r) for r in records]
                    if actual not in groups or any(s in seen for s in actual):
                        raise ReadError('pack membership')
                    seen.update(actual)
                    for raw, s in zip(records, actual):
                        verify(raw, entries[s])
                if seen != set(entries):
                    raise ReadError('pack membership')
            else:
                for s, entry in entries.items():
                    verify(self.get(base, o.object_path('records', s), s), entry)
            for child, s in shard['children'].items():
                walk(child, s)

        for prefix, sha in manifest['index'].items():
            walk(prefix, sha)
        if scope == o.Subscription() and (record_count != manifest['record_count'] or pack_count != manifest['pack_count']):
            raise ReadError('manifest counts')
        before = len(self.store.valid)
        for raw in pending:
            self.store.admit(raw)
        self.heads[base] = (seq, head)
        self.checkpoints[(base, tuple(scope.wire().items()))] = head
        return dict(head=head, seq=seq, admitted=len(self.store.valid) - before,
                    valid=len(self.store.valid), candidates=len(self.store.candidates), rejected=rejected)
