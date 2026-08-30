"""One-off: make the four anchor-sensitive fragments apply on both HEAD and the trading-node-edited tree."""
import io
import re
import sys

import yaml

sys.stdout.reconfigure(encoding='utf-8')
FR = '_docwork/qma/fragments/'


def str_presenter(dumper, data):
    if '\n' in data or len(data) > 100:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


yaml.add_representer(str, str_presenter)


def load(fn):
    return yaml.safe_load(io.open(FR + fn + '.yaml', encoding='utf-8'))


def save(fn, d):
    io.open(FR + fn + '.yaml', 'w', encoding='utf-8', newline='\n').write(
        yaml.dump(d, allow_unicode=True, sort_keys=False, width=100000))


def esc(s):
    """Escape a literal for use inside a regex replacement string (backslashes only)."""
    return s.replace('\\', '\\\\')


# agents.md: append the QMA sentence to reading-order item 4, whatever its current tail says
d = load('agents')
if d['ops'][2]['op'] == 'replace':
    op = d['ops'][2]
    suffix = op['new'][len(op['old']):]
    d['ops'][2] = {
        'op': 'regex_replace',
        'pattern': r'^(4\. The spec for every component you will touch in \[`docs/components/`\]\(components/\)\..*)$',
        'repl': r'\1' + esc(suffix),
        'all': False,
        'skip_if': 'components/qma-daemon.md) (COMP-QMA-DAEMON',
    }
    save('agents', d)
    print('agents patched')

# index.md: bump the file-count sentence instead of matching literal numbers
d = load('index')
if d['ops'][3]['op'] == 'replace':
    d['ops'][3] = {
        'op': 'regex_replace',
        'pattern': r'The corpus contains (\d+) files: (\d+) Markdown documents and (\d+) YAML artifacts\.',
        'repl': r'The corpus contains \1 files: \2 Markdown documents and \3 YAML artifacts.',
        'count_add': [{'group': 1, 'delta': 18}, {'group': 2, 'delta': 6}, {'group': 3, 'delta': 12}],
        'all': False,
        'skip_if': 'components/qma-core.md',
    }
    save('index', d)
    print('index patched')

# overview.md: insert the QMA sentence before the intro paragraph's closing citation list
d = load('overview')
if d['ops'][3]['op'] == 'replace':
    op = d['ops'][3]
    m = re.search(r'\. (A fourth named application-layer consumer.*?ADR-0020-qma-agentic-system\.md`\.) \(', op['new'])
    sentence = m.group(1).replace('A fourth named application-layer consumer', 'A further named application-layer consumer')
    d['ops'][3] = {
        'op': 'regex_replace',
        'pattern': r'^(QMF V1 is a contracts-first Python toolbox.*?)\s*\((DEC-0008, [^)]*)\)\s*$',
        'repl': r'\1 ' + esc(sentence) + r' (\2, DEC-0329, DEC-0330, DEC-0333)',
        'all': False,
        'skip_if': 'ADR-0020-qma-agentic-system.md`',
    }
    save('overview', d)
    print('overview patched')

# traceability.md: heading_regex anchors + count bumps + id-range bumps
d = load('traceability')
if not any(o['op'] == 'regex_replace' for o in d['ops']):
    d['ops'][3]['heading_regex'] = r'^## Gap locator — \d+ entries$'
    d['ops'][3].pop('heading', None)
    d['ops'][4]['heading_regex'] = r'^## Feature locator — \d+ entries$'
    d['ops'][4].pop('heading', None)
    d['ops'][5]['heading_regex'] = r'^## FEAT-00\d\d scope and gate$'
    d['ops'][5].pop('heading', None)
    bumps = [
        {'op': 'regex_replace', 'pattern': r'^## Decision locator — (\d+) entries$', 'repl': r'## Decision locator — \1 entries', 'count_add': [{'group': 1, 'delta': 71}], 'all': False, 'skip_if': '| DEC-0300 |'},
        {'op': 'regex_replace', 'pattern': r'^## Gap locator — (\d+) entries$', 'repl': r'## Gap locator — \1 entries', 'count_add': [{'group': 1, 'delta': 22}], 'all': False, 'skip_if': '| GAP-0070 |'},
        {'op': 'regex_replace', 'pattern': r'^## Feature locator — (\d+) entries$', 'repl': r'## Feature locator — \1 entries', 'count_add': [{'group': 1, 'delta': 7}], 'all': False, 'skip_if': '| FEAT-0040 |'},
        {'op': 'regex_replace', 'pattern': r'\(`DEC-0001` through `DEC-\d{4}`\)', 'repl': '(`DEC-0001` through `DEC-0379`)', 'all': False, 'skip_if': 'through `DEC-0379`'},
        {'op': 'regex_replace', 'pattern': r'\(`GAP-0001` through `GAP-\d{4}`\)', 'repl': '(`GAP-0001` through `GAP-0091`)', 'all': False, 'skip_if': 'through `GAP-0091`'},
        {'op': 'regex_replace', 'pattern': r'\(`FEAT-0001` through `FEAT-\d{4}`\)', 'repl': '(`FEAT-0001` through `FEAT-0046`)', 'all': False, 'skip_if': 'through `FEAT-0046`'},
    ]
    d['ops'] = d['ops'][:3] + bumps + d['ops'][3:]
    save('traceability', d)
    print('traceability patched')

# gap-report.md: bump the dead-decisions heading count by 20
d = load('gap-report')
if not any(o['op'] == 'regex_replace' for o in d['ops']):
    d['ops'].insert(3, {'op': 'regex_replace', 'pattern': r'^## Dead decisions — (\d+)$', 'repl': r'## Dead decisions — \1', 'count_add': [{'group': 1, 'delta': 20}], 'all': False, 'skip_if': 'DEC-0360'})
    save('gap-report', d)
    print('gap-report patched')
