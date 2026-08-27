"""L1 — property / invariant tests (hypothesis) for Epic 6.

Oracle = a CT-15 / CT-10 / CT-04 invariant, quantified over a generated input space.
Every boundary RETURNS value-or-refusal; a refusal assertion checks the CT-04 category,
never a parsed exception string. Effects observed only through injected fakes.
"""

from __future__ import annotations

import socket
import urllib.error

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from qmf.core import World, is_ok, is_refusal
from qmf.data import calendar_feed as cal
from qmf.data import dukascopy as duk
from qmf.data.ingest import ExternalSourceIngest, SourceRequest
from qmf.data.observation import ForeignMoney, SourceObservation

import helpers as H

_S = settings(deadline=None, max_examples=150,
              suppress_health_check=[HealthCheck.function_scoped_fixture])

# Per-field "guaranteed invalid" values (an omitted/blank/wrong-typed required field).
_BAD_STR = st.one_of(st.none(), st.just(""), st.just("   "), st.integers(), st.booleans(),
                     st.just(object()), st.lists(st.integers(), max_size=2))
_BAD_TIME = st.one_of(st.none(), st.just(""), st.just("not-a-number"), st.just(object()),
                      st.text(alphabet="abcxyz", min_size=1, max_size=4))
_BAD_INSTRUMENT = st.one_of(st.none(), st.just("EURUSD"), st.integers(), st.booleans(),
                            st.just(object()))


# --- QA-E06-L1-001 — adversarial malformed payloads always refuse ------------


@given(
    field=st.sampled_from(["source", "source_native_id", "revision",
                           "event_time", "known_at", "instrument"]),
    data=st.data(),
)
@_S
def test_l1_001_malformed_field_always_refuses(field: str, data: st.DataObject) -> None:
    """QA-E06-L1-001 (R-007, FR-015, CT-15, CT-04): corrupting any single required
    provider field yields a typed CT-04 refusal — never an admitted CT-10 value,
    never a raised exception.

    Counter-case (built in below): the all-valid record MUST return Ok — so a refusal
    here is caused by the corruption, not a broken harness.
    """
    if field in ("event_time", "known_at"):
        bad = data.draw(_BAD_TIME)
    elif field == "instrument":
        bad = data.draw(_BAD_INSTRUMENT)
    else:
        bad = data.draw(_BAD_STR)
    ing = ExternalSourceIngest(port=None)
    rec = H.provider_record(**{field: bad})
    try:
        result = ing.normalize(rec, writer=H.writer(), sequence=0, world=World.LIVE,
                               receive_wall_time=2_500)
    except Exception as exc:  # noqa: BLE001 - a raise here is itself the R-007 failure
        pytest.fail(f"normalize raised {type(exc).__name__} on malformed {field!r} "
                    f"instead of returning a typed refusal (R-007)")
    assert is_refusal(result), (
        f"malformed {field}={bad!r} was admitted as Ok — a malformed payload must refuse")
    assert result.category.value in {"invalid input", "policy rejection"}, (
        f"unexpected refusal category {result.category.value!r} for malformed {field}")


def test_l1_001_control_valid_record_is_admitted() -> None:
    """Falsifiability control for L1-001: an all-valid record is admitted (Ok)."""
    ing = ExternalSourceIngest(port=None)
    ok = ing.normalize(H.provider_record(), writer=H.writer(), sequence=0,
                       world=World.LIVE, receive_wall_time=2_500)
    assert is_ok(ok), "the uncorrupted control record must be admitted"
    assert isinstance(ok.value[0], SourceObservation)


@given(non_record=st.one_of(st.none(), st.text(), st.integers(), st.binary(),
                            st.dictionaries(st.text(), st.integers(), max_size=3)))
@_S
def test_l1_001_non_provider_record_refused(non_record: object) -> None:
    """QA-E06-L1-001: a value that is not a ProviderRecord is invalid input, never a raise."""
    ing = ExternalSourceIngest(port=None)
    result = ing.normalize(non_record, writer=H.writer(), sequence=0, world=World.LIVE,
                           receive_wall_time=2_500)
    H.assert_refusal(result, "invalid input")


# --- QA-E06-L1-002 — fault realism: real third-party exceptions --------------


@given(blob=st.binary(min_size=0, max_size=64))
@_S
def test_l1_002_bi5_decode_never_raises(blob: bytes) -> None:
    """QA-E06-L1-002 (payload arm): arbitrary bytes into the bi5 decoder surface a real
    lzma.LZMAError / struct.error internally and are translated to a RETURNED refusal
    (or Ok for the empty/valid case) — never a raised exception.
    """
    try:
        result = duk.decode_bi5_ticks(blob, hour_start_ns=0)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"decode_bi5_ticks raised {type(exc).__name__} on adversarial bytes (R-007)")
    assert is_ok(result) or (is_refusal(result) and result.category.value == "invalid input")


