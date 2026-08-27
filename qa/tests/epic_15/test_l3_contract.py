"""L3 contract conformance: CT-04 refusal register, CT-32/AD-12 line content,
JSONL/WriterId physical format, storage-failure honesty, CT-11 logs-not-evidence,
correlation-id fp1 exclusion.
"""

from __future__ import annotations

import json
from pathlib import Path

from _e15 import (
    REFUSAL_REGISTER,
    RUN_ROLE_SET,
    cancelled_token,
    config,
    fake_live,
    FakeProcess,
    ledger_line,
    line_count,
    make_ledger,
    ok,
    slices,
)

from qmf.core.fingerprint import World, fingerprint, governed_namespace
from qmf.core.refusal import TypedRefusal, is_ok, is_refusal

from qmb.orchestrator import (
    GovernedRequest,
    ResourceGovernor,
    collect_run,
    finish_run,
    fragment_path,
    read_book_bar,
    start_run,
)
from qmb.orchestrator.log import (
    LOG_IS_EVIDENCE,
    EVIDENCE_BEARING_FORMATS,
    LOG_KIND,
    OperationalRecord,
    propagate_correlation,
    structured_log_fp1_identity,
)
from qmb.ledger import ROLE_CONFIRMATION
from qmb.ledger.line import merge_ledger_lines


# -- T-15.2-d [R6] governor over-budget refusal is a CT-04 register value -----
def test_governor_over_budget_refusal_is_register_value_returned():
    """The over-budget refusal is a RETURNED CT-04 value of a register-legal
    category carrying the machine-readable budget shortfall.

    Counter-case that FAILS: an off-register category, a raised exception, or a
    refusal with no run id / budget context.
    """
    governor = ok(ResourceGovernor.try_create(cpu_budget=2, memory_budget=100))
    refused = governor.submit(ok(GovernedRequest.try_create(ok(fingerprint({"r": "x"})), 1000, 1)))
    assert isinstance(refused, TypedRefusal), "the refusal is returned, never raised"
    assert refused.category.value in REFUSAL_REGISTER
    assert "run_id" in refused.context
    assert refused.context.get("memory_budget_key") == "qmb_governor_memory_budget"


# -- T-15.3-d [R10] aborted refusal category is register-legal, NOT "aborted" -
def test_aborted_refusal_category_is_register_legal_not_the_word_aborted(tmp_path):
    """The aborted outcome's refusal carries a register-legal CT-04 category —
    NOT the literal ``aborted`` (which is a run role/kind), returned not raised.

    Counter-case that FAILS: a refusal whose category is the string 'aborted', an
    off-register category, or a raised exception.
    """
    out = tmp_path / "run"
    out.mkdir()
    cfg = config("abrt")
    live = fake_live(cfg, process=FakeProcess(alive=True), cancel=cancelled_token("cancel"),
                     output_dir=str(out))
    refusal = collect_run(live)
    assert isinstance(refusal, TypedRefusal)
    assert refusal.category.value in REFUSAL_REGISTER
    assert refusal.category.value != "aborted", "'aborted' is a run role/kind, never a CT-04 category"
    assert refusal.context.get("terminal") == "aborted", "the terminal kind is aborted"


# -- T-15.4-e [R14] completed line content ----------------------------------
def test_completed_confirmation_line_content(tmp_path):
    """A completed confirmation line carries the AD-12 result label, the CT-32
    fingerprint, raw AD-40 unit-kinded measures, the Book-bar fingerprint, and a
    discriminated run role — and stores NO pass/fail verdict.

    Obtained from a real spawned run so the CT-32 is genuine. Counter-case that
    FAILS: a missing ct32/label/measures/book-bar fp, a role outside the set, or a
    stored verdict field.
    """
    out = tmp_path / "out"
    out.mkdir()
    led = tmp_path / "led"
    led.mkdir()
    cfg = config("content")
    live = ok(start_run(config=cfg, slices=slices(), output_root=out))
    sink = make_ledger(led)
    ok(finish_run(live, config=cfg, ledger=sink, role=ROLE_CONFIRMATION))

    book_bar = ok(read_book_bar(led, world="replay"))
    assert len(book_bar) == 1
    line = book_bar[0]
    assert line.role in RUN_ROLE_SET and line.role == ROLE_CONFIRMATION
    assert line.ct32_fingerprint is not None, "the line carries the CT-32 fingerprint"
    assert line.book_bar_fp1 is not None, "the line carries the Book-bar fingerprint as resolved"
    assert dict(line.result_label), "the line carries the AD-12 result label"
    assert len(line.measures) >= 1, "the line carries raw AD-40 unit-kinded measures"
    for measure in line.measures:
        assert "unit_kind" in measure or measure.get("class") == "undefined-measure"
    identity = line.fp1_identity()
    assert not ({"pass", "fail", "verdict", "rated"} & set(identity)), "no stored verdict"


