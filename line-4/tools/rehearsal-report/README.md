# Rehearsal Report

Turn a saved `call-rehearsal-v1` observation into a compact, explicit report before a worker considers the call further. It binds the displayed target, calldata, value, block number/hash, outcome and source to the saved evidence, and marks incomplete evidence as `withheld`. Python 3 standard library only.

From the repository root, one command shows it working on the saved real ZTO `totalSupply()` rehearsal:

```sh
python3 -B line-4/tools/rehearsal-report/rehearsal_report.py
```

When tried on 2026-10-14, it printed `"status": "ready-to-review"`, a successful return outcome, target `0xd782bdea4ef02a0bd391eb9089470c8080f0a68e`, and the pinned block hash from the committed observation. A report is evidence navigation, not a safety or ABI oracle: it does not prove decoded meaning, gas, state effects, canonicality, authority, or future execution. It never reads secrets, signs, sends, pays, posts, or deploys.
