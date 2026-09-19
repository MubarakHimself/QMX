"""Pull method-relevant excerpts from selected MQL5 articles. Read-only on corpus."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(r"C:\Users\Mubarak\Desktop\QMX")
MD = ROOT / ".worktrees" / "mql5-library" / "data" / "mql5-library" / "md"
OUT = ROOT / "workroom" / "research" / "2026-09-15_unbounded-market-intelligence" / "recovery_staging" / "micro_excerpts"
OUT.mkdir(parents=True, exist_ok=True)

IDS = [
    22263, 22553, 22598, 22638, 23372,  # Brown 1-4, 8
    8818, 8912, 8952, 8988, 9010, 9044, 9095,  # DoEasy tick/DOM
    1179, 1793, 3336,  # BookEvent / own DOM / scalping DOM
    18821, 20371, 22998, 23299, 23755, 2739, 14035, 15622,  # spread/exec
    17934, 22963, 22990, 16984,  # VWAP/TWAP
    22063, 21825, 21829, 21984,  # imbalance/footprint
    2612, 11106, 11113, 23465, 22460, 18680,  # ticks
    20327, 23550, 22342, 18661, 21876,  # liquidity profiles
    15895, 20287, 8136,  # orderflow mashup / BS greeks / noise
]

KEYWORDS = re.compile(
    r"(?i)("
    r"spread|liquidity|order.?flow|DOM|depth of market|VPIN|VWAP|TWAP|"
    r"imbalance|tick.?volume|BookEvent|MarketBook|CopyTicks|slippage|"
    r"execution|NQ|US100|Globex|futures|crypto|FX|forex|bid.?ask|"
    r"look.?ahead|future bar|forward|percentile|P\d{2}|limitation|"
    r"caveat|volume.?bucket|aggressor|Lee.?Ready|Roll|noise|"
    r"session|NY open|quoted|BOOKDEPTH|iceberg|footprint|"
    r"conclusion|empirical|result|weak signal|proxy"
    r")"
)

HEADING = re.compile(r"^#{1,3}\s+")


def strip_md(text: str) -> str:
    # drop yaml front matter
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4 :]
    # drop data-uri images / long base64
    text = re.sub(r"!\[.*?\]\(data:[^)]+\)", "", text)
    text = re.sub(r"!\[.*?\]\(https?://[^)]+\)", "", text)
    return text


def paras(text: str) -> list[str]:
    chunks = re.split(r"\n\s*\n", text)
    out = []
    for c in chunks:
        c = c.strip()
        if not c:
            continue
        if c.startswith("```"):
            continue
        if len(c) < 40:
            continue
        out.append(c)
    return out


def main() -> None:
    index = []
    for aid in IDS:
        path = MD / f"{aid}.md"
        raw = path.read_text(encoding="utf-8", errors="replace")
        text = strip_md(raw)
        lines = text.splitlines()
        # title / author from early lines
        title = ""
        author = ""
        for i, ln in enumerate(lines[:80]):
            if ln.startswith("# ") and not title:
                title = ln[2:].strip()
            if "Max Brown" in ln or re.search(r"^\[[A-Z][^\]]+\]\(https://www\.mql5\.com/en/users/", ln):
                author = re.sub(r"[\[\]]", "", ln.split("](")[0]).strip("[]") if "](" in ln else ln.strip()
        # collect keyword-hit paragraphs + all headings + last ~15 paras (conclusions)
        ps = paras(text)
        hits = []
        for p in ps:
            if KEYWORDS.search(p):
                hits.append(p[:1200])
        # headings
        heads = [ln.strip() for ln in lines if HEADING.match(ln)]
        # conclusion-ish: last 12 non-code paras
        tail = ps[-12:] if len(ps) >= 12 else ps
        # intro: first 8 paras after title
        intro = ps[:8]
        rec = {
            "id": aid,
            "title": title,
            "author_guess": author,
            "chars": len(text),
            "n_paras": len(ps),
            "headings": heads[:40],
            "intro": intro,
            "keyword_hits": hits[:40],
            "tail": tail,
        }
        (OUT / f"{aid}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
        index.append({"id": aid, "title": title, "heads": heads[:15], "n_hits": len(hits)})
        print(f"{aid}\t{len(hits)}\t{title[:80]}")
    (OUT / "_index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
