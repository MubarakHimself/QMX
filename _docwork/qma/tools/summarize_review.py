import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
path = sys.argv[1]
raw = Path(path).read_text(encoding='utf-8')
try:
    d = json.loads(raw)
except Exception:
    # the task output may wrap JSON in text; find the first '{'
    d = json.loads(raw[raw.index('{'):])
if 'result' in d and isinstance(d['result'], dict):
    d = d['result']
print('top keys:', list(d.keys()))
f = d.get('findings', [])
print('findings:', len(f), Counter(x['severity'] for x in f))
print('files:', Counter(x['file'].replace('\\', '/').split('_docwork/qma/')[-1] for x in f).most_common(40))
print('CRITICAL:')
for x in f:
    if x['severity'] == 'critical':
        print(' -', x['file'].split('/')[-1], '::', x['summary'][:260])
print('REGATE:', json.dumps(d.get('regate'), indent=1)[:3000])
fixes = d.get('fixes') or []
print('fix seats:', len(fixes))
for i, fx in enumerate(fixes):
    s = fx if isinstance(fx, str) else json.dumps(fx)
    refused = [line for line in s.split('\n') if re.search(r'refus|declin|left (the )?text|not applied|finding (is|was) wrong|disagree|no change', line, re.I)]
    if refused:
        print(f'--- fix[{i}] refusal lines:')
        for line in refused[:8]:
            print('   ', line.strip()[:300])
