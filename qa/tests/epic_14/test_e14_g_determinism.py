"""Epic 14 · Group G — golden-slice determinism & run-id reproduction (Story 14.7).

AR-58/B-2/NFR-02/NFR-03: identical inputs + resolved config run twice produce a
byte-identical CT-32 fingerprint; re-running a run id reproduces the fingerprint
or returns a typed refusal; determinism traces ONLY to the pinned sub-phase
order + stream-set declaration order + pure aggregation/gap-fix/fill — no ambient
nondeterminism (wall clock, env, PYTHONHASHSEED, dict/set ordering). R33's loop-
purity half is testable here; byte-identity across OS-process siblings is Epic 15.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from _e14 import NS, config, ok, slices

from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, is_refusal
from qmb.results import require_reproduced_fingerprint
from qmb.runloop import reproduce_run, run


def _ct32(outcome: object) -> str:
    return ok(outcome.ct32_fingerprint()).value  # type: ignore[attr-defined]


# --- T-14.7-a (L4) two identical runs share a byte-identical CT-32 fp [R30] P0
def test_t147a_identical_runs_share_ct32_fingerprint() -> None:
    cfg = config()
    first = _ct32(ok(run(slices=slices(), config=cfg)))
    second = _ct32(ok(run(slices=slices(), config=cfg)))
    assert first == second
    assert first.startswith("fp1:sha256:")


# --- T-14.7-b (L3) re-run reproduces the fingerprint or typed-refuses [R31] P0
def test_t147b_rerun_reproduces_or_refuses() -> None:
    cfg = config()
    expected = ok(ok(run(slices=slices(), config=cfg)).ct32_fingerprint())
    reproduced = ok(
        reproduce_run(
            run_id=cfg.fingerprint,
            config=cfg,
            expected_fingerprint=expected,
            slices=slices(),
        )
    )
    assert ok(reproduced.fingerprint()) == expected
    # A wrong expected fingerprint is a typed policy rejection, never a silent pass.
    mismatch = reproduce_run(
        run_id=cfg.fingerprint,
        config=cfg,
        expected_fingerprint=ok(fingerprint({"n": "not-this-run"})),
        slices=slices(),
    )
    assert is_refusal(mismatch) and mismatch.category is RefusalCategory.POLICY_REJECTION
    compared = require_reproduced_fingerprint(expected, ok(fingerprint({"n": "x"})))
    assert is_refusal(compared) and compared.category is RefusalCategory.POLICY_REJECTION


# --- T-14.7-c (L4/L6) fingerprint invariant under ambient perturbation [R32] P0
def test_t147c_fingerprint_invariant_under_ambient_perturbation(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    cfg = config()
    baseline = _ct32(ok(run(slices=slices(), config=cfg)))
    # Perturb wall clock, monotonic clock, and the environment.
    monkeypatch.setenv("QMX_AUDIT_JUNK", "wobble")
    monkeypatch.setenv("TZ", "Pacific/Kiritimati")
    monkeypatch.setattr(time, "time", lambda: 424242.0)
    monkeypatch.setattr(time, "monotonic", lambda: 999.0)
    monkeypatch.setattr(time, "perf_counter", lambda: 111.0)
    perturbed = _ct32(ok(run(slices=slices(), config=cfg)))
    assert perturbed == baseline
    # dict/set insertion incidentals: same content, different key insertion order
    # must yield the same fingerprint (canonical bytes sort keys at every depth).
    cal_forward = {"rule_set": "qmb-replay", "rule_set_version": "v1", "tzdata_version": "UTC"}
    cal_reversed = {"tzdata_version": "UTC", "rule_set_version": "v1", "rule_set": "qmb-replay"}
    left = _ct32(ok(run(slices=slices(), config=config(account_role="demo", calendar=cal_forward))))
    right = _ct32(ok(run(slices=slices(), config=config(calendar=cal_reversed, account_role="demo"))))
    assert left == right


# --- T-14.7-c (subprocess) fingerprint invariant under PYTHONHASHSEED [R32] P0
def test_t147c_fingerprint_invariant_under_pythonhashseed() -> None:
    root = Path(__file__).resolve().parents[3]
    srcs = [root / "qmb" / "src", root / "qml" / "src", root / "extensions" / "qmf-calendar-forex" / "src"]
    srcs += sorted((root / "packages").glob("*/src"))
    pythonpath = os.pathsep.join(str(p) for p in srcs)
    script = (
        "from qmf.core.chrono import Instant\n"
        "from qmf.core.fingerprint import World, fingerprint\n"
        "from qmf.core.refusal import is_ok\n"
        "from qmb.config import ResolvedRunConfig\n"
        "from qmb.runloop import SliceObservation, run\n"
        "NS=1_700_000_000_000_000_000\n"
        "def ok(r):\n"
        "    assert is_ok(r), r\n"
        "    return r.value\n"
        "stamp=ok(fingerprint({'n':'hashseed-cfg'}))\n"
        "cfg=ResolvedRunConfig(format_version=1,book_fp1=stamp,bms_fp1=stamp,bot_fp1=stamp,"
        "book_fragment_fp1=stamp,bms_fragment_fp1=stamp,keys={'stream_set':('eurusd','gbpusd')},"
        "clock='replay',data_provenance='recorded',world=World.REPLAY,fingerprint=stamp,binding_fp1=stamp)\n"
        "def obs(s,ns):\n"
        "    return ok(SliceObservation.try_create(s,ok(Instant.try_create(ns)),True))\n"
        "sl=tuple(tuple(obs(s,NS+i) for s in ('eurusd','gbpusd')) for i in range(2))\n"
        "out=ok(run(slices=sl,config=cfg))\n"
        "print(ok(out.ct32_fingerprint()).value)\n"
    )

    def _fp_under(seed: str) -> str:
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = seed
        env["PYTHONPATH"] = pythonpath
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(root),
            timeout=120,
        )
        assert proc.returncode == 0, proc.stderr
        return proc.stdout.strip()

    fp0 = _fp_under("0")
    fp1 = _fp_under("1")
    assert fp0.startswith("fp1:sha256:")
    assert fp0 == fp1


# --- T-14.7-d (L5) a run alongside concurrent siblings is byte-identical [R33]
def test_t147d_loop_purity_under_concurrency() -> None:
    cfg = config()
    isolated = _ct32(ok(run(slices=slices(), config=cfg)))

    def isolated_again() -> str:
        return _ct32(ok(run(slices=slices(), config=cfg)))

    def sibling() -> str:
        other = config(streams=("usdjpy",))
        return _ct32(ok(run(slices=slices(("usdjpy",)), config=other)))

    with ThreadPoolExecutor(max_workers=3) as pool:
        a = pool.submit(isolated_again)
        s = pool.submit(sibling)
        b = pool.submit(isolated_again)
        concurrent_a, sibling_fp, concurrent_b = a.result(), s.result(), b.result()
    assert concurrent_a == isolated
    assert concurrent_b == isolated
    assert sibling_fp != isolated  # a different run is a different identity
