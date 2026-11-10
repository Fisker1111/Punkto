"""Generate a side index from validated frozen publication objects."""
import argparse
from pathlib import Path
from punkti_node import publication as pub
from . import index


def generate(publication, output=None):
    publication = Path(publication).resolve()
    output = (Path(output) if output else publication / 'discovery').resolve()
    # The specified ../records links require a sibling directory in this tree.
    if output.parent != publication or output.name in {'records', 'manifests', 'h', 'segments'}:
        raise ValueError('output must be a discovery directory directly inside publication')
    before = pub.root((publication / 'root.json').read_bytes())
    source = {k: before[k] for k in ('head', 'seq')}

    def read(path, checksum):
        index.sha(checksum)
        target = (publication / path).resolve()
        if not target.is_relative_to(publication):
            raise ValueError('publication path escape')
        raw = target.read_bytes()
        if pub.digest(raw) != checksum:
            raise ValueError('source digest')
        return raw

    manifest = pub.manifest(read(f"manifests/{before['head']}.json", before['head']))
    if manifest['seq'] != before['seq']:
        raise ValueError('source sequence')
    groups, seen = {}, set()
    pack_count = 0

    def walk(p, checksum):
        nonlocal pack_count
        node = pub.shard(read(pub.shard_path(p, checksum), checksum), p)
        pack_count += len(node['packs'])
        for entry in node['records']:
            checksum = entry['sha256']
            if checksum in seen:
                raise ValueError('duplicate record')
            seen.add(checksum)
            read(pub.object_path('records', checksum), checksum)
            groups.setdefault(index.leaf_prefix(entry['h']), {}).setdefault(entry['h'], []).append(
                dict(mid=entry['mid'], sha256=checksum, href='../' + pub.object_path('records', checksum)))
        for child, child_sha in node['children'].items():
            walk(child, child_sha)

    for p in manifest['index']:
        index.prefix(p)
    for p, checksum in manifest['index'].items():
        walk(p, checksum)
    if len(seen) != manifest['record_count'] or pack_count != manifest['pack_count']:
        raise ValueError('source counts')

    objects = {}

    def make(p, *, entries=None, children=None):
        obj = dict(v=index.VERSION, source=source, prefix=p)
        if entries is not None:
            obj.update(entries=entries, atoms=sum(len(e['atoms']) for e in entries), addresses=len(entries))
        else:
            descs = list(children.values())
            obj.update(children=children, atoms=sum(d['atoms'] for d in descs),
                       addresses=sum(d['addresses'] for d in descs))
        raw = pub.canonical(obj)
        index.validate(raw)
        checksum = pub.digest(raw)
        objects[checksum] = raw
        return dict(atoms=obj['atoms'], addresses=obj['addresses'], href=f'd/{checksum}.json', sha256=checksum)

    leaves = {}
    for p, addresses in sorted(groups.items()):
        entries = [dict(h=h, atoms=sorted(atoms, key=lambda a: (a['mid'], a['sha256'])))
                   for h, atoms in sorted(addresses.items())]
        leaves[p] = make(p, entries=entries)
    level = leaves
    for depth in (6, 2):
        parents = {}
        for p, desc in sorted(level.items()):
            parents.setdefault(p[:depth], {})[p] = desc
        level = {p: make(p, children=children) for p, children in sorted(parents.items())}
    root_desc = make('', children=level)
    root_raw = objects.pop(root_desc['sha256'])
    # Immutable children may remain after an interrupted run; no root is exposed.
    for checksum, raw in sorted(objects.items()):
        target = output / index.href(f'd/{checksum}.json', checksum)
        if not target.resolve().is_relative_to(output):
            raise ValueError('discovery path escape')
        pub.durable_write(target, raw)
    output.mkdir(parents=True, exist_ok=True)
    pub._fsync_dir(output)
    pub._fsync_dir(publication)
    if pub.root((publication / 'root.json').read_bytes()) != before:
        raise ValueError('source head changed')
    pub.durable_write(output / 'index.json', root_raw)
    return index.validate(root_raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('publication')
    parser.add_argument('--output')
    args = parser.parse_args()
    print(pub.canonical(generate(args.publication, args.output)).decode())


if __name__ == '__main__':
    main()
