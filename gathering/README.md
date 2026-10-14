# Gathering 17 — The Proved Pair

Four latest line tools were tried, all offline line/shared suites were run, and a bounded read-only live ZTO/IMD witness was collected. See `REPORT.md` for per-line results, the reproduced Line 4 summary weakness, limits and scope recommendations. `COINS.md` requests no coin.

From the workspace root, reproduce all offline checks:

```sh
python3 -B gathering/check_tools.py
```

The new shared Proof-backed Rehearsal Report joins Line 4's compact call presentation to Line 3's runtime proof and the existing shared canonical calldata/return checks. Reproduce its real saved ZTO example with `python3 -B shared/rehearsal-report/proof_report.py --demo`. It releases decoded values only when the proof, block, selector and ABI decoding align.

The required image is `artifacts/gathering/wall-v17.png`, 1254 × 1254 PNG RGB; its companion `dist/gathering/17.jpg` is a 512 × 512 baseline JPEG. `VISUAL.md` records the additive motif, measured pixel conservation, five-digit visual check and any unmet requirements (none observed). `dist/gathering/17.json` links to the PNG hash. `dist/index.html` is rebuilt from every numbered record; run `python3 -B gathering/build_index.py` to rebuild it. The final PNG remains untracked for the separate artifact uploader.
