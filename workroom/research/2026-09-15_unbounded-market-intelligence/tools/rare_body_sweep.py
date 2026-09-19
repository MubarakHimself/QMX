"""Body sweep for rare physics / information-flow terms. Read-only on corpus."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

MD = Path(r"C:\Users\Mubarak\Desktop\QMX\.worktrees\mql5-library\data\mql5-library\md")
OUT = Path(r"C:\Users\Mubarak\Desktop\QMX\workroom\research\2026-09-15_unbounded-market-intelligence\indexes")
OUT.mkdir(parents=True, exist_ok=True)

TERMS = {
    "mutual_information": r"mutual information",
    "transfer_entropy": r"transfer entropy",
    "hawkes": r"\bHawkes\b",
    "ising": r"\bIsing\b",
    "lyapunov": r"Lyapunov",
    "econophysics": r"econophysics",
    "criticality": r"\bcriticality\b|\bcritical point\b|\bphase transition\b",
    "random_matrix": r"random matrix|\bRMT\b|Marchenko.?Pastur|eigenvalue clutter",
    "kuramoto": r"Kuramoto",
    "percolation": r"\bpercolat",
    "information_flow": r"information flow",
    "spin_glass": r"spin glass",
    "fokker_planck": r"Fokker.?Planck",
}

compiled = {k: re.compile(v, re.I) for k, v in TERMS.items()}
hits: dict[str, list[dict]] = defaultdict(list)

for path in sorted(MD.glob("*.md")):
    text = path.read_text(encoding="utf-8", errors="replace")
    aid = int(path.stem)
    for name, pat in compiled.items():
        found = pat.findall(text)
        if found:
            # grab a short context window around first match
            m = pat.search(text)
            start = max(0, m.start() - 80)
            end = min(len(text), m.end() + 120)
            ctx = re.sub(r"\s+", " ", text[start:end]).strip()
            hits[name].append(
                {
                    "article_id": aid,
                    "count": len(found),
                    "context": ctx[:240],
                }
            )

summary = {k: len(v) for k, v in hits.items()}
# sort each by count desc
for k in hits:
    hits[k].sort(key=lambda x: -x["count"])

out = {"summary": summary, "hits": hits}
(OUT / "rare_body_hits.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
# top ids overall
seen = {}
for name, items in hits.items():
    for it in items:
        aid = it["article_id"]
        seen.setdefault(aid, {"article_id": aid, "terms": {}, "total": 0})
        seen[aid]["terms"][name] = it["count"]
        seen[aid]["total"] += it["count"]
ranked = sorted(seen.values(), key=lambda x: -x["total"])
(OUT / "rare_body_ranked.json").write_text(json.dumps(ranked[:80], indent=2), encoding="utf-8")
print("top20:")
for r in ranked[:20]:
    print(r["article_id"], r["total"], r["terms"])
