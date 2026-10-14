# Proof-backed Rehearsal Report

This shared version of Line 4's compact rehearsal report gates its `ready-to-review` summary on Line 3 runtime proof and the existing shared call surface checks. It revalidates the raw proof and call observation at one exact historical block, the selected signature's selector, canonical arguments and return layout before displaying decoded values. Line 1 can use the same entry point for a saved quoter call; Line 2 can use it for a saved ERC-20 allowance or balance call, provided it has matching raw evidence. Python standard library only; all dependencies are committed under `shared/surface-return/`.

From the workspace root, see it work offline on real saved ZTO `totalSupply()` evidence:

```sh
python3 -B shared/rehearsal-report/proof_report.py --demo
```

The demo returned `ready-to-review`, block `0x18f9518`, historical raw supply `1000000000000000000000000000`, and the unanchored proof label. `demo-result.json` records the output. Five focused tests passed, including a wrong block, wrong chosen signature, corrupted proof, and non-hex return bytes that the original Line 4 summary marked ready. A mismatch exits 2 and withholds return bytes and decoded values; invalid evidence exits 1. The original raw evidence is unchanged. For your own workspace files:

```sh
python3 -B shared/rehearsal-report/proof_report.py --bundle shared/surface-return/zto-proof.json --observation shared/surface-return/zto-call.json --signature 'totalSupply()' --types uint256
```

Run the focused checks with `python3 -B gathering/run_suite.py discover -s shared/rehearsal-report -p 'test_*.py' -v`.

Line 4 source adapted: `line-4/tools/rehearsal-report/rehearsal_report.py`, SHA-256 `ad742095b10e5c8822f441b0c6b98e01db08c0c33f874118931d447b832eaad3`. Its small status/target/calldata/outcome presentation is retained; verification is delegated to `shared/surface-return/surface_call.py`, which joins Line 3's Code Proof with Line 4's call and ABI decoders. This is a historical review aid: the header anchor is untrusted unless the caller independently supplies one, and even aligned evidence does not prove future execution, contract safety, spending authority or current state. No wallet, key, environment variable, signing, sending, payment or deployment is used.
