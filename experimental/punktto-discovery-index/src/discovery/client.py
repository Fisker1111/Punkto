"""GET-only discovery and frozen-path fallback, with optional Reader cross-check."""
import argparse
import json
from urllib.parse import urljoin, urlsplit
from urllib.request import urlopen
from punkti_node import publication as pub
from punkti_node import carrier
from punkti_node.spatial import Subscription, xy_key, parse_h
from . import index


class HTTP:
    def __init__(self):
        self.requests = 0
        self.bytes = 0
        self.paths = []

    def get(self, url, checksum=None):
        self.requests += 1
        self.paths.append(url)
        try:
            with urlopen(url, timeout=10) as response:
                raw = response.read(pub.MAX_OBJECT + 1)
        except OSError as exc:
            if hasattr(exc, 'close'):
                exc.close()
            raise ValueError('missing HTTP object') from exc
        self.bytes += len(raw)
        if len(raw) > pub.MAX_OBJECT:
            raise ValueError('resource limit')
        if checksum is not None and pub.digest(raw) != checksum:
            raise ValueError('hash mismatch')
        return raw


def scope_for(p):
    if not p:
        return Subscription()
    index.prefix(p)
    chars = list(p)
    for i in range(len(chars) - 1, -1, -1):
        at = pub.ALPHABET.index(chars[i])
        if at < 31:
            high = ''.join(chars[:i]) + pub.ALPHABET[at + 1]
            return Subscription(xy_lo=p, xy_hi=high)
    return Subscription(xy_lo=p)


class Client:
    def __init__(self, base, nodes_url=None, http=None):
        self.base = base.rstrip('/') + '/'
        self.nodes_url = urljoin(self.base, nodes_url or 'nodes.json')
        self.http = http or HTTP()

    def read(self, *, exact_h=None, prefix=None, baseline=False, cross_check=False):
        if exact_h is not None:
            parts = parse_h(exact_h)
            selected = pub.leaf_key(exact_h) if parts else ''
        else:
            selected = index.prefix(prefix) if prefix is not None else ''
        bootstrap = json.loads(self.http.get(self.nodes_url))
        if bootstrap.get('v') != 'punkti/bootstrap/1' or not bootstrap.get('nodes'):
            raise ValueError('bootstrap')
        node = bootstrap['nodes'][0]
        publication = node['publication'].rstrip('/') + '/'
        if urlsplit(publication).scheme not in ('http', 'https'):
            raise ValueError('publication URL')

        def wanted(h):
            if exact_h is not None:
                return h == exact_h
            return not selected or (bool(h) and xy_key(parse_h(h)[0]).startswith(selected))

        def intersects(p):
            if p == pub.UNANCHORED:
                return exact_h == '' or (exact_h is None and not selected)
            if exact_h == '':
                return False
            return not selected or p.startswith(selected) or selected.startswith(p)

        records = []
        reason = None

        def frozen():
            records.clear()
            root = pub.root(self.http.get(urljoin(publication, 'root.json')))
            manifest = pub.manifest(self.http.get(urljoin(publication, f"manifests/{root['head']}.json"), root['head']))
            if root['seq'] != manifest['seq']:
                raise ValueError('source sequence')
            counts = [0, 0]

            def walk(p, checksum):
                if not intersects(p):
                    return
                obj = pub.shard(self.http.get(urljoin(publication, pub.shard_path(p, checksum)), checksum), p)
                counts[0] += len(obj['records'])
                counts[1] += len(obj['packs'])
                for entry in obj['records']:
                    if wanted(entry['h']):
                        raw = self.http.get(urljoin(publication, pub.object_path('records', entry['sha256'])), entry['sha256'])
                        records.append(dict(entry, raw=raw))
                for child, checksum in obj['children'].items():
                    walk(child, checksum)
            for p, checksum in manifest['index'].items():
                walk(p, checksum)
            if not selected and exact_h is None and counts != [manifest['record_count'], manifest['pack_count']]:
                raise ValueError('manifest counts')
            return dict(head=root['head'], seq=root['seq'])

        stale = False
        if not baseline and node.get('index'):
            try:
                index_url = node['index']
                if urlsplit(index_url).scheme not in ('http', 'https'):
                    raise ValueError('index URL')
                directory = urljoin(index_url, './')
                if urljoin(directory, '../') != publication:
                    raise ValueError('index must be inside publication')
                root = index.validate(self.http.get(index_url), expected_prefix='')
                if 'children' not in root:
                    raise ValueError('root branch required')
                source = root['source']

                def walk(obj):
                    if 'entries' in obj:
                        for entry in obj['entries']:
                            if wanted(entry['h']):
                                for atom in entry['atoms']:
                                    raw = self.http.get(urljoin(directory, index.href(atom['href'], atom['sha256'], True)), atom['sha256'])
                                    records.append(dict(atom, h=entry['h'], raw=raw))
                        return
                    children = [(p, d) for p, d in obj['children'].items() if intersects(p)]
                    if 'unanchored' in obj and intersects(pub.UNANCHORED):
                        children.append(('', obj['unanchored']))
                    for p, desc in children:
                        child = index.validate(self.http.get(urljoin(directory, index.href(desc['href'], desc['sha256'])), desc['sha256']), source, p)
                        if (p == '' and 'entries' not in child) or any(child[k] != desc[k] for k in ('atoms', 'addresses')):
                            raise ValueError('child descriptor mismatch')
                        walk(child)
                walk(root)
                current = pub.root(self.http.get(urljoin(publication, 'root.json')))
                stale = source != {k: current[k] for k in ('head', 'seq')}
            except (ValueError, KeyError, TypeError) as exc:
                reason = str(exc)
                source = frozen()
        else:
            reason = 'baseline requested' if baseline else 'index absent'
            source = frozen()
        result = dict(source=source, stale=stale, fallback=reason is not None and not baseline,
                      fallback_reason=reason, records=records, raw_integrity=True,
                      authorship='not checked', cross_checked=False)
        if cross_check:
            transport = self.http

            class CheckedReader(pub.Reader):
                def get(self, base, path, sha=None):
                    return transport.get(urljoin(base.rstrip('/') + '/', path), sha)

            reader = CheckedReader()
            checked = reader.read_publication(publication.rstrip('/'), scope_for(selected))
            if checked['head'] != source['head'] or checked['seq'] != source['seq']:
                raise ValueError('frozen Reader source head differs from discovery snapshot')
            admitted = list(reader.store.valid.values()) + list(reader.store.candidates.values())
            by_digest = {pub.digest(raw): raw for raw in admitted}
            for entry in records:
                if by_digest.get(entry['sha256']) != entry['raw']:
                    raise ValueError('frozen Reader record mismatch')
                observation = carrier.validate(entry['raw'])
                if observation.address != entry['mid'] or observation.h != entry['h']:
                    raise ValueError('frozen Reader metadata mismatch')
            result['cross_checked'] = True
            result['authorship'] = ('verified' if all(carrier.validate(e['raw']).state == carrier.State.VALID for e in records)
                                    else 'contains unverified candidates')
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base')
    parser.add_argument('--nodes-url')
    parser.add_argument('--prefix')
    parser.add_argument('--exact-h')
    parser.add_argument('--cross-check', action='store_true')
    args = parser.parse_args()
    client = Client(args.base, args.nodes_url)
    result = client.read(prefix=args.prefix, exact_h=args.exact_h, cross_check=args.cross_check)
    for entry in result['records']:
        entry['raw'] = entry['raw'].hex()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
