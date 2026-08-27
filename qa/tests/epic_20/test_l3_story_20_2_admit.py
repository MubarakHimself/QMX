"""Epic 20 · Story 20.2 (L3) — one registry as-of, frozen for every combination.

  T20-307  R7   admission resolves exactly ONE as-of via the single port, no 2nd cache (P0)
  T20-308  R8   frozen for the batch; a mid-batch fresher state changes nothing;
                two combos citing the same Book resolve the identical Book fp1   (P0)
  T20-309  R9   after admission fragments resolve by explicit fp1, never name@latest (P1)
  T20-310  R10  a superseded ref -> typed `stale evidence`, severity configurable  (P0)
  T20-311  R11  the frozen registry_as_of is verbatim in every combo's CT-32 label (P1)
"""

from __future__ import annotations

from conftest import (
    SEVERITY,
    TF_1M,
    admit,
    bms_definition,
    book_definition,
    bot_record,
    declaration,
    fixture_port,
    instant,
    make_port,
    ok,
    record,
    run_settings,
    writer,
)

from qmb.registryread import (
    STALE_EVIDENCE_SEVERITY_KEY,
    AsOfSet,
    DatedPointer,
    RegistryReadPort,
    SupersedesRef,
)
from qmb.results import REGISTRY_AS_OF_KEY as CT32_REGISTRY_AS_OF_KEY
from qmb.results import mint_run_performance_result
from qmb.sweep import REGISTRY_AS_OF_KEY, AdmittedSweep, admit_sweep
from qmf.core.chrono import Interval
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import RefusalCategory, is_refusal

_NS = 1_700_000_000_000_000_000
_REGISTRY_AS_OF_CLASS = "registry-as-of"


# --- T20-307 (R7) : one as-of resolved through the single port, no 2nd cache ---


def test_t20_307_admission_resolves_one_frozen_as_of_through_one_port() -> None:
    port, book, bms, bot = fixture_port()
    live_as_of = port.bound  # the one as-of the live port is bound to
    decl = declaration(bot=bot.stable_id, book=book.stable_id, bms=bms.stable_id, parameters={"lookback": [10, 20, 30]})
    admitted = ok(admit_sweep(decl, port, writer()))
    assert isinstance(admitted, AdmittedSweep)
    # Exactly one as-of, frozen — and it IS the one the live port already held
    # (a second cache/resolver would let the batch bind a different as-of).
    assert admitted.port.frozen is True
    assert admitted.registry_as_of == live_as_of.registry_as_of
    assert admitted.set_fingerprint == live_as_of.fingerprint
    # The one as-of is a (registry_as_of instant + set fingerprint) pair.
    stamp = admitted.registry_as_of_stamp()
    assert stamp == {"value_ns": admitted.registry_as_of.value_ns, "fingerprint": admitted.set_fingerprint.value}


# --- T20-308 (R8) : frozen for the batch; fresher-mid-batch is inert -----------


def test_t20_308_one_as_of_is_frozen_for_every_combination() -> None:
    admitted = admit(parameters={"lookback": [10, 20]})
    configs = ok(admitted.compile_all(**run_settings()))
    # Two combos citing the same Book/BMS/bot resolve the IDENTICAL fp1 (SC-11).
    assert {c.book_fp1 for c in configs} == {admitted.label.book_fp1}
    assert {c.bms_fp1 for c in configs} == {admitted.label.bms_fp1}
    assert {c.bot_fp1 for c in configs} == {admitted.label.bot_fp1}
    # Every combo's run label carries the identical frozen as-of stamp.
    stamp = admitted.registry_as_of_stamp()
    for combo in admitted.combos:
        run_label = ok(admitted.run_label(combo))
        assert run_label["registry_as_of"] == stamp
        assert run_label["sweep_id"] == admitted.label.sweep_id.value


def test_t20_308_a_fresher_as_of_mid_batch_changes_no_combination() -> None:
    admitted = admit(parameters={"lookback": [10, 20]})
    settings = run_settings()
    first = ok(admitted.compile_combo(admitted.combos[0], **settings))
    again = ok(admitted.compile_combo(admitted.combos[0], **settings))
    # A frozen port yields the byte-identical run id no matter when recompiled.
    assert first.fingerprint == again.fingerprint

    # Build a FRESHER as-of that supersedes the batch's Book and grow the hub;
    # a frozen port bound to the admission as-of still resolves the frozen Book.
    book_id = _book_record_id(admitted)
    superseding = record("book-definition", book_definition(q=200))
    bound = admitted.port.bound
    fresher = ok(
        AsOfSet.try_create(
            instant(_NS + 1),
            records=(*bound.records, superseding),
            supersedes=(ok(SupersedesRef.try_create(superseding.stable_id, book_id)),),
        )
    )
    grown = ok(admitted.port.hub.with_set(fresher))
    frozen = ok(RegistryReadPort.try_create(grown, stale_evidence_severity=SEVERITY, bound=admitted.port.bound, frozen=True))
    still = ok(frozen.resolve(book_id))
    # Counter-case: if the frozen port consulted the fresher set it would return
    # the superseding fp1 (or refuse stale). It returns the frozen Book, unchanged.
    assert still.fingerprint == book_id


