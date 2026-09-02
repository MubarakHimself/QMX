"""Child-process entry for ``python -m qmn.replay`` (Story 27.7 / 27.8)."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from qmf.core import TypedRefusal, is_ok, is_refusal

from qmn.replay.ledger import TERMINAL_REFUSE
from qmn.replay.session import run_recorded_day
from qmn.replay.spawn import spec_from_jsonable, write_text_exclusive_no_follow


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
        _write_envelope(
            args.output,
            {
                "world": "replay",
                "status": TERMINAL_REFUSE,
                "refusal": {
                    "category": "invalid input",
                    "field": "spec",
                    "reason": "replay spec is not readable JSON",
                },
            },
        )
        print("replay spec is not readable JSON", file=sys.stderr)
        return 2
    spec = spec_from_jsonable(raw)
    if is_refusal(spec):
        _write_envelope(args.output, _refusal_envelope(spec))
        print(str(spec.context.get("reason", spec)), file=sys.stderr)
        return 1
    report = run_recorded_day(spec.value)
    if is_refusal(report):
        _write_envelope(args.output, _refusal_envelope(report))
        print(str(report.context.get("reason", report)), file=sys.stderr)
        return 1
    _write_envelope(args.output, dict(report.value.as_mapping()))
    return 0 if is_ok(report) else 1


def _refusal_envelope(refusal: TypedRefusal) -> dict[str, object]:
    payload: dict[str, object] = {
        "category": refusal.category.value,
        "field": str(refusal.context.get("field", "terminal")),
        "reason": str(refusal.context.get("reason", "")),
    }
    failure_id = refusal.context.get("failure_id")
    if isinstance(failure_id, str) and failure_id.strip() != "":
        payload["failure_id"] = failure_id
    return {"world": "replay", "status": TERMINAL_REFUSE, "refusal": payload}


def _write_envelope(path: Path, payload: Mapping[str, object]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_text_exclusive_no_follow(
            path,
            json.dumps(dict(payload), indent=2, sort_keys=True) + "\n",
            contain_within=path.parent,
        )
    except OSError:
        return


if __name__ == "__main__":
    raise SystemExit(main())
