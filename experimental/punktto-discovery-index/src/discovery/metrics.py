"""Reproducible real-HTTP comparison; no latency or compression assumptions."""
import argparse
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
from punkti_node import publication as pub
from .client import Client
from .generator import generate
from .geohash import encode


@contextmanager
def server(directory):
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(directory)))
    thread = threading.Thread(target=httpd.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{httpd.server_port}'
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()


def fixture_records():
    # Reuse the repository's deterministic, signed frozen-carrier test fixture.
    from punkti_node.test_publication import fixture
    addresses = ['9q8zhuwqcp_0'] * 3 + ['9q8zhuwqcp_12.5', 'u4pruydqqv_-2', 'bcde_0', '']
    return [fixture(i, h=h) for i, h in enumerate(addresses)]


def bootstrap(directory, base, include_index=True):
    node = dict(id='prototype', base=base, publication=base + '/publication', submit=base + '/submit')
    if include_index:
        node['index'] = base + '/publication/discovery/index.json'
    Path(directory, 'nodes.json').write_bytes(pub.canonical(dict(v='punkti/bootstrap/1', nodes=[node])))


def files(directory):
    paths = [p for p in Path(directory).rglob('*') if p.is_file()]
    return dict(files=len(paths), bytes=sum(p.stat().st_size for p in paths))


def measure(sizes=(10, 100, 1000, 10000)):
    from punkti_node.test_publication import fixture
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        publication = directory / 'publication'
        pub.Publisher(publication).publish(fixture_records())
        generate(publication)
        result = dict(fixture=dict(atoms=7, addresses=5, discovery=files(publication / 'discovery')), http={})
        with server(directory) as base:
            bootstrap(directory, base)
            for scenario, kwargs in [('unknown', {}), ('known', {'exact_h': '9q8zhuwqcp_0'})]:
                for method in ('discovery', 'frozen'):
                    client = Client(base)
                    read = client.read(baseline=method == 'frozen', **kwargs)
                    result['http'][scenario + '_' + method] = dict(
                        requests=client.http.requests, bytes=client.http.bytes, records=len(read['records']))
        result['synthetic'] = []
        for size in sizes:
            with tempfile.TemporaryDirectory() as corpus:
                path = Path(corpus)
                # Low-discrepancy arithmetic spreads cells reproducibly worldwide.
                hs = [encode(-80 + (i * 73.1234567 % 160), -170 + (i * 137.7654321 % 340), 10) + '_0'
                      for i in range(size)]
                if len(set(hs)) != size:
                    raise ValueError('synthetic cells collide')
                pub.Publisher(path).publish([fixture(i, h=h) for i, h in enumerate(hs)])
                generate(path)
                result['synthetic'].append(dict(atoms=size, distinct_cells=size, **files(path / 'discovery')))
        result['method'] = ('HTTP GET response-body bytes, no headers/compression/cache; fresh client per run; '
                            'bootstrap included, raw hashes checked, optional Reader cross-check excluded; '
                            'unknown fetches all occupied regions and records, known fetches one exact h. '
                            'Synthetic totals count only discovery files, not Layer-3 publication.')
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='experimental/punktto-discovery-index/evidence/metrics.json')
    args = parser.parse_args()
    result = measure()
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
