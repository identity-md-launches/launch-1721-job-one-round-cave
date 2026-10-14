# ZTO Witness Routes

Collect a ZTO/IMD Uniswap v4 witness through a caller-selected, ordered list of read-only Ethereum RPC endpoints. It distinguishes pruned history and unavailable transport from inconsistent evidence, keeps one resolved block height/hash throughout fallback, and refuses to call one source corroboration. Python 3.10+ and standard library only; keep the committed sibling `zto-witness/`, `zto-path/` and `zto-band/` sources alongside it. No installation or network is needed for the demonstration.

Run this from the repository root to see it working:

```sh
python3 -B line-1/tools/zto-witness-routes/zto_witness_routes.py --demo
```

This reuses the real saved ZTO/IMD observation and one recorded 1-ZTO V4Quoter return at block **26,184,260**. An explicitly simulated `.example` archive failure is diagnosed as `history_unavailable`; the real archived source is then validated. The result is deliberately `insufficient_sources`, with `bound_released: false` and `bound: null`. Demo exit **0** means the demonstration ran, not that a trade bound was released. The demo opens no sockets and makes no network requests. `demo-report.json` records the actual run.

For fresh read-only collection, supply history-capable endpoints in order:

```sh
python3 -B line-1/tools/zto-witness-routes/zto_witness_routes.py --live --rpc https://ethereum-rpc.publicnode.com --rpc https://eth.drpc.org --word-radius 0 --input ZTO --amount 1 --slippage-bps 100
```

Repeat `--rpc` up to eight times to add explicit fallback endpoints. HTTPS and an explicitly supplied literal loopback HTTP relay with a port are accepted by the existing transport. No relay is discovered or assumed; endpoint availability and independent upstreams are not promised. Without `--rpc`, the two public URLs above are used. `--block` accepts `finalized`, `safe`, `latest`, or a decimal block number. The first verified Ethereum header supplies the pin; every later capture uses that numeric height and must match its full recorded header. No fallback ever changes it to latest state.

Each successful source supplies its own entire initialization, pool state, bitmap/ticks and same-hash Quoter check. Partial work from a failed source is discarded. Availability failures permit advancing to the next explicit endpoint. A different block, pool state, incomplete/zero local fill, invalid evidence or Quoter mismatch stops with a withheld result; the tool does not keep looking for an agreeing pair. The first two complete matching sources feed the ancestor Witness gate and its floor-rounded planning minimum. One source, however complete, cannot release a bound.

Exit **0** in live mode means corroborated; **2** means a structured unavailable/withheld/insufficient-source result; **1** means invalid arguments or an uncaught input validation error. Reports go to stdout. There are no automatic same-endpoint retries: rate limits are reported and the next explicit route may be tried. Each inherited RPC read has a 30-second timeout and a 2 MB response limit. Bitmap radius defaults to **0** (worker-selected, matching the gathering's focused failure case), accepts 0–4, and captures at most 128 initialized ticks. There is no aggregate deadline; large coverage and slow sources can make a live invocation long. The worker-selected defaults are 1 ZTO input, 100 bps planning tolerance and finalized state; they are caller-overridable planning choices, not requester-approved trading instructions.

## What happened when tried

On 2026-10-14, the assignment's contributor transport returned Ethereum chain ID 1 and a complete capture plus matching 1-ZTO Quoter check at block **`0x18f9f4b`**, hash **`0x7ae39c89bed40bfe76c32a7048c88c67315774de25e3d8070bdaead3730999fd`**. Only that single transport was tested, so the live command correctly exited **2**, returned `insufficient_sources`, and released no bound. `live-check.json` records this limited result. The assignment's public source reference is [Ethereum PublicNode](https://ethereum-rpc.publicnode.com); the actual upstream identity behind the contributor transport was not independently established. This is a historical observation, not a continuing freshness or endpoint-availability claim. The earlier gathering's pruned-history error was not reproduced on this machine.

All **16 focused tests** passed, and the three dependency suites passed, for **55 tests total**. Tests exercise real archived arithmetic, simulated archive/transport failures, exact pin retention, fallback isolation, single-source refusal, tampered Quoter return, source mismatch, state/block disagreement, invalid evidence and incomplete fills. Positive two-source test cases are simulations using the same archived evidence with distinct test labels; they do not establish real independent providers.

```sh
python3 -B -m unittest discover -s line-1/tools/zto-witness-routes -p 'test_*.py' -v
```

This is RPC-relative planning evidence. Distinct URLs can share an upstream; no consensus proof or cryptographic state authentication is supplied. The minimum is not enforced by a router or receipt. Token settlement, transfer behavior, gas, MEV, future state and trade execution remain outside scope. It uses only the inherited four read-only RPC methods and never reads environment variables, keys, wallets or secrets, and never signs, sends, deploys, pays or posts. No new coin is required: the assigned ZTO/IMD pool remains the sole pool.
