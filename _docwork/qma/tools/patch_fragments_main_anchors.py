"""Re-point three fragment ops whose literal anchors changed under the trading-node increment; make them tree-agnostic."""
import sys
from pathlib import Path

import yaml

sys.stdout.reconfigure(encoding='utf-8')
FR = Path('_docwork/qma/fragments')


def str_presenter(dumper, data):
    if '\n' in data or len(data) > 100:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


yaml.add_representer(str, str_presenter)


def load(fn):
    return yaml.safe_load((FR / f'{fn}.yaml').read_text(encoding='utf-8'))


def save(fn, d):
    (FR / f'{fn}.yaml').write_text(
        yaml.dump(d, allow_unicode=True, sort_keys=False, width=100000),
        encoding='utf-8', newline='\n')


# agents.md: the deferred-items sentence exists as "(GAP-0016/GAP-0017, GAP-0048, GAP-0049)" on the pre-node tree and as
# "The deferred items — GAP-0016/GAP-0017, GAP-0048, GAP-0049, GAP-0050 (...)" after the node increment.
d = load('agents')
for i, op in enumerate(d['ops']):
    if op['op'] == 'replace' and op['old'] == '(GAP-0016/GAP-0017, GAP-0048, GAP-0049)':
        d['ops'][i] = {
            'op': 'regex_replace',
            'pattern': r'(The deferred items(?: —| \()\s*GAP-0016/GAP-0017, GAP-0048, GAP-0049)',
            'repl': r'\1, the QMA rows GAP-0070–GAP-0091',
            'all': False,
            'skip_if': 'the QMA rows GAP-0070–GAP-0091',
        }
        print('agents op', i, 'made regex')
save('agents', d)

# gap-report.md: "The catalog contains **49 gaps**, now in three states" became "**57 gaps** after ..." — bump the count by 22.
d = load('gap-report')
for i, op in enumerate(d['ops']):
    if op['op'] == 'replace' and op['old'].startswith('The catalog contains **49 gaps**'):
        d['ops'][i] = {
            'op': 'regex_replace',
            'pattern': r'The catalog contains \*\*(\d+) gaps\*\*',
            'repl': r'The catalog contains **\1 gaps**',
            'count_add': [{'group': 1, 'delta': 22}],
            'all': False,
            'skip_if': '## Deferred by the QMA sitting',
        }
        print('gap-report op', i, 'made regex count bump')
save('gap-report', d)

# index.md: the gap-report bullet's deferred clause was rewritten by the node increment — append the QMA clause to the
# bullet line whatever its current wording.
d = load('index')
for i, op in enumerate(d['ops']):
    if op['op'] == 'replace' and op['old'].startswith('and 4 are deferred'):
        d['ops'][i] = {
            'op': 'regex_replace',
            'pattern': r'^(- \[Gap report\]\(gap-report\.md\) — .*)$',
            'repl': r'\1 The 2026-08-29 QMA increment added GAP-0070 through GAP-0091 as 22 deferred rows, each carrying its revisit condition.',
            'all': False,
            'skip_if': 'GAP-0070 through GAP-0091 as 22 deferred rows',
        }
        print('index op', i, 'made regex append')
save('index', d)

# gap-report.md: the QMA deferred bullet goes right before the "**Operator flag — resolved:**" paragraph, whatever bullets precede it.
d = load('gap-report')
for i, op in enumerate(d['ops']):
    if op['op'] == 'replace' and op['old'].startswith('not closed.') and 'Operator flag' in op['old']:
        bullet = op['new'].split('\n\n')[1]
        d['ops'][i] = {
            'op': 'regex_replace',
            'pattern': r'^(\*\*Operator flag — resolved:\*\*)',
            'repl': bullet.replace('\\', '\\\\') + '\n\n' + r'\1',
            'all': False,
            'skip_if': '22 deferred by the QMA sitting',
        }
        print('gap-report op', i, 'made regex insert')
save('gap-report', d)

# index.md: the intro paragraph's QMA sentence goes before "Their rationale is absorbed ..." whatever ADR precedes it.
d = load('index')
for i, op in enumerate(d['ops']):
    if op['op'] == 'replace' and op['old'].startswith('and absorbed in ADR-0018. Their rationale'):
        sentence = op['new'][len('and absorbed in ADR-0018. '):-len(' Their rationale is absorbed across the architecture-decision set below.')]
        d['ops'][i] = {
            'op': 'regex_replace',
            'pattern': r'(and absorbed in ADR-00\d\d\. )(Their rationale is absorbed across the architecture-decision set below\.)',
            'repl': r'\1' + sentence.replace('\\', '\\\\') + r' \2',
            'all': False,
            'skip_if': 'and absorbed in ADR-0020',
        }
        print('index op', i, 'made regex insert')
save('index', d)
print('done')
