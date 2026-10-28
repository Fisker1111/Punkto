"""Normative revision: descriptor and page atomicity, discovery, bounds."""
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from nairobidot.carrier import StructuralError, b64, dumps, from_atom, import_json
from nairobidot.node import Node, PeerError
from vectors import atom


class RevisionTests(unittest.TestCase):
    def test_push_descriptor_atomicity(self):
        n = Node([{}]).start()
        good = from_atom(atom()).item()
        try:
            for bad in (dict(good, sha256='0'*64), dict(good, address=None),
                        dict(good, extra=1), {}, None, dict(good, record='!')):
                with self.assertRaises(HTTPError) as caught:
                    urlopen(Request(n.url+'/push', data=dumps({'records': [good, bad]})), timeout=5)
                self.assertEqual(caught.exception.code, 400)
                caught.exception.close()
                self.assertEqual(n.log, [])
        finally:
            n.stop()

    def test_negative_zero_and_initial_mid(self):
        with self.assertRaises(StructuralError):
            import_json(dumps(atom()).replace(b'"t":0', b'"t":-0'))
        n = Node([{}])
        page = n.page({'mode': 'mid'})
        self.assertIsNone(page['cursor']['after'])
        self.assertEqual(n.page({'mode': 'mid', 'cursor': page['cursor']}), page)
        for after in (0, ['', '']):
            with self.assertRaises(StructuralError):
                n.page({'mode': 'mid', 'cursor': dict(page['cursor'], after=after)})
        with self.assertRaises(StructuralError):
            n.page({'cursor': dict(n.page({})['cursor'], after=None)})
        for scope in ({'xy_lo': 'g', 'xy_hi': 'g'}, {'xy_lo': 'z', 'xy_hi': 'g'},
                      {'z_min': 1, 'z_max': 1}, {'z_min': 1, 'z_max': -1}):
            with self.assertRaises(StructuralError):
                Node([scope])

    def test_pull_validates_page_before_admission_and_retry(self):
        source, target = Node([{}]), Node([{}])
        source.add(atom()); source.add(atom(1))
        page = source.page({})
        good, second = page['records']
        forged = from_atom(dict(atom(1), sig=b64(bytes(64)))).item()
        import hashlib
        malformed = dict(second, record=b64(b'bad'), sha256=hashlib.sha256(b'bad').hexdigest())
        for bad in (dict(second, sha256='0'*64), forged, malformed):
            with patch('nairobidot.node.request', side_effect=[source.hello(), dict(page, records=[good, bad])]):
                with self.assertRaises(PeerError):
                    target._pull_from('http://127.0.0.1:1')
            self.assertEqual(target.log, [])
            self.assertEqual(target._pull_checkpoints, {})
        with patch('nairobidot.node.request', side_effect=[source.hello(), page]):
            target._pull_from('http://127.0.0.1:1')
        self.assertEqual(len(target.log), 2)
        self.assertEqual(list(target._pull_checkpoints.values()), [page['cursor']])

        target = Node([{}])
        first = source.page({'limit': 1})
        second_page = source.page({'limit': 1, 'cursor': first['cursor']})
        broken = dict(second_page, records=[dict(second_page['records'][0], sha256='0'*64)])
        with patch('nairobidot.node.request', side_effect=[source.hello(), first, broken]):
            with self.assertRaises(PeerError):
                target._pull_from('http://127.0.0.1:1')
        self.assertEqual(len(target.log), 1)
        self.assertEqual(list(target._pull_checkpoints.values()), [first['cursor']])
        with patch('nairobidot.node.request', side_effect=[source.hello(), second_page]) as req:
            target._pull_from('http://127.0.0.1:1')
        from urllib.parse import parse_qs, urlparse
        import json
        query = json.loads(parse_qs(urlparse(req.call_args_list[1].args[1]).query)['q'][0])
        self.assertEqual(query['cursor'], first['cursor'])
        self.assertEqual(len(target.log), 2)

    def test_discovery_poison_and_callback_deadline(self):
        n = Node([{}], peers=['http://127.0.0.1:1'])
        valid = 'http://127.0.0.1:2'
        for info in ({}, {'protocol': 'punkti-mesh/0.6-draft', 'peers': None}):
            with patch('nairobidot.node.request', return_value=info):
                self.assertEqual(n.discover('http://127.0.0.1:1'), [])
        with patch('nairobidot.node.request', return_value=dict(protocol='punkti-mesh/0.6-draft',
                         peers=[None, valid, 'https://example.com', valid, n.url])):
            self.assertEqual(n.discover('http://127.0.0.1:1'), [valid])
        self.assertEqual(n.peers, {'http://127.0.0.1:1'})
        self.assertEqual(n.log, [])
        with patch.object(n, '_push_to'), patch.object(n, '_pull_from'), patch('nairobidot.node.request') as req:
            n.connect('http://127.0.0.1:1')
            self.assertEqual([c.kwargs for c in req.call_args_list], [{'timeout': 300}]*2)

    def test_unreadable_or_invalid_json_page_never_commits(self):
        from unittest.mock import MagicMock
        source = Node([{}])
        source.add(atom())
        page = dumps(source.page({}))
        for raw, declared in ((page, len(page)+1), (page[:-1], len(page)-1),
                              (page[:-1]+b',"extra":NaN}', None)):
            target = Node([{}])
            responses = []
            for body, length in ((dumps(source.hello()), None), (raw, declared)):
                response = MagicMock()
                response.__enter__.return_value = response
                response.read.return_value = body
                response.headers = {'Content-Length': str(len(body) if length is None else length)}
                responses.append(response)
            with patch('nairobidot.node.urlopen', side_effect=responses), self.assertRaises(PeerError):
                target._pull_from('http://127.0.0.1:1')
            self.assertEqual(target.log, [])
            self.assertEqual(target._pull_checkpoints, {})
