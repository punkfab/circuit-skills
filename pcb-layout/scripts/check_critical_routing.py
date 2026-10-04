#!/usr/bin/env python3
"""Policy-driven routing screening, not an impedance or signal-integrity solver.

Usage: python3 check_critical_routing.py board.kicad_pcb [--policy file] [--json]
Default policy: board.routing-policy.json. Missing policy is NOT a pass.
Requires KiCad pcbnew Python bindings. Never modifies the board or fills zones.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path


def assess(metrics, policy, board_sha):
    findings = []
    def issue(kind, message):
        findings.append({'kind': kind, 'message': message})
    if policy.get('version') != 1:
        raise ValueError('policy version must be 1')
    if not policy.get('groups'):
        raise ValueError('policy must contain at least one critical routing group')
    for group in policy['groups']:
        name = group['name']
        legs = group['legs']
        for key in ('max_vias', 'max_copper_mm', 'max_copper_mismatch_mm'):
            value = group.get(key)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value) or value < 0):
                raise ValueError(f'{name}: {key} must be finite and nonnegative')
        if not isinstance(legs, list) or not legs or any(not isinstance(leg,list) or not leg or any(not isinstance(n,str) or not n for n in leg) for leg in legs):
            raise ValueError(f'{name}: legs must contain nonempty net lists')
        totals = []
        for leg in legs:
            total = 0
            for net in leg:
                if net not in metrics:
                    issue('failure', f'{name}: net {net} absent')
                    continue
                m = metrics[net]
                total += m['copper_mm']
                if not m['segments']:
                    issue('failure', f'{name}: {net} has no routed track segments')
                if m['unsupported_items']:
                    issue('unresolved', f'{name}: {net} contains unsupported copper geometry')
                for key in ('allowed_layers', 'max_vias', 'max_copper_mm'):
                    if key not in group:
                        issue('unresolved', f'{name}: missing {key} policy')
                if 'allowed_layers' in group and set(m['layers']) - set(group['allowed_layers']):
                    issue('failure', f'{name}: {net} uses disallowed layers {m["layers"]}')
                if 'max_vias' in group and m['vias'] > group['max_vias']:
                    issue('failure', f'{name}: {net} has {m["vias"]} vias, limit {group["max_vias"]}')
                if 'max_copper_mm' in group and m['copper_mm'] > group['max_copper_mm']:
                    issue('failure', f'{name}: {net} copper {m["copper_mm"]:.3f} mm exceeds {group["max_copper_mm"]}')
                if m['reference_missing_samples']:
                    issue('failure', f'{name}: {net} lacks declared filled reference copper at {m["reference_missing_samples"]}/{m["reference_samples"]} sampled points')
            totals.append(total)
        if group.get('differential_pair'):
            if len(legs) != 2:
                raise ValueError(f'{name}: differential_pair requires two legs')
            if 'max_copper_mismatch_mm' not in group:
                issue('unresolved', f'{name}: missing copper mismatch budget')
            elif abs(totals[0]-totals[1]) > group['max_copper_mismatch_mm']:
                issue('failure', f'{name}: total-copper mismatch {abs(totals[0]-totals[1]):.3f} mm exceeds {group["max_copper_mismatch_mm"]}')
        # Human/solver reviews are bound to the exact geometry. A stale signoff
        # cannot silently survive a reroute. These are NOT computed approvals.
        if not group.get('required_reviews'):
            issue('unresolved', f'{name}: no engineering review requirements declared')
        for topic in group.get('required_reviews', []):
            review = policy.get('reviews', {}).get(topic, {})
            if not (review.get('board_sha256') == board_sha and review.get('reviewer') and review.get('evidence')):
                issue('unresolved', f'{name}: {topic} requires evidence and reviewer for current board SHA')
    return {'ok': not findings, 'findings': findings, 'metrics': metrics,
            'board_sha256': board_sha,
            'limitations': 'Copper totals include stubs/branches and exclude via barrel and pad delay. Reference samples check zone fill at centerline points only; they do not prove a continuous return path, coupling, impedance, or electrical connectivity. Run native DRC too.'}


def measure(board, policy):
    import pcbnew
    wanted = {net for g in policy['groups'] for leg in g['legs'] for net in leg}
    result = {}
    for net in board.GetNetsByNetcode().values():
        if net.GetNetname() in wanted:
            result[net.GetNetname()] = dict(copper_mm=0., segments=0, vias=0,
                layers=set(), unsupported_items=0, reference_samples=0,
                reference_missing_samples=0)
    refs = policy.get('reference_layers', {})
    step = float(policy.get('reference_sample_step_mm', 0.25))
    if not math.isfinite(step) or step <= 0 or step > 0.25:
        raise ValueError('reference_sample_step_mm must be in (0, 0.25]')
    zones = list(board.Zones())
    for track in board.GetTracks():
        name = track.GetNetname()
        if name not in result:
            continue
        m = result[name]
        if isinstance(track, pcbnew.PCB_VIA):
            m['vias'] += 1
            continue
        if type(track) is not pcbnew.PCB_TRACK:
            m['unsupported_items'] += 1
            continue
        layer = board.GetLayerName(track.GetLayer())
        m['layers'].add(layer)
        length = pcbnew.ToMM(track.GetLength())
        m['copper_mm'] += length
        m['segments'] += 1
        ref = refs.get(layer)
        candidates = [z for z in zones if ref and board.GetLayerName(z.GetLayer()) == ref['layer'] and z.GetNetname() == ref['net'] and not z.GetIsRuleArea()]
        a, b = track.GetStart(), track.GetEnd()
        count = max(1, math.ceil(length/step))
        for i in range(count+1):
            point = pcbnew.VECTOR2I(round(a.x+(b.x-a.x)*i/count), round(a.y+(b.y-a.y)*i/count))
            m['reference_samples'] += 1
            if not any(z.HitTestFilledArea(z.GetLayer(), point) for z in candidates):
                m['reference_missing_samples'] += 1
    for m in result.values():
        m['layers'] = sorted(m['layers'])
        m['copper_mm'] = round(m['copper_mm'], 6)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('board', type=Path)
    ap.add_argument('--policy', type=Path)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    try:
        policy_path = args.policy or args.board.with_suffix('.routing-policy.json')
        policy = json.loads(policy_path.read_text())
        assess({}, policy, '')  # validate policy before reading geometry
        # Use the interpreter shipped with KiCad. Injecting another Python's
        # binary bindings into sys.path can crash, rather than raise ImportError.
        import pcbnew
        board = pcbnew.LoadBoard(str(args.board))
        report = assess(measure(board, policy), policy, hashlib.sha256(args.board.read_bytes()).hexdigest())
    except Exception as exc:
        print(f'critical routing: UNRESOLVED: {exc}', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f'critical routing: {"PASS" if report["ok"] else "NOT RELEASE READY"}')
        for f in report['findings']:
            print(f'  {f["kind"].upper()}: {f["message"]}')
        print(report['limitations'])
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
