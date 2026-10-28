"""Run the experimental Mesh node: python -m nairobidot.serve --config FILE."""
from __future__ import annotations
import argparse
import signal
import threading
from pathlib import Path
from .carrier import dumps, loads
from .node import Node


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, help='JSON with subscriptions, peers and optional port')
    parser.add_argument('--port', type=int, help='override configuration port (0 chooses a free port)')
    args = parser.parse_args()
    config = loads(Path(args.config).read_bytes())
    node = Node(config.get('subscriptions', []), config.get('peers', []),
                config.get('port', 0) if args.port is None else args.port)
    done = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: done.set())
    node.start()
    print(dumps({'url': node.url, 'epoch': node.epoch}).decode('utf-8'), flush=True)
    try:
        # Explicitly configured peers are attempted once; callers schedule retries.
        node.sync_known()
        done.wait()
    finally:
        node.stop()


if __name__ == '__main__':
    main()
