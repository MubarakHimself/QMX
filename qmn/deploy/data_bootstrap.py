"""Restricted ``just node-data-bootstrap`` recipe (TN-13 / Story 27.2).

Check mode plans Dukascopy history into the immutable raw archive with
provider identity, personal-use licence, and a resumable checkpoint — without
touching the live datafeed. Fixture apply writes injected hour payloads into
an isolated archive. Live ``--apply`` without ``--fixture-root`` is refused.
Venue paging is planned only for the recent continuity gap inside the
documented rate and one-week span cap.

DevOps only: never imports ``qmn.host`` / ``qmn.doors``, never places, cancels,
amends, flattens, promotes, or activates (AR-79 / DEC-0202). Never urllib.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Final, Literal

__all__ = [
    "BOOTSTRAP_RECIPE",
    "CHECKPOINT_NAME",
    "LICENSE_TAG",
    "SOURCE_IDENTITY",
    "VENUE_HISTORICAL_RATE_PER_S",
    "VENUE_SPAN_CAP_NS",
    "BootstrapPlan",
    "BootstrapStep",
    "apply_plan_to_fixture",
    "build_bootstrap_plan",
    "main",
    "write_plan",
]

_DEPLOY_ROOT: Final[Path] = Path(__file__).resolve().parent
BOOTSTRAP_RECIPE: Final[str] = "node-data-bootstrap"
SOURCE_IDENTITY: Final[str] = "dukascopy"
LICENSE_TAG: Final[str] = "internal-only"
CHECKPOINT_NAME: Final[str] = "bootstrap-checkpoint.json"
VENUE_HISTORICAL_RATE_PER_S: Final[int] = 5
VENUE_SPAN_CAP_NS: Final[int] = 7 * 24 * 3_600 * 1_000_000_000
DEFAULT_ARCHIVE: Final[str] = "/var/lib/qmx/archive"


def _load_sibling(module_name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_boundary = _load_sibling("qmn_deploy_boundary", _DEPLOY_ROOT / "boundary.py")
_safe_io = _load_sibling("qmn_deploy_safe_io", _DEPLOY_ROOT / "safe_io.py")


@dataclass(frozen=True, slots=True)
class BootstrapStep:
    """One planned bootstrap action. Never a live HTTP fetch."""

    kind: str
    target: str
    detail: str
    check_mode_only: bool = False


@dataclass(frozen=True, slots=True)
class BootstrapPlan:
    """Check-mode or fixture-apply plan. JSON-able; no live URLs."""

    recipe: str
    principal: str
    ok: bool
    mode: str
    source: str
    license_tag: str
    archive: str
    venue_rate_per_s: int
    venue_span_cap_ns: int
    live_network: bool
    ad_hoc: bool
    steps: tuple[BootstrapStep, ...]
    findings: tuple[str, ...]

    def to_jsonable(self) -> dict[str, object]:
        return {
            "recipe": self.recipe,
            "principal": self.principal,
            "ok": self.ok,
            "mode": self.mode,
            "source": self.source,
            "license_tag": self.license_tag,
            "archive": self.archive,
            "venue_rate_per_s": self.venue_rate_per_s,
            "venue_span_cap_ns": self.venue_span_cap_ns,
            "live_network": self.live_network,
            "ad_hoc": self.ad_hoc,
            "steps": [
                {
                    "kind": step.kind,
                    "target": step.target,
                    "detail": step.detail,
                    "check_mode_only": step.check_mode_only,
                }
                for step in self.steps
            ],
            "findings": list(self.findings),
        }


def build_bootstrap_plan(
    *,
    mode: Literal["check", "apply"] = "check",
    archive: str = DEFAULT_ARCHIVE,
    symbols: Sequence[str] = ("EURUSD",),
    venue_gap_ns: int = 0,
) -> BootstrapPlan:
    """Plan an idempotent, licensed, checkpointed Dukascopy bootstrap."""
    findings: list[str] = []
    steps: list[BootstrapStep] = [
        BootstrapStep(
            kind="source_identity",
            target=SOURCE_IDENTITY,
            detail="Dukascopy is the node deep-history source; never merged with venue ticks",
        ),
        BootstrapStep(
            kind="license_tag",
            target=LICENSE_TAG,
            detail="personal-use posture recorded on every window (DEC-0170)",
        ),
        BootstrapStep(
            kind="provenance",
            target="acquisition-metadata",
            detail="provider identity, licence, and recipe provenance ride the archive row",
        ),
        BootstrapStep(
            kind="checkpoint",
            target=CHECKPOINT_NAME,
            detail="idempotent resume cursor in the immutable raw archive",
        ),
        BootstrapStep(
            kind="refuse_live_network",
            target="dukascopy-datafeed",
            detail="check-mode and fixture apply never open HTTPS to the provider",
            check_mode_only=True,
        ),
        BootstrapStep(
            kind="refuse_ad_hoc",
            target="run-loop",
            detail="runs never fetch data ad hoc; only this recipe acquires history",
        ),
    ]
    for symbol in symbols:
        steps.append(
            BootstrapStep(
                kind="dukascopy_hours",
                target=symbol,
                detail="bounded hourly bi5 windows through the injected CT-15 adapter",
            )
        )
    if venue_gap_ns < 0:
        findings.append("venue continuity gap must be non-negative")
    elif venue_gap_ns > VENUE_SPAN_CAP_NS:
        findings.append(
            "venue paging refuses a gap above the one-week span cap; "
            "bridge only the recent continuity window"
        )
        steps.append(
            BootstrapStep(
                kind="refuse_span_cap",
                target="venue-tick-history",
                detail=f"gap_ns={venue_gap_ns} exceeds cap_ns={VENUE_SPAN_CAP_NS}",
            )
        )
    elif venue_gap_ns > 0:
        steps.append(
            BootstrapStep(
                kind="venue_bridge",
                target="venue-tick-history",
                detail=(
                    f"hasMore paging at {VENUE_HISTORICAL_RATE_PER_S} req/s historical "
                    "for the gap after the archive only"
                ),
            )
        )
    ok = len(findings) == 0
    return BootstrapPlan(
        recipe=BOOTSTRAP_RECIPE,
        principal=_boundary.OPS_PRINCIPAL_NAME,
        ok=ok,
        mode=mode,
        source=SOURCE_IDENTITY,
        license_tag=LICENSE_TAG,
        archive=archive,
        venue_rate_per_s=VENUE_HISTORICAL_RATE_PER_S,
        venue_span_cap_ns=VENUE_SPAN_CAP_NS,
        live_network=False,
        ad_hoc=False,
        steps=tuple(steps),
        findings=tuple(findings),
    )


def apply_plan_to_fixture(
    plan: BootstrapPlan,
    *,
    fixture_root: Path,
    hours: Mapping[str, bytes] | None = None,
) -> dict[str, object]:
    """Write injected hour payloads + checkpoint into ``fixture_root`` archive.

    Never fetches. ``hours`` is the injected CT-15 transport payload keyed by
    hour-path reference.
    """
    archive = fixture_root / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    raw = archive / "raw" / SOURCE_IDENTITY
    raw.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for path_ref, payload in (hours or {}).items():
        dest = raw / path_ref.replace("/", "_")
        dest.parent.mkdir(parents=True, exist_ok=True)
        _safe_io.write_bytes_exclusive_no_follow(dest, payload, contain_within=fixture_root)
        sidecar = dest.with_suffix(dest.suffix + ".provenance.json")
        _safe_io.write_text_exclusive_no_follow(
            sidecar,
            json.dumps(
                {
                    "source": SOURCE_IDENTITY,
                    "licence": LICENSE_TAG,
                    "path": path_ref,
                    "recipe": BOOTSTRAP_RECIPE,
                    "live_network": False,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            contain_within=fixture_root,
        )
        written.append(path_ref)
    checkpoint = {
        "symbol": next(
            (step.target for step in plan.steps if step.kind == "dukascopy_hours"),
            "EURUSD",
        ),
        "last_end_ns": 0,
        "hours_completed": len(written),
        "source": SOURCE_IDENTITY,
        "license_tag": LICENSE_TAG,
        "resumable": True,
        "idempotent": True,
    }
    _safe_io.write_text_exclusive_no_follow(
        archive / CHECKPOINT_NAME,
        json.dumps(checkpoint, indent=2, sort_keys=True) + "\n",
        contain_within=fixture_root,
    )
    return {
        "ok": plan.ok,
        "written": written,
        "checkpoint": checkpoint,
        "live_network": False,
    }


def write_plan(plan: BootstrapPlan, destination: Path) -> None:
    """Write the plan JSON. Payload never carries a live URL or fetch."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    _safe_io.write_text_exclusive_no_follow(
        destination,
        json.dumps(plan.to_jsonable(), indent=2, sort_keys=True) + "\n",
        contain_within=destination.parent,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="node-data-bootstrap",
        description=(
            "Plan or fixture-apply history bootstrap (DevOps only). "
            "Default is check mode. Never downloads from Dukascopy in this process."
        ),
    )
    parser.add_argument(
        "--check-mode",
        action="store_true",
        default=True,
        help="plan only; never fetch (default)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="apply on the VPS (refused off-VPS unless --fixture-root)",
    )
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=None,
        help="fixture apply root (CI/tests only); never a live download",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write plan JSON to this path",
    )
    parser.add_argument(
        "--venue-gap-ns",
        type=int,
        default=0,
        help="optional continuity-gap span to page from the venue (capped at one week)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.apply and args.fixture_root is None:
        print(
            "refusing --apply without --fixture-root: do not run a live Dukascopy "
            "download from this process; CI and workstations use --check-mode or "
            "--fixture-root only",
            file=sys.stderr,
        )
        return 2

    mode: Literal["check", "apply"] = "apply" if args.fixture_root is not None else "check"
    plan = build_bootstrap_plan(mode=mode, venue_gap_ns=args.venue_gap_ns)
    if args.fixture_root is not None:
        apply_plan_to_fixture(plan, fixture_root=args.fixture_root)
    payload = json.dumps(plan.to_jsonable(), indent=2, sort_keys=True)
    if args.out is not None:
        write_plan(plan, args.out)
    else:
        print(payload)
    return 0 if plan.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
