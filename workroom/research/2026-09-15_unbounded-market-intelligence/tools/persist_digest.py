#!/usr/bin/env python3
"""Build short digests of persistence-family articles for full-read extraction."""
from __future__ import annotations

import json
import re
from pathlib import Path

MD = Path(r"C:\Users\Mubarak\Desktop\QMX\.worktrees\mql5-library\data\mql5-library\md")
OUT = Path(
    r"C:\Users\Mubarak\Desktop\QMX\workroom\research\2026-09-15_unbounded-market-intelligence"
    r"\recovery_staging\persist_digests"
)
OUT.mkdir(parents=True, exist_ok=True)

IDS = [
    2930, 22484, 23488, 22754, 21142, 22553, 15222, 6834, 22519, 21299,
    22438, 22476, 22638, 23171, 21743, 21742, 22220, 22756, 23077, 23351,
    23451, 11487, 6351, 17273, 3886, 23112, 23444, 23149, 16085, 18453,
    23565, 23657, 16747, 23013, 20173, 5451, 12129, 2118, 22539, 3968,
    17910, 18566, 13915, 22519,
]

NEEDLES = re.compile(
    r"Hurst|GHE|variance ratio|half-?life|MFDFA|multifractal|fractal dimension|"
    r"permutation entropy|persistence entropy|Shannon|ADX|\+DI|\-DI|DMI|"
    r"Kalman|wavelet|DFA|Catch.?22|Ehlers|MAMA|choppiness|entropy|"
    r"long memory|anti-?persist|regime|lookahead|walk-?forward|out-?of-?sample|"
    r"closed bar|shift\(-|future|warm-?up|threshold|filter|trend|range|chop",
    re.I,
)


def first_paras(text: str, n: int = 3) -> str:
    parts = re.split(r"\n\s*\n", text)
    keep = []
    for p in parts:
        p = p.strip()
        if not p or p.startswith("![") or p.startswith("```") or p.startswith("#"):
            continue
        if len(p) < 40:
            continue
        keep.append(re.sub(r"\s+", " ", p)[:1200])
        if len(keep) >= n:
            break
    return "\n\n".join(keep)


def conclusion(text: str) -> str:
    m = re.search(r"^#+\s*Conclusion.*$", text, re.I | re.M)
    if not m:
        return ""
    chunk = text[m.start() : m.start() + 4000]
    return first_paras(chunk, 4)


def claim_hits(text: str, limit: int = 18) -> list[str]:
    lines = text.splitlines()
    hits = []
    for i, line in enumerate(lines):
        if NEEDLES.search(line) and len(line.strip()) > 60 and not line.strip().startswith("```"):
            # skip pure code-ish
            if line.count(";") > 3 or line.strip().startswith("//"):
                continue
            s = re.sub(r"\s+", " ", line.strip())[:500]
            if s not in hits:
                hits.append(s)
            if len(hits) >= limit:
                break
    return hits


def heads(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        if line.startswith("#"):
            out.append(line.strip()[:160])
            if len(out) >= 40:
                break
    return out


def main() -> None:
    rows = []
    for aid in dict.fromkeys(IDS):
        p = MD / f"{aid}.md"
        if not p.is_file():
            print("missing", aid)
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        # title from first heading or first line
        title = ""
        for line in text.splitlines()[:30]:
            if line.startswith("#"):
                title = line.lstrip("# ").strip()
                break
        rec = {
            "article_id": aid,
            "title": title,
            "chars": len(text),
            "heads": heads(text),
            "intro": first_paras(text, 4),
            "conclusion": conclusion(text),
            "claim_hits": claim_hits(text),
        }
        (OUT / f"{aid}.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
        # also a readable md digest
        md = [
            f"# Digest {aid}: {title}",
            "",
            "## Heads",
            *[f"- {h}" for h in rec["heads"]],
            "",
            "## Intro",
            rec["intro"],
            "",
            "## Conclusion",
            rec["conclusion"] or "(no Conclusion heading)",
            "",
            "## Claim hits",
            *[f"- {c}" for c in rec["claim_hits"]],
        ]
        (OUT / f"{aid}.md").write_text("\n".join(md), encoding="utf-8")
        rows.append({"id": aid, "title": title, "chars": len(text)})
        print(aid, title[:70])
    (OUT / "_index.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
