#!/usr/bin/env python3
"""Compare two exact runtime-code reports without treating missing rows as revocations."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIMIT = 98_304
ADDRESS = re.compile(r"^0x[0-9a-f]{40}$")
HASH = re.compile(r"^0x[0-9a-f]{64}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    candidate = Path(path).resolve()
    root = Path.cwd().resolve()
    require(candidate.is_relative_to(root), "input must stay inside the workspace")
    with candidate.open("rb") as stream:
        raw = stream.read(LIMIT + 1)
    require(len(raw) <= LIMIT, "input exceeds 96 KiB")
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("input is not valid JSON") from exc
    return validate(value)


def validate(value):
    require(isinstance(value, dict), "report must be an object")
    require(value.get("schema") == "active-allowance-spender-code-v1",
            "wrong spender-code report schema")
    require(value.get("chain_id") == 1, "only Ethereum chain 1 is supported")
    require(isinstance(value.get("token"), str) and value["token"], "token is required")
    require(isinstance(value.get("token_address"), str)
            and ADDRESS.fullmatch(value["token_address"]), "invalid token address")
    require(type(value.get("block_number")) is int and value["block_number"] >= 0,
            "invalid block number")
    require(isinstance(value.get("block_hash"), str) and HASH.fullmatch(value["block_hash"]),
            "invalid block hash")
    rows = value.get("spenders")
    require(isinstance(rows, list) and len(rows) <= 64, "spenders must be a list of at most 64 rows")
    normalized = {}
    for row in rows:
        require(isinstance(row, dict), "spender row must be an object")
        spender = row.get("spender")
        require(isinstance(spender, str) and ADDRESS.fullmatch(spender), "invalid spender address")
        require(spender not in normalized, "duplicate spender row")
        require(row.get("block_hash") == value["block_hash"], "row is not pinned to report block")
        code_bytes = row.get("runtime_code_bytes")
        require(type(code_bytes) is int and code_bytes >= 0, "invalid runtime code length")
        digest = row.get("runtime_code_sha256")
        require(isinstance(digest, str) and SHA256.fullmatch(digest), "invalid runtime code hash")
        expected = "runtime_code_present" if code_bytes else "no_runtime_code_at_block"
        require(row.get("classification") == expected, "classification disagrees with code length")
        normalized[spender] = {"bytes": code_bytes, "sha256": digest}
    return {
        "chain_id": 1,
        "token": value["token"],
        "token_address": value["token_address"],
        "block_number": value["block_number"],
        "block_hash": value["block_hash"],
        "spenders": normalized,
    }


def compare(before, after):
    for key in ("chain_id", "token", "token_address"):
        require(before[key] == after[key], f"reports disagree on {key}")
    require(after["block_number"] >= before["block_number"],
            "after report predates before report")
    if after["block_number"] == before["block_number"]:
        require(after["block_hash"] == before["block_hash"], "same-height block conflict")
    rows = []
    for spender in sorted(set(before["spenders"]) | set(after["spenders"])):
        old, new = before["spenders"].get(spender), after["spenders"].get(spender)
        if old is None:
            change = "appeared_in_after_report"
        elif new is None:
            change = "not_rechecked"
        elif old == new:
            change = "unchanged"
        elif old["bytes"] and not new["bytes"]:
            change = "code_became_empty"
        elif not old["bytes"] and new["bytes"]:
            change = "code_appeared"
        else:
            change = "code_hash_changed"
        rows.append({"spender": spender, "change": change, "before": old, "after": new})
    return {
        "schema": "allowance-spender-code-delta-v1",
        "chain_id": 1,
        "token": before["token"],
        "token_address": before["token_address"],
        "before": {"block_number": before["block_number"], "block_hash": before["block_hash"]},
        "after": {"block_number": after["block_number"], "block_hash": after["block_hash"]},
        "counts": {change: sum(row["change"] == change for row in rows)
                   for change in sorted({row["change"] for row in rows})},
        "spenders": rows,
        "limitations": [
            "A missing spender is not a revocation; it was not rechecked in the after report.",
            "Runtime code hashes describe bytes only, not controller, proxy target or behavior.",
            "Reports cover only active standard ERC-20 spenders already discovered by the caller.",
            "RPC reports are trusted observations, not proofs of chain state or transaction safety.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, help="earlier spender-code report")
    parser.add_argument("--after", required=True, help="later spender-code report")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(compare(load(args.before), load(args.after)), indent=2))
        return 0
    except (OSError, TypeError, ValueError, OverflowError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
