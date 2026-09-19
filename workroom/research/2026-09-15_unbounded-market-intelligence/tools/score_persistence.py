#!/usr/bin/env python3
"""Score persistence-family MQL5 articles. Read-only on corpus."""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

DB = Path(r"C:\Users\Mubarak\Desktop\QMX\.worktrees\mql5-library\data\mql5-library\index.sqlite")
MD = Path(r"C:\Users\Mubarak\Desktop\QMX\.worktrees\mql5-library\data\mql5-library\md")
OUT = Path(__file__).resolve().parent.parent / "indexes"

ALREADY = {
    17737, 23286, 22940, 16830, 15223, 23482, 23016, 10715, 23454, 21003,
    14203, 19944, 9804, 23355, 22938, 22939, 15748, 19290, 18867, 1575,
    21235, 16752, 9231, 22772,
}
LEFTOVERS = {22484, 23488, 22754, 21142, 2930}

PATS = [
    (r"\bHurst\b", "Hurst"),
    (r"\bGHE\b|Generalized Hurst", "GHE"),
    (r"variance.?ratio", "VRT"),
    (r"half.?life", "half_life"),
    (r"\bMFDFA\b|multifractal", "MFDFA"),
    (r"fractal.?dimension", "fractal_dim"),
    (r"permutation.?entropy", "perm_entropy"),
    (r"persistence.?entropy", "pers_entropy"),
    (r"Shannon.?Entropy|Shannon.?entrop", "shannon"),
    (r"\bADX\b", "ADX"),
    (r"\bDMI\b|\+DI|\-DI", "DMI"),
    (r"\bKalman\b", "Kalman"),
    (r"\bwavelet\b", "wavelet"),
    (r"\bDFA\b|detrended.?fluctuation", "DFA"),
    (r"Catch.?22|catch22", "Catch22"),
    (r"\bEhlers\b|\bMAMA\b|Hilbert", "Ehlers"),
    (r"choppiness|chop.?index", "chop"),
    (r"\bentropy\b", "entropy"),
    (r"long.?memory|anti.?persist", "long_memory"),
    (r"autocorrelat", "autocorr"),
]
COMPILED = [(re.compile(p, re.I), n) for p, n in PATS]
TITLE_FOCUS = re.compile(
    r"Hurst|fractal dimension|Catch22|entropy|Kalman|wavelet|ADX|DFA|MFDFA|"
    r"variance ratio|half-life|Ehlers|choppiness|multifractal|fractal",
    re.I,
)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = list(
        con.execute(
            "SELECT id, title, description, author, published, fetch_status, "
            "md_relpath, section FROM articles WHERE fetch_status='ok'"
        )
    )
    scored = []
    for r in rows:
        aid = int(r["id"])
        if aid in ALREADY:
            continue
        md = MD / f"{aid}.md"
        if not md.is_file():
            continue
        text = md.read_text(encoding="utf-8", errors="replace")
        head = text[:100000]
        counts = {}
        total = 0
        for cre, name in COMPILED:
            n = len(cre.findall(head))
            if n:
                counts[name] = n
                total += n
        if not counts:
            continue
        title = r["title"] or ""
        title_boost = 0
        for cre, _name in COMPILED:
            if cre.search(title):
                title_boost += 25
        if TITLE_FOCUS.search(title):
            title_boost += 40
        scored.append(
            {
                "id": aid,
                "title": title,
                "author": r["author"],
                "published": r["published"],
                "section": r["section"],
                "total": total,
                "title_boost": title_boost,
                "score": total + title_boost,
                "counts": counts,
                "leftover": aid in LEFTOVERS,
                "chars": len(text),
            }
        )
    scored.sort(key=lambda x: (-x["score"], x["id"]))
    (OUT / "persistence_candidates.json").write_text(
        json.dumps(scored[:200], indent=2), encoding="utf-8"
    )
    print("candidates", len(scored))
    print("--- LEFTOVERS ---")
    for aid in sorted(LEFTOVERS):
        hit = next((s for s in scored if s["id"] == aid), None)
        if hit:
            print(aid, hit["score"], hit["title"][:80], hit["counts"])
        else:
            row = con.execute(
                "SELECT id,title,fetch_status FROM articles WHERE id=?", (aid,)
            ).fetchone()
            print(aid, "NOT IN SCORED", dict(row) if row else "MISSING")
    print("--- TOP 60 ---")
    for s in scored[:60]:
        flag = "LEFTOVER" if s["leftover"] else ""
        top = sorted(s["counts"].items(), key=lambda x: -x[1])[:5]
        print(f"{s['score']:4d} {s['id']:5d} {flag:8s} {s['title'][:85]} | {top}")


if __name__ == "__main__":
    main()
