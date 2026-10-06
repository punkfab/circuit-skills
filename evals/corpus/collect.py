#!/usr/bin/env python3
"""collect.py — build a corpus of real, openly licensed KiCad boards from GitHub.

PCBench (the boards behind PCBWorld D3) is KiCad 5 files with no project file, so their rules are
KiCad's defaults. This collects current designs with their own rules:

  1. search    GitHub repositories under an open-hardware or permissive licence (gh api),
  2. pick      .kicad_pcb files that have a .kicad_pro beside them (at most --per-repo per repository),
  3. fetch     board, project and custom rules at a pinned commit into the cache (never into the repo),
  4. qualify   with stock KiCad: it opens, is routed, 1-4 copper layers, enough parts, and the
               designer's own routing has no open connection (so "fully routed" is reachable),
  5. write     manifest.json (source, commit, licence, stats per board) and splits.json.

  python3 evals/corpus/collect.py search            # -> candidates.json (needs gh, logged in)
  python3 evals/corpus/collect.py fetch [--limit N] # -> cache + manifest.json + splits.json
  python3 evals/corpus/collect.py fetch --from-manifest   # rebuild the cache from the committed manifest

The cache is laid out like PCBWorld's prepared D3 set, so the same harness runs it:

  python3 evals/pcbworld/run_d3.py --data ~/.cache/circuit-skills/corpus/boards \
      --splits evals/corpus/splits.json --split d3a --run corpus-easy-v1

Boards are downloaded, not redistributed: each keeps its own licence, recorded in the manifest.
"""
import argparse, base64, collections, json, os, re, subprocess, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent.parent / 'pcb-layout' / 'scripts'
CACHE = Path(os.getenv('CIRCUIT_SKILLS_CACHE', Path.home() / '.cache/circuit-skills')) / 'corpus'
STEM = 'processed_v9_guide_v3'  # the file stem run_d3.py expects
LICENCES = ['mit', 'apache-2.0', 'bsd-3-clause', 'cc0-1.0', 'cc-by-4.0', 'cc-by-sa-4.0', 'cern-ohl-p-2.0', 'cern-ohl-w-2.0', 'cern-ohl-s-2.0', 'gpl-3.0']
QUERIES = ['topic:kicad stars:>=10', 'topic:kicad-pcb stars:>=5', 'topic:oshw stars:>=10', 'topic:open-hardware kicad in:readme stars:>=20',
           'language:"KiCad Layout" stars:>=5']
SKIP = re.compile(r'(^|/)(lib|libs|library|libraries|template|templates|panel|panels|panelized|backup|backups|archive|old|test|tests|example|examples|fixture|fixtures|qa|benchmark|benchmarks|\.history)(/|$)|-backups?/|_autosave|panel', re.I)
TIERS = (('easy', 40), ('medium', 150), ('hard', 10 ** 9))  # by connections to route


def gh(*args):
    r = subprocess.run(['gh', 'api', *args], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[:200])
    return json.loads(r.stdout)


def search(a):
    repos = {}
    for q in QUERIES:
        for lic in LICENCES:
            for page in (1, 2, 3):
                try:
                    res = gh('-X', 'GET', 'search/repositories', '-f', f'q={q} license:{lic} pushed:>={a.since} fork:false', '-f', 'per_page=100', '-f', f'page={page}', '-f', 'sort=stars')
                except RuntimeError as e:
                    print(f'  ({q} {lic}: {e})')
                    break
                for r in res['items']:
                    repos[r['full_name']] = {'repo': r['full_name'], 'stars': r['stargazers_count'], 'licence': r['license']['spdx_id'], 'branch': r['default_branch'], 'description': r['description']}
                time.sleep(2.2)  # the search API allows 30 requests a minute
                if len(res['items']) < 100:
                    break
        print(f'{q}: {len(repos)} repositories so far', flush=True)
    out = sorted(repos.values(), key=lambda r: -r['stars'])
    (HERE / 'candidates.json').write_text(json.dumps(out, indent=1) + '\n')
    print(f'{len(out)} candidate repositories -> {HERE / "candidates.json"}')