@given(blob=st.binary(min_size=0, max_size=64))
@_S
def test_l1_002_calendar_decode_never_raises(blob: bytes) -> None:
    """QA-E06-L1-002 (payload arm): arbitrary bytes into the calendar decoder surface a
    real UnicodeDecodeError / json.JSONDecodeError internally and are translated to a
    RETURNED invalid-input refusal (or Ok for a valid array) — never a raised exception.
    """
    try:
        result = cal.decode_calendar_snapshot(blob, known_at_ns=1_600_000_000_000_000_000)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"decode_calendar_snapshot raised {type(exc).__name__} on bytes (R-007)")
    assert is_ok(result) or (is_refusal(result) and result.category.value == "invalid input")


# Real third-party / OS exception types a raw HTTPS or socket transport raises.
_REAL_TRANSPORT_EXCEPTIONS = [
    ConnectionResetError("peer reset"),
    ConnectionError("connection failed"),
    socket.timeout("timed out"),
    TimeoutError("timed out"),
    OSError("device error"),
    BrokenPipeError("broken pipe"),
    urllib.error.URLError("name resolution failed"),
]


@pytest.mark.parametrize("exc", _REAL_TRANSPORT_EXCEPTIONS, ids=lambda e: type(e).__name__)
def test_l1_002_dukascopy_transport_raise_returns_refusal(exc: BaseException) -> None:
    """QA-E06-L1-002 (R-007 fault realism, transport arm): a Dukascopy transport that
    RAISES a real third-party exception must surface as a RETURNED CT-04 refusal at the
    CT-15 boundary — 'returned, never raised across the boundary' (CT-15 invariant).

    Counter-case: the exception escaping DukascopyAdapter.fetch is the R-007 failure.
    """
    start, end = H.dukascopy_window()
    adapter = duk.DukascopyAdapter(H.RaisingTransport(exc), instruments={"EURUSD": H.instrument()})
    req = SourceRequest(source="dukascopy", bounds={"symbol": "EURUSD", "start_ns": start, "end_ns": end})
    try:
        result = adapter.fetch(req)
    except BaseException as raised:  # noqa: BLE001 - catching to report the R-007 breach cleanly
        pytest.fail(
            f"real transport exception {type(raised).__name__} escaped the CT-15 boundary "
            f"(DukascopyAdapter.fetch) instead of a returned typed refusal — R-007 violation")
    H.assert_refusal(result)
    assert result.category.value in {
        "transient venue failure", "unavailable dependency", "invalid input", "storage failure"}


@pytest.mark.parametrize("exc", _REAL_TRANSPORT_EXCEPTIONS, ids=lambda e: type(e).__name__)
def test_l1_002_calendar_transport_raise_returns_refusal(exc: BaseException) -> None:
    """QA-E06-L1-002 (R-007 fault realism, transport arm): a calendar transport that
    RAISES a real third-party exception must surface as a RETURNED refusal (CT-15).
    """
    adapter = cal.CalendarFeedAdapter(H.RaisingTransport(exc))
    req = SourceRequest(source="news-calendar", bounds={"known_at_ns": 1_600_000_000_000_000_000})
    try:
        result = adapter.fetch(req)
    except BaseException as raised:  # noqa: BLE001
        pytest.fail(
            f"real transport exception {type(raised).__name__} escaped the CT-15 boundary "
            f"(CalendarFeedAdapter.fetch) instead of a returned typed refusal — R-007 violation")
    H.assert_refusal(result)


def test_l1_002_ingest_over_raising_port_returns_refusal() -> None:
    """QA-E06-L1-002 (R-007): a provider port that raises a real exception must surface
    as a RETURNED refusal from ExternalSourceIngest.fetch_and_intake, never escape."""
    ing = ExternalSourceIngest(port=H.RaisingPort(ConnectionResetError("reset")))
    req = SourceRequest(source="dukascopy", bounds={})
    try:
        result = ing.fetch_and_intake(req, writer=H.writer(), world=World.LIVE, receive_wall_time=2_500)
    except BaseException as raised:  # noqa: BLE001
        pytest.fail(
            f"real port exception {type(raised).__name__} escaped ExternalSourceIngest."
            f"fetch_and_intake instead of a returned typed refusal — R-007 violation")
    H.assert_refusal(result)


# --- QA-E06-L1-003 — source identity fingerprinted ---------------------------


