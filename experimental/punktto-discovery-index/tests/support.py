from pathlib import Path
import tempfile
import unittest
from punkti_node import publication as pub
from discovery.generator import generate
from discovery.metrics import fixture_records, bootstrap, server


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.publication = self.directory / 'publication'
        self.records = fixture_records()
        self.publisher = pub.Publisher(self.publication)
        self.head = self.publisher.publish(self.records)
        self.root = generate(self.publication)
        self.discovery = self.publication / 'discovery'

    def http(self, include_index=True):
        ctx = server(self.directory)
        base = ctx.__enter__()
        self.addCleanup(ctx.__exit__, None, None, None)
        bootstrap(self.directory, base, include_index)
        return base
