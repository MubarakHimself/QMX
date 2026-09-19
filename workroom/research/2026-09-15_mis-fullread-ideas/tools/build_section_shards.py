"""Split the fetched MQL5 corpus by catalog SECTION then SERIES.

No keyword search. Work-list is sqlite section + a normalized Part-N series key.
Stay inside this QMX folder.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

PART_RE = re.compile(
    r"^(.*?)\s*(?:\(|:|,|\.|-)?\s*Part\s+\d+\b.*$",
    re.I | re.S,
)
TRAIL_RE = re.compile(r"[\s:.\-()]+$")


def series_key(title: str, series_title: str) -> str:
    t = (title or "").strip()
    m = PART_RE.match(t)
    if m:
        base = TRAIL_RE.sub("", m.group(1)).strip()
        if base:
            return base.lower()
    st = TRAIL_RE.sub("", (series_title or "").strip())
    st = re.sub(r"\s*Part\s+\d+.*$", "", st, flags=re.I)
    st = TRAIL_RE.sub("", st)
    return st.lower() if st else ""

ROOT = Path(r"C:\Users\Mubarak\Desktop\QMX")
DB = ROOT / ".worktrees" / "mql5-library" / "data" / "mql5-library" / "index.sqlite"
MD = ROOT / ".worktrees" / "mql5-library" / "data" / "mql5-library"
OUT = ROOT / "workroom" / "research" / "2026-09-15_mis-fullread-ideas"
SHARDS = OUT / "shards"
if SHARDS.exists():
    for old in SHARDS.glob("*.json"):
        old.unlink()
SHARDS.mkdir(parents=True, exist_ok=True)

# Target articles per reader. Series stay together even if this is exceeded.
TARGET = 12

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
rows = list(
    con.execute(
        """
        SELECT id, title, section, series_title, series_part, md_relpath, fetch_status
        FROM articles
        WHERE fetch_status='ok'
        ORDER BY section, COALESCE(series_title, ''), CAST(id AS INTEGER)
        """
    )
)

by_section: dict[str, list] = defaultdict(list)
series_sizes: dict[str, int] = defaultdict(int)
for r in rows:
    title = r["title"] or ""
    st = (r["series_title"] or "").strip()
    key = series_key(title, st)
    rec = {
        "id": int(r["id"]),
        "title": title,
        "section": r["section"] or "Unknown",
        "series_title": st,
        "series_key": key,
        "series_part": r["series_part"],
        "path": str(MD / (r["md_relpath"] or f"md/{r['id']}.md")),
    }
    by_section[rec["section"]].append(rec)
    if key:
        series_sizes[key] += 1

# Group each section into series-units, then pack units into shards of ~TARGET.
# A series is never split across shards.
shards = []
for section, items in sorted(by_section.items(), key=lambda x: -len(x[1])):
    units: dict[str, list] = defaultdict(list)
    for rec in items:
        key = rec["series_key"] if rec["series_key"] else f"__single__{rec['id']}"
        units[key].append(rec)
    for unit in units.values():
        unit.sort(key=lambda x: (x["series_part"] is None, x["series_part"] or 0, x["id"]))
    packed: list[list] = []
    cur: list = []
    for key, unit in units.items():
        if cur and len(cur) + len(unit) > TARGET:
            packed.append(cur)
            cur = []
        cur.extend(unit)
        if len(cur) >= TARGET:
            packed.append(cur)
            cur = []
    if cur:
        packed.append(cur)
    for i, pack in enumerate(packed):
        sid = f"{section.lower().replace(' ', '_').replace('&', 'and')}_{i:03d}"
        shards.append(
            {
                "shard_id": sid,
                "section": section,
                "n": len(pack),
                "series_in_shard": sorted({p["series_key"] for p in pack if p["series_key"]}),
                "articles": pack,
            }
        )

manifest = {
    "ok_articles": len(rows),
    "sections": {s: len(v) for s, v in by_section.items()},
    "series_with_2plus": sum(1 for n in series_sizes.values() if n >= 2),
    "shard_count": len(shards),
    "target_per_shard": TARGET,
    "shards": [{"shard_id": s["shard_id"], "section": s["section"], "n": s["n"]} for s in shards],
}
(OUT / "WORKLIST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
for s in shards:
    (SHARDS / f"{s['shard_id']}.json").write_text(json.dumps(s, indent=2), encoding="utf-8")

print(json.dumps({"ok": len(rows), "sections": manifest["sections"], "shards": len(shards), "series_2plus": manifest["series_with_2plus"]}, indent=2))
