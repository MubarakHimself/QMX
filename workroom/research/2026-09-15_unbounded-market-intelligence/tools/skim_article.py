"""Skim an article: title/meta + keyword windows. Read-only."""
from __future__ import annotations

import re
import sys
from pathlib import Path

MD = Path(r"C:\Users\Mubarak\Desktop\QMX\.worktrees\mql5-library\data\mql5-library\md")

DEFAULT_KEYS = [
    r"filter", r"gate", r"cooldown", r"sit out", r"stand.?aside", r"skip",
    r"invalidat", r"abstain", r"no.?trade", r"compatib", r"regime",
    r"market state", r"execution", r"slippage", r"spread", r"look.?ahead",
    r"lookahead", r"future", r"out.?of.?sample", r"OOS", r"walk.?forward",
    r"meta.?label", r"playbook", r"switch", r"activation",
]


def skim(aid: int, extra: list[str] | None = None, max_hits: int = 25) -> str:
    path = MD / f"{aid}.md"
    if not path.is_file():
        return f"MISSING {aid}"
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    head = "\n".join(lines[:80])
    keys = DEFAULT_KEYS + (extra or [])
    pat = re.compile("|".join(f"(?:{k})" for k in keys), re.I)
    hits = []
    for i, line in enumerate(lines, 1):
        if pat.search(line):
            hits.append(f"{i}: {line.strip()[:220]}")
            if len(hits) >= max_hits:
                break
    return f"=== {aid} bytes={path.stat().st_size} lines={len(lines)} ===\n{head}\n---HITS---\n" + "\n".join(hits)


if __name__ == "__main__":
    aids = [int(x) for x in sys.argv[1:]]
    for aid in aids:
        print(skim(aid))
        print()
