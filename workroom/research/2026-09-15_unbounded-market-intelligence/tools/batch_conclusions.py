"""Pull Introduction + Conclusion (+ Result/Limitation) from many articles."""
from __future__ import annotations

import re
import sys
from pathlib import Path

MD = Path(r"C:\Users\Mubarak\Desktop\QMX\.worktrees\mql5-library\data\mql5-library\md")
OUT = Path(
    r"C:\Users\Mubarak\Desktop\QMX\workroom\research\2026-09-15_unbounded-market-intelligence\recovery_staging"
)


def clean(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\(data:[^)]+\)", "[img]", text)
    text = re.sub(r"!\[[^\]]*\]\(https?://[^)]+\)", "[img]", text)
    text = re.sub(r"```[\s\S]*?```", "\n[CODE]\n", text)
    lines = [ln for ln in text.splitlines() if len(ln) <= 400]
    return "\n".join(lines)


def grab(aid: int) -> str:
    path = MD / f"{aid}.md"
    if not path.is_file():
        return f"MISSING {aid}\n"
    text = clean(path.read_text(encoding="utf-8", errors="replace"))
    # title line
    m = re.search(r'^title:\s*"(.*)"', text, re.M)
    title = m.group(1) if m else "?"
    sec = re.search(r'^section:\s*"(.*)"', text, re.M)
    section = sec.group(1) if sec else "?"
    parts = re.split(r"(?m)^(#{1,3} .+)$", text)
    want = re.compile(
        r"^(Introduction|Conclusion|Summary|Results?|Discussion|Limitations?|"
        r"Test Results|Final|What we|Key Take|Practical|Application|"
        r"Operational|Selection|Regime|Filter|Gate|Look.?ahead|"
        r"Lyapunov|Transfer|Mutual|Chaos|Method|Overview|Idea)\b",
        re.I,
    )
    blocks = [f"##### {aid} | {section} | {title}"]
    for i in range(1, len(parts), 2):
        h = parts[i].lstrip("# ").strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if want.search(h) or (i < 4 and "Intro" in h):
            # trim body
            body = re.sub(r"\n{3,}", "\n\n", body)
            body = body[:2200]
            blocks.append(f"### {h}\n{body}\n")
    if len(blocks) == 1:
        # fallback: first 1500 prose chars after title heading
        prose = re.split(r"(?m)^# ", text, maxsplit=1)
        chunk = prose[-1][:2000] if prose else text[:2000]
        blocks.append(chunk)
    return "\n".join(blocks) + "\n\n" + ("-" * 70) + "\n\n"


def main(aids: list[int], out_name: str) -> None:
    chunks = [grab(a) for a in aids]
    path = OUT / out_name
    path.write_text("\n".join(chunks), encoding="utf-8")
    print(f"wrote {path} articles={len(aids)} chars={path.stat().st_size}")


if __name__ == "__main__":
    aids = [int(x) for x in sys.argv[1:-1]]
    out = sys.argv[-1]
    main(aids, out)
