"""Adversarial offline proof joins; mock inventories test join semantics only."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import code_target_proofs as tool

FOLDER = Path(__file__).resolve().parent
READ = tool.calls.ancestry.read_json


def source(token='imd'):
    return READ(FOLDER.parent / 'code-routes' / (token + '-proof.json'))


def external():
    return READ(FOLDER / 'imd-target-proof.json')


class JoinTests(unittest.TestCase):
    def test_real_demo_without_network(self):
        spec = importlib.util.spec_from_file_location('target_proofs_demo', FOLDER / 'demo.py')
        demo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(demo)
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            self.assertTrue(demo.main()['demonstration_passed'])

    def test_missing_remains_explicit(self):
        r = tool.evaluate(source(), [])
        self.assertEqual(r['decision'], 'incomplete-constant-identities')
        self.assertEqual(len(r['missing_targets']), 1)
        self.assertIsNone(r['joined_targets'][0]['target_runtime'])
        self.assertEqual(len(r['unresolved_calls'][0]['sites']), 11)

    def test_unmodified_inputs_and_root_identity(self):
        s, e = source(), external()
        before = copy.deepcopy((s, e))
        r = tool.evaluate(s, [e])
        self.assertEqual((s, e), before)
        target = r['joined_targets'][0]['target_runtime']
        self.assertEqual(target['address'], e['observation']['target'])
        self.assertEqual(target['code_hash'], e['observation']['nodes'][0]['code_hash'])
        self.assertFalse(r['dependency_completeness_verified'])
        self.assertFalse(r['semantic_safety_verified'])

    def test_corrupt_source_refuses_before_target(self):
        s = source()
        s['header_rlp'] = '0x00'
        with patch.object(tool.calls.proof, 'verify', wraps=tool.calls.proof.verify) as verify:
            with self.assertRaises(ValueError):
                tool.evaluate(s, [external()])
            self.assertEqual(verify.call_count, 1)

    def test_corrupt_target_proof(self):
        e = external()
        e['proofs'][0]['codeHash'] = '0x' + '11' * 32
        with self.assertRaises(ValueError):
            tool.evaluate(source(), [e])

    def test_self_consistent_forged_target_runtime(self):
        e = external()
        node = e['observation']['nodes'][0]
        node['code'] = '0x00'
        node['code_bytes'] = 1
        node['code_hash'] = tool.lens.digest(b'\0')
        e['observation']['effective_code_hash'] = node['code_hash']
        with self.assertRaises(ValueError):
            tool.evaluate(source(), [e])

    def test_duplicate_refused(self):
        e = external()
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            tool.evaluate(source(), [e, e])

    def test_unexpected_valid_evidence_refused(self):
        with self.assertRaisesRegex(ValueError, 'unexpected'):
            tool.evaluate(source(), [source('zto')])

    def test_derived_report_not_proof(self):
        r = tool.evaluate(source('zto'), [])
        with self.assertRaises((ValueError, KeyError)):
            tool.evaluate(source(), [r])

    def test_wrong_anchor(self):
        with self.assertRaises(ValueError):
            tool.evaluate(source(), [external()], '0x' + '11' * 32)

    def test_matching_anchor_still_not_authenticated(self):
        s = source()
        r = tool.evaluate(s, [external()], s['observation']['block']['hash'])
        self.assertEqual(r['source_proof']['anchor'], 'caller-supplied-block-hash')
        self.assertFalse(r['anchor_authenticity_verified'])

    def test_limits_and_type(self):
        for evidence in (None, (), [None] * 17):
            with self.assertRaises(ValueError):
                tool.evaluate(source(), evidence)

    def test_same_hash_different_number_refused(self):
        # Isolate join validation with proof checks already represented as valid.
        s, e = source(), external()
        checked = tool.calls.proof.verify(e)
        checked['block'] = dict(checked['block'], number='0x1')
        original = tool.calls.proof.verify
        def verify(bundle, anchor=None):
            return checked if bundle is e else original(bundle, anchor)
        with patch.object(tool.calls.proof, 'verify', side_effect=verify):
            with self.assertRaisesRegex(ValueError, 'match source block'):
                tool.evaluate(s, [e])

    def test_different_hash_refused(self):
        s, e = source(), external()
        checked = tool.calls.proof.verify(e)
        checked['block'] = dict(checked['block'], hash='0x'+'22'*32)
        original = tool.calls.proof.verify
        with patch.object(tool.calls.proof, 'verify', side_effect=lambda b,a=None:
                          checked if b is e else original(b,a)):
            with self.assertRaisesRegex(ValueError, 'match source block'):
                tool.evaluate(s, [e])

    def test_source_account_can_satisfy_self_target(self):
        s = source('zto')
        inventory = tool.targets.inspect(s)
        address = s['observation']['target']
        inventory['runtimes'][0]['constant_targets'] = [
            {'address': address, 'call_site_count': 1, 'sites': [{'pc': 1}]}]
        with patch.object(tool.targets, 'inspect', return_value=inventory):
            r = tool.evaluate(s, [])
        self.assertEqual(r['joined_targets'][0]['status'], 'same-block-runtime-proven')

    def test_cli_valid_missing_invalid(self):
        command = [sys.executable, '-B', str(FOLDER / 'code_target_proofs.py'),
                   '--source', str(FOLDER.parent / 'code-routes/imd-proof.json')]
        missing = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(missing.returncode, 3)
        self.assertEqual(json.loads(missing.stdout)['decision'], 'incomplete-constant-identities')
        valid = subprocess.run(command + ['--target-proof', str(FOLDER / 'imd-target-proof.json')],
                               capture_output=True, text=True)
        self.assertEqual(valid.returncode, 0)
        invalid = subprocess.run(command + ['--anchor-hash', '0x'+'11'*32],
                                 capture_output=True, text=True)
        self.assertEqual(invalid.returncode, 1)
        self.assertEqual(invalid.stdout, '')
        escape = subprocess.run([sys.executable, '-B', str(FOLDER / 'code_target_proofs.py'),
                                 '--source', '/etc/passwd'], capture_output=True, text=True)
        self.assertEqual(escape.returncode, 1)
        self.assertEqual(escape.stdout, '')


if __name__ == '__main__':
    unittest.main()
