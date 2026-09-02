#!/usr/bin/env python3
"""land.py — land the QMA increment into a target tree (the worktree branch, or an overlay for rehearsal).

Usage:
  python _docwork/qma/tools/land.py --source <repo with _docwork/qma> --target <tree to land into> [--gates] [--hygiene-only]

Steps:
  1. hygiene grep over staged docs, fragments, harvest (rejects session-mechanics language)
  2. copy staged docs (source/_docwork/qma/staged/docs/**) into target/docs/**
  3. ensure target/_docwork/qma exists (copy tools + fragments + harvest so fragment item paths resolve)
  4. apply every fragment with apply_fragments.py against --root target
  5. optionally run the five documentation-factory gates against --root target
"""
import argparse
import contextlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

with contextlib.suppress(Exception):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SKILL = os.path.expanduser('~/.claude/skills/documentation-factory/scripts')
HYGIENE = re.compile(r"(another session|other session|second session|session is (still )?(running|live)|in[- ]flight work|concurrent(ly)? (session|pass|writer)|parallel (session|pass)|be patient|wait for the (other|node) (session|pass))", re.I)


def hygiene(source):
    bad = []
    roots = [os.path.join(source, '_docwork', 'qma', d) for d in ('staged', 'fragments', 'harvest')]
    for r in roots:
        for dp, _, fns in os.walk(r):
            for fn in fns:
                p = os.path.join(dp, fn)
                try:
                    txt = Path(p).read_text(encoding='utf-8')
                except OSError:
                    txt = None
                if txt is None:
                    continue
                for i, line in enumerate(txt.split('\n'), 1):
                    if HYGIENE.search(line):
                        rel = os.path.relpath(p, source)
                        bad.append(f'{rel}:{i}: {line.strip()[:160]}')
    return bad


def copy_staged(source, target):
    src = os.path.join(source, '_docwork', 'qma', 'staged', 'docs')
    n = 0
    for dp, _, fns in os.walk(src):
        for fn in fns:
            sp = os.path.join(dp, fn)
            rel = os.path.relpath(sp, src)
            tp = os.path.join(target, 'docs', rel)
            os.makedirs(os.path.dirname(tp), exist_ok=True)
            shutil.copyfile(sp, tp)
            n += 1
    return n


def sync_lane(source, target):
    if os.path.abspath(source) == os.path.abspath(target):
        return
    for d in ('tools', 'fragments', 'harvest', 'riders'):
        s = os.path.join(source, '_docwork', 'qma', d)
        t = os.path.join(target, '_docwork', 'qma', d)
        if os.path.isdir(s):
            if os.path.isdir(t):
                shutil.rmtree(t)
            shutil.copytree(s, t)
    for fn in ('BRIEF.md',):
        s = os.path.join(source, '_docwork', 'qma', fn)
        if os.path.exists(s):
            shutil.copyfile(s, os.path.join(target, '_docwork', 'qma', fn))


def run(cmd):
    print('$ ' + ' '.join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = (r.stdout or '') + (r.stderr or '')
    print(out[-6000:])
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', required=True)
    ap.add_argument('--target', required=True)
    ap.add_argument('--gates', action='store_true')
    ap.add_argument('--hygiene-only', action='store_true')
    a = ap.parse_args()
    bad = hygiene(a.source)
    if bad:
        print(f'HYGIENE VIOLATIONS ({len(bad)}):')
        for b in bad:
            print('  ' + b)
        if a.hygiene_only:
            sys.exit(1)
        print('-- continuing; fix these before committing --')
    else:
        print('hygiene: clean')
    if a.hygiene_only:
        return
    sync_lane(a.source, a.target)
    print(f'staged docs copied: {copy_staged(a.source, a.target)}')
    rc = run([sys.executable, os.path.join(a.target, '_docwork', 'qma', 'tools', 'apply_fragments.py'), '--root', a.target])
    if rc != 0:
        print('FRAGMENT FAILURES — fix and re-run')
    if a.gates:
        codes = {}
        for script, extra in (('validate_ledger.py', []), ('validate_registry.py', []), ('validate_inventory.py', []),
                              ('check_citations.py', []), ('lint_docs.py', []), ('lint_docs.py', ['--strict'])):
            key = script + (' --strict' if extra else '')
            codes[key] = run([sys.executable, os.path.join(SKILL, script), '--root', a.target, *extra])
        print('GATE EXIT CODES: ' + ', '.join(f'{key}={code}' for key, code in codes.items()))
        sys.exit(1 if any(codes.values()) else 0)
    sys.exit(rc)


if __name__ == '__main__':
    main()
