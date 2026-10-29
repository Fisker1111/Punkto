"""Fsynced append log and operational Node subclass."""
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import tempfile
import threading
import uuid
from . import VERSION
from .carrier import RECORD_LIMIT, State, unb64, validate
from .mesh import Node, digest, wire
from .publication import Publisher, Reader
from .spatial import Subscription

LOG = logging.getLogger(__name__)


class Response(dict):
    def __init__(self, http_status=200, **payload):
        super().__init__(payload)
        self.http_status = http_status


class DurableStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.failed = False
        self.loaded = False
        self.log_lines = self.corrupt_lines = self.duplicate_lines = 0
        self.file = None
        meta_path = self.path / 'meta.json'
        if meta_path.exists():
            self.meta = json.loads(meta_path.read_text())
            if not isinstance(self.meta.get('epoch'), str) or not self.meta['epoch'] or not isinstance(self.meta.get('created_at'), str):
                raise ValueError('invalid store metadata')
        else:
            # Never silently assign a new epoch to an existing log.
            if (self.path / 'atoms.jsonl').exists():
                raise ValueError('existing atom log has no meta.json; restore metadata from backup')
            self.meta = dict(epoch=uuid.uuid4().hex, created_at=datetime.now(timezone.utc).isoformat())
            self.atomic('meta.json', self.meta)
        self.file = open(self.path / 'atoms.jsonl', 'ab')
        # Make creation of the log itself durable before any admissions.
        try:
            fd = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError:
            self.error()
            self.file.close()
            raise

    def error(self):
        self.failed = True
        LOG.error('durable store write failed')

    def atomic(self, name, value):
        temporary = None
        with self.lock:
            try:
                with tempfile.NamedTemporaryFile(mode='w', dir=self.path, delete=False) as f:
                    temporary = f.name
                    json.dump(value, f, separators=(',', ':'), allow_nan=False)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temporary, self.path / name)
                fd = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            except OSError:
                self.error()
                raise
            finally:
                if temporary and os.path.exists(temporary):
                    os.unlink(temporary)

    def replay(self, node):
        with open(self.path / 'atoms.jsonl', 'rb') as source:
            for line in source:
                self.log_lines += 1
                try:
                    result = node.admit(json.loads(line))
                    if not result['admitted']:
                        if result.get('reason') == 'duplicate':
                            self.duplicate_lines += 1
                        else:
                            self.corrupt_lines += 1
                except (ValueError, TypeError, KeyError, IndexError, UnicodeError):
                    self.corrupt_lines += 1
        if self.corrupt_lines or self.duplicate_lines:
            LOG.warning('store replay ignored corrupt=%s duplicate=%s', self.corrupt_lines, self.duplicate_lines)
        # Separate a torn final line from future valid appends.
        with open(self.path / 'atoms.jsonl', 'rb') as source:
            source.seek(0, os.SEEK_END)
            if source.tell():
                source.seek(-1, os.SEEK_END)
                if source.read(1) != b'\n':
                    self.file.write(b'\n')
                    self.file.flush()
                    os.fsync(self.file.fileno())
        self.loaded = True

    def append(self, entry):
        with self.lock:
            try:
                if self.failed:
                    raise OSError('durable store already failed; restart after repair')
                self.file.write(json.dumps(entry.wire(), separators=(',', ':')).encode() + b'\n')
                self.file.flush()
                os.fsync(self.file.fileno())
                self.log_lines += 1
            except OSError:
                self.error()
                raise

    def close(self):
        with self.lock:
            if self.file:
                self.file.close()
                self.file = None


