"""Cluster landed full-read extracts. No title mining."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"C:\Users\Mubarak\Desktop\QMX\workroom\research\2026-09-15_mis-fullread-ideas")
EX = ROOT / "extracts"

rows = []
for p in sorted(EX.glob("*.jsonl")):
    for line in p.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        o["_pack"] = p.stem
        rows.append(o)

def sense_key(s):
    if isinstance(s, list):
        return "|".join(str(x) for x in s)
    return str(s or "unknown")

by = defaultdict(list)
for r in rows:
    by[sense_key(r.get("senses"))].append(r)

lines = []
lines.append("# In-progress MIS ideas (full-read extracts only)")
lines.append("")
lines.append(f"Packs on disk: {len(list(EX.glob('*.jsonl')))}. Idea lines: {len(rows)}.")
lines.append("This file is rewritten as extracts land. It is not a final atlas.")
lines.append("")
for sense in ["regime", "change", "volatility", "liquidity", "neural_sensor", "other_sensing", "not_mis"]:
    bucket = [r for r in rows if sense in sense_key(r.get("senses")).lower() or sense_key(r.get("senses")) == sense]
    if sense == "not_mis":
        bucket = [r for r in rows if sense_key(r.get("senses")) == "not_mis"]
    lines.append(f"## {sense} ({len(bucket)})")
    lines.append("")
    for r in bucket[:40]:
        name = r.get("idea_name") or "?"
        aid = r.get("article_id")
        mech = (r.get("mechanism") or "").replace("\n", " ")[:280]
        lines.append(f"- `{aid}` **{name}** — {mech}")
    if len(bucket) > 40:
        lines.append(f"- … {len(bucket) - 40} more in jsonl")
    lines.append("")

(ROOT / "IN_PROGRESS_IDEAS.md").write_text("\n".join(lines), encoding="utf-8")
print("rows", len(rows), "packs", len(list(EX.glob('*.jsonl'))))