def boards_in(repo):
    """(.kicad_pcb path, sibling paths, commit) for boards that have a project file beside them."""
    tree = gh(f'repos/{repo["repo"]}/git/trees/{repo["branch"]}?recursive=1')
    paths = {t['path']: t for t in tree['tree'] if t['type'] == 'blob'}
    found = []
    for p, t in paths.items():
        if not p.endswith('.kicad_pcb') or SKIP.search(p) or t.get('size', 0) > 15_000_000 or t.get('size', 0) < 20_000:
            continue
        base = p[:-len('.kicad_pcb')]
        if base + '.kicad_pro' in paths:
            found.append({'path': p, 'size': t['size'], 'blob': t['sha'], 'extras': [base + e for e in ('.kicad_pro', '.kicad_dru') if base + e in paths]})
    found.sort(key=lambda f: (f['path'].count('/'), -f['size']))
    return found, tree['sha']


def raw(repo, sha, path):
    url = f'https://raw.githubusercontent.com/{repo}/{sha}/' + urllib.request.quote(path)
    return urllib.request.urlopen(url, timeout=60).read()


QUALIFY = r'''
import json, sys
sys.path.insert(0, '/usr/lib/python3/dist-packages')
import pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
fps = list(b.GetFootprints())
tracks = list(b.GetTracks())
bb = b.GetBoardEdgesBoundingBox()
print(json.dumps({'copper_layers': b.GetCopperLayerCount(), 'footprints': len(fps),
    'parts': sum(1 for f in fps if any(p.GetNetCode() > 0 for p in f.Pads())),
    'pads': sum(1 for f in fps for p in f.Pads() if p.GetNetCode() > 0),
    'segments': sum(1 for t in tracks if t.GetClass() != 'PCB_VIA'), 'vias': sum(1 for t in tracks if t.GetClass() == 'PCB_VIA'),
    'zones': len(b.Zones()), 'width_mm': round(pcbnew.ToMM(bb.GetWidth()), 1), 'height_mm': round(pcbnew.ToMM(bb.GetHeight()), 1)}))
'''


def drc(board):
    out = board.with_suffix('.drc.json')
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--format', 'json', '--severity-error', '--units', 'mm', '-o', str(out), str(board)], capture_output=True, timeout=600)
    d = json.loads(out.read_text())
    out.unlink()
    return len(d.get('violations', [])), len(d.get('unconnected_items', []))


def qualify(folder, a):
    """Stats and a reason to reject (None = keep). Writes the unrouted board beside the routed one."""
    ref = folder / f'{STEM}.kicad_pcb'
    r = subprocess.run(['/usr/bin/python3', '-c', QUALIFY, str(ref)], capture_output=True, text=True, timeout=300)
    if r.returncode or not r.stdout.strip():
        return {}, 'KiCad cannot open it (newer file format, or broken)'
    st = json.loads(r.stdout.strip().splitlines()[-1])
    if not 1 <= st['copper_layers'] <= a.max_layers:
        return st, f"{st['copper_layers']} copper layers"
    if st['parts'] < a.min_parts or st['segments'] < 10:
        return st, 'too few parts, or not routed'
    st['ref_drv'], st['ref_open'] = drc(ref)
    if st['ref_open']:
        return st, f"the designer's routing leaves {st['ref_open']} connections open"
    sys.path.insert(0, str(SCRIPTS))
    from route_kicad_dsn import strip_routing
    bare = folder / f'{STEM}_unrouted.kicad_pcb'
    bare.write_text(strip_routing(ref.read_text()))
    for ext in ('.kicad_pro', '.kicad_dru'):
        if ref.with_suffix(ext).exists():
            bare.with_suffix(ext).write_bytes(ref.with_suffix(ext).read_bytes())
    st['bare_drv'], st['connections'] = drc(bare)
    for f in folder.glob(f'{STEM}_unrouted.kicad_*'):
        if f.suffix != '.kicad_pcb':
            f.unlink()  # run_d3 pairs both boards with the one project file
    if st['connections'] < 5:
        return st, 'fewer than 5 connections to route'
    return st, None


