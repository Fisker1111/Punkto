"""Start HTTP serving and periodic peer pulls; run from repository root."""
import logging
import signal
import threading

from .server import AtomService, Config, make_server
from .store import AtomStore


def main():
    logging.basicConfig(level=logging.INFO)
    config = Config.from_env()
    store = AtomStore(config.db)
    service = AtomService(store, config)
    server = make_server(service)
    worker = threading.Thread(target=service.sync_loop, name='atom-sync', daemon=True)

    def shutdown(signum, frame):
        service.stop.set()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    worker.start()
    logging.info('Serving %s on port %s', config.node, config.port)
    try:
        server.serve_forever()
    finally:
        service.stop.set()
        worker.join()
        server.server_close()
        store.close()


if __name__ == '__main__':
    main()