def _book_record_id(admitted: AdmittedSweep) -> Fingerprint:
    for rec in admitted.port.bound.records:
        if rec.kind == "book-definition":
            return rec.stable_id
    raise AssertionError("book record missing from the admitted as-of")


# --- T20-309 (R9) : resolve by explicit fp1, never name@latest -----------------


def test_t20_309_after_admission_resolution_is_by_fp1_never_name_at_latest() -> None:
    admitted = admit()
    # An alias and a name@latest cite are refused by the frozen port.
    assert is_refusal(admitted.port.resolve("mean-reversion"))
    at_latest = admitted.port.resolve("scalping@latest")
    assert is_refusal(at_latest)
    assert at_latest.category is RefusalCategory.INVALID_INPUT
    # The bot resolves only by the fp1 captured at admission, and the compiled
    # config cites that same fp1 — no name@version survives into the artifact.
    resolved = ok(admitted.port.resolve(admitted.label.bot_fp1))
    assert resolved.fingerprint == admitted.label.bot_fp1
    config = ok(admitted.compile_combo(admitted.combos[0], **run_settings()))
    assert config.bot_fp1 == admitted.label.bot_fp1


# --- T20-310 (R10) : a superseded ref at admission is a stale-evidence refusal --


def test_t20_310_superseded_context_reference_is_a_stale_evidence_refusal() -> None:
    book_v1 = record("book-definition", book_definition(q=100))
    book_v2 = record("book-definition", book_definition(q=200))
    bms = record("bms-definition", bms_definition())
    bot = bot_record()
    pointers = (
        ok(DatedPointer.try_create("mean-reversion", bot.stable_id, instant())),
        ok(DatedPointer.try_create("scalping", book_v2.stable_id, instant())),
    )
    supersedes = (ok(SupersedesRef.try_create(book_v2.stable_id, book_v1.stable_id)),)
    port = make_port(book_v1, book_v2, bms, bot, pointers=pointers, supersedes=supersedes)
    # The sweep cites the SUPERSEDED v1 Book directly.
    decl = declaration(bot=bot.stable_id, book=book_v1.stable_id, bms=bms.stable_id)
    refused = admit_sweep(decl, port, writer())
    assert is_refusal(refused)
    # Neither the stale nor the fresher version is silently bound — it refuses.
    assert refused.category is RefusalCategory.STALE_EVIDENCE
    # Severity is the CONFIGURED key, never an invented default (AR-55).
    assert refused.context["severity"] == SEVERITY
    assert refused.context["severity_key"] == STALE_EVIDENCE_SEVERITY_KEY
    assert refused.context["fingerprint"] == book_v1.stable_id.value


# --- T20-311 (R11) : registry_as_of verbatim in every combo's CT-32 label ------


def test_t20_311_registry_as_of_is_verbatim_in_every_combo_ct32_label() -> None:
    admitted = admit(parameters={"lookback": [10, 20]})
    settings = run_settings()
    expected_stamp = admitted.registry_as_of_stamp()
    # The one class marker CT-32 reads registry_as_of under.
    registry_input = ok(
        fingerprint(
            {
                "class": _REGISTRY_AS_OF_CLASS,
                "registry_as_of": admitted.registry_as_of.fp1_identity(),
                "fingerprint": admitted.set_fingerprint.value,
            }
        )
    )
    # The sweep key and the CT-32 field agree by construction.
    assert REGISTRY_AS_OF_KEY == CT32_REGISTRY_AS_OF_KEY == "registry_as_of"
    for combo in admitted.combos:
        config = ok(admitted.compile_combo(combo, **settings))
        assert config.keys[REGISTRY_AS_OF_KEY] == expected_stamp
        result = ok(
            mint_run_performance_result(
                config,
                evidence_range=ok(Interval.try_create(instant(_NS), instant(_NS + 1_000))),
                stream_order=(combo.instrument,),
                slice_count=1,
                filled_count=0,
                resting_count=0,
                data_points_processed=1,
                outcome_identity={"done": True},
            )
        )
        # The frozen as-of lands verbatim in this combo's CT-32 label set.
        assert registry_input in result.result_label.input_fingerprints
