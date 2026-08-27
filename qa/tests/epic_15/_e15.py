"""Construction mechanics for the INDEPENDENT Epic 15 (qmb-orchestrator) audit.

Assertions in the ``test_l*`` modules state what the RATIFIED requirements
demand (epics.md Stories 15.1-15.5 ACs + the QMB spine B-4/B-5 + the CT-*
contracts + SCN-0012, per this epic's PLAN.md), NEVER what the source happens
to do. This module only supplies fixture mechanics (a resolved run-config, event
slices, a recording ledger directory, a scriptable fake process) so the
requirement-level assertions can run. A failing test is a FINDING, never a
licence to soften an assertion or edit source. Source is read-only evidence.

Observation discipline (hardened author contract):
- The exactly-one-line matrix is observed through the REAL ledger fragment
  directory the test owns (``read_merge_view`` / ``read_book_bar``), an exact,
  deterministic, independent sink — never by trusting a returned flag.
- Terminal causes are enumerated from the B-4/B-5 contract (completion, cancel,
  time-breach, memory-breach, crash) BEFORE the assertions, so a cause the code
  forgets surfaces as a missing line, not an untested path.
- Refusals are checked as RETURNED CT-04 values of a register-legal category;
  ``aborted`` is asserted as a run role/kind, never as a refusal category.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from qmf.core.chrono import Duration, Instant
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import Result, is_ok

from qmb.config import ResolvedRunConfig
from qmb.ledger import ROLE_ABORTED, ROLE_CONFIRMATION, ROLE_REPLICATE, ROLE_TRIAL
from qmb.ledger.line import LedgerLine
from qmb.orchestrator import LedgerSink, LiveSpawn, read_merge_view
from qmb.runloop import SliceObservation
from qmb.runloop.observe import CancelToken, RunLimits, ScriptedLimitProbe

# The seven CT-04 refusal-register categories (docs/registry -> typed_refusal_codes).
REFUSAL_REGISTER: frozenset[str] = frozenset(
    {
        "invalid input",
        "unsupported capability",
        "unavailable dependency",
        "stale evidence",
        "policy rejection",
        "transient venue failure",
        "storage failure",
    }
)

# The four discriminated run roles (never a verdict).
RUN_ROLE_SET: frozenset[str] = frozenset(
    {ROLE_CONFIRMATION, ROLE_TRIAL, ROLE_REPLICATE, ROLE_ABORTED}
)

NS: int = 1_700_000_000_000_000_000

T = TypeVar("T")


def ok(result: Result[T]) -> T:
    """Unwrap an ``Ok`` or fail loudly with the refusal context."""
    assert is_ok(result), f"expected Ok, got refusal: {getattr(result, 'context', result)!r}"
    return result.value


def inst(ns: int = NS) -> Instant:
    return ok(Instant.try_create(ns))


def obs(stream_id: str, ns: int = NS, *, closed: bool = True) -> SliceObservation:
    return ok(SliceObservation.try_create(stream_id, inst(ns), closed))


def config(tag: str = "e15", streams: tuple[str, ...] = ("eurusd", "gbpusd"), **keys: object):
    """A resolved, world=replay run-config sufficient to spawn and mint CT-32.

    Built via the frozen dataclass (trusted-internal constructor), the same
    mechanic the ratified Epic 13/14 audit fixtures use. Distinct ``tag`` =>
    distinct fingerprint => distinct run id.
    """
    stamp = ok(fingerprint({"n": "e15-cfg", "tag": tag, "streams": list(streams)}))
    payload: dict[str, object] = {"stream_set": streams}
    payload.update(keys)
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys=payload,
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
        binding_fp1=stamp,
    )


def sim_config(tag: str = "sim"):
    """A world=simulated run-config (synthetic-store world, SCN-0012 Branch B)."""
    stamp = ok(fingerprint({"n": "e15-sim", "tag": tag}))
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={"stream_set": ("synthetic",)},
        clock="replay",
        data_provenance="recorded",
        world=World.SIMULATED,
        fingerprint=stamp,
        binding_fp1=stamp,
    )


def slices(streams: tuple[str, ...] = ("eurusd", "gbpusd"), n: int = 2):
    """``n`` completed event slices, one instant apart, over the declared streams."""
    return tuple(tuple(obs(s, NS + i) for s in streams) for i in range(n))


def duration(ns: int) -> Duration:
    return ok(Duration.try_create(ns))


def cancelled_token(cause: str = "cancel") -> CancelToken:
    token = CancelToken()
    ok(token.cancel(cause))
    return token


class FakeProcess:
    """A scriptable ``Popen``-like handle for the L2 terminal-cause matrix.

    Drives ``collect_run``/``finish_run`` without a real OS process so every
    terminal cause is observed deterministically through the injected ledger
    directory. The library ``run()`` is never involved; only the orchestrator's
    death-observer and ledger append are exercised.
    """

    def __init__(self, *, alive: bool = True, returncode: object = None) -> None:
        self._alive = alive
        self.returncode = returncode
        self.killed = False

    def poll(self):
        return None if self._alive else self.returncode

    def wait(self, timeout=None):  # noqa: ARG002 - signature parity with Popen
        self._alive = False
        return self.returncode

    def communicate(self):
        return ("", "")

    def kill(self) -> None:
        self.killed = True
        self._alive = False


def fake_live(
    cfg,
    *,
    process: FakeProcess,
    cancel: CancelToken | None = None,
    limits: RunLimits | None = None,
    probe: ScriptedLimitProbe | None = None,
    output_dir: str | None = None,
) -> LiveSpawn:
    """A LiveSpawn whose run id matches ``cfg`` (finish_run's precondition)."""
    tmp = output_dir if output_dir is not None else str(Path.cwd())
    return LiveSpawn(
        run_id=cfg.fingerprint,
        output_dir=tmp,
        pid=999_999,
        process=process,  # type: ignore[arg-type]
        cancel=cancel if cancel is not None else CancelToken(),
        limits=limits if limits is not None else RunLimits(),
        started_monotonic_ns=0,
        probe=probe if probe is not None else ScriptedLimitProbe(),
    )


def make_ledger(root: Path, *, machine: str = "node-a", worker_slot: object = 0) -> LedgerSink:
    """A real WriterId-scoped ledger sink over a test-owned directory."""
    return ok(
        LedgerSink.try_create(
            root, machine=machine, worker_slot=worker_slot, boot_epoch_id="boot-1"
        )
    )


def ledger_line(
    cfg,
    *,
    role: str = ROLE_CONFIRMATION,
    tag: str = "a",
    world: World = World.REPLAY,
    measures: tuple = (),
    ct32: Fingerprint | None = None,
) -> LedgerLine:
    """A hand-built ledger line (bypasses minting) for read-selection / never-two tests.

    The read-time behaviours under test (merge-view role selection, never-two
    idempotency/collision) do not depend on CT-32 minting; a directly-built line
    is the cheapest independent input for them.
    """
    bar = ok(fingerprint({"book": "bar", "tag": tag}))
    label = {"evidence_class": "provisional", "world": world.value, "tag": tag}
    return LedgerLine(
        run_id=cfg.fingerprint,
        role=role,
        world=world,
        result_label=label,
        book_bar_fp1=bar,
        measures=measures,
        ct32_fingerprint=ct32,
        refusal=None,
    )


def line_count(root: Path, world: str = "replay") -> int:
    """Total governed lines across every role in a world (test's own observation)."""
    total = 0
    for role in (ROLE_CONFIRMATION, ROLE_TRIAL, ROLE_REPLICATE, ROLE_ABORTED):
        merged = read_merge_view(root, world=world, role=role)
        if is_ok(merged):
            total += len(merged.value)
    return total


def lines_for_role(root: Path, role: str, world: str = "replay") -> tuple:
    merged = read_merge_view(root, world=world, role=role)
    return merged.value if is_ok(merged) else ()
