from urllib.parse import urljoin
from punkti_node import publication as pub
from discovery import index
from discovery.generator import generate
from .support import Fixture


class GeneratorTests(Fixture):
    def test_every_level_counts_hashes_and_exact_addresses(self):
        expected = {'': (7, 5), '9q': (4, 2), '9q8zhu': (4, 2), '9q8zhuwqcp': (4, 2),
                    'u4': (1, 1), 'u4pruy': (1, 1), 'u4pruydqqv': (1, 1),
                    'bc': (1, 1), 'bcde00': (1, 1), 'bcde000000': (1, 1)}
        visited, addresses = set(), set()

        def walk(obj, unanchored=False):
            p = obj['prefix']
            self.assertEqual(obj['source'], {k: self.head[k] for k in ('head', 'seq')})
            self.assertEqual((obj['atoms'], obj['addresses']), (1, 1) if unanchored else expected[p])
            visited.add('unanchored' if unanchored else p)
            for entry in obj.get('entries', []):
                addresses.add(entry['h'])
                for atom in entry['atoms']:
                    raw = (self.discovery / atom['href']).read_bytes()
                    self.assertEqual(pub.digest(raw), atom['sha256'])
                    self.assertTrue(urljoin('http://local/publication/discovery/', atom['href']).startswith('http://local/publication/records/'))
            children = list(obj.get('children', {}).items())
            if 'unanchored' in obj:
                children.append(('', obj['unanchored']))
            for p, desc in children:
                raw = (self.discovery / desc['href']).read_bytes()
                self.assertEqual(pub.digest(raw), desc['sha256'])
                child = index.validate(raw, obj['source'], p)
                walk(child, unanchored=p == '')
        walk(self.root)
        self.assertEqual(visited, set(expected) | {'unanchored'})
        self.assertEqual(addresses, {'9q8zhuwqcp_0', '9q8zhuwqcp_12.5', 'u4pruydqqv_-2', 'bcde_0', ''})
        self.assertNotIn('zz', self.root['children'])

    def test_empty_publication(self):
        self.publisher.publish([])
        root = generate(self.publication)
        self.assertEqual((root['atoms'], root['addresses'], root['children']), (0, 0, {}))