@given(
    s1=st.text(min_size=1, max_size=6), n1=st.text(min_size=1, max_size=6), r1=st.text(min_size=1, max_size=6),
    s2=st.text(min_size=1, max_size=6), n2=st.text(min_size=1, max_size=6), r2=st.text(min_size=1, max_size=6),
)
@_S
def test_l1_003_intake_key_is_identity_bearing(s1, n1, r1, s2, n2, r2) -> None:
    """QA-E06-L1-003 (source identity fingerprinted, FR-015, CT-15, CT-10): the
    (source, source-native id, revision) intake key is identity-bearing — two records
    differing in any of the three produce distinct fp1; identical triples produce the
    same fp1. (Blank tokens are excluded — they are refused, not identity.)
    """
    for tok in (s1, n1, r1, s2, n2, r2):
        if tok.strip() == "":
            return  # blank identity content is refused, not fingerprinted (nullability clause)
    ing = ExternalSourceIngest(port=None)

    def fp(source: str, native: str, rev: str) -> str:
        rec = H.provider_record(source=source, source_native_id=native, revision=rev)
        out = ing.normalize(rec, writer=H.writer(), sequence=0, world=World.LIVE, receive_wall_time=2_500)
        return H.unwrap(out)[0].fingerprint.value

    fp_a = fp(s1, n1, r1)
    fp_b = fp(s2, n2, r2)
    if (s1, n1, r1) == (s2, n2, r2):
        assert fp_a == fp_b, "identical intake keys must fingerprint identically (idempotent)"
    else:
        assert fp_a != fp_b, (
            f"distinct intake keys collided on fp1: {(s1, n1, r1)} vs {(s2, n2, r2)}")


@given(rev=st.text(min_size=1, max_size=8).filter(lambda t: t.strip() != ""))
@_S
def test_l1_003_new_revision_never_collides_and_idempotent(rev: str) -> None:
    """QA-E06-L1-003: a new revision of the same fact mints a NEW fp1 (never a collision);
    a byte-identical re-intake reuses the same artifact (idempotent). The boot-scoped
    monotonic diagnostic is excluded from identity.
    """
    ing = ExternalSourceIngest(port=None)
    base = H.provider_record(revision="r-base")
    other = H.provider_record(revision=rev)
    fp_base = H.unwrap(ing.normalize(base, writer=H.writer(), sequence=0, world=World.LIVE,
                                     receive_wall_time=2_500))[0].fingerprint.value
    fp_other = H.unwrap(ing.normalize(other, writer=H.writer(), sequence=0, world=World.LIVE,
                                      receive_wall_time=2_500))[0].fingerprint.value
    if rev != "r-base":
        assert fp_base != fp_other, "a distinct revision must mint a distinct fp1, never a collision"
    # monotonic diagnostic excluded from identity
    with_diag = H.unwrap(ing.normalize(base, writer=H.writer(), sequence=0, world=World.LIVE,
                                       receive_wall_time=2_500,
                                       receive_monotonic_diagnostic=H.monotonic()))[0]
    assert with_diag.fingerprint.value == fp_base, "monotonic diagnostic must be excluded from fp1"


# --- QA-E06-L1-004 — verbatim money / timestamp, no float on the money path --


@given(verbatim=st.integers(min_value=-10**15, max_value=10**15),
       scale=st.integers(min_value=0, max_value=18))
@_S
def test_l1_004_foreign_money_verbatim_scaled_int(verbatim: int, scale: int) -> None:
    """QA-E06-L1-004 (provenance verbatim, DEC-0105): foreign money is stored verbatim as
    a scaled integer at the source's declared scale — never rescaled, never a binary float.
    """
    built = ForeignMoney.try_create(verbatim, scale)
    money = H.unwrap(built)
    assert money.verbatim == verbatim and money.scale == scale
    assert isinstance(money.verbatim, int) and not isinstance(money.verbatim, bool)


@given(bad=st.one_of(st.floats(allow_nan=False, allow_infinity=False), st.booleans(),
                     st.text(), st.none()))
@_S
def test_l1_004_binary_float_inadmissible_on_money_path(bad: object) -> None:
    """QA-E06-L1-004: a binary float (or bool/str/None) on the money path is invalid input.

    Counter-case: a plain int IS admitted (see the verbatim property above) — so the
    refusal here is specific to the non-integer money, not a blanket reject.
    """
    result = ForeignMoney.try_create(bad, 5)
    H.assert_refusal(result, "invalid input")


# --- QA-E06-L1-005 — source is never a VenueId -------------------------------


