"""A local node is durable data + explicit offline publication/replication jobs."""
from pathlib import Path
from .carrier_io import Subscription
from .publisher import Publisher
from .reader import Reader
from .store import Store


class Node:
    def __init__(self, directory, mode='A', subscriptions=None, leaf_depth=10):
        self.path = Path(directory)
        self.store = Store(self.path / 'store')
        self.publisher = Publisher(self.path / 'public', mode, leaf_depth=leaf_depth)
        self.reader = Reader(self.store, mode, leaf_depth=leaf_depth)
        self.subscriptions = [Subscription()] if subscriptions is None else subscriptions

    def publish(self):
        return self.publisher.publish(self.store)

    def replicate(self, base):
        results = [self.reader.read_publication(base, s) for s in self.subscriptions]
        self.publish()
        return results

    def stop(self):
        """There is no background daemon or network listener to keep alive."""
        return None
