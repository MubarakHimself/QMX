"""``product_session`` journal projection — bound request context (Story 55.1).

COMP-QMA-DAEMON owns the sqlite fold over ``product_session.*``. Ids are
``psess:``; QMA Session ids remain ``sess:``. ``product_session.context`` is
the bound request context a public call must match. Occupancy stays none
until a live-adjacent story. A tab is not this row. No sixth COMP, no new
CT, no new sqlite class. Absent at inspect SHA 270e992 (DEC-0450; GAP-0093).
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qma.core.ontology.records import Profile, Session
from qma.core.refusals.variants import EnvelopeMismatch
from qma.core.vocabulary.enums import PrincipalClass
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qma.daemon.journal.authoritative import AuthoritativeJournal
from qma.daemon.journal.stores import StoreClass
from qma.daemon.persistence.sqlite_writer import SingleSqliteWriter
from qma.wire.envelope import SCOPE_KIND_ORDER
from qma.wire.grant_record import parse_granted_ops
from qma.wire.invocation_envelope import (
    ContributionBinding,
    InvocationEnvelope,
    parse_utc_iso_z,
)
from qmf.core.refusal import Ok, RefusalCategory, Result, Retryability, TypedRefusal, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection, storage_failure

__all__ = [
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
    "PRODUCT_SESSION_WIRED_AT_INSPECT_SHA",
    "QMA_SESSION_ID_PREFIX",
    "SELECTED_REF_KINDS",
    "BoundProductSessionCall",
    "ProductSession",
    "ProductSessionContext",
    "ProductSessionProfile",
    "ProductSessionService",
    "SelectedRef",
    "bind_public_call_to_context",
    "claim_product_session_at_inspect_sha",
    "parse_product_session_profile",
    "refuse_tab_as_product_session",
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
PRODUCT_SESSION_MINT_EVENT: Final[str] = "product_session.minted"

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
    {"tab", "tab_id", "ui_tab", "client_tab", "dashboard_tab"}
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


def refuse_tab_as_product_session(**extra: object) -> TypedRefusal:
    """A UI tab is not a product_session row (SCN-0019 Branch D; FR-WF-33)."""
    context: dict[str, object] = {
        "field": "tab",
        "reason": "a tab is not a product_session row; sessions own context",
        "tab_writes": False,
        "store": PRODUCT_SESSION_STORE,
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
    if any(part in folded for part in ("tab:", "tab/", "ui-tab")):
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
    """Mint and query the product_session journal projection (Story 55.1)."""

    journal: AuthoritativeJournal | None = None
    sqlite: SingleSqliteWriter | None = None
    _rows: dict[str, ProductSession] = field(default_factory=dict[str, ProductSession], init=False)
    _attachments: dict[str, tuple[str, ...]] = field(
        default_factory=dict[str, tuple[str, ...]], init=False
    )
    _sqlite_store: ProductSessionSqliteStore | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.sqlite is not None:
            self._sqlite_store = ProductSessionSqliteStore(self.sqlite)

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
                resume_cursor=session.resume_cursor,
                cursor_generation=session.cursor_generation,
                journal_seq=journal_seq,
                recorded_at=recorded_at,
            )
        if self._sqlite_store is not None:
            self._sqlite_store.put(session, journal_seq=journal_seq, recorded_at=recorded_at)
        self._rows[session.product_session_id] = session
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
                self._rows[parsed.value] = loaded.value
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
