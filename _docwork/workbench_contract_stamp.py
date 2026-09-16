#!/usr/bin/env python3
"""Reconcile stale defined-unwired / no code exists stamps (DEC-0286). Idempotent."""
from pathlib import Path

ROOT = Path(r"C:/Users/Mubarak/Desktop/QMX/docs/contracts")

TARGETS = [
    "ct-22-book-charter.yaml",
    "ct-23-risk-evaluation.yaml",
    "ct-24-book-mode.yaml",
    "ct-25-risk-journal.yaml",
    "ct-27-bms-definition.yaml",
    "ct-28-book-binding.yaml",
    "ct-29-exit-record.yaml",
    "ct-30-control-action.yaml",
    "ct-31-control-window.yaml",
    "ct-32-performance-result.yaml",
    "ct-33-bot-definition.yaml",
    "ct-34-confluence.yaml",
    "ct-40-qma-wire-envelope.yaml",
    "ct-41-qma-hook-event-result.yaml",
    "ct-42-qma-plugin-manifest-context.yaml",
    "ct-43-qma-memory-provider.yaml",
    "ct-44-qma-knowledge-source.yaml",
    "ct-45-qma-model-deployment-broker.yaml",
    "ct-46-qma-execution-environment-job.yaml",
    "ct-47-qma-experiment-spec.yaml",
    "ct-48-qma-mailbox-envelope.yaml",
    "ct-49-qma-routine.yaml",
    "ct-50-qma-refinement-proposal.yaml",
    "ct-51-qma-task-ledger-entry.yaml",
]

STAMP = (
    "wiring_status: source-inspected  # matching source exists on "
    "integration@1b451a8 (DEC-0286); class/test existence is not end-to-end "
    "demonstration; remaining connect / composition-root / daemon-process work "
    "is not authorized from this doc"
)


def patch(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    orig = text
    if "wiring_status: source-inspected" in text and "DEC-0286" in text:
        print(f"skip {path.name}: already source-inspected")
        return
    lines = text.splitlines(keepends=True)
    out = []
    for line in lines:
        if line.startswith("wiring_status: defined-unwired"):
            nl = "\n" if line.endswith("\n") else ""
            out.append(STAMP + nl)
            continue
        if "defined-unwired: no code exists" in line:
            line = line.replace(
                "defined-unwired: no code exists",
                "source-inspected on integration@1b451a8 (DEC-0286); not end-to-end demonstrated",
            )
        if "no code exists" in line and not line.startswith("wiring_status:"):
            line = line.replace(
                "no code exists",
                "source-inspected on integration@1b451a8; not end-to-end demonstrated (DEC-0286)",
            )
        out.append(line)
    new = "".join(out)
    rebuilt = []
    for line in new.splitlines(keepends=True):
        if line.startswith("decisions:") and "DEC-0286" not in line and line.rstrip().endswith("]"):
            line = line.rstrip("\n")[:-1] + ", DEC-0286]\n"
        rebuilt.append(line)
    new = "".join(rebuilt)
    if new != orig:
        path.write_text(new, encoding="utf-8")
        print(f"patched {path.name}")
    else:
        print(f"unchanged {path.name}")


def main() -> None:
    for name in TARGETS:
        patch(ROOT / name)


if __name__ == "__main__":
    main()
