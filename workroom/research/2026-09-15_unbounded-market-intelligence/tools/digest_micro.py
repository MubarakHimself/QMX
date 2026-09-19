"""Print compact digests of microstructure excerpts."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(
    r"C:\Users\Mubarak\Desktop\QMX\workroom\research\2026-09-15_unbounded-market-intelligence"
    r"\recovery_staging\micro_excerpts"
)
IDS = [
    22263, 22553, 22598, 22638, 23372,
    9010, 9044, 9095, 8988, 8818, 8912, 8952,
    1179, 1793, 3336,
    18821, 20371, 22998, 23299, 23755, 2739, 14035, 15622,
    17934, 22963, 22990, 16984,
    22063, 21825, 21829, 21984,
    2612, 11106, 11113, 23465, 22460, 18680,
    20327, 23550, 22342, 18661, 21876,
    15895, 20287, 8136,
]
KEYS = [
    "empirical", "limitation", "nq", "us100", "futures", "tick volume",
    "spread", "vpin", "lookahead", "proxy", "weak", "session", "crypto",
    "fx", "broker", "bookdepth", "dom", "volume", "imbalance", "vwap",
    "slippage", "execution", "noise", "percentile", "globex", "moscow",
]


def main() -> None:
    dest = OUT / "_digests.md"
    parts: list[str] = []
    for aid in IDS:
        p = OUT / f"{aid}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        parts.append(f"# {aid}: {d['title']}\n")
        parts.append("HEADS: " + " | ".join(d["headings"][:14]) + "\n")
        parts.append("\n## Intro\n")
        for x in d["intro"][:5]:
            parts.append(x[:700].replace("\n", " ") + "\n\n")
        scored = []
        for h in d["keyword_hits"]:
            low = h.lower()
            s = sum(1 for k in KEYS if k in low)
            scored.append((s, h))
        scored.sort(key=lambda t: -t[0])
        parts.append("\n## Key hits\n")
        for s, h in scored[:8]:
            parts.append(f"**score {s}:** " + h[:550].replace("\n", " ") + "\n\n")
        parts.append("\n## Tail\n")
        for x in d["tail"][-5:]:
            parts.append(x[:550].replace("\n", " ") + "\n\n")
        parts.append("\n---\n")
    dest.write_text("".join(parts), encoding="utf-8")
    print(f"wrote {dest} chars={dest.stat().st_size}")


if __name__ == "__main__":
    main()
