"""``product_session`` journal projection — bound request context (Stories 55.1–55.4).

COMP-QMA-DAEMON owns the sqlite fold over ``product_session.*``. Ids are
``psess:``; QMA Session ids remain ``sess:``. ``product_session.context`` is
the bound request context a public call must match. Occupancy stays none
until a live-adjacent story. A tab is not this row. No sixth COMP, no new
CT, no new sqlite class. Absent at inspect SHA 270e992 (DEC-0450; GAP-0093).

Story 55.2: ``granted_ops`` stores grant_ids. The host resolves GrantRecord
from the ledger beside this projection. Envelope mismatch is GRANT_MISMATCH
before execution. Revoke/expiry refuse new dispatch; already-accepted work
may finish. Upgrade cannot widen without an explicit re-grant that bumps
``context_revision``. Manifests request; the host grants.

Story 55.3: session context lives on the existing daemon journal (CAS), not
a tab. Restart/reconnect restores the same bound context by folding
``product_session.*`` events — not in-process RAM. Two tabs of one product
share one ``psess:``. Closing a tab writes nothing and does not close the
session. A new tab does not mint a new product_session.

Story 55.4: a tab/window/view is not a product_session and does not own
grants or occupancy. ``view:*`` remains an AD-17 wire DTO only — not a
plugin contribution point and not a ContributionHit (GAP-0081;
SCN-0018 Branch B). Occupancy stays none. GAP-0081 chrome is not filled.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qma.core.ontology.records import Profile, Session
from qma.core.operations.descriptor import OperationDescriptor
from qma.core.refusals.variants import EnvelopeMismatch, GrantMismatch, GrantWidenRefused
from qma.core.vocabulary.enums import PrincipalClass
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qma.daemon.journal.authoritative import AuthoritativeJournal
from qma.daemon.journal.stores import StoreClass
from qma.daemon.persistence.sqlite_writer import SingleSqliteWriter
from qma.daemon.sessions.grant_binding import (
    GRANT_SIXTH_STORE_MINTED,
    TOOL_REGISTRY_REWRITTEN,
    BoundSessionGrant,
    GrantSqliteStore,
    compare_envelope_to_grant,
    moment_for_transport,
    require_session_grant_id,
)
from qma.wire.envelope import SCOPE_KIND_ORDER
from qma.wire.grant_record import (
    AcceptedGrantWork,
    GrantRecord,
    GrantRevocation,
    HostGrantLedger,
    RegrantResult,
    parse_granted_ops,
    refuse_in_place_upgrade,
    refuse_manifest_grant,
)
from qma.wire.invocation_envelope import (
    AuthoritativeStores,
    BoundInvocation,
    ContributionBinding,
    ContributionRecord,
    InstanceRecord,
    InvocationEnvelope,
    dispatch_public_call,
    parse_invocation_envelope,
    parse_utc_iso_z,
)
from qmf.core.refusal import Ok, RefusalCategory, Result, Retryability, TypedRefusal, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection, storage_failure

__all__ = [
    "CHROME_KINDS",
    "CHROME_OWNS_GRANTS",
    "CHROME_OWNS_OCCUPANCY",
    "GAP_0081_CHROME_FILLED",
    "GRANT_SIXTH_STORE_MINTED",
    "PRODUCT_SESSION_CONTEXT_FIELDS",
    "PRODUCT_SESSION_EXISTED_AT_INSPECT_SHA",
    "PRODUCT_SESSION_FOLD_ID",
    "PRODUCT_SESSION_ID_PREFIX",
    "PRODUCT_SESSION_INSPECT_SHAS",
    "PRODUCT_SESSION_LIVE_ADJACENT",
    "PRODUCT_SESSION_NEW_CT_MINTED",
    "PRODUCT_SESSION_OCCUPANCY",
    "PRODUCT_SESSION_OWNER",
    "PRODUCT_SESSION_SIXTH_COMP_MINTED",
    "PRODUCT_SESSION_SIXTH_STORE_MINTED",
    "PRODUCT_SESSION_STORE",
    "PRODUCT_SESSION_STORE_CLASS",
    "PRODUCT_SESSION_TABLE",
    "PRODUCT_SESSION_TAB_WRITES",
    "PRODUCT_SESSION_WIRED_AT_INSPECT_SHA",
    "QMA_SESSION_ID_PREFIX",
    "RECONNECT_KIND_QUERY",
    "RECONNECT_KIND_RESYNC",
    "SELECTED_REF_KINDS",
    "TOOL_REGISTRY_REWRITTEN",
    "BoundProductSessionCall",
    "BoundSessionGrant",
    "ProductSession",
    "ProductSessionContext",
    "ProductSessionProfile",
    "ProductSessionService",
    "ReconnectSnapshot",
    "SelectedRef",
    "bind_public_call_to_context",
    "claim_product_session_at_inspect_sha",
    "compare_envelope_to_grant",
    "looks_like_chrome_id",
    "parse_product_session_profile",
    "refuse_chrome_owns_grants",
    "refuse_chrome_owns_occupancy",
    "refuse_reconnect_replays_intent",
    "refuse_tab_as_product_session",
    "refuse_tab_mints_session",
]


PRODUCT_SESSION_OWNER: Final[str] = "COMP-QMA-DAEMON"
PRODUCT_SESSION_STORE: Final[str] = "product_session"
PRODUCT_SESSION_FOLD_ID: Final[str] = "product_session_state"
PRODUCT_SESSION_TABLE: Final[str] = "product_session"
PRODUCT_SESSION_STORE_CLASS: Final[str] = StoreClass.JOURNAL_DERIVED_PROJECTION.value
PRODUCT_SESSION_ID_PREFIX: Final[str] = "psess:"
QMA_SESSION_ID_PREFIX: Final[str] = "sess:"
PRODUCT_SESSION_OCCUPANCY: Final[str] = "none"
PRODUCT_SESSION_LIVE_ADJACENT: Final[bool] = False
PRODUCT_SESSION_INSPECT_SHAS: Final[tuple[str, ...]] = ("270e992",)
PRODUCT_SESSION_EXISTED_AT_INSPECT_SHA: Final[bool] = False
PRODUCT_SESSION_WIRED_AT_INSPECT_SHA: Final[bool] = False
PRODUCT_SESSION_SIXTH_COMP_MINTED: Final[bool] = False
PRODUCT_SESSION_SIXTH_STORE_MINTED: Final[bool] = False
PRODUCT_SESSION_NEW_CT_MINTED: Final[bool] = False
PRODUCT_SESSION_TAB_WRITES: Final[bool] = False
CHROME_KINDS: Final[frozenset[str]] = frozenset({"tab", "window", "view"})
CHROME_OWNS_GRANTS: Final[bool] = False
CHROME_OWNS_OCCUPANCY: Final[bool] = False
GAP_0081_CHROME_FILLED: Final[bool] = False
_CHROME_ID_PREFIXES: Final[tuple[str, ...]] = (
    "tab:",
    "tab/",
    "window:",
    "window/",
    "view:",
    "view/",
    "ui-tab",
    "ui_view",
    "ui-view",
)
PRODUCT_SESSION_MINT_EVENT: Final[str] = "product_session.minted"
PRODUCT_SESSION_GRANT_MINTED_EVENT: Final[str] = "product_session.grant_minted"
PRODUCT_SESSION_GRANT_REVOKED_EVENT: Final[str] = "product_session.grant_revoked"
PRODUCT_SESSION_GRANT_REGRANTED_EVENT: Final[str] = "product_session.grant_regranted"
PRODUCT_SESSION_GRANT_ACCEPTED_EVENT: Final[str] = "product_session.grant_accepted"
PRODUCT_SESSION_CURSOR_RESYNC_EVENT: Final[str] = "product_session.cursor_resync"
RECONNECT_KIND_QUERY: Final[str] = "query"
RECONNECT_KIND_RESYNC: Final[str] = "snapshot/resync"
_HOST_ISSUER: Final[str] = "host"
_RECONNECT_INTENT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "command_id",
        "payload",
        "payload_hash",
        "expected_revision",
        "unacked",
        "intent",
    }
)

PRODUCT_SESSION_CONTEXT_FIELDS: Final[tuple[str, ...]] = (
    "principal",
    "account_scope",
    "occupancy",
    "contribution",
    "instance_id",
    "config_revision",
    "as_of",
)
DURABLE_FIELDS: Final[tuple[str, ...]] = (
    "product_session_id",
    "profile",
    "principal",
    "context_revision",
    "app_instance_id",
    "granted_ops",
    "selected_refs",
    "account_scope",
    "resume_cursor",
    "cursor_generation",
)
NOT_DURABLE_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "qma_session_id",
        "session_id",
        "tab",
        "tab_id",
        "ui_tab",
        "window",
        "window_id",
        "ui_window",
        "view",
        "view_id",
        "ui_view",
        "pane",
        "pane_id",
        "attachment",
        "layout",
        "board_layout",
    }
)
SELECTED_REF_KINDS: Final[frozenset[str]] = frozenset(
    {
        "artifact",
        "research_ref",
        "contribution",
        "template",
        "dataset",
        "run",
        "attempt",
        "node_ids",
    }
)
_FORBIDDEN_SELECTED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "board_layout",
        "json-render",
        "json_render",
        "layout",
        "positions",
        "tree",
        "widget",
        "widgets",
    }
)
_TAB_FIELD_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "tab",
        "tab_id",
        "ui_tab",
        "client_tab",
        "dashboard_tab",
        "window",
        "window_id",
        "ui_window",
        "client_window",
        "view",
        "view_id",
        "ui_view",
        "pane",
        "pane_id",
    }
)
_SCHEMA_SQL: Final[str] = """
CREATE TABLE IF NOT EXISTS product_session (
    product_session_id TEXT PRIMARY KEY NOT NULL,
    payload TEXT NOT NULL,
    journal_seq INTEGER NOT NULL,
    recorded_at INTEGER NOT NULL
);
"""


class ProductSessionProfile(StrEnum):
    """Closed product-session profile; immutable at create (FR-WF-29; AD-8).

    Not ``qma.core.ontology.Profile``.
    """

    AUTHORING = "authoring"
    APP_USE = "app-use"


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    return invalid_input(field, reason, **extra)


def looks_like_chrome_id(value: object) -> bool:
    """True when ``value`` names a tab/window/view rather than a ``psess:`` row."""
    if not isinstance(value, str):
        return False
    folded = value.strip().casefold()
    if folded.startswith(_CHROME_ID_PREFIXES):
        return True
    if folded.startswith(("tab-", "window-", "view-", "pane-")):
        return True
    return folded in CHROME_KINDS or folded in {"pane", "ui_tab", "ui_window"}


def refuse_tab_as_product_session(**extra: object) -> TypedRefusal:
    """A tab/window/view is not a product_session row (Story 55.4; AD-8)."""
    context: dict[str, object] = {
        "field": "tab",
        "reason": "a tab/window/view is not a product_session row; "
        "sessions own context and grants (AD-8; Story 55.4)",
        "tab_writes": False,
        "chrome_owns_grants": False,
        "chrome_owns_occupancy": False,
        "store": PRODUCT_SESSION_STORE,
    }
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=MappingProxyType(context),
    )


def refuse_chrome_owns_grants(**extra: object) -> TypedRefusal:
    """Chrome does not own grants; product_session.granted_ops does (AD-8)."""
    context: dict[str, object] = {
        "field": extra.pop("field", "grant"),
        "reason": "a tab/window/view does not own grants; "
        "product_session.granted_ops does (AD-8; Story 55.4)",
        "chrome_owns_grants": False,
        "occupancy": PRODUCT_SESSION_OCCUPANCY,
        "store": PRODUCT_SESSION_STORE,
    }
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=MappingProxyType(context),
    )


def refuse_chrome_owns_occupancy(**extra: object) -> TypedRefusal:
    """Chrome does not own occupancy; occupancy stays none (AD-8; AD-17)."""
    context: dict[str, object] = {
        "field": extra.pop("field", "occupancy"),
        "reason": "a tab/window/view does not own occupancy; occupancy stays none "
        "(AD-8; AD-17; Story 55.4)",
        "chrome_owns_occupancy": False,
        "occupancy": PRODUCT_SESSION_OCCUPANCY,
        "live_adjacent": False,
        "store": PRODUCT_SESSION_STORE,
    }
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=MappingProxyType(context),
    )


def refuse_tab_mints_session(**extra: object) -> TypedRefusal:
    """A new tab does not mint a product_session (Story 55.3; FR-WF-33; AD-8)."""
    context: dict[str, object] = {
        "field": "tab",
        "reason": "a new tab does not mint a new product_session; tabs share the journaled session",
        "tab_mints": False,
        "tab_writes": False,
        "session_closed": False,
        "store": PRODUCT_SESSION_STORE,
    }
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=MappingProxyType(context),
    )


def refuse_reconnect_replays_intent(**extra: object) -> TypedRefusal:
    """Reconnect is a query and never replays unacked intent (FR-WF-33; AD-8)."""
    context: dict[str, object] = {
        "field": "reconnect",
        "reason": "reconnect is a query from (resume_cursor, cursor_generation) "
        "and never replays unacked intent",
        "replays_unacked_intent": False,
        "is_query": True,
        "tab_writes": False,
    }
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=MappingProxyType(context),
    )


def claim_product_session_at_inspect_sha(existed: object) -> Result[bool]:
    """Claiming the projection existed at 270e992 fails the story (DEC-0450)."""
    if existed is True or existed == "true":
        return policy_rejection(
            "product_session",
            "product_session did not exist as a persisted daemon row at inspect "
            "SHA 270e992 (DEC-0450; GAP-0093; SCN-0019 Branch E)",
            existed_at_inspect_sha=False,
            inspect_shas=list(PRODUCT_SESSION_INSPECT_SHAS),
        )
    if existed is not False:
        return _invalid(
            "existed_at_inspect_sha",
            "inspect-SHA claim is a boolean",
            given=repr(existed),
        )
    return Ok(False)


def parse_product_session_profile(value: object) -> Result[ProductSessionProfile]:
    """Parse ``authoring | app-use``. Ontology Profile is refused."""
    if isinstance(value, Profile):
        return _invalid(
            "profile",
            "ProductSessionProfile is not qma.core.ontology.Profile",
            given="Profile",
        )
    try:
        return Ok(
            value
            if isinstance(value, ProductSessionProfile)
            else parse_closed(ProductSessionProfile, value)
        )
    except VocabularyError as exc:
        return _invalid("profile", str(exc), given=repr(value))


def _require_str(field: str, value: object) -> Result[str]:
    if not isinstance(value, str) or value.strip() == "":
        return _invalid(field, f"{field} must be a non-empty string", given=repr(value))
    return Ok(value.strip())


def _require_int(field: str, value: object, *, minimum: int) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return _invalid(field, f"{field} must be an integer", given=repr(value))
    if value < minimum:
        return _invalid(field, f"{field} must be >= {minimum}", given=value)
    return Ok(value)


def _as_mapping(field: str, value: object) -> Result[dict[str, object]]:
    if not isinstance(value, Mapping):
        return _invalid(field, f"{field} must be an object")
    mapping = cast("Mapping[object, object]", value)
    out: dict[str, object] = {}
    for key, item in mapping.items():
        if not isinstance(key, str):
            return _invalid(field, f"{field} keys must be strings")
        if item is None:
            return _invalid(
                field,
                "null is prohibited; omit absent optional keys (fp1)",
                key=key,
            )
        out[key] = item
    return Ok(out)


def _parse_psess_id(value: object) -> Result[str]:
    token = _require_str("product_session_id", value)
    if is_refusal(token):
        return token
    raw = token.value
    folded = raw.casefold()
    if folded.startswith(QMA_SESSION_ID_PREFIX) and not folded.startswith(
        PRODUCT_SESSION_ID_PREFIX
    ):
        return _invalid(
            "product_session_id",
            "product_session ids are psess:, never QMA Session sess: ids",
            given=raw,
        )
    if looks_like_chrome_id(raw):
        return refuse_tab_as_product_session(given=raw)
    if not raw.startswith(PRODUCT_SESSION_ID_PREFIX) or raw == PRODUCT_SESSION_ID_PREFIX:
        return _invalid(
            "product_session_id",
            "product_session ids are psess: (FR-WF-27; AD-8)",
            given=raw,
        )
    return Ok(raw)


def _parse_sess_id(value: object) -> Result[str]:
    token = _require_str("session_id", value)
    if is_refusal(token):
        return token
    raw = token.value
    if raw.startswith(PRODUCT_SESSION_ID_PREFIX):
        return _invalid(
            "session_id",
            "QMA Session ids remain sess:; product_session ids are psess:",
            given=raw,
        )
    if not raw.startswith(QMA_SESSION_ID_PREFIX) or raw == QMA_SESSION_ID_PREFIX:
        return _invalid("session_id", "QMA Session ids are sess:", given=raw)
    return Ok(raw)


def _parse_principal(value: object) -> Result[str]:
    try:
        parsed = value if isinstance(value, PrincipalClass) else parse_closed(PrincipalClass, value)
    except VocabularyError as exc:
        return _invalid("principal", str(exc), given=repr(value))
    return Ok(parsed.value)


def _parse_account_scope(value: object) -> Result[str | None]:
    if value is None:
        return Ok(None)
    token = _require_str("account_scope", value)
    if is_refusal(token):
        return token
    return Ok(token.value)


def _parse_occupancy(value: object) -> Result[str]:
    token = _require_str("occupancy", value)
    if is_refusal(token):
        return token
    if PRODUCT_SESSION_LIVE_ADJACENT:
        return _invalid("occupancy", "live-adjacent occupancy is not this story")
    if token.value != PRODUCT_SESSION_OCCUPANCY:
        return EnvelopeMismatch.of(
            field="occupancy",
            bound=PRODUCT_SESSION_OCCUPANCY,
            given=token.value,
            live_adjacent=False,
            cause="stale",
        )
    return Ok(PRODUCT_SESSION_OCCUPANCY)


def _parse_contribution(value: object) -> Result[ContributionBinding]:
    if isinstance(value, ContributionBinding):
        return Ok(value)
    mapped = _as_mapping("contribution", value)
    if is_refusal(mapped):
        return mapped
    body = mapped.value
    extra = sorted(set(body) - {"qualified_id", "package_version"})
    if extra:
        return _invalid(
            "contribution",
            "contribution is {qualified_id, package_version}",
            extra=extra,
        )
    qualified = _require_str("contribution.qualified_id", body.get("qualified_id"))
    if is_refusal(qualified):
        return qualified
    version = _require_str("contribution.package_version", body.get("package_version"))
    if is_refusal(version):
        return version
    return Ok(ContributionBinding(qualified_id=qualified.value, package_version=version.value))


def _parse_as_of(value: object) -> Result[str]:
    parsed = parse_utc_iso_z("as_of", value)
    if is_refusal(parsed):
        return parsed
    return Ok(parsed.value[1])


def _parse_instance_id(value: object) -> Result[str]:
    return _require_str("instance_id", value)


@dataclass(frozen=True, slots=True)
class SelectedRef:
    """Typed selected ref. Layout JSON, widgets, and positions are refused."""

    kind: str
    id: str
    extra: Mapping[str, object] = field(default_factory=dict[str, object])

    def __post_init__(self) -> None:
        object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {"id": self.id, "kind": self.kind}
        payload.update(dict(self.extra))
        return MappingProxyType(payload)


def parse_selected_ref(value: object) -> Result[SelectedRef]:
    mapped = _as_mapping("selected_refs", value)
    if is_refusal(mapped):
        return mapped
    body = mapped.value
    stolen = sorted(key for key in body if key.casefold() in _FORBIDDEN_SELECTED_KEYS)
    if stolen:
        return _invalid(
            "selected_refs",
            "layout JSON, positions, widgets, and json-render trees are refused (FR-WF-31; AD-4)",
            forbidden=stolen,
        )
    kind = _require_str("selected_refs.kind", body.get("kind"))
    if is_refusal(kind):
        return kind
    if kind.value not in SELECTED_REF_KINDS:
        return _invalid(
            "selected_refs.kind",
            "selected_refs kind is not in the closed AD-8 set",
            given=kind.value,
            allowed=sorted(SELECTED_REF_KINDS),
        )
    ident = body.get("id")
    extra = {key: item for key, item in body.items() if key not in {"kind", "id"}}
    if kind.value == "contribution" and ident is None:
        qualified = _require_str("selected_refs.qualified_id", extra.get("qualified_id"))
        if is_refusal(qualified):
            return qualified
        version = _require_str("selected_refs.package_version", extra.get("package_version"))
        if is_refusal(version):
            return version
        ident = f"{qualified.value}@{version.value}"
    if kind.value == "template" and ident is None:
        qualified = _require_str("selected_refs.qualified_id", extra.get("qualified_id"))
        if is_refusal(qualified):
            return qualified
        version = _require_str("selected_refs.version", extra.get("version"))
        if is_refusal(version):
            return version
        ident = f"{qualified.value}@{version.value}"
    parsed_id = _require_str("selected_refs.id", ident)
    if is_refusal(parsed_id):
        return parsed_id
    return Ok(SelectedRef(kind=kind.value, id=parsed_id.value, extra=extra))


def parse_selected_refs(value: object) -> Result[tuple[SelectedRef, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return _invalid("selected_refs", "selected_refs is an array of typed refs")
    collected: list[SelectedRef] = []
    for raw in cast("Sequence[object]", value):
        parsed = parse_selected_ref(raw)
        if is_refusal(parsed):
            return parsed
        collected.append(parsed.value)
    return Ok(tuple(collected))


@dataclass(frozen=True, slots=True)
class ProductSessionContext:
    """Bound request context on a product_session (Story 55.1).

    Public calls missing or stale versus these fields are typed mismatch.
    Occupancy remains none until live-adjacent.
    """

    principal: str
    occupancy: str
    contribution: ContributionBinding
    instance_id: str
    config_revision: int
    as_of: str
    account_scope: str | None = None

    def __post_init__(self) -> None:
        if self.occupancy != PRODUCT_SESSION_OCCUPANCY:
            msg = "product_session.context.occupancy remains none until live-adjacent"
            raise ValueError(msg)

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "as_of": self.as_of,
            "config_revision": self.config_revision,
            "contribution": dict(self.contribution.to_payload()),
            "instance_id": self.instance_id,
            "occupancy": self.occupancy,
            "principal": self.principal,
        }
        if self.account_scope is not None:
            payload["account_scope"] = self.account_scope
        return MappingProxyType(payload)


def parse_product_session_context(value: object) -> Result[ProductSessionContext]:
    mapped = _as_mapping("context", value)
    if is_refusal(mapped):
        return mapped
    body = mapped.value
    extra = sorted(set(body) - set(PRODUCT_SESSION_CONTEXT_FIELDS))
    if extra:
        return _invalid("context", "unknown product_session.context fields", extra=extra)
    missing = [
        field
        for field in PRODUCT_SESSION_CONTEXT_FIELDS
        if field != "account_scope" and field not in body
    ]
    if missing:
        return EnvelopeMismatch.of(
            field="context",
            missing=missing,
            cause="missing",
            bound=list(PRODUCT_SESSION_CONTEXT_FIELDS),
        )
    principal = _parse_principal(body["principal"])
    if is_refusal(principal):
        return principal
    occupancy = _parse_occupancy(body["occupancy"])
    if is_refusal(occupancy):
        return occupancy
    contribution = _parse_contribution(body["contribution"])
    if is_refusal(contribution):
        return contribution
    instance_id = _parse_instance_id(body["instance_id"])
    if is_refusal(instance_id):
        return instance_id
    config_revision = _require_int("config_revision", body["config_revision"], minimum=0)
    if is_refusal(config_revision):
        return config_revision
    as_of = _parse_as_of(body["as_of"])
    if is_refusal(as_of):
        return as_of
    account_scope = _parse_account_scope(body.get("account_scope"))
    if is_refusal(account_scope):
        return account_scope
    return Ok(
        ProductSessionContext(
            principal=principal.value,
            occupancy=occupancy.value,
            contribution=contribution.value,
            instance_id=instance_id.value,
            config_revision=config_revision.value,
            as_of=as_of.value,
            account_scope=account_scope.value,
        )
    )


@dataclass(frozen=True, slots=True)
class ProductSession:
    """Journal-derived product_session projection row (FR-WF-28; AD-8)."""

    product_session_id: str
    profile: ProductSessionProfile
    principal: str
    context: ProductSessionContext
    app_instance_id: str
    context_revision: int = 0
    granted_ops: tuple[str, ...] = ()
    selected_refs: tuple[SelectedRef, ...] = ()
    account_scope: str | None = None
    resume_cursor: int = 0
    cursor_generation: int = 1
    journal_seq: int | None = None
    recorded_at: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "granted_ops", tuple(self.granted_ops))
        object.__setattr__(self, "selected_refs", tuple(self.selected_refs))

    @property
    def occupancy(self) -> str:
        return self.context.occupancy

    @property
    def store(self) -> str:
        return PRODUCT_SESSION_STORE

    @property
    def store_class(self) -> str:
        return PRODUCT_SESSION_STORE_CLASS

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "app_instance_id": self.app_instance_id,
            "context": dict(self.context.to_payload()),
            "context_revision": self.context_revision,
            "cursor_generation": self.cursor_generation,
            "granted_ops": list(self.granted_ops),
            "principal": self.principal,
            "product_session_id": self.product_session_id,
            "profile": self.profile.value,
            "resume_cursor": self.resume_cursor,
            "selected_refs": [dict(ref.to_payload()) for ref in self.selected_refs],
        }
        if self.account_scope is not None:
            payload["account_scope"] = self.account_scope
        return MappingProxyType(payload)


def _dump(payload: Mapping[str, object]) -> str:
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class BoundProductSessionCall:
    """Public call compared to ``product_session.context``. Not authority."""

    session: ProductSession
    context: ProductSessionContext
    call: Mapping[str, object]
    is_authority: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "call", MappingProxyType(dict(self.call)))
        object.__setattr__(self, "is_authority", False)


@dataclass(frozen=True, slots=True)
class ReconnectSnapshot:
    """Reconnect query result. Never replays unacked intent (FR-WF-33)."""

    session: ProductSession
    context: ProductSessionContext
    resume_cursor: int
    cursor_generation: int
    kind: str
    replays_unacked_intent: bool = False
    writes: bool = False
    tab_writes: bool = False
    is_query: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "replays_unacked_intent", False)
        object.__setattr__(self, "tab_writes", False)
        if self.kind == RECONNECT_KIND_QUERY:
            object.__setattr__(self, "writes", False)
            object.__setattr__(self, "is_query", True)

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "context": dict(self.context.to_payload()),
                "cursor_generation": self.cursor_generation,
                "is_query": self.is_query,
                "kind": self.kind,
                "product_session_id": self.session.product_session_id,
                "replays_unacked_intent": False,
                "resume_cursor": self.resume_cursor,
                "tab_writes": False,
                "writes": self.writes,
            }
        )


def _is_session_payload(payload: Mapping[str, object]) -> bool:
    return (
        "product_session_id" in payload
        and "context" in payload
        and "profile" in payload
        and "app_instance_id" in payload
    )


def _parse_tab_id(value: object) -> Result[str]:
    token = _require_str("tab_id", value)
    if is_refusal(token):
        return token
    raw = token.value
    folded = raw.casefold()
    if raw.startswith(PRODUCT_SESSION_ID_PREFIX) or folded.startswith(QMA_SESSION_ID_PREFIX):
        return refuse_tab_as_product_session(given=raw, field="tab_id")
    return Ok(raw)


def _event_int(row: Mapping[str, object], field: str) -> int | None:
    raw = row.get(field)
    if isinstance(raw, bool) or not isinstance(raw, int):
        return None
    return raw


def _call_field(call: Mapping[str, object], field: str) -> object:
    if field in call:
        return call[field]
    envelope = call.get("envelope")
    if isinstance(envelope, InvocationEnvelope):
        if field == "contribution":
            return envelope.contribution
        if field == "instance_id":
            return envelope.instance_id
        if field == "config_revision":
            return envelope.config_revision
        payload = envelope.to_payload()
        return payload.get(field)
    if isinstance(envelope, Mapping):
        nested = cast("Mapping[str, object]", envelope)
        return nested.get(field)
    return None


def _contribution_tuple(value: object) -> Result[tuple[str, str]]:
    parsed = _parse_contribution(value)
    if is_refusal(parsed):
        return parsed
    return Ok(parsed.value.as_tuple())


def bind_public_call_to_context(
    context: ProductSessionContext,
    call: object,
) -> Result[Mapping[str, object]]:
    """Compare a public call to bound context. Missing/stale is typed mismatch."""
    if isinstance(call, InvocationEnvelope):
        mapped_call: dict[str, object] = {
            "config_revision": call.config_revision,
            "contribution": dict(call.contribution.to_payload()),
            "envelope": call,
            "instance_id": call.instance_id,
        }
    else:
        mapped = _as_mapping("public_call", call)
        if is_refusal(mapped):
            return mapped
        mapped_call = mapped.value
    tab_keys = sorted(key for key in mapped_call if key.casefold() in _TAB_FIELD_TOKENS)
    if tab_keys:
        return refuse_tab_as_product_session(fields=tab_keys)
    bound = context.to_payload()
    for field_name in PRODUCT_SESSION_CONTEXT_FIELDS:
        given = _call_field(mapped_call, field_name)
        if field_name == "account_scope" and context.account_scope is None:
            if given is not None:
                return EnvelopeMismatch.of(
                    field=field_name,
                    bound=None,
                    given=given,
                    cause="stale",
                    occupancy=PRODUCT_SESSION_OCCUPANCY,
                )
            continue
        if given is None:
            return EnvelopeMismatch.of(
                field=field_name,
                bound=bound.get(field_name),
                cause="missing",
                occupancy=PRODUCT_SESSION_OCCUPANCY,
            )
        if field_name == "contribution":
            expected = _contribution_tuple(context.contribution)
            got = _contribution_tuple(given)
            if is_refusal(expected):
                return expected
            if is_refusal(got):
                return EnvelopeMismatch.of(
                    field=field_name,
                    bound=dict(context.contribution.to_payload()),
                    given=repr(given),
                    cause="stale",
                )
            if got.value != expected.value:
                return EnvelopeMismatch.of(
                    field=field_name,
                    bound=dict(context.contribution.to_payload()),
                    given=given
                    if not isinstance(given, ContributionBinding)
                    else dict(given.to_payload()),
                    cause="stale",
                )
            continue
        if field_name == "as_of":
            parsed = _parse_as_of(given)
            if is_refusal(parsed):
                return EnvelopeMismatch.of(
                    field=field_name,
                    bound=context.as_of,
                    given=repr(given),
                    cause="stale",
                )
            given = parsed.value
        if field_name == "occupancy":
            occupancy = _parse_occupancy(given)
            if is_refusal(occupancy):
                return occupancy
            given = occupancy.value
        if field_name == "principal":
            principal = _parse_principal(given)
            if is_refusal(principal):
                return EnvelopeMismatch.of(
                    field=field_name,
                    bound=context.principal,
                    given=repr(given),
                    cause="stale",
                )
            given = principal.value
        if field_name == "instance_id":
            instance = _parse_instance_id(given)
            if is_refusal(instance):
                return EnvelopeMismatch.of(
                    field=field_name,
                    bound=context.instance_id,
                    given=repr(given),
                    cause="stale",
                )
            given = instance.value
        if field_name == "config_revision":
            revision = _require_int("config_revision", given, minimum=0)
            if is_refusal(revision):
                return EnvelopeMismatch.of(
                    field=field_name,
                    bound=context.config_revision,
                    given=repr(given),
                    cause="stale",
                )
            given = revision.value
        expected_value = getattr(context, field_name)
        if given != expected_value:
            return EnvelopeMismatch.of(
                field=field_name,
                bound=expected_value,
                given=given,
                cause="stale",
                occupancy=PRODUCT_SESSION_OCCUPANCY,
            )
    return Ok(MappingProxyType(dict(mapped_call)))


class ProductSessionSqliteStore:
    """Fold materialization on the existing daemon sqlite (NFR-WF-04)."""

    def __init__(self, sqlite: SingleSqliteWriter) -> None:
        self._sqlite = sqlite
        self._ensured = False

    def ensure_schema(self) -> None:
        if self._ensured:
            return

        def _ddl(conn: sqlite3.Connection) -> None:
            conn.executescript(_SCHEMA_SQL)

        self._sqlite.run(_ddl)
        self._ensured = True

    def put(self, session: ProductSession, *, journal_seq: int, recorded_at: int) -> None:
        self.ensure_schema()
        self._sqlite.execute(
            "INSERT OR REPLACE INTO product_session "
            "(product_session_id, payload, journal_seq, recorded_at) VALUES (?, ?, ?, ?)",
            (session.product_session_id, _dump(session.to_payload()), journal_seq, recorded_at),
        )

    def get(self, product_session_id: str) -> Result[ProductSession | None]:
        self.ensure_schema()
        rows = self._sqlite.execute(
            "SELECT payload FROM product_session WHERE product_session_id = ?",
            (product_session_id,),
        )
        if not rows:
            return Ok(None)
        raw = rows[0][0]
        if not isinstance(raw, str):
            return storage_failure(
                "product_session sqlite payload is not JSON text",
                context={"field": "product_session"},
            )
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            return storage_failure(
                f"product_session sqlite payload is not JSON: {exc}",
                context={"field": "product_session"},
            )
        if not isinstance(parsed, dict):
            return _invalid("product_session", "sqlite payload is a JSON object")
        loaded = parse_product_session(cast("dict[str, object]", parsed))
        if is_refusal(loaded):
            return loaded
        return Ok(loaded.value)


def parse_product_session(value: object) -> Result[ProductSession]:
    mapped = _as_mapping("product_session", value)
    if is_refusal(mapped):
        return mapped
    body = mapped.value
    stolen = sorted(key for key in body if key in NOT_DURABLE_FIELDS)
    if stolen:
        if any(key in _TAB_FIELD_TOKENS or key in {"tab", "tab_id", "ui_tab"} for key in stolen):
            return refuse_tab_as_product_session(fields=stolen)
        return _invalid(
            "product_session",
            "qma_session_id, tab attachment, and UI layout are not durable "
            "(FR-WF-27; FR-WF-28; AD-8)",
            fields=stolen,
        )
    session_id = _parse_psess_id(body.get("product_session_id"))
    if is_refusal(session_id):
        return session_id
    profile = parse_product_session_profile(body.get("profile"))
    if is_refusal(profile):
        return profile
    principal = _parse_principal(body.get("principal"))
    if is_refusal(principal):
        return principal
    context_raw = body.get("context")
    if context_raw is None:
        return EnvelopeMismatch.of(field="context", cause="missing")
    context = parse_product_session_context(context_raw)
    if is_refusal(context):
        return context
    app_instance = _require_str("app_instance_id", body.get("app_instance_id"))
    if is_refusal(app_instance):
        return app_instance
    if app_instance.value != context.value.instance_id:
        return EnvelopeMismatch.of(
            field="instance_id",
            bound=app_instance.value,
            given=context.value.instance_id,
            cause="stale",
        )
    if principal.value != context.value.principal:
        return EnvelopeMismatch.of(
            field="principal",
            bound=principal.value,
            given=context.value.principal,
            cause="stale",
        )
    account_scope = _parse_account_scope(body.get("account_scope"))
    if is_refusal(account_scope):
        return account_scope
    if account_scope.value != context.value.account_scope:
        return EnvelopeMismatch.of(
            field="account_scope",
            bound=account_scope.value,
            given=context.value.account_scope,
            cause="stale",
        )
    granted = parse_granted_ops(body.get("granted_ops", ()))
    if is_refusal(granted):
        return granted
    selected = parse_selected_refs(body.get("selected_refs", ()))
    if is_refusal(selected):
        return selected
    revision = _require_int("context_revision", body.get("context_revision", 0), minimum=0)
    if is_refusal(revision):
        return revision
    resume = _require_int("resume_cursor", body.get("resume_cursor", 0), minimum=0)
    if is_refusal(resume):
        return resume
    generation = _require_int("cursor_generation", body.get("cursor_generation", 1), minimum=1)
    if is_refusal(generation):
        return generation
    return Ok(
        ProductSession(
            product_session_id=session_id.value,
            profile=profile.value,
            principal=principal.value,
            context=context.value,
            app_instance_id=app_instance.value,
            context_revision=revision.value,
            granted_ops=granted.value,
            selected_refs=selected.value,
            account_scope=account_scope.value,
            resume_cursor=resume.value,
            cursor_generation=generation.value,
        )
    )


@dataclass
class ProductSessionService:
    """Mint and query the product_session journal projection (Story 55.1).

    Story 55.2 binds ``granted_ops`` to host GrantRecords on the same sqlite.
    Story 55.3 restores bound context from the journal, not RAM or a tab.
    Story 55.4: tab/window/view is not this row and does not own grants or
    occupancy; ``view:*`` is AD-17 wire DTO only (GAP-0081).
    """

    journal: AuthoritativeJournal | None = None
    sqlite: SingleSqliteWriter | None = None
    ledger: HostGrantLedger = field(default_factory=HostGrantLedger)
    _rows: dict[str, ProductSession] = field(default_factory=dict[str, ProductSession], init=False)
    _attachments: dict[str, tuple[str, ...]] = field(
        default_factory=dict[str, tuple[str, ...]], init=False
    )
    _tabs: dict[str, tuple[str, ...]] = field(
        default_factory=dict[str, tuple[str, ...]], init=False
    )
    _tab_index: dict[str, str] = field(default_factory=dict[str, str], init=False)
    _by_instance: dict[str, str] = field(default_factory=dict[str, str], init=False)
    _sqlite_store: ProductSessionSqliteStore | None = field(default=None, init=False)
    _grant_store: GrantSqliteStore | None = field(default=None, init=False)
    _grants_hydrated: bool = field(default=False, init=False)
    _compacted_through: int = field(default=0, init=False)
    _restored_from_journal: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if self.sqlite is not None:
            self._sqlite_store = ProductSessionSqliteStore(self.sqlite)
            self._grant_store = GrantSqliteStore(self.sqlite)

    @property
    def occupancy(self) -> str:
        return PRODUCT_SESSION_OCCUPANCY

    @property
    def owner(self) -> str:
        return PRODUCT_SESSION_OWNER

    @property
    def store(self) -> str:
        return PRODUCT_SESSION_STORE

    @property
    def sixth_comp_minted(self) -> bool:
        return PRODUCT_SESSION_SIXTH_COMP_MINTED

    @property
    def sixth_store_minted(self) -> bool:
        return PRODUCT_SESSION_SIXTH_STORE_MINTED

    @property
    def existed_at_inspect_sha(self) -> bool:
        return PRODUCT_SESSION_EXISTED_AT_INSPECT_SHA

    @property
    def tab_writes(self) -> bool:
        return PRODUCT_SESSION_TAB_WRITES

    @property
    def restored_from_journal(self) -> bool:
        return self._restored_from_journal

    def _index(self, session: ProductSession) -> None:
        self._rows[session.product_session_id] = session
        self._by_instance[session.app_instance_id] = session.product_session_id

    def _ensure_declared(self) -> Result[None]:
        journal = self.journal
        if journal is None:
            return Ok(None)
        declared = journal.declare_store(PRODUCT_SESSION_STORE)
        if is_refusal(declared):
            return declared
        folded = journal.register_fold(PRODUCT_SESSION_FOLD_ID)
        if is_refusal(folded):
            return folded
        return Ok(None)

    def mint(
        self,
        *,
        product_session_id: object,
        profile: object,
        principal: object,
        contribution: object,
        instance_id: object,
        config_revision: object,
        as_of: object,
        account_scope: object = None,
        granted_ops: object = (),
        selected_refs: object = (),
        occupancy: object = PRODUCT_SESSION_OCCUPANCY,
        app_instance_id: object | None = None,
        context_revision: object = 0,
        resume_cursor: object = 0,
        cursor_generation: object = 1,
        scope_path: object = (),
        **extra: object,
    ) -> Result[ProductSession]:
        """Persist a product_session row and bind ``.context``."""
        stolen = sorted(key for key in extra if key.casefold() in _TAB_FIELD_TOKENS)
        if stolen:
            return refuse_tab_as_product_session(fields=stolen)
        durable_stolen = sorted(key for key in extra if key in NOT_DURABLE_FIELDS)
        if durable_stolen:
            return _invalid(
                "product_session",
                "qma_session_id, tab attachment, and UI layout are not durable",
                fields=durable_stolen,
            )
        if extra:
            return _invalid(
                "product_session",
                "unknown product_session mint fields",
                extra=sorted(extra),
            )
        if isinstance(profile, Profile):
            return _invalid(
                "profile",
                "ProductSessionProfile is not qma.core.ontology.Profile",
                given="Profile",
            )
        if isinstance(product_session_id, Session) or isinstance(profile, Session):
            return _invalid(
                "product_session_id",
                "product_session is not a QMA Session record",
            )
        occupancy_parsed = _parse_occupancy(occupancy)
        if is_refusal(occupancy_parsed):
            return occupancy_parsed
        session_id = _parse_psess_id(product_session_id)
        if is_refusal(session_id):
            return session_id
        parsed_profile = parse_product_session_profile(profile)
        if is_refusal(parsed_profile):
            return parsed_profile
        parsed_principal = _parse_principal(principal)
        if is_refusal(parsed_principal):
            return parsed_principal
        parsed_contribution = _parse_contribution(contribution)
        if is_refusal(parsed_contribution):
            return parsed_contribution
        parsed_instance = _parse_instance_id(
            instance_id if app_instance_id is None else app_instance_id
        )
        if is_refusal(parsed_instance):
            return parsed_instance
        if app_instance_id is not None:
            explicit = _parse_instance_id(instance_id)
            if is_refusal(explicit):
                return explicit
            if explicit.value != parsed_instance.value:
                return EnvelopeMismatch.of(
                    field="instance_id",
                    bound=parsed_instance.value,
                    given=explicit.value,
                    cause="stale",
                )
        parsed_revision = _require_int("config_revision", config_revision, minimum=0)
        if is_refusal(parsed_revision):
            return parsed_revision
        parsed_as_of = _parse_as_of(as_of)
        if is_refusal(parsed_as_of):
            return parsed_as_of
        parsed_scope = _parse_account_scope(account_scope)
        if is_refusal(parsed_scope):
            return parsed_scope
        parsed_ops = parse_granted_ops(granted_ops)
        if is_refusal(parsed_ops):
            return parsed_ops
        parsed_refs = parse_selected_refs(selected_refs)
        if is_refusal(parsed_refs):
            return parsed_refs
        parsed_context_revision = _require_int("context_revision", context_revision, minimum=0)
        if is_refusal(parsed_context_revision):
            return parsed_context_revision
        parsed_resume = _require_int("resume_cursor", resume_cursor, minimum=0)
        if is_refusal(parsed_resume):
            return parsed_resume
        parsed_generation = _require_int("cursor_generation", cursor_generation, minimum=1)
        if is_refusal(parsed_generation):
            return parsed_generation
        if "product_session" in SCOPE_KIND_ORDER:
            return policy_rejection(
                "scope_path",
                "scope_path does not gain a product_session segment (FR-WF-28; AD-8)",
            )
        existing = self._rows.get(session_id.value)
        if existing is not None and existing.profile is not parsed_profile.value:
            return _invalid(
                "profile",
                "ProductSessionProfile is immutable at create (FR-WF-29)",
                bound=existing.profile.value,
                given=parsed_profile.value,
            )
        owner = self._by_instance.get(parsed_instance.value)
        if owner is None:
            for row in self._rows.values():
                if row.app_instance_id == parsed_instance.value:
                    owner = row.product_session_id
                    break
        if owner is not None and owner != session_id.value:
            return refuse_tab_mints_session(
                app_instance_id=parsed_instance.value,
                bound=owner,
                given=session_id.value,
            )
        context = ProductSessionContext(
            principal=parsed_principal.value,
            occupancy=occupancy_parsed.value,
            contribution=parsed_contribution.value,
            instance_id=parsed_instance.value,
            config_revision=parsed_revision.value,
            as_of=parsed_as_of.value,
            account_scope=parsed_scope.value,
        )
        session = ProductSession(
            product_session_id=session_id.value,
            profile=parsed_profile.value,
            principal=parsed_principal.value,
            context=context,
            app_instance_id=parsed_instance.value,
            context_revision=parsed_context_revision.value,
            granted_ops=parsed_ops.value,
            selected_refs=parsed_refs.value,
            account_scope=parsed_scope.value,
            resume_cursor=parsed_resume.value,
            cursor_generation=parsed_generation.value,
        )
        declared = self._ensure_declared()
        if is_refusal(declared):
            return declared
        journal_seq = 0
        recorded_at = 0
        if self.journal is not None:
            appended = self.journal.append_event(
                PRODUCT_SESSION_MINT_EVENT,
                scope_path=scope_path,
                payload=dict(session.to_payload()),
            )
            if is_refusal(appended):
                return appended
            journal_seq = appended.value.record.journal_seq
            recorded_at = appended.value.record.recorded_at
            session = ProductSession(
                product_session_id=session.product_session_id,
                profile=session.profile,
                principal=session.principal,
                context=session.context,
                app_instance_id=session.app_instance_id,
                context_revision=session.context_revision,
                granted_ops=session.granted_ops,
                selected_refs=session.selected_refs,
                account_scope=session.account_scope,
                resume_cursor=journal_seq,
                cursor_generation=session.cursor_generation,
                journal_seq=journal_seq,
                recorded_at=recorded_at,
            )
        if self._sqlite_store is not None:
            self._sqlite_store.put(session, journal_seq=journal_seq, recorded_at=recorded_at)
        self._index(session)
        return Ok(session)

    def get(self, product_session_id: object) -> Result[ProductSession]:
        parsed = _parse_psess_id(product_session_id)
        if is_refusal(parsed):
            return parsed
        cached = self._rows.get(parsed.value)
        if cached is not None:
            return Ok(cached)
        if self._sqlite_store is not None:
            loaded = self._sqlite_store.get(parsed.value)
            if is_refusal(loaded):
                return loaded
            if loaded.value is not None:
                self._index(loaded.value)
                return Ok(loaded.value)
        return _invalid(
            "product_session_id",
            "product_session is not on the journal projection",
            given=parsed.value,
        )

    def attached_sessions(self, product_session_id: object) -> Result[tuple[str, ...]]:
        """Current ``sess:`` attachment is a query, not a durable field."""
        parsed = _parse_psess_id(product_session_id)
        if is_refusal(parsed):
            return parsed
        loaded = self.get(parsed.value)
        if is_refusal(loaded):
            return loaded
        return Ok(self._attachments.get(parsed.value, ()))

    def note_session_attachment(
        self,
        product_session_id: object,
        session_id: object,
    ) -> Result[tuple[str, ...]]:
        """Record a query-only sess: attachment. Never written to the row."""
        parsed = _parse_psess_id(product_session_id)
        if is_refusal(parsed):
            return parsed
        loaded = self.get(parsed.value)
        if is_refusal(loaded):
            return loaded
        sess = _parse_sess_id(session_id)
        if is_refusal(sess):
            return sess
        current = self._attachments.get(parsed.value, ())
        if sess.value not in current:
            current = (*current, sess.value)
        self._attachments[parsed.value] = current
        payload = loaded.value.to_payload()
        if "qma_session_id" in payload or "session_id" in payload:
            return _invalid(
                "qma_session_id",
                "current sess: attachment is a query, not a durable field",
            )
        return Ok(current)

    def attached_tabs(self, product_session_id: object) -> Result[tuple[str, ...]]:
        """Current UI tabs are a query. Tabs are not durable and write nothing."""
        parsed = _parse_psess_id(product_session_id)
        if is_refusal(parsed):
            return parsed
        loaded = self.get(parsed.value)
        if is_refusal(loaded):
            return loaded
        payload = loaded.value.to_payload()
        stolen = sorted(key for key in payload if key.casefold() in _TAB_FIELD_TOKENS)
        if stolen:
            return refuse_tab_as_product_session(fields=stolen)
        return Ok(self._tabs.get(parsed.value, ()))

    def attach_tab(
        self,
        product_session_id: object,
        tab_id: object,
    ) -> Result[ProductSession]:
        """Attach a UI tab to an existing journaled session. Writes nothing."""
        parsed = _parse_psess_id(product_session_id)
        if is_refusal(parsed):
            return parsed
        loaded = self.get(parsed.value)
        if is_refusal(loaded):
            return loaded
        tab = _parse_tab_id(tab_id)
        if is_refusal(tab):
            return tab
        previous = self._tab_index.get(tab.value)
        if previous is not None and previous != parsed.value:
            current = tuple(item for item in self._tabs.get(previous, ()) if item != tab.value)
            if current:
                self._tabs[previous] = current
            else:
                self._tabs.pop(previous, None)
        attached = self._tabs.get(parsed.value, ())
        if tab.value not in attached:
            attached = (*attached, tab.value)
        self._tabs[parsed.value] = attached
        self._tab_index[tab.value] = parsed.value
        return Ok(loaded.value)

    def close_tab(
        self,
        tab_id: object,
        *,
        product_session_id: object | None = None,
    ) -> Result[ProductSession]:
        """Close a tab. The product_session stays; nothing durable is written."""
        tab = _parse_tab_id(tab_id)
        if is_refusal(tab):
            return tab
        owner = self._tab_index.get(tab.value)
        if product_session_id is not None:
            parsed = _parse_psess_id(product_session_id)
            if is_refusal(parsed):
                return parsed
            if owner is not None and owner != parsed.value:
                return refuse_tab_as_product_session(
                    given=tab.value,
                    bound=owner,
                    field="tab_id",
                )
            owner = parsed.value
        if owner is None:
            return _invalid("tab_id", "tab is not attached to a product_session", given=tab.value)
        loaded = self.get(owner)
        if is_refusal(loaded):
            return loaded
        remaining = tuple(item for item in self._tabs.get(owner, ()) if item != tab.value)
        if remaining:
            self._tabs[owner] = remaining
        else:
            self._tabs.pop(owner, None)
        self._tab_index.pop(tab.value, None)
        return Ok(loaded.value)

    def session_for_instance(self, app_instance_id: object) -> Result[ProductSession]:
        """The one product_session bound to an installed app instance."""
        parsed = _require_str("app_instance_id", app_instance_id)
        if is_refusal(parsed):
            return parsed
        token = self._by_instance.get(parsed.value)
        if token is None:
            for row in self._rows.values():
                if row.app_instance_id == parsed.value:
                    self._by_instance[parsed.value] = row.product_session_id
                    return Ok(row)
            return refuse_tab_mints_session(app_instance_id=parsed.value)
        return self.get(token)

    def open_tab(
        self,
        *,
        tab_id: object,
        app_instance_id: object | None = None,
        product_session_id: object | None = None,
    ) -> Result[ProductSession]:
        """Open a tab onto the existing product session. Never mints."""
        if product_session_id is not None:
            loaded = self.get(product_session_id)
            if is_refusal(loaded):
                return loaded
            if app_instance_id is not None:
                instance = _require_str("app_instance_id", app_instance_id)
                if is_refusal(instance):
                    return instance
                if instance.value != loaded.value.app_instance_id:
                    return EnvelopeMismatch.of(
                        field="app_instance_id",
                        bound=loaded.value.app_instance_id,
                        given=instance.value,
                        cause="stale",
                    )
            return self.attach_tab(loaded.value.product_session_id, tab_id)
        if app_instance_id is None:
            return refuse_tab_mints_session(field="app_instance_id")
        existing = self.session_for_instance(app_instance_id)
        if is_refusal(existing):
            return existing
        return self.attach_tab(existing.value.product_session_id, tab_id)

    def restore_from_journal(self) -> Result[tuple[ProductSession, ...]]:
        """Rebuild product_session rows from journal events, not RAM."""
        if self.journal is None:
            return _invalid(
                "journal",
                "journal restore requires the daemon journal (Story 55.3; AD-8)",
            )
        declared = self._ensure_declared()
        if is_refusal(declared):
            return declared
        rows = self.journal.read_all()
        if is_refusal(rows):
            return rows
        folded: dict[str, ProductSession] = {}
        for raw in rows.value:
            event = raw.get("event")
            if not isinstance(event, str) or not event.startswith("product_session."):
                continue
            payload = raw.get("payload")
            if not isinstance(payload, Mapping):
                continue
            body = cast("Mapping[str, object]", payload)
            if not _is_session_payload(body):
                continue
            parsed = parse_product_session(dict(body))
            if is_refusal(parsed):
                return parsed
            seq = _event_int(raw, "journal_seq")
            recorded = _event_int(raw, "recorded_at")
            resume = seq if seq is not None else parsed.value.resume_cursor
            session = replace(
                parsed.value,
                journal_seq=seq,
                recorded_at=recorded,
                resume_cursor=resume,
            )
            folded[session.product_session_id] = session
        self._rows = folded
        self._by_instance = {
            session.app_instance_id: session.product_session_id for session in folded.values()
        }
        self._restored_from_journal = True
        if self._sqlite_store is not None:
            for session in folded.values():
                seq = session.journal_seq if session.journal_seq is not None else 0
                recorded = session.recorded_at if session.recorded_at is not None else 0
                self._sqlite_store.put(session, journal_seq=seq, recorded_at=recorded)
        return Ok(tuple(folded.values()))

    def compact_history(self, through_seq: object) -> Result[int]:
        """Mark journal history compacted through ``through_seq`` (host-side)."""
        parsed = _require_int("through_seq", through_seq, minimum=0)
        if is_refusal(parsed):
            return parsed
        self._compacted_through = parsed.value
        return Ok(parsed.value)

    def reconnect(
        self,
        product_session_id: object,
        *,
        resume_cursor: object,
        cursor_generation: object,
        **extra: object,
    ) -> Result[ReconnectSnapshot]:
        """Query bound context from ``(resume_cursor, cursor_generation)``.

        Never replays unacked intent. Tab fields write nothing. Compacted
        history past the cursor yields snapshot/resync with a new generation.
        """
        stolen = sorted(key for key in extra if key.casefold() in _TAB_FIELD_TOKENS)
        if stolen:
            return refuse_tab_as_product_session(fields=stolen)
        intent = sorted(key for key in extra if key.casefold() in _RECONNECT_INTENT_KEYS)
        if intent or extra:
            return refuse_reconnect_replays_intent(
                fields=intent or sorted(extra),
            )
        loaded = self.get(product_session_id)
        if is_refusal(loaded):
            return loaded
        cursor = _require_int("resume_cursor", resume_cursor, minimum=0)
        if is_refusal(cursor):
            return cursor
        generation = _require_int("cursor_generation", cursor_generation, minimum=1)
        if is_refusal(generation):
            return generation
        session = loaded.value
        compacted = self._compacted_through > 0 and cursor.value <= self._compacted_through
        stale_generation = generation.value != session.cursor_generation
        if compacted or stale_generation:
            bumped = session.cursor_generation + 1
            next_cursor = session.resume_cursor
            rewritten = replace(session, cursor_generation=bumped, resume_cursor=next_cursor)
            persisted = self._persist_session(
                rewritten,
                event=PRODUCT_SESSION_CURSOR_RESYNC_EVENT,
                payload=dict(rewritten.to_payload()),
            )
            if is_refusal(persisted):
                return persisted
            live = persisted.value
            return Ok(
                ReconnectSnapshot(
                    session=live,
                    context=live.context,
                    resume_cursor=live.resume_cursor,
                    cursor_generation=live.cursor_generation,
                    kind=RECONNECT_KIND_RESYNC,
                    writes=True,
                    is_query=True,
                )
            )
        return Ok(
            ReconnectSnapshot(
                session=session,
                context=session.context,
                resume_cursor=session.resume_cursor,
                cursor_generation=session.cursor_generation,
                kind=RECONNECT_KIND_QUERY,
            )
        )

    def bind_public_call(
        self,
        product_session_id: object,
        call: object,
    ) -> Result[BoundProductSessionCall]:
        loaded = self.get(product_session_id)
        if is_refusal(loaded):
            return loaded
        compared = bind_public_call_to_context(loaded.value.context, call)
        if is_refusal(compared):
            return compared
        return Ok(
            BoundProductSessionCall(
                session=loaded.value,
                context=loaded.value.context,
                call=compared.value,
            )
        )

    def _hydrate_grants(self) -> Result[None]:
        if self._grants_hydrated:
            return Ok(None)
        self._grants_hydrated = True
        store = self._grant_store
        if store is None or self.ledger.grants:
            return Ok(None)
        grants = store.list_grants()
        if is_refusal(grants):
            return grants
        for record in grants.value:
            imported = self.ledger.import_grant(record)
            if is_refusal(imported):
                return imported
        revocations = store.list_revocations()
        if is_refusal(revocations):
            return revocations
        for revocation in revocations.value:
            imported_rev = self.ledger.import_revocation(revocation)
            if is_refusal(imported_rev):
                return imported_rev
        accepted = store.list_accepted()
        if is_refusal(accepted):
            return accepted
        for invocation, grant_id in accepted.value:
            imported_acc = self.ledger.import_accepted(
                grant_id=grant_id,
                logical_invocation_id=invocation,
            )
            if is_refusal(imported_acc):
                return imported_acc
        return Ok(None)

    def _append_event(
        self,
        event: str,
        payload: Mapping[str, object],
        *,
        scope_path: object = (),
    ) -> Result[tuple[int, int]]:
        declared = self._ensure_declared()
        if is_refusal(declared):
            return declared
        if self.journal is None:
            return Ok((0, 0))
        appended = self.journal.append_event(
            event,
            scope_path=scope_path,
            payload=dict(payload),
        )
        if is_refusal(appended):
            return appended
        return Ok((appended.value.record.journal_seq, appended.value.record.recorded_at))

    def _persist_session(
        self,
        session: ProductSession,
        *,
        event: str,
        payload: Mapping[str, object] | None = None,
        scope_path: object = (),
    ) -> Result[ProductSession]:
        if payload is not None and _is_session_payload(payload):
            body = dict(payload)
        else:
            body = dict(session.to_payload())
        stamped = self._append_event(event, body, scope_path=scope_path)
        if is_refusal(stamped):
            return stamped
        journal_seq, recorded_at = stamped.value
        written = replace(
            session,
            journal_seq=journal_seq,
            recorded_at=recorded_at,
            resume_cursor=journal_seq if journal_seq else session.resume_cursor,
        )
        if self._sqlite_store is not None:
            self._sqlite_store.put(written, journal_seq=journal_seq, recorded_at=recorded_at)
        self._index(written)
        return Ok(written)

    def resolve_grant(
        self,
        product_session_id: object,
        grant_id: object,
    ) -> Result[GrantRecord]:
        """Resolve a session grant_id to the host GrantRecord."""
        hydrated = self._hydrate_grants()
        if is_refusal(hydrated):
            return hydrated
        loaded = self.get(product_session_id)
        if is_refusal(loaded):
            return loaded
        token = require_session_grant_id(loaded.value.granted_ops, grant_id)
        if is_refusal(token):
            return token
        record = self.ledger.grants.get(token.value)
        if record is None:
            return GrantMismatch.of(field="grant_id", grant_id=token.value, live=False)
        if record.audience != loaded.value.product_session_id:
            return GrantMismatch.of(
                field="audience",
                grant_id=token.value,
                bound=loaded.value.product_session_id,
                granted=record.audience,
            )
        return Ok(record)

    def granted_records(
        self,
        product_session_id: object,
    ) -> Result[tuple[GrantRecord, ...]]:
        """Host-resolved GrantRecords for ``product_session.granted_ops``."""
        loaded = self.get(product_session_id)
        if is_refusal(loaded):
            return loaded
        collected: list[GrantRecord] = []
        for token in loaded.value.granted_ops:
            resolved = self.resolve_grant(loaded.value.product_session_id, token)
            if is_refusal(resolved):
                return resolved
            collected.append(resolved.value)
        return Ok(tuple(collected))

    def host_grant(
        self,
        product_session_id: object,
        *,
        issuer: object = _HOST_ISSUER,
        grant_id: object | None = None,
        principal: object | None = None,
        audience: object | None = None,
        contribution: object | None = None,
        instance_id: object | None = None,
        config_revision: object | None = None,
        op_id: object,
        op_version: object,
        effect_class: object,
        parameter_ceiling: object,
        expires_at: object,
        account_scope: object | None = None,
        scope_path: object = (),
    ) -> Result[GrantRecord]:
        """Host-mint a GrantRecord and store its grant_id on granted_ops."""
        if issuer != _HOST_ISSUER:
            return refuse_manifest_grant(issuer=issuer)
        hydrated = self._hydrate_grants()
        if is_refusal(hydrated):
            return hydrated
        loaded = self.get(product_session_id)
        if is_refusal(loaded):
            return loaded
        session = loaded.value
        if audience is None:
            audience = session.product_session_id
        elif looks_like_chrome_id(audience):
            return refuse_chrome_owns_grants(field="audience", given=audience)
        elif audience != session.product_session_id:
            return GrantMismatch.of(
                field="audience",
                grant_id=str(grant_id) if grant_id is not None else "",
                bound=session.product_session_id,
                granted=audience,
            )
        minted = self.ledger.mint(
            issuer=_HOST_ISSUER,
            grant_id=grant_id,
            principal=session.principal if principal is None else principal,
            audience=audience,
            contribution=(
                dict(session.context.contribution.to_payload())
                if contribution is None
                else contribution
            ),
            instance_id=session.context.instance_id if instance_id is None else instance_id,
            config_revision=(
                session.context.config_revision if config_revision is None else config_revision
            ),
            op_id=op_id,
            op_version=op_version,
            effect_class=effect_class,
            parameter_ceiling=parameter_ceiling,
            expires_at=expires_at,
            account_scope=(session.account_scope if account_scope is None else account_scope),
        )
        if is_refusal(minted):
            return minted
        record = minted.value
        stamped = self._append_event(
            PRODUCT_SESSION_GRANT_MINTED_EVENT,
            dict(record.to_payload()),
            scope_path=scope_path,
        )
        if is_refusal(stamped):
            return stamped
        journal_seq, recorded_at = stamped.value
        if self._grant_store is not None:
            self._grant_store.put_grant(record, journal_seq=journal_seq, recorded_at=recorded_at)
        if record.grant_id not in session.granted_ops:
            session = replace(session, granted_ops=(*session.granted_ops, record.grant_id))
            persisted = self._persist_session(
                session,
                event=PRODUCT_SESSION_GRANT_MINTED_EVENT,
                payload=dict(session.to_payload()),
                scope_path=scope_path,
            )
            if is_refusal(persisted):
                return persisted
        return Ok(record)

    def accept_work(
        self,
        product_session_id: object,
        *,
        grant_id: object,
        logical_invocation_id: object,
        now: object,
        scope_path: object = (),
    ) -> Result[AcceptedGrantWork]:
        """Accept work under a live session grant. Later revoke does not unwind it."""
        resolved = self.resolve_grant(product_session_id, grant_id)
        if is_refusal(resolved):
            return resolved
        accepted = self.ledger.accept(
            grant_id=resolved.value.grant_id,
            logical_invocation_id=logical_invocation_id,
            now=now,
        )
        if is_refusal(accepted):
            return accepted
        work = accepted.value
        stamped = self._append_event(
            PRODUCT_SESSION_GRANT_ACCEPTED_EVENT,
            {
                "grant_id": work.grant_id,
                "logical_invocation_id": work.logical_invocation_id,
                "moment": work.moment.value,
            },
            scope_path=scope_path,
        )
        if is_refusal(stamped):
            return stamped
        if self._grant_store is not None:
            self._grant_store.put_accepted(
                logical_invocation_id=work.logical_invocation_id,
                grant_id=work.grant_id,
            )
        return Ok(work)

    def revoke_grant(
        self,
        product_session_id: object,
        *,
        grant_id: object,
        principal: object,
        reason: object,
        revoked_at: object,
        scope_path: object = (),
    ) -> Result[GrantRevocation]:
        """Append GrantRevocation. Minted GrantRecord bytes and granted_ops stay."""
        resolved = self.resolve_grant(product_session_id, grant_id)
        if is_refusal(resolved):
            return resolved
        revoked = self.ledger.revoke(
            grant_id=resolved.value.grant_id,
            principal=principal,
            reason=reason,
            revoked_at=revoked_at,
        )
        if is_refusal(revoked):
            return revoked
        revocation = revoked.value
        stamped = self._append_event(
            PRODUCT_SESSION_GRANT_REVOKED_EVENT,
            dict(revocation.to_payload()),
            scope_path=scope_path,
        )
        if is_refusal(stamped):
            return stamped
        journal_seq, recorded_at = stamped.value
        if self._grant_store is not None:
            self._grant_store.append_revocation(
                revocation,
                journal_seq=journal_seq,
                recorded_at=recorded_at,
            )
        return Ok(revocation)

    def apply_upgrade(
        self,
        product_session_id: object,
        grant_id: object,
        **changes: object,
    ) -> GrantWidenRefused | Result[GrantRecord]:
        """In-place upgrade/widen/retarget is refused. Re-grant instead."""
        resolved = self.resolve_grant(product_session_id, grant_id)
        if is_refusal(resolved):
            return resolved
        token = resolved.value.grant_id
        return refuse_in_place_upgrade(grant_id=token, changes=sorted(changes), in_place=True)

    def regrant(
        self,
        product_session_id: object,
        previous_grant_id: object,
        *,
        context_revision: object,
        issuer: object = _HOST_ISSUER,
        scope_path: object = (),
        **changes: object,
    ) -> Result[RegrantResult]:
        """Mint a new GrantRecord and bump product_session.context_revision."""
        if issuer != _HOST_ISSUER:
            return refuse_manifest_grant(issuer=issuer)
        resolved = self.resolve_grant(product_session_id, previous_grant_id)
        if is_refusal(resolved):
            return resolved
        loaded = self.get(product_session_id)
        if is_refusal(loaded):
            return loaded
        session = loaded.value
        regranted = self.ledger.regrant(
            resolved.value.grant_id,
            context_revision=context_revision,
            from_revision=session.context_revision,
            issuer=issuer,
            **changes,
        )
        if is_refusal(regranted):
            return regranted
        result = regranted.value
        stamped = self._append_event(
            PRODUCT_SESSION_GRANT_REGRANTED_EVENT,
            dict(result.to_payload()),
            scope_path=scope_path,
        )
        if is_refusal(stamped):
            return stamped
        journal_seq, recorded_at = stamped.value
        if self._grant_store is not None:
            self._grant_store.put_grant(
                result.grant,
                journal_seq=journal_seq,
                recorded_at=recorded_at,
            )
        ops = session.granted_ops
        if result.grant.grant_id not in ops:
            ops = (*ops, result.grant.grant_id)
        persisted = self._persist_session(
            replace(session, granted_ops=ops, context_revision=result.context_revision),
            event=PRODUCT_SESSION_GRANT_REGRANTED_EVENT,
            payload=dict(result.to_payload()),
            scope_path=scope_path,
        )
        if is_refusal(persisted):
            return persisted
        return Ok(result)

    def dispatch_public_call(
        self,
        product_session_id: object,
        *,
        transport: object,
        envelope: object,
        payload: object,
        now: object,
        occupancy: object = PRODUCT_SESSION_OCCUPANCY,
        principal: object | None = None,
        as_of: object | None = None,
        contributions: Mapping[tuple[str, str], ContributionRecord] | None = None,
        descriptors: Mapping[tuple[str, int], OperationDescriptor] | None = None,
        instances: Mapping[tuple[str, int], InstanceRecord] | None = None,
        execute: Callable[[BoundInvocation], None] | None = None,
        parent_permissions: object | None = None,
    ) -> Result[BoundSessionGrant]:
        """Bind context, resolve GrantRecord, GRANT_MISMATCH / revoke refuse."""
        parsed = parse_invocation_envelope(envelope)
        if is_refusal(parsed):
            return parsed
        env = parsed.value
        loaded = self.get(product_session_id)
        if is_refusal(loaded):
            return loaded
        session = loaded.value
        call: dict[str, object] = {
            "as_of": session.context.as_of if as_of is None else as_of,
            "envelope": env,
            "occupancy": occupancy,
            "principal": session.principal if principal is None else principal,
        }
        if session.account_scope is not None:
            call["account_scope"] = session.account_scope
        bound = self.bind_public_call(session.product_session_id, call)
        if is_refusal(bound):
            return bound
        resolved = self.resolve_grant(session.product_session_id, env.grant_id)
        if is_refusal(resolved):
            return resolved
        compared = compare_envelope_to_grant(env, resolved.value)
        if is_refusal(compared):
            return compared
        evaluated = self.ledger.evaluate(
            grant_id=compared.value.grant_id,
            moment=moment_for_transport(transport),
            now=now,
            logical_invocation_id=env.logical_invocation_id,
            parent_logical_invocation_id=env.parent_logical_invocation_id,
        )
        if is_refusal(evaluated):
            return evaluated
        invocation: BoundInvocation | None = None
        if contributions is not None and descriptors is not None and instances is not None:
            stores = AuthoritativeStores(
                contributions=contributions,
                descriptors=descriptors,
                grants={evaluated.value.grant_id: evaluated.value},
                instances=instances,
            )
            dispatched = dispatch_public_call(
                transport=transport,
                envelope=env,
                payload=payload,
                stores=stores,
                execute=execute,
                parent_permissions=parent_permissions,
            )
            if is_refusal(dispatched):
                return dispatched
            invocation = dispatched.value
        return Ok(
            BoundSessionGrant(
                grant=evaluated.value,
                envelope=env,
                grant_ids=session.granted_ops,
                invocation=invocation,
            )
        )