# -- T-15.4-f [R15] JSONL / WriterId-scoped physical format ------------------
def test_fragment_is_lf_terminated_jsonl_writer_scoped(tmp_path):
    """Each fragment is JSONL (one JSON object per LF-terminated line) at a
    world-and-role-scoped WriterId path; concurrent slots never share a file.

    Counter-case that FAILS: a fragment not LF-terminated, a line that is not one
    JSON object, or a fragment path that is not world/role/WriterId scoped.
    """
    led = tmp_path / "led"
    led.mkdir()
    sink = make_ledger(led, machine="node-a", worker_slot=0)
    ok(sink.append(ledger_line(config("f1"), role=ROLE_CONFIRMATION, tag="f1")))
    ok(sink.append(ledger_line(config("f2"), role=ROLE_CONFIRMATION, tag="f2")))

    writer = ok(sink.writer_id(ROLE_CONFIRMATION))
    frag = ok(fragment_path(led, writer, world="replay", role=ROLE_CONFIRMATION))
    assert frag.is_file(), "the fragment file exists at the WriterId-scoped path"
    raw = frag.read_bytes()
    assert raw.endswith(b"\n"), "each committed line is LF-terminated"
    body_lines = [chunk for chunk in raw.split(b"\n") if chunk]
    assert len(body_lines) == 2, "two runs => two JSONL lines in this slot's fragment"
    for chunk in body_lines:
        obj = json.loads(chunk)
        assert obj["class"] == "qmb-ledger-line" and obj["role"] == ROLE_CONFIRMATION
    # world-and-role-scoped path components
    parts = frag.parts
    assert "replay" in parts and ROLE_CONFIRMATION in parts, "fragment is world-and-role-scoped"

    # A different worker-slot writes a DIFFERENT fragment file (no sharing).
    other = make_ledger(led, machine="node-a", worker_slot=1)
    other_writer = ok(other.writer_id(ROLE_CONFIRMATION))
    other_frag = ok(fragment_path(led, other_writer, world="replay", role=ROLE_CONFIRMATION))
    assert other_frag != frag, "distinct worker-slots never share a fragment file"


def test_cross_fragment_merge_refuses_differing_lines_for_one_run(tmp_path):
    """Two fragments carrying DIFFERING lines for the same run id are a collision
    on merge (never two, never an overwrite); byte-identical duplicates collapse.

    Counter-case that FAILS: a merge that silently keeps two lines for one run id,
    or that overwrites one with the other.
    """
    cfg = config("mergecol")
    a = ledger_line(cfg, role=ROLE_CONFIRMATION, tag="A")
    b = ledger_line(cfg, role=ROLE_CONFIRMATION, tag="B")
    collision = merge_ledger_lines([a, b], world="replay", role=ROLE_CONFIRMATION)
    assert is_refusal(collision), "a differing second line for one run is a merge collision"
    identical = merge_ledger_lines([a, a], world="replay", role=ROLE_CONFIRMATION)
    assert is_ok(identical) and len(identical.value) == 1, "identical duplicates collapse to one"


# -- T-15.4-k [R13, R15] storage-failure honesty ----------------------------
def test_ledger_append_storage_failure_is_surfaced_not_silent(tmp_path):
    """When the ledger append cannot persist, the orchestrator surfaces a
    ``storage failure`` CT-04 refusal and does not silently drop the line.

    A real OSError is provoked: a FILE occupies the world-namespace directory the
    fragment tree needs, so the fragment directory cannot be created. Counter-case
    that FAILS: a silent success (never-zero with no signal) or a raised exception.
    """
    led = tmp_path / "led"
    led.mkdir()
    namespace = ok(governed_namespace(World.REPLAY))  # "replay"
    (led / namespace).write_bytes(b"not a directory")  # block the fragment tree
    sink = make_ledger(led)
    appended = sink.append(ledger_line(config("stor"), role=ROLE_CONFIRMATION, tag="s"))
    assert is_refusal(appended), "an unpersistable append is a returned refusal, never silent"
    assert appended.category.value == "storage failure", "append/fsync failure is CT-04 storage failure"


# -- T-15.5-b [R19] per-run logs are AD-14 operational, NEVER evidence -------
def test_per_run_log_is_never_evidence_bearing():
    """Per-run operational logs are AD-14 only and never CT-11 evidence — even a
    record constructed claiming evidence is coerced to non-evidence.

    Counter-case that FAILS: a record that reports is_evidence True, or the log
    format appearing among the evidence-bearing formats.
    """
    record = OperationalRecord(
        event="run-started",
        message="driving pure run()",
        run_id="fp1:sha256:" + "0" * 64,
        correlation_id="corr-1",
        timestamp="2026-08-27T00:00:00Z",
        is_evidence=True,  # a caller trying to claim evidence...
    )
    assert record.is_evidence is False, "an operational record is coerced to non-evidence (CT-11)"
    assert record.fp1_identity()["is_evidence"] is False
    assert LOG_IS_EVIDENCE is False
    assert LOG_KIND == "ad-14-operational"
    assert "journal" in EVIDENCE_BEARING_FORMATS and LOG_KIND not in EVIDENCE_BEARING_FORMATS


# -- T-15.5-c [R20] correlation_id crosses boundaries, excluded from fp1 ------
def test_correlation_id_excluded_from_fp1_identity():
    """A structured log crossing a package boundary carries a correlation_id that
    is excluded from fp1 identity.

    Counter-case that FAILS: correlation_id (or timestamp) entering the fp1
    identity, or not being propagated onto the boundary payload.
    """
    propagated = ok(propagate_correlation({"event": "spawned", "run_id": "r"}, correlation_id="corr-9"))
    assert propagated["correlation_id"] == "corr-9", "correlation_id rides the boundary payload"
    identity = ok(structured_log_fp1_identity(propagated))
    assert "correlation_id" not in identity, "correlation_id never enters fp1 identity"
    assert "timestamp" not in identity

    record = OperationalRecord(
        event="spawned",
        message="m",
        run_id="fp1:sha256:" + "0" * 64,
        correlation_id="corr-9",
        timestamp="2026-08-27T00:00:00Z",
    )
    assert "correlation_id" not in record.fp1_identity()
    assert record.to_row()["correlation_id"] == "corr-9", "the row keeps the linking annotation"
