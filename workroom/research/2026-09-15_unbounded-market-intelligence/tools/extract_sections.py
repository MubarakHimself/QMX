#!/usr/bin/env python3
"""Pull method-relevant sections from regime candidate articles for full-read notes."""
import re
from pathlib import Path

MD = Path(r"C:\Users\Mubarak\Desktop\QMX\.worktrees\mql5-library\data\mql5-library\md")
OUT = Path(__file__).resolve().parent.parent / "recovery_staging" / "regime_section_dumps"
OUT.mkdir(parents=True, exist_ok=True)

IDS = [
    15541, 23444, 15033, 23488, 17781, 22484, 22258, 22754, 23677, 23137,
    17917, 22783, 23734, 20996, 21833, 18192, 11930, 22807, 21743, 22220,
    23149, 20414, 15222, 22553, 23372, 21142, 16213, 3395, 20037, 752,
    4534, 6834, 2930, 16030, 17273, 23451, 22638, 23310, 18097, 15445,
    22290, 23491, 21351, 20478, 19797, 16971, 18187, 3886, 22274, 22755,
]

# Section headers and claim phrases to keep
KEEP = re.compile(
    r"(?i)^(#{1,3}\s|"
    r".{0,20}(regime|HMM|Markov|MAMA|Ehlers|Nash|Hurst|GARCH|EGARCH|GJR|"
    r"catch22|ADX|Kalman|entropy|chopp|sideways|ranging|trending|volatile|"
    r"playbook|switch|filter|threshold|state|classif|Viterbi|Baum|"
    r"conclusion|result|limitation|backtest|formula|algorithm|"
    r"fractal|ARFIMA|BOSS|L1 trend|ATR|time filter|flat|"
    r"mean.?reversion|volatility|dominant cycle|Hilbert))"
)

# Also keep lines near formula-ish content
FORMULAISH = re.compile(r"(?i)(σ|sigma|α|β|ω|Hurst|H\(|ADX|ATR|entropy|threshold|percentile|P\(|state\s*=|regime\s*=)")


def strip_base64(text: str) -> str:
    # drop huge data URIs
    text = re.sub(r"data:image/[^)]+\)", "IMAGE)", text)
    text = re.sub(r"!\[.*?\]\(data:[^)]+\)", "[img]", text)
    return text


def dump_article(aid: int) -> None:
    p = MD / f"{aid}.md"
    if not p.exists():
        print(f"MISSING {aid}")
        return
    raw = p.read_text(encoding="utf-8", errors="ignore")
    raw = strip_base64(raw)
    lines = raw.splitlines()
    # Drop YAML frontmatter after first ---
    start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, min(30, len(lines))):
            if lines[i].strip() == "---":
                start = i + 1
                break
    body = lines[start:]

    kept = []
    # Always keep title region first 80 content lines (sans images)
    head_kept = 0
    for ln in body:
        if head_kept >= 60:
            break
        if ln.strip().startswith("![") or "data:image" in ln:
            continue
        if len(ln.strip()) < 2:
            continue
        kept.append(ln)
        head_kept += 1
    kept.append("\n----- METHOD/CLAIM SWEEP -----\n")

    # Sweep: keep headers + surrounding context for matches
    for i, ln in enumerate(body):
        if ln.startswith("#") or KEEP.search(ln) or FORMULAISH.search(ln):
            # context
            lo = max(0, i - 1)
            hi = min(len(body), i + 3)
            chunk = body[lo:hi]
            for c in chunk:
                if c not in kept[-20:]:
                    kept.append(c)

    # Also grab Conclusion section fully
    conc_idx = None
    for i, ln in enumerate(body):
        if re.match(r"(?i)^#{1,3}\s*conclusion", ln):
            conc_idx = i
            break
    if conc_idx is not None:
        kept.append("\n----- CONCLUSION -----\n")
        kept.extend(body[conc_idx : conc_idx + 80])

    out = OUT / f"{aid}.txt"
    text = "\n".join(kept)
    # Cap size
    if len(text) > 80000:
        text = text[:80000] + "\n...TRUNC...\n"
    out.write_text(text, encoding="utf-8")
    print(f"{aid}: {len(kept)} lines -> {out.name} ({len(text)} chars)")


def main():
    for aid in IDS:
        dump_article(aid)


if __name__ == "__main__":
    main()
