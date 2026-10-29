from punkti_node.test_publication import fixture
from discovery.generator import generate
from discovery.client import Client
from discovery.geohash import encode
from .support import Fixture


class ClientTests(Fixture):
    def test_blank_get_traversal_and_authoritative_reader(self):
        client = Client(self.http())
        result = client.read()
        self.assertEqual(len(result['records']), 7)
        self.assertTrue(result['raw_integrity'])
        self.assertEqual(result['authorship'], 'not checked')
        self.assertFalse(result['fallback'])
        self.assertEqual(result['source']['head'], self.head['head'])
        self.assertTrue(client.http.paths[0].endswith('/nodes.json'))
        result = Client(client.base).read(exact_h='9q8zhuwqcp_0', cross_check=True)
        self.assertEqual(len(result['records']), 3)
        self.assertTrue(result['cross_checked'])
        self.assertEqual(result['authorship'], 'verified')

    def test_bridge_prefix_no_invented_height(self):
        region = encode(37.8188889, -122.4779444, 6)
        result = Client(self.http()).read(prefix=region)
        self.assertEqual({e['h'] for e in result['records']}, {'9q8zhuwqcp_0', '9q8zhuwqcp_12.5'})
        self.assertEqual(len(result['records']), 4)

    def test_empty_region_short_zero_cell_and_fine_prefix(self):
        base = self.http()
        for kwargs, count in [({'prefix': 'zz'}, 0), ({'exact_h': 'bcde_0'}, 1),
                              ({'exact_h': '0000_0'}, 1), ({'prefix': '9q8zhuwqcp00'}, 4)]:
            self.assertEqual(len(Client(base).read(**kwargs)['records']), count)

    def test_unknown_algorithm_is_not_verified_authorship(self):
        self.publisher.publish([fixture(99, h='bcde_0', alg='future-signature')])
        generate(self.publication)
        result = Client(self.http()).read(cross_check=True)
        self.assertTrue(result['raw_integrity'])
        self.assertTrue(result['cross_checked'])
        self.assertEqual(result['authorship'], 'contains unverified candidates')
