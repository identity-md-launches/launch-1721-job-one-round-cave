#!/usr/bin/env python3
"""Print a bounded, human-readable summary of saved call-rehearsal evidence."""
import argparse
import json
from pathlib import Path


def report(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"schema", "source", "chain_id", "block", "call", "outcome"}
    missing = sorted(required - set(value))
    if missing:
        raise ValueError("missing fields: " + ", ".join(missing))
    if value["schema"] != "call-rehearsal-v1":
        raise ValueError("unsupported rehearsal schema")
    block = value["block"]
    call = value["call"]
    outcome = value["outcome"]
    result = outcome.get("result")
    revert = outcome.get("revert")
    if result is not None and revert is not None:
        raise ValueError("outcome cannot contain both result and revert")
    status = "ready-to-review" if result is not None and value.get("code_present") is True else "withheld"
    reason = ("successful return bytes and contract code were recorded" if status == "ready-to-review"
              else "return evidence, code presence, or execution outcome is incomplete")
    return {
        "status": status,
        "reason": reason,
        "chain_id": value["chain_id"],
        "block": block["number"],
        "block_hash": block["hash"],
        "target": call["to"],
        "calldata": call["data"],
        "native_value": call.get("value", "0x0"),
        "outcome": "return" if result is not None else "revert" if revert is not None else "missing",
        "return_bytes": result,
        "source": value["source"],
        "limits": "This summarizes evidence only; it does not authenticate ABI meaning, gas, state effects, or future execution, and never signs or sends."
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("observation", nargs="?", default=str(Path(__file__).parent.parent / "return-lens" / "zto-live-observation.json"))
    args = parser.parse_args()
    print(json.dumps(report(args.observation), indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit("rehearsal-report: " + str(exc))
