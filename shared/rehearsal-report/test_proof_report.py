"""Real historical replay and refusal checks for the shared report."""
import copy
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import proof_report as tool


class ProofReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = json.loads((tool.SURFACE / 'zto-proof.json').read_text())
        cls.observation = json.loads((tool.SURFACE / 'zto-call.json').read_text())

    def test_real_zto_ready(self):
        result = tool.report(self.bundle, self.observation, 'totalSupply()', ['uint256'])
        self.assertEqual(result['status'], 'ready-to-review')
        self.assertEqual(result['decoded_values'][0]['value'], '1000000000000000000000000000')
        self.assertEqual(result['return_bytes'], self.observation['outcome']['result'])

    def test_block_mismatch_withholds_return(self):
        changed = copy.deepcopy(self.observation)
        changed['block']['number'] = '0x18f9519'
        result = tool.report(self.bundle, changed, 'totalSupply()', ['uint256'])
        self.assertEqual(result['status'], 'withheld')
        self.assertIsNone(result['decoded_values'])
        self.assertIsNone(result['return_bytes'])
        self.assertIn('same_block_number', result['failed_checks'])

    def test_wrong_signature_withholds_return(self):
        result = tool.report(self.bundle, self.observation, 'balanceOf(address)', ['uint256'])
        self.assertEqual(result['status'], 'withheld')
        self.assertIsNone(result['return_bytes'])

    def test_corrupt_proof_refused(self):
        changed = copy.deepcopy(self.bundle)
        changed['header_rlp'] = '0x80'
        with self.assertRaises(ValueError):
            tool.report(changed, self.observation, 'totalSupply()', ['uint256'])

    def test_non_hex_return_refused(self):
        changed = copy.deepcopy(self.observation)
        changed['outcome']['result'] = 'not-hex-return-bytes'
        with self.assertRaises(ValueError):
            tool.report(self.bundle, changed, 'totalSupply()', ['uint256'])


if __name__ == '__main__':
    unittest.main()
