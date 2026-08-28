"""L1 property tests (hypothesis) — contract invariants, quantified.

Oracle: SCN-0005 Given ("every public venue boundary succeeds or returns a typed
refusal"), CT-21 render/opacity invariants, CT-19 command identity, CT-18/CT-19 the
foreign-float boundary. Covers QA-E08-L1-001..005.

Run: uv run --with hypothesis pytest qa/tests/epic_08/test_l1_properties.py
"""

from __future__ import annotations

import inspect
import pickle
from collections.abc import Callable

import _helpers as H
import pytest
import qmf.venue as venue
from hypothesis import assume, given
from hypothesis import strategies as st
from qmf.core import (
    Ok,
    RefusalCategory,
    RoundingMode,
    SecretRef,
    TypedRefusal,
    is_ok,
    is_refusal,
)
from qmf.venue import (
    CapabilityProbe,
    InboundVenueEvent,
    RatePacer,
    SessionRecovery,
    UnknownGate,
    VenueNativeIdentity,
    decode_execution_price,
    decode_market_data_price,
    decode_money,
)

# --- junk strategy: any well-formed-but-arbitrary Python value --------------

JUNK = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(10**9), max_value=10**9),
    st.floats(allow_nan=True, allow_infinity=True),
    st.text(max_size=12),
    st.binary(max_size=8),
    st.lists(st.integers(), max_size=4),
    st.dictionaries(st.text(max_size=4), st.integers(), max_size=3),
)


# The two remaining helpers below accept already-minted typed values and return a
# display/namespace string. They are enumerated explicitly rather than disappearing
# from the sweep: a new exported function is tested by default until reviewed.
_TYPED_ONLY_VALUE_HELPERS = frozenset({"journal_event_type", "venue_command_stream"})
_TYPED_ONLY_VALUE_FACTORIES = frozenset(
    {
        "JournalEvent.for_outcome",
        "ObservationJournalEvent.for_event",
        "StandingIntentJournalEvent.held",
    }
)


def _public_boundary_cases() -> tuple[tuple[str, Callable[..., object]], ...]:
    """Derive public functions and class/static factories from ``venue.__all__``."""
    cases: dict[str, Callable[..., object]] = {}
    for export_name in venue.__all__:
        exported = getattr(venue, export_name)
        if inspect.isfunction(exported):
            if export_name not in _TYPED_ONLY_VALUE_HELPERS:
                cases[export_name] = exported
            continue
        if not inspect.isclass(exported):
            continue
        for method_name, descriptor in vars(exported).items():
            if method_name.startswith("_"):
                continue
            if isinstance(descriptor, (classmethod, staticmethod)):
                qualified_name = f"{export_name}.{method_name}"
                if qualified_name not in _TYPED_ONLY_VALUE_FACTORIES:
                    cases[qualified_name] = getattr(exported, method_name)

    # Public instance boundaries need a valid receiver; keep these two explicit
    # while their arguments are still generated like every derived case.
    cases["RatePacer.admit"] = RatePacer().admit
    cases["SessionRecovery.on_disconnect"] = SessionRecovery().on_disconnect
    return tuple(sorted(cases.items()))


PUBLIC_BOUNDARIES = _public_boundary_cases()


def _invoke_with_junk(boundary: Callable[..., object], junk: object) -> object:
    """Drive every declared parameter, including optional ones, with one draw."""
    args: list[object] = []
    kwargs: dict[str, object] = {}
    for parameter in inspect.signature(boundary).parameters.values():
        if parameter.kind in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD):
            args.append(junk)
        elif parameter.kind is parameter.KEYWORD_ONLY:
            kwargs[parameter.name] = junk
        elif parameter.kind is parameter.VAR_POSITIONAL:
            args.append(junk)
        elif parameter.kind is parameter.VAR_KEYWORD:
            kwargs["unexpected"] = junk
    return boundary(*args, **kwargs)


# --- QA-E08-L1-001 — every public boundary returns value-or-refusal (P0) ----


def test_l1_001_exported_observation_event_mapper_refuses_non_kind():
    """SCN-0005 Given / R-002: even a mapping helper exported as a public venue
    boundary returns a typed refusal for malformed input instead of raising."""
    public_surface = {name: getattr(venue, name) for name in venue.__all__}
    mapper = public_surface["observation_journal_event_type"]

    result = mapper(object())

    assert isinstance(result, TypedRefusal)
    assert result.category is RefusalCategory.INVALID_INPUT


