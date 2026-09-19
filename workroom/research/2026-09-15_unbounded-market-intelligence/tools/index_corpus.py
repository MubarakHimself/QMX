"""Index the local MQL5 article corpus for regime / market-state research.

Stay inside this QMX folder. Read-only on the article library.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"C:\Users\Mubarak\Desktop\QMX")
CORPUS = ROOT / ".worktrees" / "mql5-library" / "data" / "mql5-library"
DB = CORPUS / "index.sqlite"
MD = CORPUS / "md"
OUT = ROOT / "workroom" / "research" / "2026-09-15_unbounded-market-intelligence"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "indexes").mkdir(exist_ok=True)
(OUT / "extractions").mkdir(exist_ok=True)
(OUT / "recovery_staging").mkdir(exist_ok=True)

# Broad families. Physics is one family, not the frame.
FAMILIES: dict[str, list[str]] = {
    "regime": [
        r"\bregime\b", r"market state", r"market condition", r"\bchop(?:py|piness)?\b",
        r"\brang(?:e|ing)\b", r"\btrend(?:ing)?\b", r"\bsideways\b", r"\bvolatile\b",
        r"HIGH_CHAOS", r"trend.?range", r"playbook switch", r"strategy switch",
        r"class activation", r"market mode",
    ],
    "changeover": [
        r"change.?point", r"changepoint", r"structural break", r"regime switch",
        r"regime change", r"regime transition", r"break.?point", r"\bBOCPD\b",
        r"\bPELT\b", r"run.?length", r"\bCUSUM\b", r"\bHMM\b", r"hidden markov",
        r"markov.?switch", r"Viterbi", r"Hamilton filter", r"jump model",
        r"\bMS-?GARCH\b",
    ],
    "volatility": [
        r"\bGARCH\b", r"\bEGARCH\b", r"\bGJR\b", r"\bFIGARCH\b", r"\bATR\b",
        r"Parkinson", r"Garman.?Klass", r"Yang.?Zhang", r"realized vol",
        r"implied vol", r"conditional variance", r"\bRVOL\b", r"relative volume",
    ],
    "persistence": [
        r"\bHurst\b", r"fractal", r"multifractal", r"\bMFDFA\b", r"\bentropy\b",
        r"permutation entropy", r"persistence entropy", r"\bKalman\b",
        r"\bwavelet\b", r"\bADX\b", r"choppiness", r"\bDFA\b", r"half.?life",
        r"variance ratio", r"autocorrelat",
    ],
    "microstructure": [
        r"\bspread\b", r"\bliquidity\b", r"order.?flow", r"\bDOM\b", r"\bVPIN\b",
        r"imbalance", r"\btick\b", r"order book", r"absorption", r"aggression",
        r"\bVWAP\b", r"quoted spread", r"\bPIN\b",
    ],
    "session_calendar": [
        r"\bsession\b", r"\bLondon\b", r"\bAsia\b", r"\bTokyo\b", r"New York",
        r"overlap", r"time filter", r"time.?of.?day", r"\bnews\b", r"calendar",
        r"kill zone", r"dead zone",
    ],
    "ml_sequence": [
        r"\bcluster", r"k-?means", r"gaussian mixture", r"neural", r"\bLSTM\b",
        r"transformer", r"random forest", r"gradient boost", r"\bLightGBM\b",
        r"FreqAI", r"\bKronos\b", r"embedding", r"self.?supervised",
    ],
    "information": [
        r"mutual information", r"transfer entropy", r"information flow",
        r"\bKL divergence\b", r"\bentropic\b", r"\bShannon\b",
    ],
    "network_physics": [
        r"Ising", r"Lyapunov", r"econophysics", r"criticality", r"Hawkes",
        r"spin glass", r"Fokker.?Planck", r"Kuramoto", r"percolation",
        r"phase transition", r"susceptibility", r"eigenvalue",
        r"random matrix", r"graph Laplacian",
    ],
    "placement_filter": [
        r"\bfilter\b", r"\bgate\b", r"compatib", r"activation", r"abstain",
        r"no.?trade", r"stand aside", r"sit out", r"skip trad", r"cooldown",
        r"invalidat", r"execution quality", r"\bslippage\b",
    ],
    "risk_portfolio": [
        r"correlation", r"crowding", r"drawdown", r"portfolio", r"\bKelly\b",
        r"position siz", r"kill switch", r"circuit breaker",
    ],
}

COMPILED = {
    fam: [re.compile(p, re.I) for p in pats] for fam, pats in FAMILIES.items()
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = list(con.execute("SELECT * FROM articles ORDER BY id"))
    print(f"sqlite articles: {len(rows)}")

    inv_path = OUT / "09_CORPUS_INVENTORY.csv"
    with inv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "article_id", "url", "title", "author", "published", "section",
                "platform", "tags", "series_title", "series_part",
                "fetch_status", "error", "sha256", "md_relpath",
                "md_bytes", "approx_tokens",
            ],
        )
        w.writeheader()
        for r in rows:
            md_path = CORPUS / (r["md_relpath"] or "")
            md_bytes = md_path.stat().st_size if md_path.is_file() else 0
            w.writerow(
                {
                    "article_id": r["id"],
                    "url": r["url"],
                    "title": r["title"] or "",
                    "author": r["author"] or "",
                    "published": r["published"] or "",
                    "section": r["section"] or "",
                    "platform": r["platform"] or "",
                    "tags": r["tags_json"] or "",
                    "series_title": r["series_title"] or "",
                    "series_part": r["series_part"] or "",
                    "fetch_status": r["fetch_status"],
                    "error": r["error"] or "",
                    "sha256": r["sha256"] or "",
                    "md_relpath": r["md_relpath"] or "",
                    "md_bytes": md_bytes,
                    "approx_tokens": md_bytes // 4,
                }
            )

    family_hits: dict[str, list[dict]] = defaultdict(list)
    title_hits: dict[str, list[dict]] = defaultdict(list)
    body_scan_ok = 0
    body_scan_fail = 0
    per_article: dict[int, dict[str, int]] = {}

    for r in rows:
        title = (r["title"] or "") + " " + (r["description"] or "")
        rec = {
            "article_id": r["id"],
            "title": r["title"] or "",
            "section": r["section"] or "",
            "published": r["published"] or "",
            "md_relpath": r["md_relpath"] or "",
            "fetch_status": r["fetch_status"],
        }
        title_fam: dict[str, int] = {}
        for fam, pats in COMPILED.items():
            n = sum(len(p.findall(title)) for p in pats)
            if n:
                title_fam[fam] = n
                title_hits[fam].append({**rec, "hits": n})
        body_fam: dict[str, int] = dict(title_fam)
        md_path = CORPUS / (r["md_relpath"] or "")
        if r["fetch_status"] == "ok" and md_path.is_file():
            try:
                text = md_path.read_text(encoding="utf-8", errors="replace")
                body_scan_ok += 1
                for fam, pats in COMPILED.items():
                    n = sum(len(p.findall(text)) for p in pats)
                    if n:
                        body_fam[fam] = n
                        family_hits[fam].append({**rec, "hits": n, "chars": len(text)})
            except OSError:
                body_scan_fail += 1
        if body_fam:
            per_article[int(r["id"])] = body_fam

    summary = {
        "sqlite_rows": len(rows),
        "ok": sum(1 for r in rows if r["fetch_status"] == "ok"),
        "failed": sum(1 for r in rows if r["fetch_status"] == "failed"),
        "body_scan_ok": body_scan_ok,
        "body_scan_fail": body_scan_fail,
        "family_article_counts_body": {k: len(v) for k, v in family_hits.items()},
        "family_article_counts_title": {k: len(v) for k, v in title_hits.items()},
    }
    (OUT / "indexes" / "scan_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    # Ranked hit lists per family
    for fam, items in family_hits.items():
        items.sort(key=lambda x: -x["hits"])
        path = OUT / "indexes" / f"hits_{fam}.json"
        path.write_text(json.dumps(items, indent=2), encoding="utf-8")

    # Combined score for deep-read sharding (regime+changeover weighted highest)
    weights = {
        "regime": 4, "changeover": 4, "volatility": 3, "persistence": 3,
        "microstructure": 2, "session_calendar": 2, "ml_sequence": 2,
        "information": 3, "network_physics": 2, "placement_filter": 3,
        "risk_portfolio": 1,
    }
    ranked = []
    for aid, fams in per_article.items():
        score = sum(weights.get(f, 1) * n for f, n in fams.items())
        ranked.append({"article_id": aid, "score": score, "families": fams})
    ranked.sort(key=lambda x: -x["score"])
    (OUT / "indexes" / "ranked_articles.json").write_text(
        json.dumps(ranked, indent=2), encoding="utf-8"
    )

    # Deep-read shards: top-N per family + stratified rest
    shards: dict[str, list[int]] = {}
    taken: set[int] = set()
    for fam, items in family_hits.items():
        ids = []
        for it in items:
            aid = int(it["article_id"])
            if aid in taken:
                continue
            ids.append(aid)
            taken.add(aid)
            if len(ids) >= 40:
                break
        shards[fam] = ids
    leftover = [x["article_id"] for x in ranked if x["article_id"] not in taken][:80]
    shards["novelty_highscore_leftover"] = leftover
    (OUT / "indexes" / "deepread_shards.json").write_text(
        json.dumps(shards, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    print("shards", {k: len(v) for k, v in shards.items()})


if __name__ == "__main__":
    main()
