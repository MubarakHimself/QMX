"""Extract conclusion / limitation / venue paragraphs from selected articles."""
from __future__ import annotations

import json
import re
from pathlib import Path

MD = Path(r"C:\Users\Mubarak\Desktop\QMX\.worktrees\mql5-library\data\mql5-library\md")
OUT = Path(
    r"C:\Users\Mubarak\Desktop\QMX\workroom\research\2026-09-15_unbounded-market-intelligence"
    r"\recovery_staging\micro_excerpts"
)

IDS = [
    22263, 22553, 22598, 22638, 23372,
    8818, 8912, 8952, 8988, 9010, 9044, 9095,
    1179, 1793, 3336,
    18821, 20371, 22998, 23299, 23755, 2739, 14035, 15622,
    17934, 22963, 22990, 16984,
    22063, 21825, 21829, 21984,
    2612, 11106, 11113, 23465, 22460, 18680,
    20327, 23550, 22342, 18661, 21876,
    15895, 20287, 8136,
]

SECTION = re.compile(
    r"(?im)^(#{1,3}\s+.*(conclusion|limitation|caveat|empirical|result|discussion|"
    r"practical|summary|what.?s next|final|interpretation|transfer|warning).*)\s*$"
)
KEY = re.compile(
    r"(?i)\b(limitation|caveat|NQ\b|US100|Globex|CME|futures|tick volume|"
    r"BOOKDEPTH|BookEvent|tester|lookahead|look-ahead|forward.?looking|"
    r"percentile|P9[05]|proxy|slippage|spread|VWAP|VPIN|imbalance|"
    r"crypto|forex|FX\b|Moscow|MOEX|session|aggressor|Lee-Ready|"
    r"volume bucket|quoted spread|range.?proxy|conflate)\b"
)


def strip_noise(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4 :]
    text = re.sub(r"!\[.*?\]\([^)]+\)", "", text)
    text = re.sub(r"```[\s\S]*?```", "\n", text)
    return text


def main() -> None:
    rows = []
    for aid in IDS:
        raw = (MD / f"{aid}.md").read_text(encoding="utf-8", errors="replace")
        text = strip_noise(raw)
        lines = text.splitlines()
        # frontmatter-ish title
        title = ""
        for ln in lines[:60]:
            if ln.startswith("# "):
                title = ln[2:].strip()
                break
        # find section starts
        sec_idxs = [i for i, ln in enumerate(lines) if SECTION.match(ln)]
        sections = []
        for j, i in enumerate(sec_idxs[:8]):
            end = sec_idxs[j + 1] if j + 1 < len(sec_idxs) else min(len(lines), i + 80)
            block = "\n".join(lines[i:end]).strip()
            # trim related-articles footer noise
            cut = re.search(r"(?im)^\[.*\]\(https://www\.mql5\.com/en/articles/", block)
            if cut and cut.start() > 200:
                block = block[: cut.start()].strip()
            sections.append(block[:2500])
        # key sentences
        paras = [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) > 80]
        hits = []
        for p in paras:
            if KEY.search(p):
                hits.append(p[:900])
            if len(hits) >= 25:
                break
        rows.append(
            {
                "id": aid,
                "title": title,
                "sections": sections,
                "key_paras": hits,
            }
        )
        print(f"{aid} secs={len(sections)} hits={len(hits)} {title[:70]}")
    (OUT / "_conclusions.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
