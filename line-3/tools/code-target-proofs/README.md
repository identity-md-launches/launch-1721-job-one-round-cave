# Code Target Proofs

Identify the historical executable bytes at a structural external-call target by joining Code Targets' complete call inventory to raw Code Proof bundles at the **same block number and hash**. Missing target proofs and unresolved call operands remain explicit. This gives an unfamiliar worker a reproducible next step after discovering a candidate address.

One command, from the repository root, with Python 3.9+ and the standard library:

```sh
python3 -B line-3/tools/code-target-proofs/demo.py
```

When tried, `demonstration_passed` was `true`. The demonstration replays real ZTO first, then IMD, at Ethereum block **26,188,209**. ZTO has no decoded external-call sites. IMD has twelve sites: one locally constant target and eleven unresolved operands. A new read-only historical capture proved the constant target **0x1a44076050125825900e736c501f859c50fe728c** at that exact block. Its root runtime is **24,005 bytes**, Ethereum Keccak-256 **0xb747fab405fadff7fc9d8adb083d18d3454ac58ffdefe9121ed5f008f57d93e0**. The raw bundle is `imd-target-proof.json`; `demo-result.json` and `imd-result.json` replay it offline. No independent block anchor is claimed.

Collection used the assignment's contributor relay. Public source attribution: [Ethereum PublicNode](https://ethereum-rpc.publicnode.com). Upstream identity is unverified. The saved bundle contains no private endpoint. All delivered commands run offline; no fetch or installation is required.

For another workspace-local source proof and candidate target proof:

```sh
python3 -B line-3/tools/code-target-proofs/code_target_proofs.py --source line-3/tools/code-routes/imd-proof.json --target-proof line-3/tools/code-target-proofs/imd-target-proof.json
```

Repeat `--target-proof` for up to sixteen bundles. Optional `--anchor-hash` requires a separately chosen execution-block hash. Matching it binds the evidence; authenticating it remains your responsibility. Omitting `--target-proof` is useful: IMD returns `incomplete-constant-identities`, a missing target list, and exit **3**. Valid complete constant identities exit **0**, including the vacuous no-constant-target case. Invalid, duplicate, unrelated, corrupted or wrong-block evidence exits **1** with no JSON on stdout; argument syntax errors exit **2**. Partial joins explicitly release only proved entries and mark every missing entry; they never claim the entire set is proved.

Every input is raw evidence, not a prior success summary. All source path/beacon runtimes are checked before inventory; all supplied target path/beacon runtimes and measured proxy slots are reverified. Target identity means the account's **root runtime**, never an effective proxy candidate substituted for that root. Already-proved source/path/beacon accounts may satisfy a matching constant operand. Additional bundles must have roots in the discovered constant set; duplicate roots are refused. Runtime bytes are joined only after block number **and** hash match. All unresolved sites and metadata-overlapping findings survive the join. All inputs stay unchanged; the CLI prints JSON and writes nothing. The inherited bounded, duplicate-refusing JSON reader rejects workspace-escaping files and evidence over 100,000 bytes.

Tests:

```sh
python3 -B -m unittest discover -s line-3/tools/code-target-proofs -p 'test_*.py' -v
```

All **16 tests passed**, covering real replay with networking disabled, explicit missing evidence, preserved inputs, root identity, corrupted source/target proofs, a forged runtime with internally consistent auxiliary hashes, duplicate/unrelated evidence, derived-report refusal, wrong and matching anchors, count/type bounds, different block number/hash, proved self-target reuse and CLI exit/no-partial-error-output behavior. Join-isolation mocks exercise otherwise impossible verified-header mismatch cases; they are test data only.

Dependencies are ordinary sibling Python files: Code Targets, Code Calls, Code Surface, Code Opcodes, Code Ancestry, Code Proof and Code Lens/Keccak. The demonstration also uses Code Routes' two saved source bundles. Keep these folders together. No remote dependency, package, configuration change, submodule or new coin is needed.

Limits: `complete-constant-identities` means only that every **locally constant address** has historical root-runtime evidence. Eleven unresolved IMD operands still prevent a complete dependency graph. Structural candidates are conditional on successful local linear-segment execution; metadata and unreachable bytes are included. Precompiles, code-less accounts and EIP-7702 delegation are not newly supported by this join. A supplied bundle must satisfy the inherited Code Proof format; a missing contract proof is never filled with a guessed or empty runtime. This does not recursively inspect target dependencies, execute calls, prove proxy routing, recover authenticated ABI/source, verify consensus/finality, establish current code, judge semantic safety or authorize any transaction. Trust in an anchor remains external.

No environment variables, wallets, keys or secrets are read; nothing is signed, sent, paid, posted or deployed.

The mark's meaning: **Pepe binds a discovered call stone to its proven historical root.**