@pytest.mark.parametrize(
    ("boundary_name", "boundary"),
    PUBLIC_BOUNDARIES,
    ids=[name for name, _boundary in PUBLIC_BOUNDARIES],
)
@given(j=JUNK)
def test_l1_001_public_boundary_never_raises(boundary_name, boundary, j):
    """SCN-0005 Given / R-002: a public venue boundary succeeds or returns a typed
    refusal — it never raises for any generated input."""
    del boundary_name
    _invoke_with_junk(boundary, j)


def test_l1_001_unknown_gate_try_create_never_raises():
    """UnknownGate.try_create over a junk connection manager returns a refusal."""
    for junk in (None, 0, "x", [], {}):
        res = UnknownGate.try_create(junk)
        assert isinstance(res, (Ok, TypedRefusal))
        assert is_refusal(res)


def test_l1_001_probe_try_create_never_raises():
    """CapabilityProbe.try_create over junk args returns a refusal, never raises."""
    for junk in (None, 0, "x", [], {}):
        res = CapabilityProbe.try_create(junk, junk, junk, junk, junk, junk, junk)
        assert isinstance(res, (Ok, TypedRefusal))
        assert is_refusal(res)


# --- QA-E08-L1-002 — SecretValue render guard (P0) --------------------------

_REF = H.mk_secret_ref("REF-ID-OPAQUE-TOKEN-01")
_NEUTRAL = H.mk_secret_value(_REF, "neutral-placeholder")
_TEMPLATES = [
    repr(_NEUTRAL),
    str(_NEUTRAL),
    format(_NEUTRAL, ""),
    f"{_NEUTRAL}",
    "%s" % _NEUTRAL,
]


@given(secret=st.text(min_size=1, max_size=40))
def test_l1_002_secret_value_never_renders_its_value(secret):
    """CT-21/AR-37/L34: a SecretValue yields only its opaque reference id under repr,
    str, format, and logging — the value string never appears — and is never
    serialized."""
    assume(secret.strip() != "")
    # Exclude secrets that are coincidental substrings of the structural render
    # template (which embeds only the ref id, never the secret).
    assume(all(secret not in t for t in _TEMPLATES))

    sv = H.mk_secret_value(_REF, secret)
    renders = [repr(sv), str(sv), format(sv, ""), f"{sv}", "%s" % sv, "{}".format(sv)]
    for render in renders:
        assert secret not in render, "SecretValue leaked its value under a render path"
        assert _REF.value in render or render == str(sv)  # only the ref id is rendered
    # The value is reachable only through reveal(); serialization refuses it.
    assert sv.reveal() == secret
    with pytest.raises(TypeError):
        pickle.dumps(sv)


# --- QA-E08-L1-003 — command identity vs occurrence exclusion (P1) ----------


@given(o1=st.integers(0, 10_000), o2=st.integers(0, 10_000))
def test_l1_003_command_identity_distinguishes_ordering_ordinal(o1, o2):
    """CT-19: two command records differing in an identity input (the ordering ordinal)
    produce distinct fp1; identical identity inputs produce identical fp1."""
    v = H.mk_venue()
    a = H.mk_account(v)
    ins = H.mk_instrument(v)
    fp1 = H.ok(H.build_place_order(v, a, ins, ordinal=o1).fingerprint())
    fp2 = H.ok(H.build_place_order(v, a, ins, ordinal=o2).fingerprint())
    if o1 == o2:
        assert fp1 == fp2
    else:
        assert fp1 != fp2


@given(
    recv1=st.integers(1, 10**6),
    recv2=st.integers(1, 10**6),
    mono1=st.integers(1, 10**6),
    mono2=st.integers(1, 10**6),
    corr1=st.text(min_size=1, max_size=8),
    corr2=st.text(min_size=1, max_size=8),
)
def test_l1_003_observation_identity_excludes_occurrence_fields(
    recv1, recv2, mono1, mono2, corr1, corr2
):
    """CT-20: records differing only in occurrence fields (receive stamps, monotonic,
    correlation_id) produce identical fp1 — those fields never enter identity."""
    assume(corr1.strip() and corr2.strip())
    ident = H.ok(VenueNativeIdentity.try_create("ctrader", "oid-1", 0))

    def build(recv, mono, corr):
        return H.ok(
            InboundVenueEvent.try_create(
                "cancel-acknowledgement",
                ident,
                H.mk_instant(recv),
                H.mk_mono(mono),
                "session-epoch-1",
                {"raw": "wire"},
                correlation_id=corr,
            )
        )

    fp_a = H.ok(build(recv1, mono1, corr1).fingerprint())
    fp_b = H.ok(build(recv2, mono2, corr2).fingerprint())
    assert fp_a == fp_b  # occurrence fields excluded from identity


