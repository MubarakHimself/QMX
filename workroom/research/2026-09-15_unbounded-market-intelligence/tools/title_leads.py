"""Fast title/description leads from sqlite. Read-only."""
from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

DB = Path(r"C:\Users\Mubarak\Desktop\QMX\.worktrees\mql5-library\data\mql5-library\index.sqlite")
OUT = Path(r"C:\Users\Mubarak\Desktop\QMX\workroom\research\2026-09-15_unbounded-market-intelligence\indexes")
OUT.mkdir(parents=True, exist_ok=True)

NEEDLES = {
    "regime": r"regime|market state|market condition|choppy|choppiness",
    "changeover": r"change.?point|changepoint|regime switch|regime change|regime transition|hidden markov|\bHMM\b|BOCPD|structural break|Markov",
    "volatility": r"GARCH|EGARCH|ATR|Parkinson|Garman|Yang.?Zhang|realized vol|volatility",
    "persistence": r"Hurst|fractal|entropy|Kalman|ADX|wavelet|Catch22|DFA",
    "microstructure": r"spread|liquidity|order.?flow|DOM|VPIN|imbalance|tick|order book|VWAP",
    "session": r"session|London|Asia|Tokyo|time filter|calendar|news window",
    "ml": r"machine learning|neural|LSTM|ONNX|cluster|k-means|LightGBM|transformer|FreqAI",
    "placement": r"filter|gate|cooldown|sit out|stand aside|skip trade|invalidat",
    "rare": r"Ising|Lyapunov|econophysics|Hawkes|Kuramoto|mutual information|transfer entropy|chaos theory",
}

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
rows = list(con.execute(
    "SELECT id, title, description, section, published, author, fetch_status FROM articles"
))
out: dict[str, list[dict]] = defaultdict(list)
for r in rows:
    blob = f"{r['title'] or ''} {r['description'] or ''}"
    rec = {
        "id": r["id"],
        "title": r["title"],
        "section": r["section"],
        "published": r["published"],
        "author": r["author"],
        "fetch_status": r["fetch_status"],
    }
    for fam, pat in NEEDLES.items():
        if re.search(pat, blob, re.I):
            out[fam].append(rec)

summary = {k: len(v) for k, v in out.items()}
(OUT / "title_leads.json").write_text(json.dumps({"summary": summary, "leads": out}, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
print("ok", sum(1 for r in rows if r["fetch_status"] == "ok"), "of", len(rows))
