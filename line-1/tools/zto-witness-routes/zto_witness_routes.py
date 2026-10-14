#!/usr/bin/env python3
"""Pinned, read-only ZTO witness collection with explicit archive fallback."""
import argparse
import json
from pathlib import Path
import re
import sys
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'zto-witness'))
import zto_witness as witness

path = witness.path
ERRORS = (ValueError, KeyError, TypeError, AttributeError, OSError, OverflowError)
DEFAULT_RPCS = (path.z.PUBLIC_RPC, 'https://eth.drpc.org')


def failure_kind(exc):
    """Diagnostics only: an unavailable read never becomes a quote mismatch."""
    text = str(exc).lower()
    if any(s in text for s in ('pruned', 'history unavailable', 'historical state unavailable',
                               'missing trie', 'archive state unavailable', 'archive required')):
        return 'history_unavailable'
    if isinstance(exc, urllib.error.HTTPError):
        return 'http_' + str(exc.code)
    if isinstance(exc, OSError):
        return 'transport_unavailable'
    if text.startswith('rpc error:'):
        return 'rpc_unavailable'
    return 'invalid_evidence'


def block_header(block):
    path.z.require(isinstance(block, dict), 'block unavailable')
    pin = {key: block[key] for key in ('number', 'hash', 'timestamp')}
    path.z.require(isinstance(pin['number'], str) and
                   re.fullmatch(r'0x[0-9a-f]+', pin['number']) is not None and
                   int(pin['number'], 16) >= path.z.INIT_BLOCK, 'invalid block number')
    path.z.require(isinstance(pin['hash'], str) and
                   re.fullmatch(r'0x[0-9a-f]{64}', pin['hash']) is not None,
                   'invalid block hash')
    path.z.require(isinstance(pin['timestamp'], str) and
                   re.fullmatch(r'0x[0-9a-f]+', pin['timestamp']) is not None and
                   int(pin['timestamp'], 16) > 0, 'invalid block timestamp')
    return pin


def result(pin, attempts, status, decision=None, mode='live_read_only'):
    return {
        'schema': 'zto-witness-routes-report-v1', 'mode': mode,
        'chain_id': 1, 'pool_id': path.z.POOL, 'block': pin,
        'status': status, 'attempts': attempts,
        'bound_released': bool(decision and decision['bound_released']),
        'bound': decision['bound'] if decision else None,
        'witness': decision,
        'invariant': 'One block pin; each selected source supplies its whole capture and quoter check.',
        'limitations': [
            'Endpoint labels do not prove independent providers or authenticated state.',
            'Fallback handles unavailable reads, never searches for a preferred agreeing quote.',
            'A planning minimum is not enforced by a router; no signing or sending is supported.',
            'No settlement, transfer behavior, gas, MEV, future liquidity or freshness guarantee.',
        ],
    }


