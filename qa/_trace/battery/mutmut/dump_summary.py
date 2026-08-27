import re
import sys
from pathlib import Path

from mutmut.__main__ import (
    Config,
    find_mutant,
    get_diff_for_mutant,
    orig_function_and_class_names_from_key,
)

Config.ensure_loaded()

results_path = "/root/mutmut_results.txt"
out_path = "/root/survivors_summary.txt"

survived = []
with open(results_path) as f:
    for line in f:
        line = line.strip()
        if line.endswith(": survived"):
            name = line[: -len(": survived")].strip()
            survived.append(name)

print(f"Total survived to process: {len(survived)}", file=sys.stderr)


def find_line(path: Path, func_name: str, class_name: str | None) -> int:
    text = Path(path).read_text().splitlines()
    def_re = re.compile(r"^(\s*)def\s+" + re.escape(func_name) + r"\s*\(")
    class_re = re.compile(r"^class\s+" + re.escape(class_name) + r"\b") if class_name else None

    start = 0
    if class_re:
        for i, line in enumerate(text):
            if class_re.match(line):
                start = i
                break
    for i in range(start, len(text)):
        if def_re.match(text[i]):
            return i + 1  # 1-indexed
    return -1


rows = []
with open(out_path, "w") as out:
    for name in survived:
        try:
            m = find_mutant(name)
            path = m.path  # e.g. src/qmf/core/chrono.py
            func_name, class_name = orig_function_and_class_names_from_key(name)
            line_no = find_line(path, func_name, class_name)
            diff = get_diff_for_mutant(name, path=path)
            changed = [
                line
                for line in diff.splitlines()
                if (line.startswith("-") and not line.startswith("---"))
                or (line.startswith("+") and not line.startswith("+++"))
            ]
            # pair up removed/added for a compact one-liner
            removed = [line[1:].strip() for line in changed if line.startswith("-")]
            added = [line[1:].strip() for line in changed if line.startswith("+")]
            oneline = " || ".join(
                f"{r} -> {a}" for r, a in zip(removed, added) if r != a
            )
            if not oneline:
                oneline = " ;; ".join(changed)
            qualified = f"{class_name + '.' if class_name else ''}{func_name}"
            out.write(f"{path}:{line_no}\t{qualified}\t{name}\t{oneline}\n")
            rows.append((path, line_no, qualified, name, oneline))
        except Exception as e:  # noqa: BLE001
            out.write(f"ERROR\t{name}\t{e!r}\n")

print("done", file=sys.stderr)

# quick per-file breakdown to stderr
from collections import Counter

file_counts = Counter(r[0] for r in rows)
print(f"By file: {dict(file_counts)}", file=sys.stderr)
