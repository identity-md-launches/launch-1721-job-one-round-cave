import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import urllib.error

import zto_witness_routes as routes

HERE = Path(__file__).resolve().parent
OBS = json.loads((HERE.parent / 'zto-path/observation.json').read_text())
EVIDENCE = json.loads((HERE.parent / 'zto-path/quoter-check.json').read_text())
ROW = next(r for r in EVIDENCE['results'] if r['input_token'] == 'ZTO' and r['amount'] == '1')
A, B, C = ('https://a.example', 'https://b.example', 'https://c.example')


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.capture_errors = {}
        self.compare_errors = {}
        self.changes = {}

    def rpc(self, endpoint):
        calls = self.calls
        class RPC:
            def call(self, method, params):
                calls.append((endpoint, method, params))
                return '0x1' if method == 'eth_chainId' else OBS['base']['block']
        return RPC()

    def capture(self, endpoint, tag, radius):
        self.calls.append((endpoint, 'capture', tag))
        if endpoint in self.capture_errors:
            raise self.capture_errors[endpoint]
        obs = copy.deepcopy(OBS)
        obs['base']['source'] = endpoint
        if endpoint in self.changes:
            self.changes[endpoint](obs)
        return obs

    def compare(self, observation, endpoint, cases):
        self.calls.append((endpoint, 'compare', cases))
        if endpoint in self.compare_errors:
            raise self.compare_errors[endpoint]
        check = copy.deepcopy(EVIDENCE)
        check.update(source=endpoint, results=[copy.deepcopy(ROW)], all_match=True)
        return check

    def collect(self, endpoints=(A, B, C), compare=None, **kwargs):
        return routes.collect(endpoints, radius=1, rpc_factory=self.rpc,
                              capture=self.capture, compare=compare or self.compare, **kwargs)

    def test_matching_captures_release_exact_floor_and_stop_after_two(self):
        report = self.collect()
        self.assertTrue(report['bound_released'])
        self.assertEqual(report['bound']['planning_minimum_raw'],
                         str(int(ROW['local_output_raw']) * 9900 // 10000))
        self.assertFalse(any(c[0] == C for c in self.calls))

    def test_pruned_capture_fallback_keeps_pin_and_failed_data_out(self):
        self.capture_errors[A] = ValueError('RPC error: {"code":4444,"message":"pruned history unavailable"}')
        report = self.collect()
        self.assertTrue(report['bound_released'])
        self.assertEqual(report['witness']['source_labels'], [B, C])
        self.assertEqual(report['attempts'][1]['status'], 'history_unavailable')
        self.assertEqual([c[2] for c in self.calls if c[1] == 'capture'],
                         [OBS['base']['block']['number']] * 3)

    def test_all_history_failures_are_unavailable_not_quote_mismatch(self):
        self.capture_errors = {s: ValueError('missing trie node') for s in (A, B, C)}
        report = self.collect()
        self.assertEqual(report['status'], 'unavailable')
        self.assertIsNone(report['bound'])
        self.assertEqual(sum(r['status'] == 'history_unavailable' for r in report['attempts']), 3)

    def test_single_source_never_releases(self):
        report = self.collect([A])
        self.assertEqual(report['status'], 'insufficient_sources')
        self.assertFalse(report['bound_released'])

    def test_quote_mismatch_cannot_be_replaced_with_agreeing_third(self):
        def compare(obs, endpoint, cases):
            check = self.compare(obs, endpoint, cases)
            if endpoint == B:
                check['results'][0]['raw_result'] = '0x' + '00' * 64
            return check
        report = self.collect(compare=compare)
        self.assertEqual(report['status'], 'withheld')
        self.assertEqual(report['attempts'][-1]['status'], 'quote_mismatch')
        self.assertFalse(any(c[0] == C for c in self.calls))

    def test_hash_disagreement_stops_and_preserves_first_pin(self):
        self.changes[B] = lambda obs: obs['base']['block'].update(hash='0x' + '12' * 32)
        report = self.collect()
        self.assertEqual(report['attempts'][-1]['status'], 'block_disagreement')
        self.assertEqual(report['block'], OBS['base']['block'])
        self.assertFalse(report['bound_released'])
        self.assertFalse(any(c[0] == C for c in self.calls))

    def test_state_disagreement_stops_before_second_quoter(self):
        def change(obs):
            raw = obs['base']['raw']
            raw['liquidity'] = '0x' + format(int(raw['liquidity'], 16) + 1, '064x')
        self.changes[B] = change
        report = self.collect()
        self.assertEqual(report['attempts'][-1]['status'], 'state_disagreement')
        self.assertFalse(any(c[0] == B and c[1] == 'compare' for c in self.calls))
        self.assertFalse(any(c[0] == C for c in self.calls))

    def test_invalid_evidence_stops_without_availability_fallback(self):
        self.capture_errors[A] = ValueError('wrong PoolKey hash')
        report = self.collect()
        self.assertEqual(report['attempts'][-1]['status'], 'invalid_evidence')
        self.assertEqual(report['status'], 'withheld')
        self.assertFalse(any(c[0] == B for c in self.calls))

    def test_quoter_transport_failure_discards_whole_source(self):
        self.compare_errors[A] = urllib.error.URLError('timed out')
        report = self.collect()
        self.assertTrue(report['bound_released'])
        self.assertEqual(report['witness']['source_labels'], [B, C])
        self.assertEqual(report['attempts'][1]['stage'], 'quoter')
        self.assertEqual(report['attempts'][1]['status'], 'transport_unavailable')

    def test_quoter_wrong_source_is_invalid_not_fallback(self):
        def compare(obs, endpoint, cases):
            check = self.compare(obs, endpoint, cases)
            check['source'] = C
            return check
        report = self.collect(compare=compare)
        self.assertEqual(report['status'], 'withheld')
        self.assertFalse(any(c[0] == B for c in self.calls))

    def test_incomplete_quote_stops_before_quoter_or_later_source(self):
        report = self.collect(amount='1000000000000000000')
        self.assertEqual(report['attempts'][-1]['status'], 'incomplete_or_zero_output')
        self.assertFalse(any(c[1] == 'compare' or c[0] == B for c in self.calls))

    def test_duplicate_sources_invalid_radius_and_invalid_amount_prevent_network(self):
        for endpoints, kwargs in (([A, A], {}), ([A], {'radius': 5}),
                                  ([A], {'amount': '-1'}), ([A], {'slippage': True})):
            with self.subTest(endpoints=endpoints, kwargs=kwargs), self.assertRaises(ValueError):
                routes.collect(endpoints, rpc_factory=self.rpc, **kwargs)
        self.assertEqual(self.calls, [])

    def test_failed_resolution_falls_back_then_pins_numeric_height(self):
        def factory(endpoint):
            if endpoint == A:
                raise urllib.error.URLError('unavailable')
            return self.rpc(endpoint)
        report = routes.collect([A, B, C], rpc_factory=factory, capture=self.capture, compare=self.compare)
        self.assertTrue(report['bound_released'])
        self.assertEqual(report['attempts'][0]['stage'], 'resolve_block')
        self.assertEqual([c[2] for c in self.calls if c[1] == 'capture'],
                         [OBS['base']['block']['number']] * 2)

    def test_all_resolution_failures_have_no_invented_pin(self):
        def factory(endpoint):
            raise urllib.error.URLError('unavailable')
        report = routes.collect([A, B], rpc_factory=factory)
        self.assertIsNone(report['block'])
        self.assertIsNone(report['bound'])
        self.assertEqual(report['status'], 'unavailable')

    def test_demo_is_offline_real_single_source_with_explicit_simulated_failure(self):
        with patch.object(routes.path.z, 'RPC', side_effect=AssertionError('network forbidden')):
            report = routes.demo()
        self.assertIn('simulated', report['mode'])
        self.assertFalse(report['bound_released'])
        self.assertEqual(report['block'], OBS['base']['block'])

    def test_error_classification_keeps_http_and_rpc_separate(self):
        error = urllib.error.HTTPError(A, 429, 'Too Many Requests', {}, None)
        self.assertEqual(routes.failure_kind(error), 'http_429')
        self.assertEqual(routes.failure_kind(ValueError('RPC error: method unavailable')), 'rpc_unavailable')
        self.assertEqual(routes.failure_kind(ValueError('wrong ABI length')), 'invalid_evidence')
        self.assertEqual(routes.failure_kind(ValueError('invalid archive evidence')), 'invalid_evidence')


if __name__ == '__main__':
    unittest.main()
