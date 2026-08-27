import sys

from mutmut.__main__ import Config, find_mutant, get_diff_for_mutant

Config.ensure_loaded()

results_path = "/root/mutmut_results.txt"
out_path = "/root/survivors_diffs.txt"

survived = []
with open(results_path) as f:
    for line in f:
        line = line.strip()
        if line.endswith(": survived"):
            name = line[: -len(": survived")].strip()
            survived.append(name)

print(f"Total survived to process: {len(survived)}", file=sys.stderr)

with open(out_path, "w") as out:
    for name in survived:
        try:
            m = find_mutant(name)
            diff = get_diff_for_mutant(name, path=m.path)
            out.write(f"===== {name} | file={m.path} =====\n")
            out.write(diff + "\n\n")
        except Exception as e:  # noqa: BLE001
            out.write(f"===== {name} | ERROR: {e!r} =====\n\n")

print("done", file=sys.stderr)
