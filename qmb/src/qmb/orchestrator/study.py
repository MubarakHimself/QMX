"""Operator-terminated Study: a clean ``stopped`` state, one line per run (B-4, OPT-18).

When the operator terminates a running Study, the orchestrator transitions it to a
clean :data:`STUDY_STATE_STOPPED` state: every already-spawned run gets **exactly
one** ledger line — a ``completed`` line for a run that already finished, an
``aborted`` line for a run still in flight when the stop signal arrives — never
zero, never two (AR-51, B-4). Partial results are preserved (the completed lines
stay in the ledger) and the Study is resumable from them
(:func:`qmb.optimize.plan_study_resume`).

This is the impure Study-level composition of the one-line-per-run law: it signals
each run's cancel token, then drives :func:`qmb.orchestrator.finish_run`, which
collects a finished run into a ``completed`` line or aborts an in-flight run into
an ``aborted`` line. Siblings are never signalled beyond their own tokens.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import Ok, Result, is_ok, is_refusal

from qmb._refuse import invalid
from qmb.config.compiler import ResolvedRunConfig
from qmb.ledger.line import ROLE_TRIAL
from qmb.orchestrator.ledger import LedgerSink, finish_run
from qmb.orchestrator.spawn import LiveSpawn
from qmb.runloop.observe import CAUSE_CANCEL

__all__ = [
    "STUDY_STATE_RUNNING",
    "STUDY_STATE_STOPPED",
    "STUDY_STOP_OUTCOME_CLASS",
    "STUDY_STOP_OUTCOME_FORMAT_VERSION",
    "StudyStopOutcome",
    "stop_study",
]

STUDY_STATE_RUNNING: Final[str] = "running"
STUDY_STATE_STOPPED: Final[str] = "stopped"
STUDY_STOP_OUTCOME_CLASS: Final[str] = "qmb-study-stop-outcome"
STUDY_STOP_OUTCOME_FORMAT_VERSION: Final[int] = 1


@dataclass(frozen=True, slots=True)
class StudyStopOutcome:
    """The clean ``stopped`` outcome of an operator-terminated Study (OPT-18, AC5).

    ``completed`` names the runs that finished before the stop and ledgered a
    ``completed`` line; ``aborted`` names the in-flight runs that ledgered an
    ``aborted`` line. ``lines_appended`` equals the number of already-spawned runs —
    exactly one line each. ``partial_preserved`` and ``resumable`` are always true:
    completed trials stay in the ledger and a resume reads them (B-4, AR-51).
    """

    state: str
    completed: tuple[Fingerprint, ...]
    aborted: tuple[Fingerprint, ...]
    lines_appended: int
    partial_preserved: bool = True
    resumable: bool = True

    @property
    def total_runs(self) -> int:
        """Already-spawned runs the stop accounted for — one ledger line each."""
        return len(self.completed) + len(self.aborted)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Package SemVer is omitted."""
        return {
            "aborted": [item.value for item in self.aborted],
            "class": STUDY_STOP_OUTCOME_CLASS,
            "completed": [item.value for item in self.completed],
            "format_version": STUDY_STOP_OUTCOME_FORMAT_VERSION,
            "lines_appended": self.lines_appended,
            "partial_preserved": self.partial_preserved,
            "resumable": self.resumable,
            "state": self.state,
        }