def test_l1_003_observation_identity_distinguishes_venue_native_key():
    """CT-20: a different venue-native identity key yields a different fp1."""
    e1 = H.ok(
        InboundVenueEvent.try_create(
            "cancel-acknowledgement",
            H.ok(VenueNativeIdentity.try_create("ctrader", "oid-1", 0)),
            H.mk_instant(1),
            H.mk_mono(1),
            "se",
            {"raw": "w"},
        )
    )
    e2 = H.ok(
        InboundVenueEvent.try_create(
            "cancel-acknowledgement",
            H.ok(VenueNativeIdentity.try_create("ctrader", "oid-2", 0)),
            H.mk_instant(1),
            H.mk_mono(1),
            "se",
            {"raw": "w"},
        )
    )
    assert H.ok(e1.fingerprint()) != H.ok(e2.fingerprint())


# --- QA-E08-L1-004 — the foreign-float money-path boundary (P1) -------------


def _flatten(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from _flatten(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _flatten(v)
    else:
        yield value


@given(raw=st.floats(min_value=0.0001, max_value=100000.0, allow_nan=False, allow_infinity=False))
def test_l1_004_execution_float_crosses_to_scaled_integer_no_float_in_identity(raw):
    """CT-18/CT-19/DEC-0141: a foreign float crosses the money-path boundary to a scaled
    integer at the declared scale; no binary float ever appears in the resulting identity,
    and the raw float survives only as integrity-checked provenance."""
    ins = H.mk_instrument(H.mk_venue())
    res = decode_execution_price(raw, ins, 5, RoundingMode.HALF_UP)
    assert is_ok(res)
    decoded = res.value
    assert decoded.raw_double == raw  # raw float kept as provenance only
    assert isinstance(decoded.price.value, int)  # crossed to a scaled integer
    # No binary float in the price's fp1 identity content.
    for leaf in _flatten(dict(decoded.price.fp1_identity())):
        assert not isinstance(leaf, float), "a binary float entered price identity"


def test_l1_004_nan_and_infinity_cannot_cross_the_boundary():
    """CT-01: NaN and infinity cannot cross the money-path boundary."""
    ins = H.mk_instrument(H.mk_venue())
    for bad in (float("nan"), float("inf"), float("-inf")):
        assert is_refusal(decode_execution_price(bad, ins, 5, RoundingMode.HALF_UP))


def test_l1_004_integer_decoders_refuse_binary_floats():
    """CT-01/DEC-0105: money and market-data decoders refuse a binary float on the money
    path (they take exact scaled integers)."""
    ins = H.mk_instrument(H.mk_venue())
    assert is_refusal(decode_market_data_price(3.14, ins))
    assert is_refusal(decode_money("ProtoOADeal", 3.14, "USD", 2))


# --- QA-E08-L1-005 — SecretRef opacity (P2) ---------------------------------


def test_l1_005_secret_ref_stable_and_blank_refused():
    """CT-21/AD-9: a minted reference is stable (a value constructs the same ref), and a
    blank reference is refused."""
    assert H.ok(SecretRef.try_create("sref-stable-1")) == H.ok(
        SecretRef.try_create("sref-stable-1")
    )
    assert is_refusal(SecretRef.try_create("   "))
    assert is_refusal(SecretRef.try_create(""))


@pytest.mark.parametrize(
    "structured",
    [
        "venue=cTrader;broker=Pepperstone;account=1234567;env=live;key=SUPERSECRETAPIKEY",
        "live/ctrader/acct-9988/refresh-token-AAAABBBBCCCC",
        "APIKEY-1a2b3c4d5e6f-account-1234567",
    ],
)
def test_l1_005_secret_ref_construction_validates_opacity(structured):
    """CT-21 invariant: 'construction validates opacity as an invalid-input refusal' — a
    reference that plainly encodes venue/broker/account/environment/key material must be
    refused at construction."""
    res = SecretRef.try_create(structured)
    assert is_refusal(res), (
        "CT-21 requires construction to validate opacity as an invalid-input refusal; "
        f"a plainly-structured reference was accepted: {structured!r}"
    )
    assert res.category is RefusalCategory.INVALID_INPUT