class PersistentNode(Node):
    def __init__(self, config):
        self.config = config
        self.durable = DurableStore(config['storage']['data_path'])
        super().__init__([Subscription(**s) for s in config['subscriptions']],
                         config['network']['peers'], self.durable.meta['epoch'])
        self.publication = None
        self.publication_reader = None
        self.publication_state = None
        self.replaying = True
        try:
            # Replay historical admissions independently of today's subscriptions.
            subscriptions = self.subscriptions
            self.subscriptions = (Subscription(),)
            self.durable.replay(self)
            self.subscriptions = subscriptions
            self.replaying = False
            self.restore_cursors()
            publication_config = self.config['publication']
            if publication_config['enabled']:
                self.publication = Publisher(publication_config['path'], packs=publication_config['packs'])
                self.publication_reader = Reader(packs=publication_config['packs'])
                self.publication_state = self.republish_publication()
        except Exception:
            self.durable.close()
            raise

    def persisted(self, entry):
        if not self.replaying:
            self.durable.append(entry)

    def restore_cursors(self):
        path = self.durable.path / 'cursors.json'
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            restored = []
            for name, length in [('cursors', 2), ('push_cursors', 3)]:
                entries = data[name]
                if any(not isinstance(k, list) or len(k) != length or
                       not all(isinstance(part, str) for part in k) for k, v in entries):
                    raise ValueError('invalid cursor keys')
                for key, value in entries:
                    if name == 'push_cursors':
                        if type(value) is not int or value < 0:
                            raise ValueError('invalid push cursor')
                    elif (not isinstance(value, dict) or
                          not isinstance(value.get('epoch'), str) or
                          not isinstance(value.get('scope'), str) or
                          type(value.get('ceiling')) is not int or value['ceiling'] < 0 or
                          not ((type(value.get('after')) is int and 0 <= value['after'] <= value['ceiling']) or
                               (isinstance(value.get('after'), list) and len(value['after']) == 2 and
                                all(isinstance(part, str) for part in value['after'])))):
                        raise ValueError('invalid pull cursor')
                restored.append({tuple(k): v for k, v in entries})
            self.cursors, self.push_cursors = restored
        except (ValueError, KeyError, TypeError):
            LOG.warning('invalid cursors.json; resuming from null')
        # A damaged log can shift sequence numbers; never reuse its high-water marks.
        if self.durable.corrupt_lines or self.durable.duplicate_lines:
            self.cursors.clear()
            self.push_cursors.clear()

    def after_sync(self):
        with self.lock:
            self.durable.atomic('cursors.json', {
                'cursors': [[list(k), v] for k, v in self.cursors.copy().items()],
                'push_cursors': [[list(k), v] for k, v in self.push_cursors.copy().items()],
            })

    def counts(self):
        return dict(valid=len(self.store), candidates=len(self.candidates),
                    log_lines=self.durable.log_lines, corrupt_lines=self.durable.corrupt_lines,
                    duplicate_lines=self.durable.duplicate_lines)

    def publication_records(self):
        """Records that are publishable under the ``punkti/pub/0.6`` profile.

        The static publication indexes records by their ``punkti/0.6`` MID, so a
        record from another namespace (an opaque future version) has no
        namespace-qualified address to publish and is carried by the node only.
        The publisher stays strict; the node filters here.
        """
        with self.lock:
            raws = [entry.raw for entry in self.store.values()]
            raws += [entry.raw for entry in self.candidates.values()]
        publishable = []
        for raw in raws:
            observation = validate(raw)
            if observation.state in (State.VALID, State.ALGORITHM, State.KEY):
                publishable.append(raw)
        return publishable

    def republish_publication(self):
        if not self.publication:
            return None
        self.publication_state = self.publication.publish(self.publication_records())
        return self.publication_state

    def replicate_publication(self, peer_base):
        if not self.publication_reader:
            raise ValueError('publication disabled')
        with self.lock:
            self.publication_reader.store.valid.clear()
            self.publication_reader.store.candidates.clear()
            self.publication_reader.read_publication(peer_base)
            for raw in list(self.publication_reader.store.valid.values()) + list(self.publication_reader.store.candidates.values()):
                self.admit(wire(raw))
            return self.republish_publication()

    def submit_records(self, records):
        if not isinstance(records, list) or not records:
            raise ValueError('records list required')
        results = []
        for item in records:
            if not isinstance(item, dict):
                raise ValueError('record wrapper required')
            raw = unb64(item['record'])
            if len(raw) > RECORD_LIMIT:
                raise ValueError('record limit')
            sha = digest(raw)
            if item['sha256'] != sha:
                raise ValueError('transport digest mismatch')
            observation = validate(raw)
            if observation.state in (State.STRUCTURAL, State.PROVENANCE):
                raise ValueError(observation.state.value)
            if item['address'] != observation.address:
                raise ValueError('address mismatch')
            admitted = self.admit(item)
            results.append(dict(
                address=observation.address,
                sha256=sha,
                state=admitted['state'],
                admitted=admitted['admitted'],
                duplicate=admitted.get('reason') == 'duplicate',
            ))
        publication = self.republish_publication()
        return dict(results=results,
                    head=publication['head'] if publication else None,
                    seq=publication['seq'] if publication else None)

    def special_route(self, method, path, query, body=None):
        if method == 'POST' and path == '/submit' and body is not None:
            return Response(**self.submit_records(body['records']))
        if method != 'GET':
            return None
        version = os.environ.get('PUNKTO_BUILD_VERSION') or VERSION
        if path == '/nodes.json':
            nodes = [{key: entry[key] for key in ('id', 'base', 'publication', 'submit', 'index') if key in entry}
                     for entry in sorted(self.config['bootstrap']['nodes'],
                                         key=lambda item: (item['id'].encode('utf-8'),
                                                           json.dumps(item, sort_keys=True)))]
            return Response(v='punkti/bootstrap/1', nodes=nodes,
                            notice="Recommended bootstrap list. Not a trust authority and not a completeness claim: one node's publication is one published view, not all of Punkto.")
        if path == '/health':
            return Response(status='ok', service='punkti-node', version=version)
        if path == '/ready':
            reasons = []
            if not self.durable.loaded:
                reasons.append('store not loaded')
            if not os.access(self.durable.path, os.W_OK):
                reasons.append('data directory not writable')
            if self.server is None:
                reasons.append('node not started')
            if self.durable.failed:
                reasons.append('durable write failure')
            return Response(503 if reasons else 200, **dict(
                status='not-ready' if reasons else 'ready', store=self.counts(), reasons=reasons))
        if path == '/node/info':
            node = self.config['node']
            return Response(node={k: node[k] for k in ('name', 'public_url', 'description')},
                            branding=self.config['branding'], version=version,
                            protocol='punkti-mesh/0.6-draft',
                            subscriptions=[s.wire() for s in self.subscriptions],
                            peers=self.config['network']['peers'], epoch=self.epoch,
                            store=self.counts(), metrics=dict(self.metrics),
                            build=dict(version=version, revision=os.environ.get('PUNKTO_BUILD_REVISION', ''),
                                       image=os.environ.get('PUNKTO_BUILD_IMAGE', '')),
                            config_loaded=self.config['config_loaded'], config_path=self.config['config_path'])
        return None
