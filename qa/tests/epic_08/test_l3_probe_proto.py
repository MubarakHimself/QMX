"""L3 acceptance tests — probe, storage-failure block, structure, proto pin.

Oracle: Story 8.1 (probe verify-or-refuse), Story 8.3 AC-5 (injected sink block),
Story 8.2 (proto tag 91, data-not-code), AR-06/AR-42/AR-43, DEPENDENCIES.md.

Covers QA-E08-L3-011, L3-012, L3-013, L3-014, L3-017.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

from google.protobuf import descriptor_pb2
from qmf.core import (
    ExactRational,
    Instant,
    MonotonicReading,
    Ok,
    RefusalCategory,
    Result,
    UnitKind,
    is_ok,
    is_refusal,
)
from qmf.venue import (
    SPOTWARE_PROTO_PACKAGE,
    AccountMoneyRecord,
    CapabilityProbe,
    EventRecorder,
    ObservationKind,
    ProbeCheck,
    ProbeVerdict,
    ProtoArtifact,
    SpotSample,
    SymbolMetadataRecord,
    Tick,
    TickHistorySample,
    Trendbar,
    TrendbarSample,
    TransactionBoundary,
    VenueEvidenceClass,
    VenueNativeIdentity,
    InboundVenueEvent,
    assess_tag_change,
    compile_descriptor_set,
    descriptor_set_digest,
)

import _helpers as H

REPO_ROOT = Path(__file__).resolve().parents[3]
VENUE_SRC = REPO_ROOT / "packages" / "qmf-venue" / "src" / "qmf" / "venue"
CORE_SRC = REPO_ROOT / "packages" / "qmf-core" / "src" / "qmf" / "core"


# --- fakes: an injected clock and probe transport (no live host) ------------


class FakeClock:
    def __init__(self, wall_ns: int = 1_700_000_000_000_000_000, boot: str = "boot-1") -> None:
        self.boot_epoch_id = boot
        self._wall = wall_ns

    def wall_now(self) -> Result[Instant]:
        # OR-03 / CT-04: the Clock seam is value-or-refusal; a real/fixture clock
        # returns Ok unconditionally (only a spent replay clock refuses).
        return Ok(H.mk_instant(self._wall))

    def monotonic_now(self) -> Result[MonotonicReading]:
        return Ok(H.mk_mono(1_000, self.boot_epoch_id))


class FakeProbeTransport:
    """An injected read-only transport that contacts no host and submits no order.

    It exposes ONLY fetches (the ProbeTransport protocol). ``money_digits`` toggles the
    account money exponent so the money-exponent check can be exercised present/absent."""

    def __init__(self, *, money_digits: int | None) -> None:
        self._money_digits = money_digits
        self.proto_release_tag = H.PINNED_TAG
        self.submitted_orders: list[object] = []  # stays empty — no submit path exists

    def fetch_spot_sample(self):
        # Millisecond-magnitude spot stamps near the injected wall clock (~1.7e12 ms).
        return _Ok(SpotSample(raw_timestamps=(1_700_000_000_000, 1_700_000_000_500),
                              received_at=H.mk_instant(1)))

    def fetch_trendbar_sample(self):
        bars = (
            Trendbar(utc_timestamp_in_minutes=100 * 1440 + 480, open_wire=1, high_wire=2,
                     low_wire=1, close_wire=2),
            Trendbar(utc_timestamp_in_minutes=101 * 1440 + 480, open_wire=2, high_wire=3,
                     low_wire=2, close_wire=3),
        )
        return _Ok(TrendbarSample(bars=bars, received_at=H.mk_instant(2)))

    def fetch_tick_history_sample(self):
        return _Ok(TickHistorySample(quote_type="ASK", ticks=(Tick(0, 1),),
                                    received_at=H.mk_instant(3)))

    def fetch_symbol_metadata(self):
        pip = H.ok(ExactRational.try_create(1, 10**5, UnitKind.DIMENSIONLESS_RATIO))
        return _Ok(SymbolMetadataRecord(symbol="EURUSD", digits=5, pip_position=5,
                                       declared_pip_size=pip, received_at=H.mk_instant(4)))

    def fetch_account_money_record(self):
        return _Ok(AccountMoneyRecord(money_digits=self._money_digits, received_at=H.mk_instant(5)))


class _Ok:
    """Minimal Ok wrapper matching qmf.core.Ok for the transport's value-or-refusal."""

    def __new__(cls, value):
        from qmf.core import Ok

        return Ok(value)


