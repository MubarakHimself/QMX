"""Render conclusion digests to markdown for researcher reading."""
from __future__ import annotations

import json
from pathlib import Path

SRC = Path(
    r"C:\Users\Mubarak\Desktop\QMX\workroom\research\2026-09-15_unbounded-market-intelligence"
    r"\recovery_staging\micro_excerpts\_conclusions.json"
)
DEST = SRC.with_name("_conclusions.md")

rows = json.loads(SRC.read_text(encoding="utf-8"))
parts = []
for r in rows:
    parts.append(f"# {r['id']}: {r['title']}\n\n")
    if r["sections"]:
        parts.append("## Sections\n\n")
        for s in r["sections"][:3]:
            parts.append(s[:1800] + "\n\n")
    parts.append("## Key paras\n\n")
    for p in r["key_paras"][:12]:
        parts.append(p.replace("\n", " ")[:700] + "\n\n")
    parts.append("---\n\n")
DEST.write_text("".join(parts), encoding="utf-8")
print(DEST, DEST.stat().st_size)
