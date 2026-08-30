"""Turn fragments/stage-state.md (the drafted change_mode entry) into an append fragment for _docwork/stage_state.yaml.

Usage: python make_stage_state_fragment.py --review "<text>" --orchestration "<text>" [--date 2026-08-30]
"""
import argparse
import io
import re
import sys

import yaml

sys.stdout.reconfigure(encoding='utf-8')
ap = argparse.ArgumentParser()
ap.add_argument('--review', required=True)
ap.add_argument('--orchestration', required=True)
ap.add_argument('--date', default=None)
a = ap.parse_args()

src = io.open('_docwork/qma/fragments/stage-state.md', encoding='utf-8').read()
m = re.search(r'```yaml\n(.*?)```', src, re.S)
block = m.group(1).rstrip('\n')
entry = yaml.safe_load(block)[0]
entry['review'] = a.review
entry['orchestration'] = a.orchestration
if a.date:
    entry['date'] = a.date
# render as one list item, block style, preserving key order
text = yaml.safe_dump([entry], allow_unicode=True, sort_keys=False, width=100000, default_flow_style=False)
frag = {'target': '_docwork/stage_state.yaml', 'ops': [{'op': 'append', 'text': text}]}


def str_presenter(dumper, data):
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


yaml.add_representer(str, str_presenter)
io.open('_docwork/qma/fragments/stage-state.yaml', 'w', encoding='utf-8', newline='\n').write(
    yaml.dump(frag, allow_unicode=True, sort_keys=False, width=100000))
# prove the appended file still parses
target = io.open('../QMX-qma/_docwork/stage_state.yaml', encoding='utf-8').read()
yaml.safe_load(target.rstrip('\n') + '\n' + text)
print('fragments/stage-state.yaml written; append parses')