def stop_study(
    live_runs: object,
    *,
    configs: object,
    ledger: object,
    role: object = ROLE_TRIAL,
    factory_sandbox: object = None,
    cause: object = CAUSE_CANCEL,
) -> Result[StudyStopOutcome]:
    """Terminate a running Study into a clean ``stopped`` state (AC5, OPT-18, B-4).

    ``live_runs`` is the sequence of already-spawned :class:`~qmb.orchestrator.LiveSpawn`
    runs; ``configs`` resolves each run id to its :class:`ResolvedRunConfig` (a
    run-id -> config mapping, or a sequence keyed by each config's fingerprint).
    Each run is signalled to cancel, then :func:`~qmb.orchestrator.finish_run`
    appends exactly one ledger line — ``completed`` for a run that already finished,
    ``aborted`` for one still in flight (never zero, never two). Partial results are
    preserved and resumable.
    """
    parsed_live = _coerce_live(live_runs)
    if is_refusal(parsed_live):
        return parsed_live
    if not isinstance(ledger, LedgerSink):
        return invalid(
            "ledger",
            "a Study stop appends its ledger lines through the orchestrator LedgerSink",
            given=repr(type(ledger).__name__),
        )
    lookup = _coerce_configs(configs)
    if is_refusal(lookup):
        return lookup
    by_id = lookup.value
    completed: list[Fingerprint] = []
    aborted: list[Fingerprint] = []
    lines = 0
    for live in parsed_live.value:
        config = by_id.get(live.run_id.value)
        if config is None:
            return invalid(
                "configs",
                "every already-spawned run needs its resolved run-config so the stop "
                "can write exactly one ledger line for it (B-4)",
                run_id=live.run_id.value,
            )
        # Signal a clean cancel so an in-flight run aborts at its next slice boundary.
        live.cancel.cancel(cause)
        finished = finish_run(
            live,
            config=config,
            ledger=ledger,
            role=role,
            factory_sandbox=factory_sandbox,
        )
        if is_ok(finished):
            completed.append(live.run_id)
            lines += 1
            continue
        if finished.context.get("writes_ledger") is True:
            # finish_run appended the one aborted line and returned its refusal.
            aborted.append(live.run_id)
            lines += 1
            continue
        # The one-line-per-run invariant could not be met (e.g. a storage failure);
        # surface it rather than claim a clean stop.
        return finished
    return Ok(
        StudyStopOutcome(
            state=STUDY_STATE_STOPPED,
            completed=tuple(completed),
            aborted=tuple(aborted),
            lines_appended=lines,
        )
    )


def _coerce_live(value: object) -> Result[tuple[LiveSpawn, ...]]:
    if isinstance(value, LiveSpawn):
        return Ok((value,))
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "live_runs",
            "a Study stop accounts for a sequence of already-spawned LiveSpawn runs",
            given=repr(type(value).__name__),
        )
    items = cast("Sequence[object]", value)
    out: list[LiveSpawn] = []
    seen: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, LiveSpawn):
            return invalid(
                "live_runs",
                "each already-spawned run is a LiveSpawn started by start_run",
                index=index,
                given=repr(type(item).__name__),
            )
        token = item.run_id.value
        if token in seen:
            return invalid(
                "live_runs",
                "two already-spawned runs share one run id; each is accounted once (B-4)",
                run_id=token,
            )
        seen.add(token)
        out.append(item)
    return Ok(tuple(out))


def _coerce_configs(value: object) -> Result[dict[str, ResolvedRunConfig]]:
    out: dict[str, ResolvedRunConfig] = {}
    if isinstance(value, ResolvedRunConfig):
        out[value.fingerprint.value] = value
        return Ok(out)
    if isinstance(value, Mapping):
        for key, item in cast("Mapping[object, object]", value).items():
            if not isinstance(item, ResolvedRunConfig):
                return invalid(
                    "configs",
                    "a run-id -> ResolvedRunConfig mapping resolves each run's config",
                    given=repr(type(item).__name__),
                )
            token = key if isinstance(key, str) else item.fingerprint.value
            out[token] = item
        return Ok(out)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, item in enumerate(cast("Sequence[object]", value)):
            if not isinstance(item, ResolvedRunConfig):
                return invalid(
                    "configs",
                    "a config sequence carries one ResolvedRunConfig per run",
                    index=index,
                    given=repr(type(item).__name__),
                )
            out[item.fingerprint.value] = item
        return Ok(out)
    return invalid(
        "configs",
        "resolve each run's config through a run-id -> ResolvedRunConfig mapping or a "
        "sequence of resolved run-configs",
        given=repr(type(value).__name__),
    )
