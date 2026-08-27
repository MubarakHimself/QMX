#!/usr/bin/env python3
"""
Deterministic cross-check of Skylos dead-code findings against Vulture
findings and coverage.py "never executed" line data.

Inputs (relative to battery/):
  skylos/dead-code-findings.csv
  vulture/vulture-60.txt, vulture/vulture-80.txt, vulture/vulture-100.txt
  coverage/uncovered-lines.csv

Outputs:
  intersection/dead-code-verdict.csv
  intersection/SUMMARY.txt
"""
import csv
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SKYLOS_CSV = BASE / "skylos" / "dead-code-findings.csv"
VULTURE_FILES = [
    BASE / "vulture" / "vulture-60.txt",
    BASE / "vulture" / "vulture-80.txt",
    BASE / "vulture" / "vulture-100.txt",
]
COVERAGE_CSV = BASE / "coverage" / "uncovered-lines.csv"
OUT_CSV = Path(__file__).resolve().parent / "dead-code-verdict.csv"
OUT_SUMMARY = Path(__file__).resolve().parent / "SUMMARY.txt"

LINE_WINDOW = 2

# The 4 vulture 100%-confidence findings to reverse-check against Skylos.
REVERSE_CHECK = [
    ("packages/qmf-core/src/qmf/core/secret.py", 198, "format_spec"),
    ("packages/qmf-core/src/qmf/core/secret.py", 219, "protocol"),
    ("packages/qmf-core/tests/test_sinks.py", 165, "thing"),
    ("packages/qmf-registry/src/qmf/registry/persistence.py", 402, "exc_info"),
]


def norm_path(p: str) -> str:
    return p.strip().replace("\\", "/")


def load_skylos(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        lines = f.readlines()
    # First line is a run-metadata comment (starts with '#'); skip it.
    data_lines = [ln for ln in lines if not ln.lstrip().startswith("#")]
    reader = csv.DictReader(data_lines)
    for r in reader:
        rows.append(
            {
                "subtype": r["subtype"].strip(),
                "file": norm_path(r["file"]),
                "line": int(r["line"]),
                "symbol": r["symbol"].strip(),
                "confidence": r["confidence"].strip(),
                "classification": r["classification"].strip(),
            }
        )
    return rows


VULTURE_RE = re.compile(
    r"^(?P<file>.+):(?P<line>\d+):\s*unused\s+(?P<kind>[a-zA-Z ]+?)\s+'(?P<symbol>[^']+)'\s+\((?P<conf>\d+)%\s+confidence\)\s*$"
)


def load_vulture(paths):
    """Union of all vulture findings across the three threshold files,
    deduplicated by (file, line, symbol, kind, confidence)."""
    seen = set()
    findings = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            for raw in f:
                raw = raw.rstrip("\n")
                if not raw.strip():
                    continue
                m = VULTURE_RE.match(raw)
                if not m:
                    continue
                key = (
                    norm_path(m.group("file")),
                    int(m.group("line")),
                    m.group("symbol"),
                    m.group("kind").strip(),
                    m.group("conf"),
                )
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    {
                        "file": key[0],
                        "line": key[1],
                        "symbol": key[2],
                        "kind": key[3],
                        "confidence": key[4],
                    }
                )
    return findings


def parse_ranges(range_str):
    """Parse a compressed range string like '56-57,65,76,82' into a list
    of (start, end) tuples (inclusive)."""
    ranges = []
    range_str = range_str.strip()
    if not range_str:
        return ranges
    for part in range_str.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            ranges.append((int(start_s), int(end_s)))
        else:
            n = int(part)
            ranges.append((n, n))
    return ranges


def load_coverage(path):
    """Return dict: normalized file path -> list of (start, end) uncovered
    line ranges."""
    coverage = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            file_norm = norm_path(r["file"])
            ranges = parse_ranges(r["uncovered_ranges"])
            coverage[file_norm] = ranges
    return coverage


def line_in_ranges(line, ranges):
    for start, end in ranges:
        if start <= line <= end:
            return True
    return False


def find_vulture_match(file_norm, line, vulture_findings):
    """Return sorted list of distinct confidence values (as strings) for
    vulture findings in the same file within +/- LINE_WINDOW lines."""
    confidences = set()
    for v in vulture_findings:
        if v["file"] != file_norm:
            continue
        if abs(v["line"] - line) <= LINE_WINDOW:
            confidences.add(int(v["confidence"]))
    return sorted(confidences, reverse=True)


