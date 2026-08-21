"""Tier-1 secret-scan gate (AR-24; enforcing L34 / AR-37).

Scans the workspace's shipped source (packages/, extensions/, tools/) for
high-signal committed secrets and exits nonzero on any finding, so `poe check`
fails closed the instant a credential lands in tracked code. QMF components
handle secret *references*, never values, and secret values must never appear in
repositories at all — this gate catches that mistake at Tier 1.

Detection is pattern-based and deliberately high-precision (private-key blocks,
cloud/provider access keys, and quoted credential assignments) to keep the gate
free of false alarms on ordinary source. It is a gate, not a vault: a green
result means "nothing matched the known-bad shapes", not "provably secret-free".
Stdlib only; run via `python tools/secret_scan.py` or `poe secret-scan`.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = Path(__file__).resolve()

SCAN_ROOTS: tuple[str, ...] = ("packages", "extensions", "tools")
TEXT_SUFFIXES: frozenset[str] = frozenset(
    {".py", ".toml", ".cfg", ".ini", ".json", ".yaml", ".yml", ".md", ".txt", ".env"}
)

_NamedPattern = tuple[str, re.Pattern[str]]

# High-precision shapes only. Each is unlikely to occur in ordinary source.
PATTERNS: tuple[_NamedPattern, ...] = (
    ("private-key-block", re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----")),
    ("aws-access-key-id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    (
        "quoted-credential-assignment",
        re.compile(
            r"(?i)\b(?:password|passwd|secret|token|api[_-]?key|access[_-]?token|"
            r"refresh[_-]?token|client[_-]?secret)\b\s*[:=]\s*[\"'][^\"'\s]{8,}[\"']"
        ),
    ),
)


def _iter_files(roots: Iterable[str]) -> Iterator[Path]:
    for root in roots:
        base = ROOT / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
                continue
            if path.resolve() == SELF:
                # The scanner's own pattern definitions must not trip it.
                continue
            yield path


def _scan_file(path: Path) -> list[str]:
    findings: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return findings
    rel = path.relative_to(ROOT).as_posix()
    for lineno, line in enumerate(text.splitlines(), start=1):
        for rule, pattern in PATTERNS:
            if pattern.search(line):
                findings.append(f"{rel}:{lineno}: {rule}")
    return findings


def main() -> int:
    findings: list[str] = []
    for path in _iter_files(SCAN_ROOTS):
        findings.extend(_scan_file(path))
    if findings:
        sys.stdout.write("secret-scan: FAIL - potential secrets found:\n")
        for finding in findings:
            sys.stdout.write(f"  {finding}\n")
        return 1
    sys.stdout.write(f"secret-scan: clean ({', '.join(SCAN_ROOTS)}).\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
