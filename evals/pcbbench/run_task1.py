#!/usr/bin/env python3
"""run_task1.py — PCB-Bench Task 1 (text multiple choice) with and without the circuit-skills skill.

PCB-Bench (Li et al., ICLR 2026, github.com/digailab/PCB-Bench) asks 1,848 expert-written
multiple-choice questions on PCB placement and routing practice (signal integrity, EMI, power
planning, differential pairs, DFM, ...), each with five options. It measures what a model knows,
not whether it can produce a board, so for circuit-skills the question is narrower: does loading
the pcb-layout skill change what the model answers? Two conditions, same model, same questions:

  baseline   the paper's own English system prompt
  skill      the same prompt + pcb-layout/SKILL.md, as the agent would have it loaded

Calls go through `claude -p --safe-mode` (no CLAUDE.md, memory, hooks, plugins or MCP; no tools),
so the baseline is the bare model. Questions are sent in batches (default 25 per call) and the
model replies with a JSON object of letters; the paper sends one question per call.

  python3 evals/pcbbench/run_task1.py --data <PCB-Bench clone> [--conditions baseline,skill]
          [--model claude-opus-5-5] [--batch 25] [--jobs 4] [--limit N] [--run NAME]
  python3 evals/pcbbench/run_task1.py --summarize <run>

Results: evals/pcbbench/results/<run>/{answers.jsonl, meta.json, summary.md}. A run resumes.
"""
import argparse, concurrent.futures as cf, datetime, json, re, subprocess, sys, threading
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent.parent / 'pcb-layout' / 'SKILL.md'
SCQ = 'Task1-Text-Text-QA_evaluation/data/processed/scq'

# The paper's English system prompt for choice questions (Task1 config.yaml), adapted to a batch.
PROMPT = """You are a professional PCB design and electronic engineering expert with extensive knowledge in circuit design, PCB layout, signal integrity analysis, and related areas.

Please answer the following PCB-related multiple-choice questions based on your expertise. For each question:
1.Carefully analyze the question and each option.
2.Apply your PCB design knowledge for reasoning.
3.Choose the most accurate answer.
4.Only provide the letter of the option (A, B, C, D, or E), no explanation is needed.

Please remain professional and accurate.

You will receive several numbered questions. Reply with only a JSON object mapping each question id to its letter, e.g. {"q1": "B", "q2": "E"}."""

SKILL_HEADER = "\n\nYou have the following skill loaded. Use it where it applies:\n\n<skill name=\"pcb-layout\">\n"

# PCB-Bench Table 2 (CQ accuracy %, zero-shot, one question per call): placement macro/micro, routing macro/micro.
PAPER = {'GPT-4o': (92.74, 93.82, 98.32, 91.13), 'GPT-5': (88.27, 91.79, 99.16, 90.17), 'Claude-Opus-4.1': (93.30, 94.35, 99.16, 92.32),
         'Gemini-2.5-Pro': (86.03, 90.82, 98.31, 88.73), 'DeepSeek-V3.1-671B': (92.74, 93.64, 97.48, 88.49),
         'Qwen2.5-7B-Instruct': (84.36, 86.85, 94.12, 82.50)}
GROUPS = ['placement-macro', 'placement-micro', 'routing-macro', 'routing-micro']


def group(fname):
    """Layout/Routing x Easy/Hard in the file names. Easy = macro, Hard = micro: this reproduces the
    paper's split sizes only approximately; the repo does not state the mapping."""
    side = 'placement' if '_Layout_' in fname else 'routing'
    return f"{side}-{'macro' if '_Easy_' in fname else 'micro'}"


def load(data, limit=None):
    qs = []
    for f in sorted((Path(data) / SCQ).glob('*_scq.jsonl')):
        for line in f.read_text().splitlines():
            if line.strip():
                q = json.loads(line)
                qs.append({'key': f'{f.stem}:{q["id"]}', 'group': group(f.name), 'topic': f.stem, 'question': q['question'],
                           'options': q['options'], 'answer': q['correct_answer']})
    return qs[:limit] if limit else qs


def ask(batch, condition, model):
    system = PROMPT + (SKILL_HEADER + SKILL.read_text() + '\n</skill>' if condition == 'skill' else '')
    body = '\n\n'.join(f"q{i + 1}. {q['question']}\n" + '\n'.join(f'{k}. {v}' for k, v in q['options']) for i, q in enumerate(batch))
    cmd = ['claude', '-p', '--safe-mode', '--model', model, '--system-prompt', system, '--tools', '', '--strict-mcp-config',
           '--no-session-persistence', '--output-format', 'json']
    for attempt in range(3):
        r = subprocess.run(cmd, input=body, capture_output=True, text=True, cwd='/tmp', timeout=600)
        try:
            out = json.loads(r.stdout)
            m = re.search(r'\{[\s\S]*\}', out.get('result') or '')
            letters = json.loads(m.group(0)) if m else {}
            got = {f'q{i + 1}': str(letters.get(f'q{i + 1}', '')).strip().upper()[:1] for i in range(len(batch))}
            if sum(1 for v in got.values() if v) >= len(batch) * 0.9 or attempt == 2:
                return got, out.get('total_cost_usd', 0.0)
        except (ValueError, AttributeError):
            pass
    return {}, 0.0


