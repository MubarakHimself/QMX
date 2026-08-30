import io
import json
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')
path = sys.argv[1]
raw = io.open(path, encoding='utf-8').read()
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
    refused = [l for l in s.split('\n') if re.search(r'refus|declin|left (the )?text|not applied|finding (is|was) wrong|disagree|no change', l, re.I)]
    if refused:
        print('--- fix[%d] refusal lines:' % i)
        for l in refused[:8]:
            print('   ', l.strip()[:300])
