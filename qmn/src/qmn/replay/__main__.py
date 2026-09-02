"""Child-process entry for ``python -m qmn.replay`` (Story 27.7)."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from qmf.core import is_ok, is_refusal

from qmn.replay.session import run_recorded_day
from qmn.replay.spawn import spec_from_jsonable


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="qmn.replay",
        description="Credential-free recorded-day decision diff (never a trading control).",
    )
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        raw = json.loads(args.spec.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        print("replay spec is not readable JSON", file=sys.stderr)
        return 2
    spec = spec_from_jsonable(raw)
    if is_refusal(spec):
        print(str(spec.context.get("reason", spec)), file=sys.stderr)
        return 1
    report = run_recorded_day(spec.value)
    if is_refusal(report):
        print(str(report.context.get("reason", report)), file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(dict(report.value.as_mapping()), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if is_ok(report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
