"""Real HTTP negative tests for hosted /submit admission limits.

No public endpoints, no production writes, no claim of protection from Sybils.
"""
import http.client
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from .config import load_config
from .store import PersistentNode
from .write_safety import AdmissionRejected, WriteSafety


class HttpWriteSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def start(self, safety=None):
        config = load_config(environ={'PUNKTO_WEB_ENABLED': 'false',
                                      'PUNKTO_DATA_DIR': str(self.root / 'data'),
                                      'PUNKTO_HOST': '127.0.0.1',
                                      'PUNKTO_PORT': '0'})
        config['write_safety'].update(safety or {})
        node = PersistentNode(config).start(0, '127.0.0.1')
        self.addCleanup(node.durable.close)
        self.addCleanup(node.stop)
        return node

    def post(self, node, route='/submit', headers=None, body=None):
        conn = http.client.HTTPConnection('127.0.0.1', node.server.server_port, timeout=3)
        conn.request('POST', route,
                     body=json.dumps({'records': []} if body is None else body),
                     headers={'Content-Type': 'application/json', **(headers or {})})
        res = conn.getresponse()
        result = (res.status, dict(res.getheaders()), json.loads(res.read()))
        conn.close()
        return result

    def test_per_ip_rate_returns_429_with_retry_after(self):
        node = self.start({'per_ip_burst': 2, 'per_ip_rate': .01})
        self.assertEqual(self.post(node)[0], 400)
        self.assertEqual(self.post(node)[0], 400)
        status, headers, body = self.post(node)
        self.assertEqual(status, 429)
        self.assertEqual(headers.get('Retry-After'), '1')
        self.assertEqual(body.get('kind'), 'admission')

    def test_alias_shares_same_budget(self):
        node = self.start({'per_ip_burst': 1, 'per_ip_rate': .01})
        self.assertEqual(self.post(node, '/api/submit')[0], 400)
        self.assertEqual(self.post(node, '/submit')[0], 429)

    def test_untrusted_spoofed_headers_are_ignored(self):
        node = self.start({'per_ip_burst': 1, 'per_ip_rate': .01})
        self.assertEqual(self.post(node, headers={'X-Punkto-Client-IP': '8.8.8.8',
                                                  'X-Forwarded-For': '8.8.4.4'})[0], 400)
        self.assertEqual(self.post(node, headers={'X-Punkto-Client-IP': '1.1.1.1'})[0], 429)

    def test_trusted_proxy_explicit_ip_only(self):
        node = self.start({'trusted_proxy_cidrs': ['127.0.0.1/32'],
                           'per_ip_burst': 1, 'per_ip_rate': .01})
        self.assertEqual(self.post(node)[0], 403)
        self.assertEqual(self.post(node, headers={'X-Punkto-Client-IP': '1.1.1.1, 2.2.2.2'})[0], 403)
        self.assertEqual(self.post(node, headers={'X-Punkto-Client-IP': '1.1.1.1'})[0], 400)
        self.assertEqual(self.post(node, headers={'X-Punkto-Client-IP': '2.2.2.2'})[0], 400)
        self.assertEqual(self.post(node, headers={'X-Punkto-Client-IP': '1.1.1.1'})[0], 429)

    def test_global_limiter_spans_distinct_clients(self):
        node = self.start({'trusted_proxy_cidrs': ['127.0.0.1/32'],
                           'per_ip_burst': 10, 'global_burst': 1,
                           'global_rate': .01})
        self.assertEqual(self.post(node, headers={'X-Punkto-Client-IP': '1.1.1.1'})[0], 400)
        self.assertEqual(self.post(node, headers={'X-Punkto-Client-IP': '2.2.2.2'})[0], 429)

    def test_batch_rejected_before_records_are_accepted(self):
        node = self.start({'max_batch': 1})
        status, _, body = self.post(node, body={'records': [{}, {}]})
        self.assertEqual(status, 400)
        self.assertIn('submit batch size', body['error'])
        self.assertEqual(node.counts()['valid'], 0)

    def test_body_limit_precedes_json_parse(self):
        node = self.start({'max_http_bytes': 8})
        status, _, body = self.post(node)
        self.assertEqual(status, 413)
        self.assertIn('size', body['error'])

    def test_disk_limit_returns_507(self):
        node = self.start({'max_data_bytes': 1024, 'min_free_bytes': 0})
        status, _, body = self.post(node)
        self.assertEqual(status, 507)
        self.assertIn('budget', body['error'])

    def test_read_routes_still_work_under_write_limit(self):
        node = self.start({'per_ip_burst': 1, 'per_ip_rate': .01})
        self.post(node)
        self.post(node)
        conn = http.client.HTTPConnection('127.0.0.1', node.server.server_port)
        conn.request('GET', '/health')
        res = conn.getresponse()
        self.assertEqual(res.status, 200)
        self.assertEqual(json.loads(res.read())['status'], 'ok')
        conn.close()


class WriteSafetyPolicyTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config(environ={'PUNKTO_WEB_ENABLED': 'false'})['write_safety']

    def test_concurrent_submissions_fail_closed(self):
        cfg = {**self.config, 'max_in_flight': 1}
        guard = WriteSafety(cfg)
        with patch.object(guard, 'check_storage', return_value=None):
            with guard.admit('127.0.0.1', {'Content-Length': '10'}, '/unused'):
                with self.assertRaises(AdmissionRejected) as caught:
                    with guard.admit('127.0.0.2', {'Content-Length': '10'}, '/unused'):
                        pass
                self.assertEqual(caught.exception.http_status, 503)
        self.assertEqual(guard.in_flight, 0)

    def test_storage_unavailable_is_not_success(self):
        guard = WriteSafety(self.config)
        with patch('punkti_node.write_safety.os.statvfs', side_effect=OSError('fail')):
            with self.assertRaises(AdmissionRejected) as caught:
                with guard.admit('127.0.0.1', {'Content-Length': '10'}, '/missing'):
                    pass
        self.assertEqual(caught.exception.http_status, 503)
        self.assertEqual(guard.in_flight, 0)

    def test_config_rejects_bad_proxies_and_budgets(self):
        with tempfile.TemporaryDirectory() as folder:
            for field, value in [
                ('trusted_proxy_cidrs', ['0.0.0.0/0']),
                ('trusted_proxy_cidrs', ['bad_ip']),
                ('per_ip_rate', 0),
                ('per_ip_burst', True),
                ('max_in_flight', 0),
                ('max_http_bytes', 999999999),
            ]:
                with self.subTest(field=field, value=value):
                    path = Path(folder) / 'c.yml'
                    path.write_text(json.dumps({'web': {'enabled': False},
                                                'write_safety': {field: value}}))
                    with self.assertRaises(ValueError):
                        load_config(path, {})

    def test_disabled_guard_requires_explicit_opt_out(self):
        self.assertTrue(self.config['enabled'])
        cfg = {**self.config, 'enabled': False}
        guard = WriteSafety(cfg)
        with guard.admit('127.0.0.1', {}, '/not-used'):
            self.assertEqual(guard.in_flight, 0)


if __name__ == '__main__':
    unittest.main()
