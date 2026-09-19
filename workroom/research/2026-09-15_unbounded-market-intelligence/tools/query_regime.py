#!/usr/bin/env python3
"""Query MQL5 corpus for regime / market-state articles."""
import sqlite3
import json
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(r"C:\Users\Mubarak\Desktop\QMX\.worktrees\mql5-library\data\mql5-library")
DB = ROOT / "index.sqlite"
MD = ROOT / "md"
OUT = Path(__file__).resolve().parent.parent / "indexes"

ALREADY = {
    17737, 23286, 22940, 16830, 15223, 23482, 23016, 10715, 23454, 21003,
    14203, 19944, 9804, 23355, 22938, 22939, 15748, 19290, 18867, 1575,
    21235, 16752, 9231, 22772,
}

LEFTOVERS = {15033, 17781, 15541, 23137, 23444, 22258, 23677, 22484, 23488, 22754, 16213, 3395, 20037, 21142, 752}

TERMS = [
    "regime", "market state", "market condition", "chop", "ranging",
    "trending", "sideways", "volatile", "HMM", "hidden markov", "Markov",
    "playbook", "strategy switch", "class activation", "market mode",
    "Nash", "Ehlers", "MAMA", "choppiness", "GARCH", "Hurst",
    "fractal dimension", "change-point", "changepoint", "BOCPD",
    "ADX", "Kalman", "Catch22", "meta-label", "EGARCH", "GJR",
    "volatility regime", "regime switch", "regime change", "market regime",
]

GREP_PATTERNS = [
    r"\bregime\b", r"market state", r"market condition", r"\bchop\b",
    r"\branging\b", r"\btrending\b", r"\bsideways\b", r"\bvolatile\b",
    r"\bHMM\b", r"hidden markov", r"\bMarkov\b", r"playbook switch",
    r"strategy switch", r"class activation", r"market mode", r"\bNash\b",
    r"bagging regime", r"\bEhlers\b", r"\bMAMA\b", r"choppiness",
]


def score_title(title: str, desc: str, tags: str) -> int:
    text = f"{title} {desc} {tags}".lower()
    s = 0
    high = [
        ("regime", 10), ("hmm", 9), ("hidden markov", 9), ("markov", 7),
        ("garch", 6), ("bocpd", 8), ("change-point", 7), ("changepoint", 7),
        ("choppiness", 8), ("chop", 5), ("sideways", 5), ("ranging", 5),
        ("trending", 4), ("volatile", 4), ("ehlers", 7), ("mama", 8),
        ("nash", 6), ("hurst", 6), ("fractal dimension", 6), ("kalman", 5),
        ("catch22", 6), ("meta-label", 5), ("egarch", 5), ("gjr", 5),
        ("market state", 8), ("market condition", 6), ("market mode", 7),
        ("strategy switch", 7), ("playbook", 6), ("adx", 3),
    ]
    for kw, w in high:
        if kw in text:
            s += w
    # Prefer method over UI
    if any(x in text for x in ("indicator", "classifier", "detection", "filter", "prediction", "algorithm")):
        s += 3
    if any(x in text for x in ("library", "gui", "chart", "ui ", "panel", "widget")):
        s -= 2
    return s


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row

    clauses = []
    params = []
    for t in TERMS:
        clauses.append(
            "(IFNULL(title,'') LIKE ? OR IFNULL(description,'') LIKE ? OR IFNULL(tags_json,'') LIKE ? OR IFNULL(section,'') LIKE ?)"
        )
        params.extend([f"%{t}%"] * 4)

    sql = f"""
    SELECT id, title, description, published, author, section, tags_json,
           series_title, series_part, fetch_status, md_relpath, platform
    FROM articles
    WHERE ({' OR '.join(clauses)})
    ORDER BY id
    """
    rows = c.execute(sql, params).fetchall()
    print(f"SQL HITS: {len(rows)}")

    scored = []
    for r in rows:
        aid = r["id"]
        sc = score_title(r["title"] or "", r["description"] or "", r["tags_json"] or "")
        entry = {
            "id": aid,
            "title": r["title"],
            "description": (r["description"] or "")[:300],
            "published": r["published"],
            "author": r["author"],
            "section": r["section"],
            "tags_json": r["tags_json"],
            "series_title": r["series_title"],
            "series_part": r["series_part"],
            "fetch_status": r["fetch_status"],
            "md_relpath": r["md_relpath"],
            "platform": r["platform"],
            "score": sc,
            "already_read": aid in ALREADY,
            "leftover_named": aid in LEFTOVERS,
            "has_md": bool(r["md_relpath"]) and r["fetch_status"] == "ok",
        }
        scored.append(entry)

    scored.sort(key=lambda x: (-x["score"], x["id"]))
    (OUT / "regime_sql_hits.json").write_text(json.dumps(scored, indent=2), encoding="utf-8")

    # Print top new candidates with md
    print("\n=== TOP NEW (has_md, not already) ===")
    new = [e for e in scored if e["has_md"] and not e["already_read"]]
    for e in new[:80]:
        flag = "LEFTOVER" if e["leftover_named"] else ""
        print(f"{e['score']:3d}  {e['id']:5d}  {flag:8s}  {(e['title'] or '')[:100]}")

    print(f"\nNew with md: {len(new)}")
    print(f"Leftovers present: {[e['id'] for e in scored if e['leftover_named'] and e['has_md']]}")

    # Grep md files for keyword density
    print("\n=== GREP md for keyword hits (counting) ===")
    combined = re.compile("|".join(GREP_PATTERNS), re.I)
    # Focus patterns for ranking new articles
    focus = re.compile(
        r"\bregime\b|market.?state|market.?condition|\bHMM\b|hidden.?markov|\bMarkov\b|"
        r"choppiness|\bchop\b|sideways|ranging|trending|volatile|playbook|strategy.?switch|"
        r"class.?activation|market.?mode|\bNash\b|\bEhlers\b|\bMAMA\b|bagging.?regime|"
        r"BOCPD|change.?point|GARCH|Hurst|fractal.?dimension",
        re.I,
    )
    grep_scores = []
    for p in MD.glob("*.md"):
        try:
            aid = int(p.stem)
        except ValueError:
            continue
        if aid in ALREADY:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        # Only scan first 80k chars for speed + title area
        head = text[:80000]
        matches = focus.findall(head)
        if not matches:
            continue
        # Count unique pattern families
        lower_m = [m.lower() for m in matches]
        counts = defaultdict(int)
        for m in lower_m:
            counts[m] += 1
        n = len(matches)
        # Boost title hits
        title_line = head.split("\n", 5)[0] if head else ""
        title_boost = 20 if focus.search(title_line or "") else 0
        # Prefer articles whose title mentions regime-ish
        grep_scores.append({
            "id": aid,
            "path": f"md/{aid}.md",
            "match_count": n,
            "unique": len(counts),
            "top_terms": sorted(counts.items(), key=lambda x: -x[1])[:8],
            "score": n + title_boost + 5 * len(counts),
        })

    grep_scores.sort(key=lambda x: -x["score"])
    (OUT / "regime_grep_hits.json").write_text(
        json.dumps([{**g, "top_terms": g["top_terms"]} for g in grep_scores[:200]], indent=2),
        encoding="utf-8",
    )
    print(f"Grep articles with hits: {len(grep_scores)}")
    print("\n=== TOP GREP ===")
    for g in grep_scores[:50]:
        print(f"{g['score']:4d}  {g['id']:5d}  matches={g['match_count']:4d}  uniq={g['unique']:2d}  {g['top_terms'][:4]}")


if __name__ == "__main__":
    main()