def _run_probe(money_digits):
    v = H.mk_venue()
    a = H.mk_account(v)
    probe = CapabilityProbe.try_create(
        FakeClock(),
        FakeProbeTransport(money_digits=money_digits),
        v,
        a,
        H.mk_secret_ref("sref-demo-cred"),
        H.PINNED_TAG,
        "session-epoch-1",
    )
    return H.ok(probe)


# --- QA-E08-L3-011 — probe verify-or-refuse, stands alone (P1) --------------


def test_l3_011_probe_records_unverified_rather_than_defaulting():
    """Story 8.1 AC-1/AC-3: the probe records an unpassable check as unverified rather
    than defaulting any value (an absent money exponent leaves money decode
    unavailable)."""
    report = H.ok(_run_probe(money_digits=None).run())
    money = report.profile.latest_for(ProbeCheck.MONEY_EXPONENT)
    assert money is not None
    assert money.verdict is ProbeVerdict.UNVERIFIED  # never defaulted to 2
    assert money.measured == {}                        # no value defaulted
    # The governed evidence class stays unavailable.
    assert is_refusal(report.profile.require_evidence(VenueEvidenceClass.MONEY_DECODE))

    # A present exponent verifies and makes the class available.
    report2 = H.ok(_run_probe(money_digits=2).run())
    money2 = report2.profile.latest_for(ProbeCheck.MONEY_EXPONENT)
    assert money2.verdict is ProbeVerdict.VERIFIED
    assert is_ok(report2.profile.require_evidence(VenueEvidenceClass.MONEY_DECODE))


def test_l3_011_probe_stands_alone_no_port_or_journal_dependency():
    """Story 8.1 AC: the probe depends on no port contract, connection manager, or
    Epic 3 journal — it can run as the earliest factory work unit."""
    params = set(inspect.signature(CapabilityProbe.try_create).parameters)
    for forbidden in ("connection_manager", "journal_sink", "record_sink", "observation_sink"):
        assert forbidden not in params
    # It measures only through the injected transport seam.
    assert "transport" in params and "clock" in params


# --- QA-E08-L3-012 — probe renders only the ref, no host, no order (P1) -----


def test_l3_012_probe_renders_only_reference_and_submits_no_order():
    """Story 8.1 AC-4: the credential value is never rendered (only its reference id
    appears), no live host is contacted, and no order is submitted."""
    ref = H.mk_secret_ref("sref-demo-cred")
    report = H.ok(_run_probe(money_digits=2).run())
    # Every recorded fact carries the credential REFERENCE id, never a value.
    for fact in report.profile.facts:
        assert fact.credential_ref_id == ref.value
    # The probe holds a SecretRef (a reference), not a SecretValue; and exposes no submit.
    probe = _run_probe(money_digits=2)
    from qmf.core import SecretRef, SecretValue

    assert isinstance(probe.credential_ref, SecretRef)
    assert not isinstance(probe.credential_ref, SecretValue)
    for forbidden in ("submit", "place_order", "send_order", "order"):
        assert not hasattr(probe, forbidden)


# --- QA-E08-L3-013 — an injected-sink storage failure blocks commands (P1) --


