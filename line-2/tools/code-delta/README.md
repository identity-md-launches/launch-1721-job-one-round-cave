# Allowance Code Delta

This offline checker compares two strict `Allowance Spender Code` reports at their exact block hashes. It distinguishes unchanged runtime bytes, a changed code hash, code appearing or becoming empty, and a spender that was not rechecked. A missing row is deliberately reported as `not_rechecked`, never as a revoked allowance.

One command shows it working from the repository root:

```sh
python3 -B line-2/tools/code-delta/code_delta.py \
  --before line-2/tools/code-delta/example-report.json \
  --after line-2/tools/code-delta/example-report.json
```

The bundled report is a real ZTO Ethereum observation from PublicNode at block 26,187,572, with two active spenders and their bytecode hashes. Comparing the same exact report is an honest unchanged demonstration; a later report should be produced by `line-2/tools/spender-code/spender_code.py` before comparing different blocks. The checker never signs, sends, simulates, pays, posts, reads secrets or environment variables.

Limitations: it only compares already-discovered active standard ERC-20 spender rows; runtime bytes do not identify a controller, proxy implementation or behavior; RPC evidence is trusted rather than cryptographically proved.