def fetch(a):
    boards_dir = CACHE / 'boards'
    manifest_path = HERE / 'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'boards': [], 'rejected': []}
    if a.from_manifest:
        work = [({'repo': b['repo'], 'licence': b['licence'], 'stars': b['stars']}, [b], b['commit']) for b in manifest['boards']]
        manifest = {'boards': [], 'rejected': []}
    else:
        seen = {b['repo'] for b in manifest['boards']} | {b['repo'] for b in manifest['rejected']}
        work = [(r, None, None) for r in json.loads((HERE / 'candidates.json').read_text()) if r['repo'] not in seen]
    blobs = {b.get('blob') for b in manifest['boards']}
    ids = set() if a.from_manifest else {b['id'] for b in manifest['boards']}
    for repo, picks, commit in work:
        if a.limit and len(manifest['boards']) >= a.limit:
            break
        try:
            if picks is None:
                picks, commit = boards_in(repo)
        except RuntimeError as e:
            manifest['rejected'].append({'repo': repo['repo'], 'why': f'tree: {e}'})
            continue
        if not picks:
            manifest['rejected'].append({'repo': repo['repo'], 'why': 'no .kicad_pcb with a .kicad_pro beside it'})
        kept = 0
        for pk in picks:
            if kept >= a.per_repo or pk.get('blob') in blobs:
                continue
            bid = pk.get('id') or re.sub(r'[^A-Za-z0-9._-]+', '_', f"{repo['repo'].replace('/', '__')}__{Path(pk['path']).stem}")[:110]
            if bid in ids:  # the same file name twice in one repository
                bid += '_' + pk['blob'][:6]
            ids.add(bid)
            folder = boards_dir / bid
            folder.mkdir(parents=True, exist_ok=True)
            try:
                (folder / f'{STEM}.kicad_pcb').write_bytes(raw(repo['repo'], commit, pk['path']))
                for e in pk['extras']:
                    (folder / (STEM + Path(e).suffix)).write_bytes(raw(repo['repo'], commit, e))
                st, why = qualify(folder, a)
            except Exception as e:  # one bad board must not stop the collection
                st, why = {}, f'{type(e).__name__}: {e}'[:160]
            entry = {'id': bid, 'repo': repo['repo'], 'commit': commit, 'path': pk['path'], 'extras': pk['extras'], 'blob': pk.get('blob'),
                     'licence': repo['licence'], 'stars': repo['stars'], **st}
            if why:
                manifest['rejected'].append({**entry, 'why': why})
                for f in folder.iterdir():
                    f.unlink()
                folder.rmdir()
            else:
                manifest['boards'].append(entry)
                blobs.add(pk.get('blob'))
                kept += 1
            print(f"  {'keep  ' if not why else 'reject'} {bid[:70]:70s} {why or str(st['connections']) + ' connections, ' + str(st['copper_layers']) + ' layers'}", flush=True)
            manifest_path.write_text(json.dumps(manifest, indent=1) + '\n')
    splits = {t: {'train': [], 'test': []} for t, _ in TIERS}
    for b in manifest['boards']:
        tier = next(t for t, top in TIERS if b['connections'] < top)
        splits[tier]['test'].append(b['id'])
        splits[tier]['train'].append(b['id'])
    (HERE / 'splits.json').write_text(json.dumps(splits, indent=1) + '\n')
    manifest_path.write_text(json.dumps(manifest, indent=1) + '\n')
    why = collections.Counter(re.sub(r'\d+', 'N', r['why'])[:60] for r in manifest['rejected'])
    print(f"\n{len(manifest['boards'])} boards kept ({', '.join(f'{t} {len(v[chr(116) + 'est'])}' for t, v in splits.items())}); "
          f"{len(manifest['rejected'])} rejected: " + '; '.join(f'{n} {w}' for w, n in why.most_common(6)))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('step', choices=['search', 'fetch'])
    p.add_argument('--since', default='2023-01-01', help='search: repositories pushed since')
    p.add_argument('--limit', type=int, help='fetch: stop once this many boards are kept')
    p.add_argument('--per-repo', type=int, default=2)
    p.add_argument('--max-layers', type=int, default=4)
    p.add_argument('--min-parts', type=int, default=5)
    p.add_argument('--from-manifest', action='store_true')
    a = p.parse_args()
    (search if a.step == 'search' else fetch)(a)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
