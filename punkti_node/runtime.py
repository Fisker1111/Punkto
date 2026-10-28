"""Service lifecycle; signal handlers only request shutdown."""
import argparse
import logging
import signal
import sys
import threading
import yaml
from .config import load_config
from .store import PersistentNode
from .web import StaticWeb

LOG = logging.getLogger(__name__)


def run(config):
    stopping = threading.Event()
    node = PersistentNode(config)
    publication = config['publication']
    mounts = {}
    if publication['enabled']:
        mounts[publication['serve_prefix']] = publication['path']
    if config['web']['enabled'] or mounts:
        node.web = StaticWeb(config['web']['root'] if config['web']['enabled'] else None,
                             config['web']['spa_fallback'], mounts)
    net = config['network']

    def stop_requested(signum, frame):
        LOG.info('shutdown requested signal=%s', signum)
        stopping.set()

    def sync_loop():
        delay = 2
        while not stopping.wait(delay):
            try:
                failures = node.sync_known()
                if failures:
                    LOG.warning('sync peers unavailable count=%s', len(failures))
            except Exception:
                LOG.error('sync attempt failed', exc_info=False)
            finally:
                try:
                    node.after_sync()
                except OSError:
                    LOG.error('cursor persistence failed')
            delay = net['sync_interval_seconds']

    previous = {sig: signal.signal(sig, stop_requested) for sig in (signal.SIGTERM, signal.SIGINT)}
    worker = None
    try:
        node.start(net['listen_port'], net['listen_host'], net['advertise_url'] or config['node']['public_url'] or None)
        node.server.daemon_threads = False
        LOG.info('node started origin=%s epoch=%s', node.url, node.epoch)
        worker = threading.Thread(target=sync_loop, name='mesh-sync')
        worker.start()
        stopping.wait()
    finally:
        stopping.set()
        if worker:
            worker.join()
        # HTTPServer.shutdown must run outside its serve_forever thread.
        shutdown = threading.Thread(target=node.stop, name='http-shutdown')
        shutdown.start()
        shutdown.join()
        try:
            node.after_sync()
        except OSError:
            LOG.error('shutdown cursor persistence failed')
        finally:
            node.durable.close()
            for sig, handler in previous.items():
                signal.signal(sig, handler)
        LOG.info('node stopped')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Self-hostable Punkti draft Mesh node')
    parser.add_argument('--config')
    parser.add_argument('--check-config', action='store_true')
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        parser.error(str(exc))
    logging.basicConfig(stream=sys.stdout, level=config['logging']['level'].upper(),
                        format='%(asctime)s %(levelname)s %(message)s')
    if args.check_config:
        print('Configuration valid')
        return 0
    run(config)
    return 0
