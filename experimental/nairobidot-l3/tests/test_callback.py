"""Item 11: real callback dispatch and deterministic transport deadline failures."""
import copy
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from nairobidot.node import Node, request, PeerError


class CallbackConformance(unittest.TestCase):
    def test_each_callback_dispatches_one_phase_without_connect(self):
        n = Node([{}]).start()
        peer = 'http://127.0.0.1:1'
        n.peers.add(peer)
        try:
            for phase, selected, other in (('push', '_push_to', '_pull_from'),
                                            ('pull', '_pull_from', '_push_to')):
                with self.subTest(phase=phase), \
                     patch.object(n, 'connect', side_effect=AssertionError('recursive connect')) as connect, \
                     patch.object(n, selected) as run, patch.object(n, other) as skipped:
                    self.assertEqual(request(n.url, '/sync', {'peer': peer, 'phase': phase}), {'ok': True})
                    run.assert_called_once_with(peer)
                    skipped.assert_not_called()
                    connect.assert_not_called()
        finally:
            n.stop()

    def test_callback_transport_deadline_is_bounded_and_nonfatal(self):
        n = Node([{}])
        n.peers.update(('http://127.0.0.1:1', 'http://127.0.0.1:2'))
        # Fail at either reciprocal phase, preserving previously completed work.
        for phase in ('push', 'pull'):
            with self.subTest(phase=phase):
                calls = []
                def transport(req, *, timeout):
                    import json
                    body = json.loads(req.data)
                    calls.append((body['phase'], timeout))
                    if body['phase'] == phase:
                        raise TimeoutError('deterministic deadline')
                    from unittest.mock import MagicMock
                    response = MagicMock()
                    response.__enter__.return_value = response
                    response.read.return_value = b'{"ok":true}'
                    response.headers = {'Content-Length': '11'}
                    return response
                before = copy.deepcopy((n._push_checkpoints, n._pull_checkpoints))
                with patch.object(n, '_push_to'), patch.object(n, '_pull_from'), \
                     patch('nairobidot.node.urlopen', side_effect=transport):
                    failures = n.sync_known()
                self.assertEqual(len(failures), 2)
                self.assertTrue(all(value != 'ok' for value in failures.values()))
                self.assertEqual(calls, ([('push', 300)] if phase == 'push' else
                                         [('push', 300), ('pull', 300)]) * 2)
                self.assertEqual((n._push_checkpoints, n._pull_checkpoints), before)
        with patch('nairobidot.node.urlopen', side_effect=TimeoutError('ordinary')) as transport:
            with self.assertRaises(PeerError):
                request('http://127.0.0.1:1', '/hello')
            self.assertEqual(transport.call_args.kwargs, {'timeout': 5})

    def test_failed_reciprocal_operation_retains_checkpoints(self):
        n = Node([{}]).start()
        peer = 'http://127.0.0.1:1'
        n.peers.add(peer)
        n._push_checkpoints[('retained',)] = 7
        n._pull_checkpoints[('retained',)] = {'after': 7}
        before = copy.deepcopy((n._push_checkpoints, n._pull_checkpoints))
        # Keep the incoming HTTP real; fail outbound peer I/O inside the phase.
        import nairobidot.node as implementation
        original = implementation.urlopen
        def transport(req, **kwargs):
            if req.full_url.startswith(peer + '/'):
                raise TimeoutError('peer unavailable')
            return original(req, **kwargs)
        try:
            for phase in ('push', 'pull'):
                with self.subTest(phase=phase), patch('nairobidot.node.urlopen', side_effect=transport):
                    with self.assertRaises(PeerError) as caught:
                        request(n.url, '/sync', {'peer': peer, 'phase': phase})
                    self.assertEqual((n._push_checkpoints, n._pull_checkpoints), before)
                    self.assertEqual(request(n.url, '/hello')['protocol'], 'punkti-mesh/0.6-draft')
        finally:
            n.stop()
