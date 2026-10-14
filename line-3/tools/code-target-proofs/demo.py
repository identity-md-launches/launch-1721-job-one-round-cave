"""Replay real ZTO-first, then IMD external-target proof evidence, without networking."""
import json
from pathlib import Path
import code_target_proofs as tool

FOLDER = Path(__file__).resolve().parent


def main():
    read = tool.calls.ancestry.read_json
    results = []
    for token in ('zto', 'imd'):
        source = read(FOLDER.parent / 'code-routes' / (token + '-proof.json'))
        evidence = [] if token == 'zto' else [read(FOLDER / 'imd-target-proof.json')]
        result = tool.evaluate(source, evidence)
        results.append({'token': token.upper(), 'result': result})
    zto, imd = [item['result'] for item in results]
    passed = (zto['constant_address_count'] == 0 and not zto['unresolved_calls']
              and imd['constant_address_count'] == 1 and not imd['missing_targets']
              and imd['joined_targets'][0]['target_runtime']['runtime_bytes'] == 24005
              and len(imd['unresolved_calls'][0]['sites']) == 11
              and all(r['decision'] == 'complete-constant-identities' for r in (zto, imd)))
    return {'demonstration_passed': passed, 'results': results,
            'note': 'Source proofs are inherited historical observations; the IMD target proof '
                    'was newly collected at that same historical block. No independent anchor claimed.'}


if __name__ == '__main__':
    result = main()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['demonstration_passed'] else 1)