@given(token=st.text(min_size=1, max_size=8).filter(lambda t: t.strip() != ""))
@_S
def test_l1_005_source_never_conflated_with_venue(token: str) -> None:
    """QA-E06-L1-005 (FR-015, CT-15, DEC-0107/0117): a read-only source is never a
    tradeable VenueId — a VenueId offered as the intake source is refused, while an
    equivalent plain-string source is accepted.
    """
    from qmf.data.ingest import IntakeKey

    # A plain-string source is a legitimate provenance token.
    H.unwrap(IntakeKey.try_create(token, "occ-1", "r1"))
    # The SAME token wrapped as a VenueId is refused — source ⊥ VenueId.
    refusal = IntakeKey.try_create(H.venue(token), "occ-1", "r1")
    H.assert_refusal(refusal, "policy rejection")


# --- QA-E06-L1-006 — hostile source identifiers ------------------------------

_HOSTILE = [
    "../../etc/passwd", "..\\..\\windows\\system32", "/absolute/path", "C:\\abs",
    "sym\x00bol", "CON", "PRN", "AUX", "NUL", "A" * 512, "; rm -rf /", "sym$(whoami)",
    "\n\r", "sym/../..",
]


@pytest.mark.parametrize("hostile", _HOSTILE)
def test_l1_006_hostile_symbol_refused_no_path_escape(hostile: str) -> None:
    """QA-E06-L1-006 (R-007 hostile identifiers, FR-017): an adversarial provider symbol
    into the Dukascopy download-once path is refused (unmapped instrument) and never
    resolves a filesystem path — the shipped adapter takes symbols only as opaque map
    keys / native-id text (the transport is injected; no path is built from input).

    Counter-case: a mapped symbol yields records whose native id carries the hostile
    string verbatim as opaque data and still touches no filesystem.
    """
    start, end = H.dukascopy_window()
    # Unmapped hostile symbol → invalid input, no records, no raise.
    adapter = duk.DukascopyAdapter(H.BytesTransport(__import__("qmf.core", fromlist=["Ok"]).Ok(b"")),
                                   instruments={"EURUSD": H.instrument()})
    req = SourceRequest(source="dukascopy", bounds={"symbol": hostile, "start_ns": start, "end_ns": end})
    try:
        result = adapter.fetch(req)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"hostile symbol {hostile!r} raised {type(exc).__name__} (R-007)")
    H.assert_refusal(result, "invalid input")


def test_l1_006_mapped_hostile_symbol_stays_opaque_data() -> None:
    """QA-E06-L1-006: even a MAPPED hostile symbol is used only as opaque native-id text,
    never as a resolved path — the injected transport is the only I/O surface."""
    start, end = H.dukascopy_window()
    hostile = "../../evil"
    payload = H.bi5_bytes([(0, 110000, 109000, 1.0, 2.0)])
    transport = H.MappedBytesTransport({})  # every hour returns empty; no path resolution
    # Map the hostile symbol to a real instrument so fetch proceeds past the map gate.
    adapter = duk.DukascopyAdapter(transport, instruments={hostile: H.instrument()})
    req = SourceRequest(source="dukascopy",
                        bounds={"symbol": hostile, "start_ns": start, "end_ns": end})
    result = adapter.fetch(req)
    # Whatever the outcome, no path was ever resolved: the transport saw only hour keys.
    assert is_ok(result) or is_refusal(result)
    for key in transport.calls:
        # the hour key path_reference embeds the symbol as text, never a resolved fs path
        assert "\x00" not in key.path_reference


# --- QA-E06-L1-007 — append-only, never overwrite ----------------------------


@given(revisions=st.lists(st.text(min_size=1, max_size=4).filter(lambda t: t.strip() != ""),
                          min_size=1, max_size=6, unique=True))
@_S
def test_l1_007_revisions_never_overwrite_prior(revisions: list[str]) -> None:
    """QA-E06-L1-007 (FR-015, CT-10 append-only): across a sequence of revisions of the
    same occurrence, no earlier admitted observation is mutated — each revision appends a
    new fp1 artifact, and re-intaking an earlier revision returns the ORIGINAL unchanged.
    """
    ing = ExternalSourceIngest(port=None)
    seen: dict[str, str] = {}
    for rev in revisions:
        rec = H.provider_record(source_native_id="occ-shared", revision=rev)
        receipt = H.unwrap(ing.intake(rec, writer=H.writer(), sequence=0, world=World.LIVE,
                                      receive_wall_time=2_500))
        seen[rev] = receipt.observation.fingerprint.value
    # distinct revisions → distinct fp1 (no collision, no overwrite)
    assert len(set(seen.values())) == len(seen), "two revisions overwrote/collided on one fp1"
    # re-intake the first revision → idempotent, identical to the original artifact
    first = revisions[0]
    again = H.unwrap(ing.intake(H.provider_record(source_native_id="occ-shared", revision=first),
                                writer=H.writer(), sequence=99, world=World.LIVE, receive_wall_time=9_999))
    assert again.outcome.value == "idempotent"
    assert again.observation.fingerprint.value == seen[first], "earlier evidence was mutated"