def summarize(rows, meta):
    by = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    cost = defaultdict(float)
    for r in rows:
        for g in (r['group'], 'all'):
            by[r['condition']][g][0] += r['pred'] == r['answer']
            by[r['condition']][g][1] += 1
    for c, v in meta.get('cost', {}).items():
        cost[c] = v
    conds = [c for c in ('baseline', 'skill') if c in by]
    pct = lambda c, g: 100 * by[c][g][0] / by[c][g][1] if by[c][g][1] else None
    lines = [f"# PCB-Bench Task 1 (multiple choice) · {meta['run']}", '',
             f"Model `{meta['model']}` via `claude -p --safe-mode`, {meta['batch']} questions per call. "
             f"Questions: {by[conds[0]]['all'][1] if conds else 0} per condition.", '',
             '| condition | ' + ' | '.join(GROUPS) + ' | all |', '|---|' + '---|' * (len(GROUPS) + 1)]
    for c in conds:
        lines.append(f'| {c} | ' + ' | '.join(f'{pct(c, g):.2f} ({by[c][g][1]})' if pct(c, g) is not None else '–' for g in GROUPS) + f" | **{pct(c, 'all'):.2f}** |")
    lines += ['', 'PCB-Bench paper, Table 2 (CQ accuracy %, one question per call):', '', '| model | ' + ' | '.join(GROUPS) + ' |', '|---|' + '---|' * len(GROUPS)]
    lines += [f'| {k} | ' + ' | '.join(f'{x:.2f}' for x in v) + ' |' for k, v in PAPER.items()]
    if len(conds) == 2:
        keyed = {c: {r['key']: r for r in rows if r['condition'] == c} for c in conds}
        both = keyed['baseline'].keys() & keyed['skill'].keys()
        fixed = sorted(k for k in both if keyed['baseline'][k]['pred'] != keyed['baseline'][k]['answer'] and keyed['skill'][k]['pred'] == keyed['skill'][k]['answer'])
        broke = sorted(k for k in both if keyed['baseline'][k]['pred'] == keyed['baseline'][k]['answer'] and keyed['skill'][k]['pred'] != keyed['skill'][k]['answer'])
        lines += ['', f'Skill vs baseline on the same {len(both)} questions: **{len(fixed)} fixed, {len(broke)} broken**.']
        for title, ks in (('Fixed by the skill', fixed), ('Broken by the skill', broke)):
            if ks:
                lines += ['', f'### {title}', '']
                for k in ks[:25]:
                    b, s = keyed['baseline'][k], keyed['skill'][k]
                    lines.append(f"- {b['question']} (key {b['answer']}; baseline {b['pred'] or '–'}, skill {s['pred'] or '–'}) — `{b['topic']}`")
    if cost:
        lines += ['', 'Reported cost: ' + ', '.join(f'{c} ${v:.2f}' for c, v in cost.items())]
    lines += ['', 'Easy files are counted as macro-level and Hard as micro-level (the repo does not state the mapping).']
    return '\n'.join(lines) + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data', type=Path, help='a clone of github.com/digailab/PCB-Bench')
    p.add_argument('--conditions', default='baseline,skill')
    p.add_argument('--model', default='claude-opus-5-5')
    p.add_argument('--batch', type=int, default=25)
    p.add_argument('--jobs', type=int, default=4)
    p.add_argument('--limit', type=int)
    p.add_argument('--run')
    p.add_argument('--summarize', metavar='RUN')
    a = p.parse_args()
    if a.summarize:
        out = HERE / 'results' / a.summarize
        rows = [json.loads(l) for l in (out / 'answers.jsonl').read_text().splitlines() if l.strip()]
        (out / 'summary.md').write_text(summarize(rows, json.loads((out / 'meta.json').read_text())))
        print((out / 'summary.md').read_text())
        return 0
    if not a.data or not (a.data / SCQ).is_dir():
        p.error('--data must be a PCB-Bench clone (git clone https://github.com/digailab/PCB-Bench)')
    qs = load(a.data, a.limit)
    run = a.run or f"task1-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    out = HERE / 'results' / run
    out.mkdir(parents=True, exist_ok=True)
    answers = out / 'answers.jsonl'
    done = {(r['condition'], r['key']) for r in map(json.loads, answers.read_text().splitlines())} if answers.exists() else set()
    meta_path = out / 'meta.json'
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {'run': run, 'model': a.model, 'batch': a.batch, 'cost': {}}
    jobs = []
    for c in a.conditions.split(','):
        todo = [q for q in qs if (c, q['key']) not in done]
        jobs += [(c, todo[i:i + a.batch]) for i in range(0, len(todo), a.batch)]
    print(f'PCB-Bench task 1: {len(qs)} questions · {a.conditions} · {a.model} · {len(jobs)} calls · {out}', flush=True)
    lock = threading.Lock()
    with cf.ThreadPoolExecutor(a.jobs) as pool, open(answers, 'a') as sink:
        futs = {pool.submit(ask, b, c, a.model): (c, b) for c, b in jobs}
        for n, f in enumerate(cf.as_completed(futs), 1):
            c, b = futs[f]
            got, cost = f.result()
            with lock:
                meta['cost'][c] = meta['cost'].get(c, 0.0) + cost
                for i, q in enumerate(b):
                    sink.write(json.dumps({'condition': c, **{k: q[k] for k in ('key', 'group', 'topic', 'question', 'answer')}, 'pred': got.get(f'q{i + 1}', '')}) + '\n')
                sink.flush()
                meta_path.write_text(json.dumps(meta, indent=1) + '\n')
            right = sum(1 for i, q in enumerate(b) if got.get(f'q{i + 1}') == q['answer'])
            print(f'  [{n}/{len(jobs)}] {c:8s} {right}/{len(b)}  (${cost:.3f})', flush=True)
    rows = [json.loads(l) for l in answers.read_text().splitlines() if l.strip()]
    (out / 'summary.md').write_text(summarize(rows, meta))
    print('\n' + (out / 'summary.md').read_text().split('### ')[0])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
