#!/usr/bin/env python3
"""apply_fragments.py — deterministic, re-runnable application of QMA increment fragments.

Usage:
  python _docwork/qma/tools/apply_fragments.py --root <project-root> [--fragments DIR] [--only NAME] [--dry-run]

Each fragment is a YAML file in _docwork/qma/fragments/ with the shape:

  target: docs/glossary.md          # path relative to --root
  ops:
    - op: frontmatter_add           # add ids to a frontmatter LIST field (dedup; appended in given order)
      field: decisions
      ids: [DEC-0300, DEC-0301]
    - op: frontmatter_set           # set / overwrite a scalar frontmatter field
      field: verified
      value: '2026-08-29'
    - op: insert_before_heading     # insert text before the FIRST line equal to `heading` (or matching `heading_regex`)
      heading: '## Retired or prohibited names'
      text: |
        ...
    - op: insert_after_heading      # insert text after the heading line and its trailing blank lines / intro paragraphs
      heading: '## Reading order'
      after_paragraphs: 0           # optional: skip N paragraphs after the heading before inserting (default 0)
      text: |
        ...
    - op: append                    # append text at end of file (ensures one blank line before)
      text: |
        ...
    - op: replace                   # replace a unique literal string (fails if 0 or >1 occurrences)
      old: '...'
      new: '...'
    - op: replace_all               # replace every occurrence of a literal string (fails if 0)
      old: '...'
      new: '...'
    - op: regex_replace             # Python regex replace; \1 / \g<1> backrefs; optional numeric bumps on groups
      pattern: '^## Gap locator — (\d+) entries$'
      repl: '## Gap locator — \1 entries'
      count_add: [{group: 1, delta: 22}]
      skip_if: 'GAP-0070'           # literal whose presence means the op already ran (idempotency)
      flags: M                      # any of M I S (default M)
      all: true                     # replace every match (default true)
    - op: glossary_insert_sorted    # insert '### Term' blocks into a section, alphabetically by term
      section_heading: '## Canonical terms'
      entries:
        - term: Quant
          text: |
            The persistent named organizational actor ...
    - op: yaml_append_items         # textual append of list items from a harvest file whose top-level key is `key`
      key: ledger
      items_file: _docwork/qma/harvest/ledger-L1.yaml

Every op is idempotent where possible: an insertion whose text already appears verbatim in the target is skipped;
frontmatter_add skips ids already present; replace with `old` absent but `new` present is skipped; regex_replace
skips when `skip_if` is present. The tool never touches a file it cannot fully apply: all ops for a target are
computed in memory first.
"""
import argparse
import os
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    print("pip install pyyaml", file=sys.stderr)
    sys.exit(2)


class FragmentError(Exception):
    pass


def split_frontmatter(text):
    if not text.startswith('---\n'):
        return None, text
    end = text.find('\n---\n', 4)
    if end < 0:
        return None, text
    return text[4:end], text[end + 5:]


def join_frontmatter(fm, body):
    return '---\n' + fm + '\n---\n' + body


def op_frontmatter_add(text, field, ids):
    fm, body = split_frontmatter(text)
    if fm is None:
        raise FragmentError('no frontmatter')
    lines = fm.split('\n')
    for i, line in enumerate(lines):
        m = re.match(r'^(%s):\s*\[(.*)\]\s*$' % re.escape(field), line)
        if m:
            existing = [x.strip() for x in m.group(2).split(',') if x.strip()]
            for x in ids:
                if x not in existing:
                    existing.append(x)
            lines[i] = '%s: [%s]' % (field, ', '.join(existing))
            return join_frontmatter('\n'.join(lines), body)
        if re.match(r'^%s:\s*$' % re.escape(field), line):
            raise FragmentError('frontmatter field %s is a block list; only flow lists are supported' % field)
    ins = '%s: [%s]' % (field, ', '.join(ids))
    for i, line in enumerate(lines):
        if line.startswith('status:'):
            lines.insert(i + 1, ins)
            break
    else:
        lines.append(ins)
    return join_frontmatter('\n'.join(lines), body)