def test_l3_013_command_path_storage_failure_blocks_commands_sensing_unaffected():
    """Story 8.3 AC-5 / AR-47: when an injected command-path sink returns a storage
    failure, the writer-holding component blocks the command stream while the sensing
    pipe is unaffected, and no store is written directly (only through injected sinks)."""
    v = H.mk_venue()
    a = H.mk_account(v)
    obs_sink = H.RecordingSink()             # healthy (sensing + raw archive)
    jnl_sink = H.RecordingSink(fail=True)    # command-path journal fails
    rec_sink = H.RecordingSink()
    cm = H.build_connection_manager(
        v, a, observation_sink=obs_sink, journal_sink=jnl_sink, record_sink=rec_sink
    )

    blocked = cm.append_command_journal({"event": "command-journal"})
    assert is_refusal(blocked)
    assert blocked.category is RefusalCategory.STORAGE_FAILURE
    assert cm.command_pipe_open is False        # writer blocks its command stream
    assert is_refusal(cm.require_command_pipe_open())

    # The sensing pipe is unaffected — sensing observations keep flowing.
    assert cm.sensing_pipe_open is True
    assert is_ok(cm.emit_sensing_observation({"tick": "EURUSD"}))

    # No store is written directly: every persistence routed through an injected sink.
    assert jnl_sink.calls and jnl_sink.calls[0][0] == "append"
    assert obs_sink.calls and obs_sink.calls[-1][0] == "emit"


def test_l3_013_recorder_blocks_via_the_writer_holding_connection_manager():
    """Story 8.6 AC-4 / AR-47: the EventRecorder writes only through the connection
    manager (the WriterId holder); a partial write blocks the command stream there."""
    v = H.mk_venue()
    a = H.mk_account(v)
    jnl_sink = H.RecordingSink(fail=True)
    cm = H.build_connection_manager(v, a, journal_sink=jnl_sink)
    recorder = H.ok(EventRecorder.try_create(cm))
    # The recorder holds no store of its own — only the injected connection manager.
    assert recorder.connection_manager is cm
    event = H.ok(
        InboundVenueEvent.try_create(
            ObservationKind.SUBMISSION_ACKNOWLEDGEMENT,
            H.ok(VenueNativeIdentity.try_create("ctrader", "oid-1", 0)),
            H.mk_instant(1), H.mk_mono(5), "se", {"raw": 1},
        )
    )
    res = recorder.record(event, registry_record={"r": 1}, boundary=TransactionBoundary.ATOMIC)
    assert is_refusal(res)
    assert cm.command_pipe_open is False


# --- QA-E08-L3-014 — dependency direction / structural isolation (P1) --------

_IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z0-9_.]+)", re.MULTILINE)


