"""Tier-1 secret-scan gate (AR-24; enforcing L34 / AR-37).

Scans the workspace's **tracked tree** for high-signal committed secrets and exits
nonzero on any finding, so ``poe check`` fails closed the instant a credential lands
in tracked content. QMF components handle secret *references*, never values, and
secret values must never appear in repositories at all — this gate catches that
mistake at Tier 1.

**Scope.** The gate walks the whole repository from the root, not just the shipped
``packages/ + extensions/ + tools/`` code: repo-root files, ``.github/workflows/``,
``queue/``, and every other tracked directory are covered, because a leaked
credential in a workflow, a queued brief, or a root dotfile is exactly as dangerous
as one in source. Covered surfaces explicitly include source, fixtures, unit files,
rendered config, logs, and refusal snapshots (QMX-F064 / Story 25.13). ``adws/`` is
scanned **read-only** (the factory machinery is never modified). Machine-noise and
vendored trees are skipped by ``SKIP_DIRS``; only this scanner's own planted fixture
corpus under ``tools/tests/fixtures`` is path-skipped so deliberately assembled fake
secrets cannot trip the live gate.

**Detection** is pattern-based and deliberately high-precision (private-key blocks,
cloud/provider access keys, and quoted credential assignments) to keep the gate free
of false alarms on ordinary content. It is a gate, not a vault: a green result means
"nothing matched the known-bad shapes", not "provably secret-free". Stdlib only; run
via ``python tools/secret_scan.py`` or ``poe secret-scan``.
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = Path(__file__).resolve()

# Machine-noise and vendored trees never scanned — the same discipline the money-path
# and ambient scanners apply. ``adw_data`` is the factory's gitignored runtime session
# output (transcripts, stamped prompts) — not tracked source — so it is skipped too;
# the tracked ``adws`` machinery is still scanned read-only.
SKIP_DIRS: frozenset[str] = frozenset(
    {
        "__pycache__",
        ".venv",
        ".git",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        ".vscode",
        "node_modules",
        "build",
        "dist",
        "adw_data",
    }
)

# Only this scanner's planted must_flag corpus is path-skipped. Project fixtures,
# unit files, rendered config, logs, and refusal snapshots stay in scope (QMX-F064).
SKIP_PATH_PREFIXES: frozenset[str] = frozenset(
    {
        "tools/tests/fixtures",
    }
)

# Surfaces the gate must cover (Story 25.13 / QMX-F064). Proven by discovery tests.
COVERED_SURFACES: frozenset[str] = frozenset(
    {
        "source",
        "fixtures",
        "unit_files",
        "rendered_config",
        "logs",
        "refusal_snapshots",
    }
)

TEXT_SUFFIXES: frozenset[str] = frozenset(
    {
        ".py",
        ".toml",
        ".cfg",
        ".ini",
        ".json",
        ".yaml",
        ".yml",
        ".md",
        ".txt",
        ".env",
        ".sample",
        ".sh",
        ".ps1",
        ".log",
        ".jsonl",
    }
)

_NamedPattern = tuple[str, re.Pattern[str]]

# High-precision shapes only. Each is unlikely to occur in ordinary content.
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


@dataclass(frozen=True)
class Finding:
    """One potential-secret match located in a tracked file."""

    path: str
    line: int
    rule: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.rule}"


def _is_skipped_path(path: Path, *, root: Path) -> bool:
    """True when ``path`` sits under a planted-corpus prefix relative to ``root``."""
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel = path.as_posix().replace("\\", "/")
    return any(rel == prefix or rel.startswith(prefix + "/") for prefix in SKIP_PATH_PREFIXES)


def iter_scanned_files(root: Path = ROOT) -> Iterator[Path]:
    """Yield every scannable file in the repository tree, root files included.

    Walks ``root`` with in-place directory pruning so a ``SKIP_DIRS`` tree (a
    virtualenv, a cache) is never descended into. The scanner's own planted fixture
    corpus under ``tools/tests/fixtures`` is path-skipped; project fixtures, unit
    files, rendered config, logs, and refusal snapshots remain in scope. Only
    recognized text suffixes are yielded, and the scanner's own source is skipped so
    its pattern definitions cannot trip it.
    """
    root_resolved = root.resolve()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        current = Path(dirpath)
        if _is_skipped_path(current, root=root_resolved):
            dirnames[:] = []
            continue
        for filename in sorted(filenames):
            path = current / filename
            if path.suffix not in TEXT_SUFFIXES:
                continue
            if path.resolve() == SELF:
                continue
            if _is_skipped_path(path, root=root_resolved):
                continue
            yield path


def scan_text(text: str, filename: str) -> list[Finding]:
    """Scan one document's text, returning source-ordered findings."""
    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for rule, pattern in PATTERNS:
            if pattern.search(line):
                findings.append(Finding(filename, lineno, rule))
    return findings


def scan_file(path: Path, *, root: Path = ROOT) -> list[Finding]:
    """Scan one file, reporting its path relative to ``root`` when possible.

    Only a regular file is read. A directory, device, FIFO or dangling symlink is not
    a document that can carry a committed secret, and reading a FIFO would block the
    gate forever, so the check sits immediately before the read it guards."""
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    try:
        rel = path.resolve().relative_to(root).as_posix()
    except ValueError:
        rel = path.as_posix()
    return scan_text(text, rel)


def scan_workspace(root: Path = ROOT) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_scanned_files(root):
        findings.extend(scan_file(path, root=root))
    return findings


def main(root: Path = ROOT) -> int:
    findings = scan_workspace(root)
    if findings:
        sys.stdout.write("secret-scan: FAIL - potential secrets found:\n")
        for finding in findings:
            sys.stdout.write(f"  {finding.render()}\n")
        return 1
    sys.stdout.write("secret-scan: clean (whole tracked tree).\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
