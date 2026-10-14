#!/usr/bin/env python3
"""Summarize one saved call only after proof, block, selector and ABI checks."""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SURFACE = HERE.parent / 'surface-return'
sys.path.insert(0, str(SURFACE))
import surface_call


def report(bundle, observation, signature, return_types, anchor_hash=None):
    """Keep the small Line 4 report shape, gated by shared Line 3/4 evidence checks."""
    joined = surface_call.evaluate(bundle, observation, signature, return_types, anchor_hash)
    aligned = joined['verdict'] == 'aligned'
    call = joined['call']
    block = joined['call_block']
    return {
        'schema': 'proof-backed-rehearsal-report-v1',
        'status': 'ready-to-review' if aligned else 'withheld',
        'reason': ('historical call, candidate selector, exact block and runtime proof align'
                   if aligned else 'one or more evidence checks failed'),
        'failed_checks': joined['failed_checks'],
        'chain_id': joined['chain_id'],
        'block': block['number'],
        'block_hash': block['hash'],
        'target': joined['target'],
        'calldata': call['data'],
        'native_value': call['value'],
        'signature': signature,
        'source': joined['source'],
        'outcome': 'return' if aligned else 'withheld',
        'return_bytes': observation['outcome']['result'] if aligned else None,
        'decoded_arguments': joined['decoded_arguments'] if aligned else None,
        'decoded_values': joined['decoded_values'] if aligned else None,
        'proof_anchor': joined['proof_anchor'],
        'input_sha256': joined['input_sha256'],
        'limits': ('The ABI signature and return layout are reviewer assertions. Historical RPC '
                   'returns are not locally executed or proved; the supplied header is not '
                   'independently authenticated. Selector presence does not prove reachability, '
                   'and this report gives no freshness, state-effect, authority or future-execution guarantee.'),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--bundle')
    parser.add_argument('--observation')
    parser.add_argument('--signature')
    parser.add_argument('--types', help='comma-separated flat ABI return types')
    parser.add_argument('--anchor-hash', help='optional independently obtained block hash')
    args = parser.parse_args(argv)
    try:
        explicit = [args.bundle, args.observation, args.signature, args.types]
        surface_call.context.surface.require(
            (args.demo and not any(explicit) and not args.anchor_hash)
            or (not args.demo and all(explicit)),
            'choose --demo or all four explicit inputs')
        if args.demo:
            bundle_path = SURFACE / 'zto-proof.json'
            observation_path = SURFACE / 'zto-call.json'
            signature, return_types = 'totalSupply()', ['uint256']
        else:
            bundle_path, observation_path = args.bundle, args.observation
            signature, return_types = args.signature, args.types.split(',')
        bundle = surface_call.context.surface.ancestry.read_json(bundle_path)
        observation = surface_call.calldata.load(observation_path)
        result = report(bundle, observation, signature, return_types, args.anchor_hash)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if result['status'] == 'ready-to-review' else 2
    except (ValueError, KeyError, TypeError, OSError, OverflowError, AttributeError,
            IndexError, RecursionError) as error:
        print(json.dumps({'schema': 'proof-backed-rehearsal-report-v1',
                          'status': 'invalid', 'error': str(error)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
