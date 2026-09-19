"""Cluster full-read extracts into a MIS idea atlas. No titles, no physics hunt."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"C:\Users\Mubarak\Desktop\QMX\workroom\research\2026-09-15_mis-fullread-ideas")
EX = ROOT / "extracts"

rows = []
bad = 0
for p in sorted(EX.glob("*.jsonl")):
    for line in p.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            bad += 1
            continue
        o["_pack"] = p.stem
        rows.append(o)

def senses_of(r):
    s = r.get("senses")
    if isinstance(s, list):
        return [str(x).strip().lower() for x in s]
    return [x.strip().lower() for x in str(s or "unknown").split("|")]

def is_not_mis(r):
    return "not_mis" in senses_of(r) and len(senses_of(r)) == 1

keep = [r for r in rows if not is_not_mis(r)]
not_mis = [r for r in rows if is_not_mis(r)]
articles = {str(r.get("article_id")) for r in rows}
keep_articles = {str(r.get("article_id")) for r in keep}

BUCKETS = ["regime", "change", "volatility", "liquidity", "neural_sensor", "other_sensing"]


def bucket(r):
    s = senses_of(r)
    for b in BUCKETS:
        if b in s:
            return b
    return "other_sensing"

by = defaultdict(list)
for r in keep:
    by[bucket(r)].append(r)

lines = []
lines.append("# New MIS ideas from full-read MQL5 articles")
lines.append("")
lines.append("Method: catalog section + series packs; agents read markdown bodies. Not a title or keyword index.")
lines.append(f"Extract rows: {len(rows)} (parse_fail {bad}). Unique article_ids: {len(articles)}.")
lines.append(f"Sensing ideas: {len(keep)} from {len(keep_articles)} articles. Honest `not_mis` after full read: {len(not_mis)}.")
lines.append("Four last Example packs may still be in flight; this file is regenerated when they land.")
lines.append("")
lines.append("QMX home for all of these is **MIS snapshot / shadow**, never bot direction, never sizing.")
lines.append("")

for b in BUCKETS:
    items = by[b]
    lines.append(f"## {b} ({len(items)} idea lines)")
    lines.append("")
    # Dedup loosely on idea_name stem
    seen = set()
    shown = 0
    for r in items:
        name = (r.get("idea_name") or "?").strip()
        key = re.sub(r"\s+", " ", name.lower())[:80]
        if key in seen:
            continue
        seen.add(key)
        aid = r.get("article_id")
        mech = (r.get("mechanism") or r.get("why_new_for_mis") or "").replace("\n", " ")[:320]
        lines.append(f"- `{aid}` **{name}** — {mech}")
        shown += 1
        if shown >= 35:
            break
    extra = len(items) - shown
    if extra > 0:
        lines.append(f"- … {extra} more lines in jsonl for this bucket (duplicates/near-duplicates skipped above)")
    lines.append("")

(ROOT / "NEW_MIS_IDEAS.md").write_text("\n".join(lines), encoding="utf-8")
print("rows", len(rows), "keep", len(keep), "not_mis", len(not_mis), "articles", len(articles))
