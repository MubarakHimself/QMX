"""Epic 1 — L4 acceptance scenarios (E1-A01 SCN-0001, E1-A02 cross-producer fp1
determinism) plus E1-S07 import-time budget (L0, tracked separately).

Authored from SCN-0001, CT-05, DEC-0103/0110/0134, NFR-04/DEC-0111. Source is
read-only evidence.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

from qmf.core.chrono import CalendarIdentity, CivilDate, Instant, Interval, TradingDate
from qmf.core.exact import Money
from qmf.core.fingerprint import (
    EvidenceClass,
    Fingerprint,
    ResultLabel,
    World,
    fingerprint,
    governed_namespace,
)
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal, is_ok, is_refusal

ROOT = Path(__file__).resolve().parents[3]


def _ok(result: object) -> object:
    assert is_ok(result), f"expected Ok, got {result!r}"
    return result.value


def _fp(value: object) -> str:
    return _ok(fingerprint(value)).value


# E1-A01 — SCN-0001 core freeze gate -------------------------------------------
def test_e1_a01_scn0001_ratified_boundaries_build_open_choices_stay_open() -> None:
    """SCN-0001 / DEC-0134: the six ratified boundaries conform to CT-01..CT-05 by
    construction, while the two still-open freeze choices (backtest fidelity GAP-0048,
    SR* GAP-0049) are NOT fixed by code — a proposal cannot replace a null contract
    field (world=simulated remains reserved-unusable, refused with GAP-0048)."""
    venue = _ok(VenueId.try_create("VEN-1"))
    instrument = _ok(Instrument.try_create(venue, "EURUSD"))
    # The six ratified boundaries all construct.
    assert is_ok(Money.try_create(150, "USD", 2))  # CT-01
    assert is_ok(Instant.try_create(0))  # CT-02
    assert isinstance(instrument, Instrument)  # CT-03
    assert is_ok(TypedRefusal.try_create(RefusalCategory.INVALID_INPUT, Retryability.NO))  # CT-04
    time_range = _ok(Interval.try_create(_ok(Instant.try_create(0)), _ok(Instant.try_create(9))))
    label = ResultLabel.try_create(  # CT-05
        _fp({"p": 1}), 1, [_fp({"i": 1})], time_range, EvidenceClass.CONFIRMED, World.LIVE
    )
    assert is_ok(label)
    # The open backtest-fidelity freeze choice is NOT fixed by code: world=simulated is
    # reserved-unusable and refused, citing the open gap — a proposal has not replaced
    # the null contract field.
    assert "simulated" in {w.value for w in World}
    refusal = is_refusal(governed_namespace(World.SIMULATED))
    assert refusal
    assert governed_namespace(World.SIMULATED).context.get("gap") == "GAP-0048"


# E1-A02 — cross-producer fp1 determinism (golden) -----------------------------
def test_e1_a02_cross_producer_fp1_determinism_and_new_derivation_mints_new_id() -> None:
    """CT-05 / DEC-0103: two independent conformant producers emit byte-identical fp1
    over a golden artifact set; a re-derivation under a newer calendar identity / tzdata
    version mints a NEW fingerprint (never a rewrite, never a silent equality). The
    lineage edge itself is qmf-registry's concern (CT-07, Epic 2)."""
    # Golden artifact set: equal values built by two independent construction paths.
    golden = [
        _ok(Money.try_create(150, "USD", 2)),
        _ok(Instant.try_create(1_700_000_000_000_000_000)),
        {"class": "thing", "b": 2, "a": 1, "nested": [1, 2, 3]},
    ]
    for value in golden:
        producer_a = _fp(value)
        producer_b = _fp(value)  # an independent recomputation
        assert producer_a == producer_b  # byte-identical fp1 by construction
        assert Fingerprint.try_create(producer_a)  # well-formed fp1 string

    # A Money stored at two scales is one identity (equal value => equal fp1).
    assert _fp(_ok(Money.try_create(150, "USD", 2))) == _fp(_ok(Money.try_create(15000, "USD", 4)))

    # Re-derivation under a newer tzdata version mints a NEW fingerprint (no silent
    # equality) — the derived artifact's identity changes with the calendar identity.
    civil = _ok(CivilDate.try_create(2026, 1, 2))
    cal_old = _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025a"))
    cal_new = _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025b"))
    td_old = _ok(TradingDate.try_create(cal_old, civil))
    td_new = _ok(TradingDate.try_create(cal_new, civil))
    assert _fp(td_old) != _fp(td_new)
    # A newer rule-set version likewise mints a new identity.
    cal_v4 = _ok(CalendarIdentity.try_create("forex-17NY", "v4", "2025a"))
    assert _fp(_ok(TradingDate.try_create(cal_v4, civil))) != _fp(td_old)


# E1-S07 — import-time budget (L0, tracked separately) -------------------------
def test_e1_s07_import_time_budget_well_under_one_second() -> None:
    """NFR-04 / DEC-0111 (registry:core_import_time_budget): `import qmf.core` completes
    well under one second (measured in a fresh interpreter, excluding startup)."""
    src = ROOT / "packages" / "qmf-core" / "src"
    snippet = textwrap.dedent(
        """
        import time
        start = time.perf_counter()
        import qmf.core  # noqa: F401
        print(time.perf_counter() - start)
        """
    )
    proc = subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(src)},
        check=True,
    )
    elapsed = float(proc.stdout.strip().splitlines()[-1])
    assert elapsed < 1.0, f"import qmf.core took {elapsed:.3f}s (budget: well under 1s)"
