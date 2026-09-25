"""Executable definition of honest FX paper (Story 31.6; CONNECT AD-2).

An FX paper claim requires every element together: vendor demo host
``demo.ctraderapi.com``; ``AccountRole.DEMO``; ``world = live``;
``VenueClientKind.CTRADER``; the same ``LiveCTraderClient`` used for live;
submit encode of every CT-19 kind the bound CT-18 supports; position and
balance read-back per Story 31.5. Absence of any element fails the claim.

This module does not run a soak week, invent KSA values, treat profit as
evidence, or grant live-money, promotion, or go-live authority. Book PAPER
routing remains one paired demo with its own BMS and virtual ledger.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    AccountRole,
    Fingerprint,
    Ok,
    Result,
    TypedRefusal,
    World,
    fingerprint,
    is_refusal,
)

from qmn.paper._refuse import clean_token, invalid, policy, unsupported
from qmn.paper.first_deployment import LIVE_SENSING_FORBIDDEN, LiveSensingAdmission
from qmn.paper.routing import NODE_PAPER_ACCOUNT_ROLE, NODE_PAPER_WORLD, PairedDemoBinding
from qmn.venue import (
    CommandKind,
    LiveCTraderClient,
    Reconciliation,
    ReconciliationVerdict,
    VenueClientKind,
    select_venue_client,
)
from qmn.venue.live import WireKind

__all__ = [
    "CANONICAL_SOURCE_TOKEN",
    "FX_PAPER_CLAIM_CLASS",
    "FX_PAPER_CLAIM_FORMAT_VERSION",
    "FX_PAPER_CLAIM_SURFACE",
    "FX_PAPER_REQUIRED_ELEMENTS",
    "GRANTS_LIVE_MONEY",
    "ILLEGAL_PAPER_SKIPS",
    "INVENTS_KSA_VALUES",
    "LOCAL_MATCHING_ENGINE",
    "PROFIT_IS_EVIDENCE",
    "RUNS_SOAK_WEEK",
    "SPOT_FX_INCLUDED",
    "V1_VENUE_CLIENT_KINDS",
    "VENDOR_DEMO_HOST",
    "FxPaperClaim",
    "encoded_kinds_from_client",
    "evaluate_fx_paper_claim",
    "live_client_implementation_for",
    "readback_kinds_from_client",
    "refuse_fourth_venue_client_kind",
    "refuse_fx_paper_illegal_skip",
    "refuse_fx_paper_invented_ksa",
    "refuse_fx_paper_live_authority",
    "refuse_fx_paper_local_matching",
    "refuse_fx_paper_profit",
    "refuse_fx_paper_soak_week",
    "refuse_fx_paper_twins",
    "refuse_non_ctrader_live_mapping",
]

FX_PAPER_CLAIM_SURFACE: Final[str] = "qmn.paper.fx_claim"
FX_PAPER_CLAIM_CLASS: Final[str] = "fx-paper-claim"
FX_PAPER_CLAIM_FORMAT_VERSION: Final[int] = 1
VENDOR_DEMO_HOST: Final[str] = "demo.ctraderapi.com"
CANONICAL_SOURCE_TOKEN: Final[str] = "ctrader"  # noqa: S105
SPOT_FX_INCLUDED: Final[bool] = True
RUNS_SOAK_WEEK: Final[bool] = False
GRANTS_LIVE_MONEY: Final[bool] = False
PROFIT_IS_EVIDENCE: Final[bool] = False
INVENTS_KSA_VALUES: Final[bool] = False
LOCAL_MATCHING_ENGINE: Final[bool] = False

FX_PAPER_REQUIRED_ELEMENTS: Final[tuple[str, ...]] = (
    "vendor_demo_host",
    "account_role_demo",
    "world_live",
    "venue_client_kind_ctrader",
    "live_ctrader_client",
    "submit_encode",
    "position_balance_readback",
)

V1_VENUE_CLIENT_KINDS: Final[tuple[str, ...]] = (
    VenueClientKind.CTRADER.value,
    VenueClientKind.REPLAY.value,
    VenueClientKind.CONFORMANCE.value,
)

ILLEGAL_PAPER_SKIPS: Final[frozenset[str]] = frozenset(
    {
        "live-capital-size",
        "spot-fx-later",
    }
)

_REQUIRED_READBACKS: Final[frozenset[str]] = frozenset(
    {WireKind.POSITION_READBACK.value, WireKind.BALANCE_READBACK.value}
)
_READBACK_ALIASES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "balance-read-back": WireKind.BALANCE_READBACK.value,
        "balance-readback": WireKind.BALANCE_READBACK.value,
        "position-read-back": WireKind.POSITION_READBACK.value,
        "position-readback": WireKind.POSITION_READBACK.value,
    }
)
_SKIP_ALIASES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "live capital size": "live-capital-size",
        "live-capital-size": "live-capital-size",
        "live_capital_size": "live-capital-size",
        "spot fx later": "spot-fx-later",
        "spot-fx-later": "spot-fx-later",
        "spot_fx_later": "spot-fx-later",
    }
)
_LIVE_AUTHORITY_IDS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "command-stream": "fx_paper.live_command_stream",
        "execution-target": "fx_paper.live_execution_target",
        "go-live": "fx_paper.go_live",
        "live-binding": "fx_paper.live_binding",
        "promotion": "fx_paper.promotion",
        "sequencer": "fx_paper.live_sequencer",
    }
)

_ID_MISSING = "fx_paper.missing_element"
_ID_SKIP = "fx_paper.illegal_skip"
_ID_FOURTH = "fx_paper.fourth_kind"
_ID_MAP = "fx_paper.non_ctrader_mapping"
_ID_SOAK = "fx_paper.soak_week"
_ID_KSA = "fx_paper.invented_ksa"
_ID_PROFIT = "fx_paper.profit"
_ID_TWINS = "fx_paper.twins"
_ID_MATCHING = "fx_paper.local_matching"


@dataclass(frozen=True, slots=True)
class FxPaperClaim:
    """Sealed honest-FX-paper claim. Machinery proof, never live-money authority."""

    fingerprint: Fingerprint
    vendor_host: str
    account_role: AccountRole
    world: World
    venue_client_kind: VenueClientKind
    client_type: str
    declared_kinds: frozenset[str]
    encoded_kinds: frozenset[str]
    readback_kinds: frozenset[str]
    reconcile_verdict: ReconciliationVerdict
    paired_demo_account: str
    own_bms: bool
    paper_virtual_ledger: bool
    live_sensing_only: bool
    spot_fx_included: bool = True
    bot_twin_minted: bool = False
    book_twin_minted: bool = False
    local_matching_engine: bool = False
    runs_soak_week: bool = False
    grants_live_money: bool = False
    profit_is_evidence: bool = False
    invents_ksa: bool = False
    canonical_source_token: str = CANONICAL_SOURCE_TOKEN

    def fp1_identity(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "account_role": self.account_role.value,
                "canonical_source_token": self.canonical_source_token,
                "class": FX_PAPER_CLAIM_CLASS,
                "client_type": self.client_type,
                "declared_kinds": sorted(self.declared_kinds),
                "encoded_kinds": sorted(self.encoded_kinds),
                "format_version": FX_PAPER_CLAIM_FORMAT_VERSION,
                "grants_live_money": self.grants_live_money,
                "live_sensing_only": self.live_sensing_only,
                "own_bms": self.own_bms,
                "paired_demo_account": self.paired_demo_account,
                "paper_virtual_ledger": self.paper_virtual_ledger,
                "readback_kinds": sorted(self.readback_kinds),
                "reconcile_verdict": self.reconcile_verdict.value,
                "required_elements": list(FX_PAPER_REQUIRED_ELEMENTS),
                "runs_soak_week": self.runs_soak_week,
                "spot_fx_included": self.spot_fx_included,
                "venue_client_kind": self.venue_client_kind.value,
                "vendor_host": self.vendor_host,
                "world": self.world.value,
            }
        )

    def as_mapping(self) -> Mapping[str, object]:
        payload = dict(self.fp1_identity())
        payload["fingerprint"] = self.fingerprint.value
        return MappingProxyType(payload)


def refuse_fx_paper_illegal_skip(reason: object, **extra: object) -> TypedRefusal:
    """Live-capital size and 'spot FX later' are not legal adapter skips."""
    token = _skip_token(reason)
    return policy(
        "skip",
        "live-capital size and spot-FX-later are not legal skips; spot FX stays in",
        given=token if token is not None else repr(reason),
        illegal=sorted(ILLEGAL_PAPER_SKIPS),
        spot_fx_included=True,
        failure_id=_ID_SKIP,
        **extra,
    )


def refuse_fourth_venue_client_kind(kind: object, **extra: object) -> TypedRefusal:
    """A fourth V1 kind is out of scope and never mapped onto LiveCTraderClient."""
    return unsupported(
        "venue_client_kind",
        "V1 VenueClientKind is ctrader | replay | conformance; a fourth kind is "
        "out of scope and is never config-mapped onto LiveCTraderClient",
        given=_kind_token(kind),
        allowed=list(V1_VENUE_CLIENT_KINDS),
        canonical_source_token=CANONICAL_SOURCE_TOKEN,
        failure_id=_ID_FOURTH,
        **extra,
    )


def refuse_non_ctrader_live_mapping(kind: object, **extra: object) -> TypedRefusal:
    """Replay/conformance (and any other kind) never bind LiveCTraderClient."""
    return unsupported(
        "venue_client_kind",
        "LiveCTraderClient is selected only by roster VenueClientKind ctrader; "
        "no other kind is config-mapped onto it",
        given=_kind_token(kind),
        required=VenueClientKind.CTRADER.value,
        canonical_source_token=CANONICAL_SOURCE_TOKEN,
        failure_id=_ID_MAP,
        **extra,
    )


def refuse_fx_paper_live_authority(kind: object, **extra: object) -> TypedRefusal:
    """Live roster stays sensing/recording until a live binding."""
    token = clean_token(kind) or "live-binding"
    failure_id = _LIVE_AUTHORITY_IDS.get(token, "fx_paper.live_binding")
    return policy(
        "live_authority",
        "a live-role roster entry with credentials remains sensing and recording "
        "only until a live binding — no live command stream, sequencer, or "
        "execution target; this claim grants no live-money, promotion, or "
        "go-live authority",
        given=token,
        forbidden=[*LIVE_SENSING_FORBIDDEN, "promotion", "go-live"],
        failure_id=failure_id,
        **extra,
    )


def refuse_fx_paper_soak_week(**extra: object) -> TypedRefusal:
    """Story 31.6 does not run the unattended week."""
    return policy(
        "soak_week",
        "honest FX paper is a soak precondition; this story does not run the unattended week",
        failure_id=_ID_SOAK,
        runs_soak_week=False,
        **extra,
    )


def refuse_fx_paper_invented_ksa(**extra: object) -> TypedRefusal:
    """This story does not invent KSA matrix values."""
    return policy(
        "invented-value",
        "this story does not invent KSA values",
        failure_id=_ID_KSA,
        invents_ksa=False,
        **extra,
    )


def refuse_fx_paper_profit(**extra: object) -> TypedRefusal:
    """Profit is not evidence of an honest paper claim."""
    return policy(
        "profit",
        "profit is not evidence of honest FX paper; the claim is machinery only",
        failure_id=_ID_PROFIT,
        profit_is_evidence=False,
        **extra,
    )


def refuse_fx_paper_twins(**extra: object) -> TypedRefusal:
    """Paper routing never mints a Bot or Book twin."""
    return policy(
        "twins",
        "Book PAPER routing goes to one paired demo account; no Bot or Book twin",
        failure_id=_ID_TWINS,
        **extra,
    )


def refuse_fx_paper_local_matching(**extra: object) -> TypedRefusal:
    """Honest FX paper has no local matching engine."""
    return policy(
        "local_matching_engine",
        "honest FX paper has no local matching engine",
        failure_id=_ID_MATCHING,
        local_matching_engine=False,
        **extra,
    )


def live_client_implementation_for(kind: object) -> Result[type[LiveCTraderClient]]:
    """Resolve the live client class for a roster kind. Only ctrader maps."""
    token = _kind_token(kind)
    if token == VenueClientKind.CTRADER.value:
        return Ok(LiveCTraderClient)
    if token in {VenueClientKind.REPLAY.value, VenueClientKind.CONFORMANCE.value}:
        return refuse_non_ctrader_live_mapping(kind)
    return refuse_fourth_venue_client_kind(kind)


def encoded_kinds_from_client(client: object) -> Result[frozenset[str]]:
    """CT-19 kinds that reached submit encode-handoff on ``client``."""
    if not isinstance(client, LiveCTraderClient):
        return invalid(
            "client",
            "encoded kinds are collected from a LiveCTraderClient",
            given=type(client).__name__,
            failure_id=_ID_MISSING,
            missing_element="live_ctrader_client",
        )
    rows = client.observations()
    if is_refusal(rows):
        return rows
    kinds: set[str] = set()
    for row in rows.value:
        if row.get("kind") != "encode-handoff" or row.get("encoded") is not True:
            continue
        token = _command_kind_token(row.get("command_kind"))
        if token is not None:
            kinds.add(token)
    return Ok(frozenset(kinds))


def readback_kinds_from_client(client: object) -> Result[frozenset[str]]:
    """Persisted position/balance read-back wire kinds on ``client``."""
    if not isinstance(client, LiveCTraderClient):
        return invalid(
            "client",
            "read-back kinds are collected from a LiveCTraderClient",
            given=type(client).__name__,
            failure_id=_ID_MISSING,
            missing_element="live_ctrader_client",
        )
    rows = client.observations()
    if is_refusal(rows):
        return rows
    kinds: set[str] = set()
    for row in rows.value:
        token = _readback_token_from_row(row)
        if token in _REQUIRED_READBACKS:
            kinds.add(token)
    return Ok(frozenset(kinds))


def evaluate_fx_paper_claim(
    *,
    vendor_host: object,
    client: object,
    paired: object,
    declared_kinds: object,
    encoded_kinds: object,
    readback_kinds: object,
    reconcile_result: object,
    paper_virtual_ledger: object = True,
    live_sensing: object = None,
    skip: object = None,
    proposed_kind: object = None,
    local_matching_engine: object = False,
    run_soak_week: object = False,
    invent_ksa: object = False,
    treat_profit_as_evidence: object = False,
    request_live_binding: object = False,
    request_command_stream: object = False,
    request_sequencer: object = False,
    request_execution_target: object = False,
    request_promotion: object = False,
    request_go_live: object = False,
) -> Result[FxPaperClaim]:
    """Seal an honest FX paper claim, or refuse. Credential-free; no live token."""
    blocked = _refuse_fx_paper_openers(
        run_soak_week=run_soak_week,
        invent_ksa=invent_ksa,
        treat_profit_as_evidence=treat_profit_as_evidence,
        local_matching_engine=local_matching_engine,
        skip=skip,
        request_live_binding=request_live_binding,
        request_command_stream=request_command_stream,
        request_sequencer=request_sequencer,
        request_execution_target=request_execution_target,
        request_promotion=request_promotion,
        request_go_live=request_go_live,
        proposed_kind=proposed_kind,
    )
    if is_refusal(blocked):
        return blocked
    parts = _bind_fx_paper_parts(
        vendor_host=vendor_host,
        client=client,
        paired=paired,
        declared_kinds=declared_kinds,
        encoded_kinds=encoded_kinds,
        readback_kinds=readback_kinds,
        reconcile_result=reconcile_result,
        paper_virtual_ledger=paper_virtual_ledger,
        live_sensing=live_sensing,
        proposed_kind=proposed_kind,
    )
    if is_refusal(parts):
        return parts
    client_obj, paired_obj, declared, encoded, readbacks, reconcile, sensing_only = parts.value
    return _seal_fx_paper_claim(
        client=client_obj,
        paired=paired_obj,
        declared=declared,
        encoded=encoded,
        readbacks=readbacks,
        reconcile=reconcile,
        sensing_only=sensing_only,
    )


def _refuse_fx_paper_openers(
    *,
    run_soak_week: object,
    invent_ksa: object,
    treat_profit_as_evidence: object,
    local_matching_engine: object,
    skip: object,
    request_live_binding: object,
    request_command_stream: object,
    request_sequencer: object,
    request_execution_target: object,
    request_promotion: object,
    request_go_live: object,
    proposed_kind: object,
) -> Result[None]:
    blocked = _refuse_fx_paper_policy_flags(
        run_soak_week=run_soak_week,
        invent_ksa=invent_ksa,
        treat_profit_as_evidence=treat_profit_as_evidence,
        local_matching_engine=local_matching_engine,
        skip=skip,
    )
    if is_refusal(blocked):
        return blocked
    blocked = _refuse_fx_paper_live_requests(
        request_live_binding=request_live_binding,
        request_command_stream=request_command_stream,
        request_sequencer=request_sequencer,
        request_execution_target=request_execution_target,
        request_promotion=request_promotion,
        request_go_live=request_go_live,
    )
    if is_refusal(blocked):
        return blocked
    if proposed_kind is not None:
        impl = live_client_implementation_for(proposed_kind)
        if is_refusal(impl):
            return impl
    return Ok(None)


def _bind_fx_paper_parts(
    *,
    vendor_host: object,
    client: object,
    paired: object,
    declared_kinds: object,
    encoded_kinds: object,
    readback_kinds: object,
    reconcile_result: object,
    paper_virtual_ledger: object,
    live_sensing: object,
    proposed_kind: object,
) -> Result[
    tuple[
        LiveCTraderClient,
        PairedDemoBinding,
        frozenset[str],
        frozenset[str],
        frozenset[str],
        Reconciliation,
        bool,
    ]
]:
    sensing = _bind_fx_paper_sensing(live_sensing)
    if is_refusal(sensing):
        return sensing
    bound_client = _bind_fx_paper_client(vendor_host, client)
    if is_refusal(bound_client):
        return bound_client
    bound_paired = _bind_fx_paper_paired(paired, paper_virtual_ledger)
    if is_refusal(bound_paired):
        return bound_paired
    kinds = _bind_fx_paper_kinds(declared_kinds, encoded_kinds)
    if is_refusal(kinds):
        return kinds
    readbacks = _bind_fx_paper_readbacks(readback_kinds, reconcile_result)
    if is_refusal(readbacks):
        return readbacks
    if proposed_kind is not None:
        selected = _bind_fx_paper_proposed_kind(bound_client.value, proposed_kind)
        if is_refusal(selected):
            return selected
    declared, encoded = kinds.value
    readback_set, reconcile = readbacks.value
    return Ok(
        (
            bound_client.value,
            bound_paired.value,
            declared,
            encoded,
            readback_set,
            reconcile,
            sensing.value,
        )
    )


def _refuse_fx_paper_policy_flags(
    *,
    run_soak_week: object,
    invent_ksa: object,
    treat_profit_as_evidence: object,
    local_matching_engine: object,
    skip: object,
) -> Result[None]:
    if RUNS_SOAK_WEEK or run_soak_week is True:
        return refuse_fx_paper_soak_week()
    if INVENTS_KSA_VALUES or invent_ksa is True:
        return refuse_fx_paper_invented_ksa()
    if PROFIT_IS_EVIDENCE or treat_profit_as_evidence is True:
        return refuse_fx_paper_profit()
    if LOCAL_MATCHING_ENGINE or local_matching_engine is True:
        return refuse_fx_paper_local_matching()
    if skip is not None:
        return refuse_fx_paper_illegal_skip(skip)
    return Ok(None)


def _refuse_fx_paper_live_requests(
    *,
    request_live_binding: object,
    request_command_stream: object,
    request_sequencer: object,
    request_execution_target: object,
    request_promotion: object,
    request_go_live: object,
) -> Result[None]:
    if request_live_binding is True:
        return refuse_fx_paper_live_authority("live-binding")
    if request_command_stream is True:
        return refuse_fx_paper_live_authority("command-stream")
    if request_sequencer is True:
        return refuse_fx_paper_live_authority("sequencer")
    if request_execution_target is True:
        return refuse_fx_paper_live_authority("execution-target")
    if request_promotion is True:
        return refuse_fx_paper_live_authority("promotion")
    if request_go_live is True:
        return refuse_fx_paper_live_authority("go-live")
    return Ok(None)


def _bind_fx_paper_sensing(live_sensing: object) -> Result[bool]:
    if live_sensing is None:
        return Ok(True)
    if not isinstance(live_sensing, LiveSensingAdmission):
        return invalid(
            "live_sensing",
            "live sensing is a LiveSensingAdmission or omitted",
            given=type(live_sensing).__name__,
        )
    if live_sensing.has_live_binding:
        return refuse_fx_paper_live_authority("live-binding")
    if live_sensing.has_command_stream:
        return refuse_fx_paper_live_authority("command-stream")
    if live_sensing.opens_sequencer:
        return refuse_fx_paper_live_authority("sequencer")
    if live_sensing.resolves_execution_target:
        return refuse_fx_paper_live_authority("execution-target")
    return Ok(True)


def _require_fx_paper_client_shape(client: LiveCTraderClient) -> Result[None]:
    if client.kind is not VenueClientKind.CTRADER:
        return _missing(
            "venue_client_kind_ctrader",
            "FX paper requires VenueClientKind ctrader",
            given=client.kind.value,
            expected=VenueClientKind.CTRADER.value,
        )
    if client.world is not World.LIVE:
        return _missing(
            "world_live",
            "FX paper requires world=live",
            given=client.world.value,
            expected=World.LIVE.value,
        )
    bound_host = client.open_api_host
    if bound_host is not None and bound_host.strip() != VENDOR_DEMO_HOST:
        return _missing(
            "vendor_demo_host",
            "a bound Open API host for FX paper must be demo.ctraderapi.com",
            given=bound_host,
            expected=VENDOR_DEMO_HOST,
        )
    account = client.account
    if account is None or account.role is not NODE_PAPER_ACCOUNT_ROLE:
        return _missing(
            "account_role_demo",
            "FX paper requires AccountRole.DEMO",
            given=None if account is None else account.role.value,
            expected=AccountRole.DEMO.value,
        )
    if not client.capabilities_verified:
        return _missing(
            "submit_encode",
            "submit encode requires an open session and verified capabilities",
            given="capabilities_unverified",
        )
    return Ok(None)


def _bind_fx_paper_client(vendor_host: object, client: object) -> Result[LiveCTraderClient]:
    host = clean_token(vendor_host)
    if host != VENDOR_DEMO_HOST:
        return _missing(
            "vendor_demo_host",
            "vendor host must be demo.ctraderapi.com",
            given=host if host is not None else repr(vendor_host),
            expected=VENDOR_DEMO_HOST,
        )
    if not isinstance(client, LiveCTraderClient):
        return _missing(
            "live_ctrader_client",
            "FX paper uses LiveCTraderClient, the same implementation used for live",
            given=type(client).__name__,
            expected="LiveCTraderClient",
        )
    shaped = _require_fx_paper_client_shape(client)
    if is_refusal(shaped):
        return shaped
    return Ok(client)


def _bind_fx_paper_paired(
    paired: object, paper_virtual_ledger: object
) -> Result[PairedDemoBinding]:
    if not isinstance(paired, PairedDemoBinding):
        return invalid(
            "paired",
            "Book PAPER routing reads a PairedDemoBinding",
            given=type(paired).__name__,
        )
    if paired.bot_twin_minted or paired.book_twin_minted:
        return refuse_fx_paper_twins(
            bot_twin_minted=paired.bot_twin_minted,
            book_twin_minted=paired.book_twin_minted,
        )
    if paired.world is not NODE_PAPER_WORLD:
        return _missing(
            "world_live",
            "paired demo paper routing keeps world=live",
            given=paired.world.value,
            expected=World.LIVE.value,
        )
    if paired.paper_target.role is not NODE_PAPER_ACCOUNT_ROLE:
        return _missing(
            "account_role_demo",
            "the paper-routing target is a paired demo account",
            given=paired.paper_target.role.value,
            expected=AccountRole.DEMO.value,
        )
    own_bms = paired.pairing.live_bms_instance_id != paired.pairing.paired_bms_instance_id
    if not own_bms:
        return policy(
            "paired_bms",
            "the paired demo account has its own BMS instance",
            failure_id=_ID_MISSING,
            missing_element="paired_demo",
        )
    if paper_virtual_ledger is not True:
        return policy(
            "paper_virtual_ledger",
            "the paired demo account has its own virtual ledger",
            given=repr(paper_virtual_ledger),
            failure_id=_ID_MISSING,
            missing_element="paired_demo",
        )
    return Ok(paired)


def _bind_fx_paper_kinds(
    declared_kinds: object, encoded_kinds: object
) -> Result[tuple[frozenset[str], frozenset[str]]]:
    declared = _as_kind_set(declared_kinds, "declared_kinds")
    if is_refusal(declared):
        return declared
    encoded = _as_kind_set(encoded_kinds, "encoded_kinds")
    if is_refusal(encoded):
        return encoded
    if not declared.value:
        return _missing(
            "submit_encode",
            "the bound CT-18 declaration must name at least one CT-19 kind",
            given=[],
        )
    missing_kinds = sorted(declared.value - encoded.value)
    if missing_kinds:
        return _missing(
            "submit_encode",
            "submit encode of every CT-19 kind the bound CT-18 supports is required",
            missing_kinds=missing_kinds,
            declared=sorted(declared.value),
            encoded=sorted(encoded.value),
        )
    return Ok((declared.value, encoded.value))


def _bind_fx_paper_readbacks(
    readback_kinds: object, reconcile_result: object
) -> Result[tuple[frozenset[str], Reconciliation]]:
    readbacks = _as_readback_set(readback_kinds)
    if is_refusal(readbacks):
        return readbacks
    missing_readbacks = sorted(_REQUIRED_READBACKS - readbacks.value)
    if missing_readbacks:
        return _missing(
            "position_balance_readback",
            "position and balance read-back per Story 31.5 are required",
            missing_kinds=missing_readbacks,
            expected=sorted(_REQUIRED_READBACKS),
        )
    if isinstance(reconcile_result, TypedRefusal):
        return _missing(
            "position_balance_readback",
            "reconcile must return a four-verdict Reconciliation, not a refusal",
            given=reconcile_result.category.value,
        )
    if not isinstance(reconcile_result, Reconciliation):
        return invalid(
            "reconcile_result",
            "reconcile evidence is a Reconciliation",
            given=type(reconcile_result).__name__,
            failure_id=_ID_MISSING,
            missing_element="position_balance_readback",
        )
    if reconcile_result.verdict not in ReconciliationVerdict:
        return _missing(
            "position_balance_readback",
            "reconcile verdict is reconciled | drift | unknown | out-of-lookback",
            given=repr(reconcile_result.verdict),
        )
    return Ok((readbacks.value, reconcile_result))


def _bind_fx_paper_proposed_kind(client: LiveCTraderClient, proposed_kind: object) -> Result[None]:
    selection = select_venue_client(client.world, client.venue_id, proposed_kind)
    if is_refusal(selection):
        return selection
    if selection.value.kind is not VenueClientKind.CTRADER:
        return refuse_non_ctrader_live_mapping(proposed_kind)
    return Ok(None)


def _provisional_fx_paper_claim(
    *,
    client: LiveCTraderClient,
    paired: PairedDemoBinding,
    declared: frozenset[str],
    encoded: frozenset[str],
    readbacks: frozenset[str],
    reconcile: Reconciliation,
    sensing_only: bool,
) -> FxPaperClaim:
    return FxPaperClaim(
        fingerprint=Fingerprint(value="fp1:sha256:" + ("0" * 64)),
        vendor_host=VENDOR_DEMO_HOST,
        account_role=NODE_PAPER_ACCOUNT_ROLE,
        world=NODE_PAPER_WORLD,
        venue_client_kind=VenueClientKind.CTRADER,
        client_type=type(client).__name__,
        declared_kinds=declared,
        encoded_kinds=encoded,
        readback_kinds=readbacks,
        reconcile_verdict=reconcile.verdict,
        paired_demo_account=paired.paper_target.account_id,
        own_bms=True,
        paper_virtual_ledger=True,
        live_sensing_only=sensing_only,
        spot_fx_included=SPOT_FX_INCLUDED,
        bot_twin_minted=False,
        book_twin_minted=False,
        local_matching_engine=False,
        runs_soak_week=False,
        grants_live_money=GRANTS_LIVE_MONEY,
        profit_is_evidence=False,
        invents_ksa=False,
        canonical_source_token=CANONICAL_SOURCE_TOKEN,
    )


def _seal_fx_paper_claim(
    *,
    client: LiveCTraderClient,
    paired: PairedDemoBinding,
    declared: frozenset[str],
    encoded: frozenset[str],
    readbacks: frozenset[str],
    reconcile: Reconciliation,
    sensing_only: bool,
) -> Result[FxPaperClaim]:
    provisional = _provisional_fx_paper_claim(
        client=client,
        paired=paired,
        declared=declared,
        encoded=encoded,
        readbacks=readbacks,
        reconcile=reconcile,
        sensing_only=sensing_only,
    )
    packet_fp = fingerprint(dict(provisional.fp1_identity()))
    if is_refusal(packet_fp):
        return packet_fp
    return Ok(replace(provisional, fingerprint=packet_fp.value))


def _missing(element: str, reason: str, **extra: object) -> TypedRefusal:
    extra.setdefault("required_elements", list(FX_PAPER_REQUIRED_ELEMENTS))
    return policy(
        "fx_paper_claim",
        reason,
        failure_id=_ID_MISSING,
        missing_element=element,
        **extra,
    )


def _kind_token(value: object) -> str | None:
    if isinstance(value, VenueClientKind):
        return value.value
    return clean_token(value)


def _command_kind_token(value: object) -> str | None:
    if isinstance(value, CommandKind):
        return value.value
    return clean_token(value)


def _skip_token(value: object) -> str | None:
    raw = clean_token(value)
    if raw is None:
        return None
    return _SKIP_ALIASES.get(raw.strip().lower(), raw.strip().lower())


def _readback_token_from_payload(payload_obj: object) -> str | None:
    if not isinstance(payload_obj, dict):
        return None
    payload = cast("Mapping[str, object]", payload_obj)
    nested = _normalize_readback(payload.get("wire_kind"))
    if nested in _REQUIRED_READBACKS:
        return nested
    nested_kind = _normalize_readback(payload.get("kind"))
    if nested_kind in _REQUIRED_READBACKS:
        return nested_kind
    return None


def _readback_token_from_row(row: Mapping[str, object]) -> str | None:
    token = _normalize_readback(row.get("kind"))
    if token in _REQUIRED_READBACKS:
        return token
    token = _normalize_readback(row.get("wire_kind"))
    if token in _REQUIRED_READBACKS:
        return token
    return _readback_token_from_payload(row.get("payload"))


def _normalize_readback(value: object) -> str | None:
    token = value.value if isinstance(value, WireKind) else clean_token(value)
    if token is None:
        return None
    return _READBACK_ALIASES.get(token, token)


def _as_kind_set(value: object, field: str) -> Result[frozenset[str]]:
    if isinstance(value, str | bytes) or not isinstance(value, Iterable):
        return invalid(
            field,
            "command kinds are a collection of CT-19 kind tokens",
            given=type(value).__name__,
            failure_id=_ID_MISSING,
            missing_element="submit_encode",
        )
    tokens: set[str] = set()
    for item in cast("Iterable[object]", value):
        token = _command_kind_token(item)
        if token is None:
            return invalid(
                field,
                "each command kind is a non-empty CT-19 token",
                given=repr(item),
                failure_id=_ID_MISSING,
                missing_element="submit_encode",
            )
        tokens.add(token)
    return Ok(frozenset(tokens))


def _as_readback_set(value: object) -> Result[frozenset[str]]:
    if isinstance(value, str | bytes) or not isinstance(value, Iterable):
        return invalid(
            "readback_kinds",
            "read-back kinds are a collection of wire-kind tokens",
            given=type(value).__name__,
            failure_id=_ID_MISSING,
            missing_element="position_balance_readback",
        )
    tokens: set[str] = set()
    for item in cast("Iterable[object]", value):
        token = _normalize_readback(item)
        if token is None:
            return invalid(
                "readback_kinds",
                "each read-back kind is a non-empty wire-kind token",
                given=repr(item),
                failure_id=_ID_MISSING,
                missing_element="position_balance_readback",
            )
        tokens.add(token)
    return Ok(frozenset(tokens))
