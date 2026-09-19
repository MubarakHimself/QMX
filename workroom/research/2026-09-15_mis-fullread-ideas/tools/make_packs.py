"""Turn section shards into reader packs. Mega-series are split in part order, never shuffled."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"C:\Users\Mubarak\Desktop\QMX\workroom\research\2026-09-15_mis-fullread-ideas")
SHARDS = ROOT / "shards"
PACKS = ROOT / "packs"
if PACKS.exists():
    for p in PACKS.glob("*.json"):
        p.unlink()
PACKS.mkdir(parents=True, exist_ok=True)

MAX_N = 12

packs = []
for shard_path in sorted(SHARDS.glob("*.json")):
    shard = json.loads(shard_path.read_text(encoding="utf-8"))
    arts = shard["articles"]
    if len(arts) <= MAX_N:
        chunks = [arts]
    else:
        chunks = [arts[i : i + MAX_N] for i in range(0, len(arts), MAX_N)]
    for j, chunk in enumerate(chunks):
        pid = shard["shard_id"] if len(chunks) == 1 else f"{shard['shard_id']}_p{j:02d}"
        pack = {
            "pack_id": pid,
            "section": shard["section"],
            "parent_shard": shard["shard_id"],
            "part_index": j,
            "part_count": len(chunks),
            "series_in_pack": sorted({a["series_key"] for a in chunk if a.get("series_key")}),
            "n": len(chunk),
            "articles": chunk,
        }
        (PACKS / f"{pid}.json").write_text(json.dumps(pack, indent=2), encoding="utf-8")
        packs.append({"pack_id": pid, "section": pack["section"], "n": pack["n"]})

(ROOT / "PACKS.json").write_text(json.dumps({"pack_count": len(packs), "packs": packs}, indent=2), encoding="utf-8")
from collections import Counter
print(json.dumps({"pack_count": len(packs), "by_section": dict(Counter(p["section"] for p in packs))}, indent=2))