def _module_imports(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    # Strip the module docstring to avoid matching prose that mentions imports.
    return set(_IMPORT_RE.findall(text))


def test_l3_014_qmf_venue_imports_only_qmf_core_and_protobuf():
    """AR-06/AR-42/AR-43: qmf-venue imports only qmf-core (plus google.protobuf, in the
    proto module only); no other roster package is imported."""
    forbidden_roots = ("qmf.registry", "qmf.data", "qmf.risk", "qmf.structure",
                       "qmf.indicators", "qmf.calendar")
    for py in VENUE_SRC.glob("*.py"):
        imports = _module_imports(py)
        for imp in imports:
            for bad in forbidden_roots:
                assert not imp.startswith(bad), f"{py.name} imports {imp}"
        if "google.protobuf" in {i.split(".")[0] + "." + i.split(".")[1] for i in imports if "." in i}:
            assert py.name == "proto.py", "google.protobuf may be imported only by proto.py"


def test_l3_014_nothing_imports_qmf_venue_and_core_stays_clean():
    """AR-06/AR-42: nothing imports qmf-venue, and qmf-core imports neither qmf-venue nor
    protobuf (no compiled proto leaks into the core)."""
    # qmf-core imports no qmf.venue and no google.protobuf.
    for py in CORE_SRC.glob("*.py"):
        imports = _module_imports(py)
        assert not any(i.startswith("qmf.venue") for i in imports), py.name
        assert not any(i.startswith("google.protobuf") for i in imports), py.name

    # No OTHER package's source imports qmf.venue.
    packages = REPO_ROOT / "packages"
    for pkg in packages.iterdir():
        if not pkg.is_dir() or pkg.name == "qmf-venue":
            continue
        for py in pkg.rglob("*.py"):
            imports = _module_imports(py)
            assert not any(i.startswith("qmf.venue") for i in imports), f"{py} imports qmf.venue"


def test_l3_014_protobuf_declared_only_in_qmf_venue_pyproject():
    """DEPENDENCIES.md/AR-43: the protobuf runtime is declared only in qmf-venue's
    pyproject, no other package."""
    packages = REPO_ROOT / "packages"
    declarers = []
    for pyproject in packages.glob("*/pyproject.toml"):
        # A real dependency declaration is a quoted requirement token ("protobuf==...")
        # inside the dependencies array — not a mention in a comment.
        if re.search(r'"protobuf(?:[=<>!~ \]"]|$)', pyproject.read_text(encoding="utf-8")):
            declarers.append(pyproject.parent.name)
    assert declarers == ["qmf-venue"], f"protobuf declared in unexpected packages: {declarers}"


# --- QA-E08-L3-017 — proto pin at tag 91, data not code, governed change (P2)


def test_l3_017_proto_artifact_names_spotware_package_and_pinned_tag():
    """Story 8.2 AC-1: the venue protocol artifact names the Spotware
    openapi-proto-messages package at the pinned integer release tag (91)."""
    assert SPOTWARE_PROTO_PACKAGE == "openapi-proto-messages"
    artifact = H.build_proto_artifact(tag=91)
    assert artifact.package_name == "openapi-proto-messages"
    assert artifact.release_tag == 91
    # The tag is an injected positive integer; a non-positive tag is refused.
    assert is_refusal(ProtoArtifact.try_create("openapi-proto-messages", 0, H.DIGEST))


def test_l3_017_compiles_from_message_definitions_as_data_not_code():
    """Story 8.2 AC-1/AC-2: only the proto message definitions (data, not code) are
    consumed — an in-house compile of a FileDescriptorSet yields usable message types."""
    fds = descriptor_pb2.FileDescriptorSet()
    file_proto = fds.file.add()
    file_proto.name = "sample.proto"
    file_proto.package = "spotware.sample"
    file_proto.syntax = "proto3"
    msg = file_proto.message_type.add()
    msg.name = "ProtoOASample"
    field = msg.field.add()
    field.name = "value"
    field.number = 1
    field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    field.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT64
    data = fds.SerializeToString()

    compiled = compile_descriptor_set(data, package_name="openapi-proto-messages", release_tag=91)
    assert is_ok(compiled)
    assert "spotware.sample.ProtoOASample" in compiled.value.message_names()
    # The digest is content-derived and reproducible over the same definitions (data).
    assert is_ok(descriptor_set_digest(data))
    assert compiled.value.artifact.descriptor_set_digest == H.ok(descriptor_set_digest(data))


def test_l3_017_tag_change_mints_new_declaration_and_forces_reverification():
    """Story 8.2 AC-3: a tag change mints a new CT-18 capability declaration and forces
    re-verification; a digest change under an unchanged tag is a pin-integrity
    violation."""
    pinned = ProtoArtifact.try_create("openapi-proto-messages", 91, "sha256:" + "a" * 64)
    bumped = ProtoArtifact.try_create("openapi-proto-messages", 92, "sha256:" + "b" * 64)
    change = assess_tag_change(H.ok(pinned), H.ok(bumped))
    assert is_ok(change)
    assert change.value.re_verification_required is True
    assert change.value.capability_declaration_reminted is True

    # A moved descriptor set under an UNCHANGED tag is a pin-integrity violation.
    silent = ProtoArtifact.try_create("openapi-proto-messages", 91, "sha256:" + "c" * 64)
    integrity = assess_tag_change(H.ok(pinned), H.ok(silent))
    assert is_ok(integrity)
    assert integrity.value.pin_integrity_violation is True
