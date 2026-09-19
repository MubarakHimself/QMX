"""Extract prose core from an MQL5 article (strip images/code bloat). Read-only."""
from __future__ import annotations

import re
import sys
from pathlib import Path

MD = Path(r"C:\Users\Mubarak\Desktop\QMX\.worktrees\mql5-library\data\mql5-library\md")


def clean(text: str) -> str:
    # drop data-uri / huge base64 blobs
    text = re.sub(r"!\[[^\]]*\]\(data:[^)]+\)", "[img]", text)
    text = re.sub(r"!\[[^\]]*\]\(https?://[^)]+\)", "[img]", text)
    # collapse fenced code to markers
    text = re.sub(r"```[\s\S]*?```", "\n[CODE]\n", text)
    # drop very long lines (tables of numbers / remaining base64)
    lines = []
    for ln in text.splitlines():
        if len(ln) > 500:
            continue
        lines.append(ln)
    return "\n".join(lines)


def sections(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"(?m)^(#{1,3} .+)$", text)
    out = []
    if parts and parts[0].strip():
        out.append(("__preamble__", parts[0]))
    for i in range(1, len(parts), 2):
        title = parts[i].lstrip("# ").strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        out.append((title, body))
    return out


def extract(aid: int, max_chars: int = 12000) -> str:
    path = MD / f"{aid}.md"
    if not path.is_file():
        return f"MISSING {aid}"
    raw = path.read_text(encoding="utf-8", errors="replace")
    text = clean(raw)
    secs = sections(text)
    # prefer intro/conclusion/method narrative
    prefer = re.compile(
        r"intro|conclusion|summary|result|method|filter|gate|regime|discussion|"
        r"look.?ahead|limitation|test|edge|invalid|cooldown|news|time|risk|"
        r"lyapunov|entropy|mutual|hawkes|ising|matrix|chaos|transfer",
        re.I,
    )
    chosen = []
    for title, body in secs:
        body = body.strip()
        if not body:
            continue
        score = 2 if prefer.search(title) else 0
        if prefer.search(body[:800]):
            score += 1
        chosen.append((score, title, body))
    chosen.sort(key=lambda x: -x[0])
    # always include first real heading after preamble
    pieces = [f"=== {aid} clean_chars={len(text)} sections={len(secs)} ==="]
    # meta from frontmatter-ish first 30 lines of clean
    pieces.append("\n".join(text.splitlines()[:40]))
    budget = max_chars
    seen = set()
    for score, title, body in chosen:
        if title in seen:
            continue
        seen.add(title)
        chunk = f"\n## {title}\n{body[:3500]}"
        if len(chunk) > budget:
            chunk = chunk[:budget]
            pieces.append(chunk)
            break
        pieces.append(chunk)
        budget -= len(chunk)
        if budget < 800:
            break
    return "\n".join(pieces)


if __name__ == "__main__":
    for a in sys.argv[1:]:
        print(extract(int(a)))
        print("\n" + "=" * 60 + "\n")
