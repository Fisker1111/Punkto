"""Normative revision: request and page admission boundaries."""
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from carrier import ResourceLimit
from mesh import Node, request, packed, wire
from support import fixture


class RevisionTests(unittest.TestCase):
    def test_push_descriptor_atomicity_and_limit_status(self):
        n = Node().start()
        good = wire(fixture())
        try:
            for bad in (dict(good, sha256='0'*64), dict(good, address=None),
                        dict(good, extra=1), {}, None, dict(good, record='!')):
                with self.assertRaises(HTTPError) as caught:
                    request(n.url, '/push', {'records': [good, bad]})
                self.assertEqual(caught.exception.code, 400)
                caught.exception.close()
                self.assertEqual(n.log, [])
            for path, body in (('/push', {'records': [good]*33}),
                               ('/pull?' + urlencode({'q': '{"limit":33}'}), None)):
                with self.assertRaises(HTTPError) as caught:
                    request(n.url, path, body)
                self.assertEqual(caught.exception.code, 413)
                self.assertIn(b'"resource"', caught.exception.read())
                caught.exception.close()
            legacy = wire(b'legacy', 'punkti/0.5.1:'+'0'*64)
            self.assertEqual(request(n.url, '/push', {'records': [legacy]})['results'][0]['reason'],
                             'legacy-adapter-unavailable')
        finally:
            n.stop()

    def test_initial_mid_cursor_and_modes(self):
        n = Node()
        page = n.page({'mode': 'mid'})
        self.assertIsNone(page['cursor']['after'])
        self.assertEqual(n.page({'mode': 'mid', 'cursor': page['cursor']}), page)
        for after in (0, ['', '']):
            with self.assertRaises(ValueError):
                n.page({'mode': 'mid', 'cursor': dict(page['cursor'], after=after)})
        spatial = n.page({})['cursor']
        with self.assertRaises(ValueError):
            n.page({'cursor': dict(spatial, after=None)})

    def test_pull_validates_page_before_admission_and_retry(self):
        source, target = Node(), Node()
        source.add(fixture()); source.add(fixture(1))
        page = source.page({})
        good, second = page['records']
        forged = wire(fixture(1)[:-1] + bytes([fixture(1)[-1] ^ 1]))
        for bad in (dict(second, sha256='0'*64), forged, wire(b'bad', second['address'])):
            response = dict(page, records=[good, bad])
            with patch('mesh.request', side_effect=[source.hello(), response]):
                with self.assertRaises(ValueError):
                    target.pull('http://127.0.0.1:1')
            self.assertEqual(target.log, [])
            self.assertEqual(target.cursors, {})
        with patch('mesh.request', side_effect=[source.hello(), page]):
            target.pull('http://127.0.0.1:1')
        self.assertEqual(len(target.log), 2)
        self.assertEqual(list(target.cursors.values()), [page['cursor']])

        target = Node()
        first = source.page({'limit': 1})
        second_page = source.page({'limit': 1, 'cursor': first['cursor']})
        broken = dict(second_page, records=[dict(second_page['records'][0], sha256='0'*64)])
        with patch('mesh.request', side_effect=[source.hello(), first, broken]):
            with self.assertRaises(ValueError):
                target.pull('http://127.0.0.1:1', limit=1)
        self.assertEqual(len(target.log), 1)
        self.assertEqual(list(target.cursors.values()), [first['cursor']])
        with patch('mesh.request', side_effect=[source.hello(), second_page]) as req:
            target.pull('http://127.0.0.1:1', limit=1)
        from urllib.parse import parse_qs, urlparse
        import json
        query = json.loads(parse_qs(urlparse(req.call_args_list[1].args[1]).query)['q'][0])
        self.assertEqual(query['cursor'], first['cursor'])
        self.assertEqual(len(target.log), 2)

    def test_discovery_skips_individual_poison_and_callback_deadline(self):
        n = Node(peers=['http://127.0.0.1:1'])
        valid = 'http://127.0.0.1:2'
        for info in ({}, {'protocol': 'punkti-mesh/0.6-draft', 'peers': None}):
            with patch('mesh.request', return_value=info):
                self.assertEqual(n.discover(), set())
        with patch('mesh.request', return_value=dict(protocol='punkti-mesh/0.6-draft',
                                                     peers=[None, valid, 'https://example.com', valid])):
            self.assertEqual(n.discover(), {valid})
        self.assertEqual(n.peers, {'http://127.0.0.1:1'})
        self.assertEqual(n.log, [])
        with patch.object(n, 'push_to'), patch.object(n, 'catchup'), patch('mesh.request') as req:
            n.connect(valid)
            self.assertEqual([c.kwargs for c in req.call_args_list], [{'timeout': 300}]*2)

    def test_unreadable_or_invalid_json_page_never_commits(self):
        from unittest.mock import MagicMock
        source = Node()
        source.add(fixture())
        page = packed(source.page({}))
        for raw, declared in ((page, len(page)+1), (page[:-1], len(page)-1),
                              (page[:-1]+b',"extra":NaN}', None)):
            target = Node()
            responses = []
            for body, length in ((packed(source.hello()), None), (raw, declared)):
                response = MagicMock()
                response.__enter__.return_value = response
                response.read.return_value = body
                response.headers = {'Content-Length': str(len(body) if length is None else length)}
                responses.append(response)
            with patch('mesh.urlopen', side_effect=responses), self.assertRaises(ValueError):
                target.pull('http://127.0.0.1:1')
            self.assertEqual(target.log, [])
            self.assertEqual(target.cursors, {})
