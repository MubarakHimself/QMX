"""Assemble epics-QMA-parts/epic-NN.md into epics-QMA-2026-08-29.md (Step 3 completion).

Replaces everything from the template tail marker ('<!-- Repeat for each epic in epics_list') to the end of file
with the concatenated epic sections in numeric order, and sets frontmatter stepsCompleted: [1, 2, 3].
"""
import os
import re
import sys
from pathlib import Path

import yaml

sys.stdout.reconfigure(encoding='utf-8')
WT = 'C:/Users/Mubarak/Desktop/QMX-qma'
EPICS = WT + '/_bmad-output/planning-artifacts/epics-QMA-2026-08-29.md'
PARTS = WT + '/_bmad-output/planning-artifacts/epics-QMA-parts'

parts = sorted(f for f in os.listdir(PARTS) if re.match(r'epic-\d+\.md$', f))
nums = [int(re.search(r'\d+', f).group()) for f in parts]
expected = list(range(40, 49))
missing = [n for n in expected if n not in nums]
if missing:
    print('MISSING PARTS:', missing)
    sys.exit(1)

doc = Path(EPICS).read_text(encoding='utf-8').replace('\r\n', '\n')
marker = '<!-- Repeat for each epic in epics_list'
i = doc.find(marker)
if i < 0:
    # already assembled: cut at the first '## Epic 40:' section heading
    m = re.search(r'^## Epic 40: ', doc, re.M)
    if not m:
        print('no template tail and no Epic 40 section found')
        sys.exit(1)
    i = m.start()
head = doc[:i].rstrip('\n') + '\n\n'
body = []
stories = 0
for f in parts:
    t = Path(PARTS, f).read_text(encoding='utf-8').replace('\r\n', '\n').strip('\n')
    stories += len(re.findall(r'^### Story \d+\.\d+:', t, re.M))
    body.append(t)
out = head + '\n\n'.join(body) + '\n'
# frontmatter stepsCompleted
fm_end = out.find('\n---\n', 4)
fm = out[4:fm_end]
fm = re.sub(r'^stepsCompleted:.*$', 'stepsCompleted: [1, 2, 3]', fm, flags=re.M)
out = '---\n' + fm + out[fm_end:]
yaml.safe_load(fm)
Path(EPICS).write_text(out, encoding='utf-8', newline='\n')
epics = len(re.findall(r'^## Epic \d+: ', out, re.M))
frs = sorted(set(re.findall(r'FR-Q\d\d', out)))
print(f'assembled: {epics} epics, {stories} stories, {len(frs)} distinct FR-Q ids cited')
