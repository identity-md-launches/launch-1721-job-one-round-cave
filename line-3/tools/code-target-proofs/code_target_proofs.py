#!/usr/bin/env python3
"""Join structural external-call targets to same-block raw runtime proofs, offline."""
import argparse
import json
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS / 'code-targets'))
import code_targets as targets

calls = targets.calls
lens = calls.lens
require = lens.require


def evaluate(source, evidence, anchor_hash=None):
    """Never accept derived reports or treat proxy effective code as target root code."""
    require(isinstance(evidence, list) and len(evidence) <= 16,
            'provide at most 16 target proof bundles')
    inventory = targets.inspect(source, anchor_hash)
    block = inventory['code_block']
    required = {group['address'] for runtime in inventory['runtimes']
                for group in runtime['constant_targets']}
    proved = {}

    def add(bundle, verified):
        for node in bundle['observation']['nodes']:
            for item in (node, node.get('beacon')):
                if item is None:
                    continue
                address = lens.address(item['address'])
                raw = lens.code_bytes(item['code'])
                entry = {'address': address, 'code_hash': lens.digest(raw),
                         'runtime_bytes': len(raw)}
                require(address not in proved or proved[address] == entry,
                        'conflicting proven runtime')
                proved[address] = entry
        require(all(account['address'] in proved for account in verified['accounts']),
                'missing proven runtime bytes')

    add(source, inventory['proof'])
    seen = set()
    for bundle in evidence:
        verified = calls.proof.verify(bundle, anchor_hash)
        root = lens.address(verified['target'])
        require(root in required, 'unexpected target proof root')
        require(root not in seen, 'duplicate target proof root')
        seen.add(root)
        require(calls.ancestry.block_identity(verified['block']) == block,
                'target proof must match source block number and hash')
        add(bundle, verified)
    joined = []
    for runtime in inventory['runtimes']:
        for group in runtime['constant_targets']:
            entry = proved.get(group['address'])
            joined.append({'caller': runtime['address'], 'target': group['address'],
                           'call_site_count': group['call_site_count'],
                           'sites': group['sites'],
                           'status': 'same-block-runtime-proven' if entry else 'missing-proof',
                           'target_runtime': entry})
    missing = sorted(required - set(proved))
    unresolved = [{'caller': runtime['address'], 'sites': runtime['unresolved_sites']}
                  for runtime in inventory['runtimes'] if runtime['unresolved_sites']]
    return {'schema': 'code-target-proofs-result-v1', 'chain_id': 1,
            'source_target': inventory['target'], 'code_block': block,
            'decision': 'incomplete-constant-identities' if missing else 'complete-constant-identities',
            'constant_address_count': len(required), 'missing_targets': missing,
            'joined_targets': joined, 'unresolved_calls': unresolved,
            'source_proof': inventory['proof'],
            'anchor_authenticity_verified': False, 'reachability_verified': False,
            'dependency_completeness_verified': False, 'semantic_safety_verified': False,
            'scope': 'Raw state/header/runtime proofs at one historical block, joined to '
                     'locally constant decoded call operands. Root target bytes are identified, '
                     'not replaced by candidate proxy implementation bytes. Source-path and beacon '
                     'accounts may satisfy matching operands. Missing proofs remain explicit; '
                     'unresolved calls and metadata findings remain included. No recursive dependency '
                     'scan, execution, ABI/source equivalence, current code, consensus, finality, '
                     'anchor authenticity, safety or permission to transact is established.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--target-proof', action='append', default=[])
    parser.add_argument('--anchor-hash')
    args = parser.parse_args()
    try:
        require(len(args.target_proof) <= 16, 'too many target proof bundles')
        read = calls.ancestry.read_json
        result = evaluate(read(args.source), [read(path) for path in args.target_proof],
                          args.anchor_hash)
        print(json.dumps(result, indent=2))
        return 3 if result['missing_targets'] else 0
    except (ValueError, KeyError, TypeError, OSError, OverflowError, AttributeError,
            IndexError, RecursionError) as error:
        print('Code Target Proofs: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