def collect(endpoints, tag='finalized', radius=0, token='ZTO', amount='1', slippage=100,
            rpc_factory=None, capture=None, compare=None):
    """Each endpoint is tried at most once per phase. Never re-pin after resolution."""
    endpoints = tuple(endpoints)
    path.z.require(1 <= len(endpoints) <= 8, 'supply one to eight endpoints')
    path.z.require(len(set(endpoints)) == len(endpoints), 'duplicate endpoint URLs')
    for endpoint in endpoints:
        path.z.validate_endpoint(endpoint)
    path.z.require(tag in ('finalized', 'safe', 'latest') or
                   (isinstance(tag, str) and re.fullmatch(r'0x[0-9a-f]+', tag)),
                   'invalid block tag')
    path.z.require(type(radius) is int and 0 <= radius <= 4, 'word radius must be 0..4')
    path.z.require(token in ('ZTO', 'IMD'), 'input must be ZTO or IMD')
    path.z.require(type(slippage) is int and 0 <= slippage <= 9999, 'slippage bps must be 0..9999')
    # Validate syntax before opening the network; observed decimals validate precision later.
    path.z.parse_amount(amount, 36)
    rpc_factory = rpc_factory or path.z.RPC
    capture = capture or path.capture
    compare = compare or path.compare
    attempts, pin, anchor = [], None, None
    for index, endpoint in enumerate(endpoints):
        try:
            rpc = rpc_factory(endpoint)
            path.z.require(rpc.call('eth_chainId', []) == '0x1', 'expected Ethereum chain 1')
            pin = block_header(rpc.call('eth_getBlockByNumber', [tag, False]))
            anchor = index
            attempts.append({'source': endpoint, 'stage': 'resolve_block', 'status': 'pinned'})
            break
        except ERRORS as exc:
            attempts.append({'source': endpoint, 'stage': 'resolve_block',
                             'status': failure_kind(exc), 'error': str(exc)[:500]})
    if pin is None:
        return result(None, attempts, 'unavailable')

    selected = []
    for endpoint in endpoints[anchor:]:
        stage = 'capture'
        try:
            observation = capture(endpoint, pin['number'], radius)
            path.decode(observation)
            path.z.require(observation['base']['source'] == endpoint, 'capture source mismatch')
            if observation['base']['block'] != pin:
                attempts.append({'source': endpoint, 'stage': stage, 'status': 'block_disagreement'})
                return result(pin, attempts, 'withheld')
            local = path.quote(observation, token, amount)
            if local['status'] != 'estimated' or int(local['estimate']['output_raw']) <= 0:
                attempts.append({'source': endpoint, 'stage': 'local_quote',
                                 'status': 'incomplete_or_zero_output', 'quote_status': local['status']})
                return result(pin, attempts, 'withheld')
            # Stop on state disagreement before looking at quoter returns or later sources.
            if selected and not witness.compare_snapshots(selected[0][0], observation)[
                    'same_pool_state_and_coverage']:
                attempts.append({'source': endpoint, 'stage': stage, 'status': 'state_disagreement'})
                return result(pin, attempts, 'withheld')
            stage = 'quoter'
            check = compare(observation, endpoint, [(token, amount)])
            path.z.require(check['source'] == endpoint and check['quoter'] == path.QUOTER,
                           'quoter source or contract mismatch')
            _, matches = witness._quoter_output(check, observation, token, amount,
                                                local['estimate']['output_raw'])
            if not matches:
                attempts.append({'source': endpoint, 'stage': stage, 'status': 'quote_mismatch'})
                return result(pin, attempts, 'withheld')
            selected.append((observation, check))
            attempts.append({'source': endpoint, 'stage': 'capture_and_quoter', 'status': 'complete'})
            if len(selected) == 2:
                decision = witness.corroborate(selected[0][0], selected[1][0],
                                               selected[0][1], selected[1][1], token, amount, slippage)
                return result(pin, attempts, decision['status'], decision)
        except ERRORS as exc:
            kind = failure_kind(exc)
            attempts.append({'source': endpoint, 'stage': stage,
                             'status': kind, 'error': str(exc)[:500]})
            # Only availability permits fallback. Invalid data cannot be voted away.
            if kind == 'invalid_evidence':
                return result(pin, attempts, 'withheld')
    return result(pin, attempts, 'insufficient_sources' if selected else 'unavailable')


def demo():
    """Real historical evidence; unavailable archive is an explicitly simulated fault."""
    observation = path.read_json(str(witness.FIXTURE))
    evidence = path.read_json(str(witness.FIXTURE.parent / 'quoter-check.json'))
    source = observation['base']['source']
    case = next(r for r in evidence['results'] if r['input_token'] == 'ZTO' and r['amount'] == '1')
    check = dict(evidence, results=[case], all_match=case['matches'])
    first = 'https://archive-unavailable.example'

    class ReplayRPC:
        def __init__(self, endpoint):
            self.endpoint = endpoint
        def call(self, method, params):
            if self.endpoint == first:
                raise ValueError('RPC error: {"code":4444,"message":"pruned history unavailable"}')
            return '0x1' if method == 'eth_chainId' else observation['base']['block']

    report = collect([first, source], observation['base']['block']['number'],
                     observation['word_radius'], rpc_factory=ReplayRPC,
                     capture=lambda *args: observation, compare=lambda *args: check)
    report['mode'] = 'offline_historical_fixture_with_simulated_archive_failure'
    report['limitations'].append('The .example failure is simulated; only one real archived source is available.')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--demo', action='store_true')
    mode.add_argument('--live', action='store_true')
    parser.add_argument('--rpc', action='append', help='ordered HTTPS endpoints or explicit loopback relay')
    parser.add_argument('--block', default='finalized')
    parser.add_argument('--word-radius', type=int, default=0)
    parser.add_argument('--input', choices=('ZTO', 'IMD'), default='ZTO')
    parser.add_argument('--amount', default='1')
    parser.add_argument('--slippage-bps', type=int, default=100)
    args = parser.parse_args(argv)
    try:
        if args.demo:
            path.z.require(args.rpc is None, '--rpc requires --live')
            report = demo()
        else:
            tag = args.block if args.block in ('finalized', 'safe', 'latest') else hex(int(args.block))
            report = collect(args.rpc or DEFAULT_RPCS, tag, args.word_radius, args.input,
                             args.amount, args.slippage_bps)
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0 if args.demo or report['bound_released'] else 2
    except ERRORS as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