def find_skylos_match(file_norm, line, skylos_findings):
    for s in skylos_findings:
        if s["file"] != file_norm:
            continue
        if abs(s["line"] - line) <= LINE_WINDOW:
            return s
    return None


def main():
    skylos_findings = load_skylos(SKYLOS_CSV)
    vulture_findings = load_vulture(VULTURE_FILES)
    coverage = load_coverage(COVERAGE_CSV)

    out_rows = []
    bucket_counts = {
        "THREE_WAY": 0,
        "TWO_WAY_VULTURE": 0,
        "TWO_WAY_COVERAGE": 0,
        "SKYLOS_ONLY": 0,
    }

    for s in skylos_findings:
        file_norm = s["file"]
        line = s["line"]

        v_confidences = find_vulture_match(file_norm, line, vulture_findings)
        vulture_matched = len(v_confidences) > 0
        vulture_match_field = (
            ";".join(f"{c}%" for c in v_confidences) if vulture_matched else "no_match"
        )

        ranges = coverage.get(file_norm, [])
        never_executed = line_in_ranges(line, ranges)

        if vulture_matched and never_executed:
            verdict = "THREE_WAY"
        elif vulture_matched and not never_executed:
            verdict = "TWO_WAY_VULTURE"
        elif (not vulture_matched) and never_executed:
            verdict = "TWO_WAY_COVERAGE"
        else:
            verdict = "SKYLOS_ONLY"

        bucket_counts[verdict] += 1

        out_rows.append(
            {
                "subtype": s["subtype"],
                "file": file_norm,
                "line": line,
                "symbol": s["symbol"],
                "vulture_match": vulture_match_field,
                "never_executed": never_executed,
                "verdict": verdict,
                "direction": "",
            }
        )

    # Reverse check: the 4 vulture 100%-confidence findings against Skylos's 79.
    reverse_results = []
    for file_raw, line, symbol in REVERSE_CHECK:
        file_norm = norm_path(file_raw)
        match = find_skylos_match(file_norm, line, skylos_findings)
        found = match is not None
        reverse_results.append((file_norm, line, symbol, found))
        if not found:
            ranges = coverage.get(file_norm, [])
            never_executed = line_in_ranges(line, ranges)
            out_rows.append(
                {
                    "subtype": "unused_variable",
                    "file": file_norm,
                    "line": line,
                    "symbol": symbol,
                    "vulture_match": "100%",
                    "never_executed": never_executed,
                    "verdict": "",
                    "direction": "vulture_high",
                }
            )

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "subtype",
                "file",
                "line",
                "symbol",
                "vulture_match",
                "never_executed",
                "verdict",
                "direction",
            ],
        )
        writer.writeheader()
        writer.writerows(out_rows)

    # Summary
    lines = []
    lines.append("Dead-code verdict summary")
    lines.append(f"Skylos findings processed: {len(skylos_findings)}")
    lines.append("")
    lines.append("Bucket counts:")
    for bucket in ["THREE_WAY", "TWO_WAY_VULTURE", "TWO_WAY_COVERAGE", "SKYLOS_ONLY"]:
        lines.append(f"  {bucket}: {bucket_counts[bucket]}")
    lines.append("")
    lines.append("THREE_WAY rows:")
    for r in out_rows:
        if r["verdict"] == "THREE_WAY":
            lines.append(f"  {r['file']}:{r['line']} {r['symbol']}")
    lines.append("")
    lines.append("TWO_WAY_VULTURE rows:")
    for r in out_rows:
        if r["verdict"] == "TWO_WAY_VULTURE":
            lines.append(f"  {r['file']}:{r['line']} {r['symbol']}")
    lines.append("")
    lines.append("TWO_WAY_COVERAGE rows:")
    for r in out_rows:
        if r["verdict"] == "TWO_WAY_COVERAGE":
            lines.append(f"  {r['file']}:{r['line']} {r['symbol']}")
    lines.append("")
    lines.append("Reverse check (vulture 100%-confidence findings vs Skylos 79):")
    for file_norm, line, symbol, found in reverse_results:
        status = "FOUND in Skylos" if found else "MISSING from Skylos (flagged direction=vulture_high)"
        lines.append(f"  {file_norm}:{line} {symbol} -> {status}")

    with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