def op_frontmatter_set(text, field, value):
    fm, body = split_frontmatter(text)
    if fm is None:
        raise FragmentError('no frontmatter')
    lines = fm.split('\n')
    sval = str(value)
    if isinstance(value, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', value):
        sval = "'%s'" % value
    for i, line in enumerate(lines):
        if re.match(r'^%s:' % re.escape(field), line):
            lines[i] = '%s: %s' % (field, sval)
            return join_frontmatter('\n'.join(lines), body)
    lines.append('%s: %s' % (field, sval))
    return join_frontmatter('\n'.join(lines), body)


def _norm(s):
    return s.strip()


def _find_heading(lines, heading=None, heading_regex=None):
    for i, line in enumerate(lines):
        if heading is not None and line.strip() == heading.strip():
            return i
        if heading_regex is not None and re.match(heading_regex, line.strip()):
            return i
    return None


def op_insert_before_heading(text, heading, ins, heading_regex=None):
    if _norm(ins) and _norm(ins) in text:
        return text, 'skipped (present)'
    lines = text.split('\n')
    i = _find_heading(lines, heading, heading_regex)
    if i is None:
        raise FragmentError('heading not found: %r' % (heading or heading_regex))
    block = ins.rstrip('\n') + '\n\n'
    new = lines[:i] + block.split('\n')[:-1] + lines[i:]
    return '\n'.join(new), 'inserted'


def op_insert_after_heading(text, heading, ins, after_paragraphs=0, heading_regex=None):
    if _norm(ins) and _norm(ins) in text:
        return text, 'skipped (present)'
    lines = text.split('\n')
    i = _find_heading(lines, heading, heading_regex)
    if i is None:
        raise FragmentError('heading not found: %r' % (heading or heading_regex))
    j = i + 1
    while j < len(lines) and lines[j].strip() == '':
        j += 1
    for _ in range(after_paragraphs):
        while j < len(lines) and lines[j].strip() != '':
            j += 1
        while j < len(lines) and lines[j].strip() == '':
            j += 1
    block = ins.rstrip('\n') + '\n\n'
    new = lines[:j] + block.split('\n')[:-1] + lines[j:]
    return '\n'.join(new), 'inserted'


def op_append(text, ins):
    if _norm(ins) and _norm(ins) in text:
        return text, 'skipped (present)'
    if not text.endswith('\n'):
        text += '\n'
    if not text.endswith('\n\n'):
        text += '\n'
    return text + ins.rstrip('\n') + '\n', 'appended'


def op_replace(text, old, new, all_=False):
    n = text.count(old)
    if n == 0:
        if new and new in text:
            return text, 'skipped (already replaced)'
        raise FragmentError('replace: old text not found: %r' % old[:80])
    if not all_ and n > 1:
        raise FragmentError('replace: old text occurs %d times (must be unique): %r' % (n, old[:80]))
    return text.replace(old, new), 'replaced %d' % n


def op_regex_replace(text, pattern, repl, count_add=None, all_=True, skip_if=None, flags='M'):
    if skip_if and skip_if in text:
        return text, 'skipped (present)'
    fl = 0
    for ch in (flags or ''):
        fl |= {'M': re.M, 'I': re.I, 'S': re.S}.get(ch, 0)
    rx = re.compile(pattern, fl)
    if not rx.search(text):
        raise FragmentError('regex_replace: pattern not found: %r' % pattern[:100])
    bumps = count_add or []
    if isinstance(bumps, dict):
        bumps = [bumps]
    backref = re.compile(r'\\(\d)|\\g<(\d+)>')

    def _sub(m):
        groups = list(m.groups())
        for b in bumps:
            gi = int(b['group']) - 1
            groups[gi] = str(int(groups[gi]) + int(b['delta']))

        def expand(mm):
            n = int(mm.group(1) or mm.group(2))
            g = groups[n - 1]
            return g if g is not None else ''
        return backref.sub(expand, repl)

    new, n = rx.subn(_sub, text, count=0 if all_ else 1)
    return new, 'regex replaced %d' % n


def op_glossary_insert_sorted(text, section_heading, entries):
    lines = text.split('\n')
    start = _find_heading(lines, section_heading)
    if start is None:
        raise FragmentError('section heading not found: %r' % section_heading)
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith('## '):
            end = j
            break
    section = lines[start + 1:end]
    blocks = []
    intro = []
    cur = None
    for line in section:
        if line.startswith('### '):
            if cur is not None:
                blocks.append(cur)
            cur = [line[4:].strip(), [line]]
        elif cur is None:
            intro.append(line)
        else:
            cur[1].append(line)
    if cur is not None:
        blocks.append(cur)
    existing_terms = {b[0].lower() for b in blocks}
    added = 0
    for e in entries:
        term = e['term'].strip()
        if term.lower() in existing_terms:
            continue
        body = e['text'].rstrip('\n')
        blk = ['### ' + term, ''] + body.split('\n') + ['']
        blocks.append([term, blk])
        existing_terms.add(term.lower())
        added += 1

    def key(b):
        return re.sub(r'[`*_]', '', b[0]).lower()
    blocks.sort(key=key)
    out = []
    for b in blocks:
        blines = b[1]
        while blines and blines[-1].strip() == '':
            blines.pop()
        out.extend(blines + [''])
    new_section = intro + out
    while new_section and new_section[-1].strip() == '':
        new_section.pop()
    new_section.append('')
    new_lines = lines[:start + 1] + new_section + lines[end:]
    return '\n'.join(new_lines), 'inserted %d' % added


def op_yaml_append_items(text, key, items_path):
    with open(items_path, encoding='utf-8') as f:
        src = f.read().replace('\r\n', '\n')
    data = yaml.safe_load(src)
    if not isinstance(data, dict) or key not in data or not isinstance(data[key], list):
        raise FragmentError('items file %s has no top-level list %r' % (items_path, key))
    m = re.search(r'^%s:\s*\n' % re.escape(key), src, re.M)
    if not m:
        raise FragmentError('items file %s: cannot find textual key line %r' % (items_path, key))
    body = src[m.end():].rstrip('\n') + '\n'
    first = data[key][0] if data[key] else None
    if isinstance(first, dict):
        fid = first.get('id') or first.get('name')
        if fid and re.search(r'^\s*-\s*(id|name):\s*%s\s*$' % re.escape(str(fid)), text, re.M):
            return text, 'skipped (present)'
    tdata = yaml.safe_load(text)
    if not isinstance(tdata, dict) or key not in tdata:
        raise FragmentError('target has no top-level key %r' % key)
    out = text.rstrip('\n') + '\n\n' + body
    yaml.safe_load(out)
    return out, 'appended %d items' % len(data[key])


def apply_fragment(root, frag, dry):
    target = os.path.join(root, frag['target'])
    if not os.path.exists(target):
        raise FragmentError('target missing: %s' % frag['target'])
    with open(target, encoding='utf-8', newline='') as f:
        text = f.read()
    crlf = '\r\n' in text
    if crlf:
        text = text.replace('\r\n', '\n')
    original = text
    notes = []
    for op in frag.get('ops', []):
        kind = op['op']
        if kind == 'frontmatter_add':
            text = op_frontmatter_add(text, op['field'], list(op['ids']))
            notes.append('frontmatter_add %s' % op['field'])
        elif kind == 'frontmatter_set':
            text = op_frontmatter_set(text, op['field'], op['value'])
            notes.append('frontmatter_set %s' % op['field'])
        elif kind == 'insert_before_heading':
            text, n = op_insert_before_heading(text, op.get('heading'), op['text'], op.get('heading_regex'))
            notes.append('insert_before %r: %s' % (op.get('heading') or op.get('heading_regex'), n))
        elif kind == 'insert_after_heading':
            text, n = op_insert_after_heading(text, op.get('heading'), op['text'], int(op.get('after_paragraphs', 0)), op.get('heading_regex'))
            notes.append('insert_after %r: %s' % (op.get('heading') or op.get('heading_regex'), n))
        elif kind == 'append':
            text, n = op_append(text, op['text'])
            notes.append('append: %s' % n)
        elif kind == 'replace':
            text, n = op_replace(text, op['old'], op['new'])
            notes.append('replace: %s' % n)
        elif kind == 'replace_all':
            text, n = op_replace(text, op['old'], op['new'], all_=True)
            notes.append('replace_all: %s' % n)
        elif kind == 'regex_replace':
            text, n = op_regex_replace(text, op['pattern'], op['repl'], op.get('count_add'), bool(op.get('all', True)), op.get('skip_if'), op.get('flags', 'M'))
            notes.append('regex_replace: %s' % n)
        elif kind == 'glossary_insert_sorted':
            text, n = op_glossary_insert_sorted(text, op['section_heading'], op['entries'])
            notes.append('glossary: %s' % n)
        elif kind == 'yaml_append_items':
            text, n = op_yaml_append_items(text, op['key'], os.path.join(root, op['items_file']))
            notes.append('yaml_append %s: %s' % (op['key'], n))
        else:
            raise FragmentError('unknown op %r' % kind)
    if text != original and not dry:
        out = text.replace('\n', '\r\n') if crlf else text
        with open(target, 'w', encoding='utf-8', newline='') as f:
            f.write(out)
    return notes, text != original


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--fragments', default=None, help='fragments dir (default <root>/_docwork/qma/fragments)')
    ap.add_argument('--only', default=None, help='apply only fragments whose filename contains this')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    fdir = a.fragments or os.path.join(a.root, '_docwork', 'qma', 'fragments')
    files = sorted(f for f in os.listdir(fdir) if f.endswith(('.yaml', '.yml')))
    if a.only:
        files = [f for f in files if a.only in f]
    failures = 0
    for fn in files:
        path = os.path.join(fdir, fn)
        with open(path, encoding='utf-8') as f:
            try:
                frag = yaml.safe_load(f)
            except Exception as e:  # noqa
                print('FAIL %s: yaml parse error: %s' % (fn, e))
                failures += 1
                continue
        try:
            notes, changed = apply_fragment(a.root, frag, a.dry_run)
            print('%s %s -> %s: %s' % ('DRY ' if a.dry_run else 'OK  ', fn, frag['target'], '; '.join(notes) or 'no ops'))
        except FragmentError as e:
            print('FAIL %s -> %s: %s' % (fn, frag.get('target'), e))
            failures += 1
        except Exception as e:  # noqa
            print('FAIL %s -> %s: unexpected %s: %s' % (fn, frag.get('target'), type(e).__name__, e))
            failures += 1
    print('%d fragment(s), %d failure(s)' % (len(files), failures))
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
