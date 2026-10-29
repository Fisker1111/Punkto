#!/usr/bin/env python3
"""Serve a disposable publication; all generated files stay in its temp directory."""
import sys
sys.dont_write_bytecode = True
import functools
import http.server
import importlib.util
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from punkti_node.publication import Publisher

spec = importlib.util.spec_from_file_location(
    'fixture_support', REPO / 'experimental/punkti-v0.6-mesh/tests/support.py')
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)


def main():
    targets = ['u3butz7k9q_23', 'u3bu_23', '', 'u3butz7k9q_23', 'u3butz7k9q_24']
    # Keep the temp directory inside this worktree; it is removed on Ctrl-C.
    with tempfile.TemporaryDirectory(prefix='.fixture-', dir=Path(__file__).resolve().parents[1]) as directory:
        root = Publisher(directory).publish([
            support.fixture(i + 1, h=h) for i, h in enumerate(targets)])
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
        with http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
            print(f'BASE=http://127.0.0.1:{server.server_port}', flush=True)
            print(f'HEAD={root["head"]}', flush=True)
            print(f'TARGETS={targets!r}', flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == '__main__':
    main()
