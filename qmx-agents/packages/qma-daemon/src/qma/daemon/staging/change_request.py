"""Story 58.4 / SCN-0019 — app-use change-request fixture.

Three records, not one mutable payload: app-use mints an immutable
``ChangeRequest``; authoring writes ``ChangeValidationRecord``; authoring plus
an operator principal appends ``ChangeApplyRecord``. App-use never applies,
never writes package source, and never widens grants or retargets accounts.
A stale base hash surfaces ``conflict`` / ``rebase-required`` and does not
apply. v1 instance, GrantRecords, and running jobs stay unchanged by the mint.
Distinct from Story 47.3 ``RefinementProposal``. ``promote`` remains L17.
No new sqlite class.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Final, cast

from qma.core.content import content_address
from qma.core.ports.refinement import STAGING_STORE_RECORD_TYPE
from qma.core.refusals import GrantWidenRefused, OperatorPrincipalRequired
from qma.core.vocabulary.enums import PrincipalClass
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qma.daemon.sessions.product_session import (
    PRODUCT_SESSION_ID_PREFIX,
    PRODUCT_SESSION_TAB_WRITES,
    ProductSession,
    ProductSessionProfile,
    ProductSessionService,
    ReconnectSnapshot,
    SelectedRef,
    parse_selected_refs,
    refuse_reconnect_replays_intent,
    refuse_tab_as_product_session,
)
from qma.wire.invocation_envelope import parse_utc_iso_z
from qmf.core import Ok, Result, is_ok, is_refusal
from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import TypedRefusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "ALLOWED_PATCH_KINDS",
    "CHANGE_APPLY_OUTCOMES",
    "CHANGE_REQUEST_HASH_FIELDS",
    "CHANGE_REQUEST_ID_PREFIX",
    "CHANGE_REQUEST_SIXTH_STORE_MINTED",
    "CHANGE_REQUEST_STAGING_KIND",
    "CHANGE_VALIDATION_VERDICTS",
    "ChangeApplyRecord",
    "ChangeRequest",
    "ChangeRequestFixture",
    "ChangeTarget",
    "ChangeValidationRecord",
    "InstalledAppSnapshot",
    "hash_change_request",
]


CHANGE_REQUEST_STAGING_KIND: Final[str] = "change_request"
CHANGE_REQUEST_ID_PREFIX: Final[str] = "cr:"
CHANGE_REQUEST_SIXTH_STORE_MINTED: Final[bool] = False
CHANGE_REQUEST_HASH_FIELDS: Final[tuple[str, ...]] = (
    "change_request_id",
    "from_session",
    "source_instance_id",
    "source_config_revision",
    "context_revision",
    "app_instance",
    "targets",
    "patch",
    "copied_private_memory",
)
CHANGE_VALIDATION_VERDICTS: Final[tuple[str, ...]] = (
    "conflict",
    "rebase-required",
    "valid",
)
CHANGE_APPLY_OUTCOMES: Final[tuple[str, ...]] = ("applied",)
ALLOWED_PATCH_KINDS: Final[frozenset[str]] = frozenset(
    {"filter_add", "filter_remove", "runtime_input"}
)
_FORBIDDEN_PATCH_KINDS: Final[frozenset[str]] = frozenset(
    {
        "account_retarget",
        "account-retarget",
        "apply",
        "grant_widen",
        "grant-widen",
        "install_code",
        "install-code",
        "package_source",
        "package-source",
        "promote",
        "role.set_base",
    }
)
_FORBIDDEN_PATCH_KEYS: Final[frozenset[str]] = frozenset(
    {
        "account_scope",
        "app_instance_id",
        "granted_ops",
        "install_code",
        "package_source",
        "package_source_hash",
        "promote",
        "source",
    }
)
_HASH_EXCLUDED: Final[frozenset[str]] = frozenset(
    {
        "applied_at",
        "applied_base_hashes",
        "apply",
        "outcome",
        "result_hashes",
        "validated_at",
        "validation",
        "validator_principal",
        "verdict",
    }
)
_TRANSCRIPT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "layout",
        "private_transcript",
        "transcript",
        "widget",
        "widgets",
        "board_layout",
    }
)
_DEFAULT_AS_OF: Final[str] = "2026-09-20T00:00:00Z"


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    return invalid_input(field, reason, **extra)


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    return policy_rejection(field, reason, **extra)


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


def _require_bool(field: str, value: object) -> Result[bool]:
    if not isinstance(value, bool):
        return _invalid(field, f"{field} must be a boolean", given=repr(value))
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


def _parse_fp1(field: str, value: object) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    token = _require_str(field, value)
    if is_refusal(token):
        return token
    parsed = Fingerprint.try_create(token.value)
    if is_refusal(parsed):
        return parsed
    return Ok(parsed.value)


def _dump(payload: Mapping[str, object]) -> str:
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))


def _parse_cr_id(value: object) -> Result[str]:
    token = _require_str("change_request_id", value)
    if is_refusal(token):
        return token
    raw = token.value
    if not raw.startswith(CHANGE_REQUEST_ID_PREFIX) or raw == CHANGE_REQUEST_ID_PREFIX:
        return _invalid(
            "change_request_id",
            "change_request ids are cr: (FR-WF-36; AD-29)",
            given=raw,
        )
    return Ok(raw)


def _parse_psess(field: str, value: object) -> Result[str]:
    token = _require_str(field, value)
    if is_refusal(token):
        return token
    raw = token.value
    if not raw.startswith(PRODUCT_SESSION_ID_PREFIX) or raw == PRODUCT_SESSION_ID_PREFIX:
        return _invalid(field, "product_session ids are psess:", given=raw)
    return Ok(raw)


def _parse_principal_class(value: object) -> Result[PrincipalClass]:
    try:
        parsed = value if isinstance(value, PrincipalClass) else parse_closed(PrincipalClass, value)
    except VocabularyError as exc:
        return _invalid("operator_principal", str(exc), given=repr(value))
    return Ok(parsed)


@dataclass(frozen=True, slots=True)
class ChangeTarget:
    """Paired ``{target_ref, base_hash}`` (RC-12; SCN-0019 Then 1)."""

    target_ref: str
    base_hash: Fingerprint

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType({"base_hash": self.base_hash.value, "target_ref": self.target_ref})


def parse_change_target(value: object) -> Result[ChangeTarget]:
    mapped = _as_mapping("targets", value)
    if is_refusal(mapped):
        return mapped
    body = mapped.value
    extra = sorted(set(body) - {"target_ref", "base_hash"})
    if extra:
        return _invalid("targets", "target is {target_ref, base_hash}", extra=extra)
    ref = _require_str("target_ref", body.get("target_ref"))
    if is_refusal(ref):
        return ref
    hashed = _parse_fp1("base_hash", body.get("base_hash"))
    if is_refusal(hashed):
        return hashed
    return Ok(ChangeTarget(target_ref=ref.value, base_hash=hashed.value))


def parse_change_targets(value: object) -> Result[tuple[ChangeTarget, ...]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return _invalid("targets", "targets is an array of {target_ref, base_hash}")
    collected: list[ChangeTarget] = []
    seen: set[str] = set()
    for raw in cast("Sequence[object]", value):
        parsed = parse_change_target(raw)
        if is_refusal(parsed):
            return parsed
        if parsed.value.target_ref in seen:
            return _invalid(
                "targets",
                "target_ref must be unique on a ChangeRequest",
                given=parsed.value.target_ref,
            )
        seen.add(parsed.value.target_ref)
        collected.append(parsed.value)
    if not collected:
        return _invalid("targets", "ChangeRequest names at least one target")
    return Ok(tuple(collected))


def _parse_patch(value: object) -> Result[Mapping[str, object]]:
    mapped = _as_mapping("patch", value)
    if is_refusal(mapped):
        return mapped
    body = mapped.value
    stolen = sorted(key for key in body if key.casefold() in _FORBIDDEN_PATCH_KEYS)
    if stolen:
        return _package_source_or_widen(stolen[0], body)
    kind = _require_str("patch.kind", body.get("kind"))
    if is_refusal(kind):
        return kind
    folded = kind.value.casefold()
    if folded in _FORBIDDEN_PATCH_KINDS:
        return _package_source_or_widen(kind.value, body)
    if kind.value not in ALLOWED_PATCH_KINDS:
        return _invalid(
            "patch.kind",
            "app-use patch is a permitted runtime-input kind, never package source",
            given=kind.value,
            allowed=sorted(ALLOWED_PATCH_KINDS),
            branch="A",
        )
    path = _require_str("patch.path", body.get("path"))
    if is_refusal(path):
        return path
    if path.value.casefold() in _FORBIDDEN_PATCH_KEYS:
        return _package_source_or_widen(path.value, body)
    extra = {key: item for key, item in body.items() if key not in {"kind", "path"}}
    payload: dict[str, object] = {"kind": kind.value, "path": path.value}
    payload.update(extra)
    return Ok(MappingProxyType(payload))


def _package_source_or_widen(token: str, body: Mapping[str, object]) -> TypedRefusal:
    folded = token.casefold()
    if folded in {"grant_widen", "grant-widen", "granted_ops"}:
        return GrantWidenRefused.of(
            grant_id=str(body.get("grant_id", "")),
            field="patch",
            branch="B",
            reason="mint or apply cannot elevate grants without explicit re-grant",
        )
    if folded in {"account_retarget", "account-retarget", "account_scope", "app_instance_id"}:
        return GrantWidenRefused.of(
            grant_id=str(body.get("grant_id", "")),
            field="patch",
            branch="B",
            reason="mint or apply cannot retarget accounts or substitute app_instance_id",
        )
    return _policy(
        "patch",
        "app-use must not edit package source, install code, or apply (SCN-0019 Branch A)",
        branch="A",
        given=token,
        writes_package_source=False,
        applies=False,
    )


@dataclass(frozen=True, slots=True)
class ChangeRequest:
    """Immutable requester facts + patch. Validation and apply never enter."""

    change_request_id: str
    from_session: str
    source_instance_id: str
    source_config_revision: int
    context_revision: int
    app_instance: Mapping[str, object]
    targets: tuple[ChangeTarget, ...]
    patch: Mapping[str, object]
    request_hash: Fingerprint
    copied_private_memory: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "app_instance", MappingProxyType(dict(self.app_instance)))
        object.__setattr__(self, "patch", MappingProxyType(dict(self.patch)))
        object.__setattr__(self, "targets", tuple(self.targets))

    def hash_preimage(self) -> dict[str, object]:
        return {
            "app_instance": dict(self.app_instance),
            "change_request_id": self.change_request_id,
            "context_revision": self.context_revision,
            "copied_private_memory": self.copied_private_memory,
            "from_session": self.from_session,
            "patch": dict(self.patch),
            "source_config_revision": self.source_config_revision,
            "source_instance_id": self.source_instance_id,
            "targets": [dict(item.to_payload()) for item in self.targets],
        }

    def to_payload(self) -> Mapping[str, object]:
        payload = self.hash_preimage()
        payload["request_hash"] = self.request_hash.value
        payload["type"] = CHANGE_REQUEST_STAGING_KIND
        return MappingProxyType(payload)


def hash_change_request(preimage: Mapping[str, object]) -> Result[Fingerprint]:
    """``request_hash`` over requester facts + patch only (FR-WF-37; RC-12)."""
    stolen = sorted(key for key in preimage if key.casefold() in _HASH_EXCLUDED)
    if stolen:
        return _invalid(
            "request_hash",
            "no validation verdict and no apply evidence may enter the preimage",
            extra=stolen,
        )
    body: dict[str, object] = {}
    for name in CHANGE_REQUEST_HASH_FIELDS:
        if name not in preimage:
            return _invalid("request_hash", f"preimage missing {name}", field_name=name)
        body[name] = preimage[name]
    return content_address(body)


@dataclass(frozen=True, slots=True)
class ChangeValidationRecord:
    """Validator-authority record. Never rewrites the request bytes."""

    change_request_id: str
    request_hash: Fingerprint
    validator_principal: str
    verdict: str
    validated_at: str
    conflicts: tuple[Mapping[str, object], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "conflicts",
            tuple(MappingProxyType(dict(item)) for item in self.conflicts),
        )

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "change_request_id": self.change_request_id,
                "conflicts": [dict(item) for item in self.conflicts],
                "request_hash": self.request_hash.value,
                "validated_at": self.validated_at,
                "validator_principal": self.validator_principal,
                "verdict": self.verdict,
            }
        )


@dataclass(frozen=True, slots=True)
class ChangeApplyRecord:
    """Append-only apply evidence. Authoring + operator principal."""

    change_request_id: str
    request_hash: Fingerprint
    applied_base_hashes: tuple[str, ...]
    result_hashes: tuple[str, ...]
    authoring_principal: str
    operator_principal: str
    applied_at: str
    outcome: str = "applied"

    def __post_init__(self) -> None:
        object.__setattr__(self, "applied_base_hashes", tuple(self.applied_base_hashes))
        object.__setattr__(self, "result_hashes", tuple(self.result_hashes))

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "applied_at": self.applied_at,
                "applied_base_hashes": list(self.applied_base_hashes),
                "authoring_principal": self.authoring_principal,
                "change_request_id": self.change_request_id,
                "operator_principal": self.operator_principal,
                "outcome": self.outcome,
                "request_hash": self.request_hash.value,
                "result_hashes": list(self.result_hashes),
            }
        )


@dataclass(frozen=True, slots=True)
class InstalledAppSnapshot:
    """v1 instance row the mint must leave untouched (SCN-0019 Then 3)."""

    instance_id: str
    package_id: str
    version: str
    package_source_hash: Fingerprint
    config_revision: int
    granted_ops: tuple[str, ...]
    running_jobs: tuple[str, ...]
    account_scope: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "granted_ops", tuple(self.granted_ops))
        object.__setattr__(self, "running_jobs", tuple(self.running_jobs))

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "config_revision": self.config_revision,
            "granted_ops": list(self.granted_ops),
            "instance_id": self.instance_id,
            "package_id": self.package_id,
            "package_source_hash": self.package_source_hash.value,
            "running_jobs": list(self.running_jobs),
            "version": self.version,
        }
        if self.account_scope is not None:
            payload["account_scope"] = self.account_scope
        return MappingProxyType(payload)


def _parse_jobs(value: object) -> Result[tuple[str, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return _invalid("running_jobs", "running_jobs is an array of job ids")
    collected: list[str] = []
    for raw in cast("Sequence[object]", value):
        token = _require_str("running_jobs", raw)
        if is_refusal(token):
            return token
        collected.append(token.value)
    return Ok(tuple(collected))


def _parse_granted(value: object) -> Result[tuple[str, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, str):
        return Ok((value,))
    if isinstance(value, (bytes,)) or not isinstance(value, Sequence):
        return _invalid("granted_ops", "granted_ops is an array of grant_ids")
    collected: list[str] = []
    for raw in cast("Sequence[object]", value):
        token = _require_str("granted_ops", raw)
        if is_refusal(token):
            return token
        collected.append(token.value)
    return Ok(tuple(collected))


@dataclass
class ChangeRequestFixture:
    """J01 three-record change path. App-use mints; authoring+operator applies."""

    sessions: ProductSessionService = field(default_factory=ProductSessionService)
    v1: InstalledAppSnapshot | None = None
    _live_hashes: dict[str, str] = field(default_factory=dict[str, str], init=False)
    _requests: dict[str, ChangeRequest] = field(
        default_factory=dict[str, ChangeRequest], init=False
    )
    _request_bytes: dict[str, str] = field(default_factory=dict[str, str], init=False)
    _validations: list[ChangeValidationRecord] = field(
        default_factory=list[ChangeValidationRecord], init=False
    )
    _applies: list[ChangeApplyRecord] = field(default_factory=list[ChangeApplyRecord], init=False)

    @property
    def staging_kind(self) -> str:
        return CHANGE_REQUEST_STAGING_KIND

    @property
    def sixth_store_minted(self) -> bool:
        return CHANGE_REQUEST_SIXTH_STORE_MINTED

    @property
    def tab_writes(self) -> bool:
        return PRODUCT_SESSION_TAB_WRITES

    @property
    def distinct_from_refinement_proposal(self) -> bool:
        return CHANGE_REQUEST_STAGING_KIND != STAGING_STORE_RECORD_TYPE

    def validations(self) -> tuple[ChangeValidationRecord, ...]:
        return tuple(self._validations)

    def applies(self) -> tuple[ChangeApplyRecord, ...]:
        return tuple(self._applies)

    def get(self, change_request_id: object) -> Result[ChangeRequest]:
        parsed = _parse_cr_id(change_request_id)
        if is_refusal(parsed):
            return parsed
        row = self._requests.get(parsed.value)
        if row is None:
            return _invalid(
                "change_request_id",
                "ChangeRequest is not on the staging path",
                given=parsed.value,
            )
        return Ok(row)

    def install_v1(
        self,
        *,
        instance_id: object,
        package_id: object,
        version: object,
        package_source_hash: object,
        config_revision: object,
        granted_ops: object = (),
        running_jobs: object = (),
        account_scope: object = None,
        live_hashes: object = (),
    ) -> Result[InstalledAppSnapshot]:
        """Bind the installed v1 instance the mint must not mutate."""
        inst = _require_str("instance_id", instance_id)
        if is_refusal(inst):
            return inst
        package = _require_str("package_id", package_id)
        if is_refusal(package):
            return package
        ver = _require_str("version", version)
        if is_refusal(ver):
            return ver
        source = _parse_fp1("package_source_hash", package_source_hash)
        if is_refusal(source):
            return source
        revision = _require_int("config_revision", config_revision, minimum=0)
        if is_refusal(revision):
            return revision
        grants = _parse_granted(granted_ops)
        if is_refusal(grants):
            return grants
        jobs = _parse_jobs(running_jobs)
        if is_refusal(jobs):
            return jobs
        scope: str | None = None
        if account_scope is not None:
            parsed_scope = _require_str("account_scope", account_scope)
            if is_refusal(parsed_scope):
                return parsed_scope
            scope = parsed_scope.value
        hashed = parse_change_targets(live_hashes) if live_hashes else Ok(())
        if is_refusal(hashed):
            return hashed
        snapshot = InstalledAppSnapshot(
            instance_id=inst.value,
            package_id=package.value,
            version=ver.value,
            package_source_hash=source.value,
            config_revision=revision.value,
            granted_ops=grants.value,
            running_jobs=jobs.value,
            account_scope=scope,
        )
        self.v1 = snapshot
        self._live_hashes = {item.target_ref: item.base_hash.value for item in hashed.value}
        return Ok(snapshot)

    def v1_snapshot(self) -> Result[InstalledAppSnapshot]:
        if self.v1 is None:
            return _invalid("v1", "install_v1 before minting a ChangeRequest")
        session = self.sessions.session_for_instance(self.v1.instance_id)
        granted = self.v1.granted_ops
        revision = self.v1.config_revision
        scope = self.v1.account_scope
        if is_ok(session):
            granted = session.value.granted_ops
            revision = session.value.context.config_revision
            scope = session.value.account_scope
        return Ok(
            replace(
                self.v1,
                granted_ops=granted,
                config_revision=revision,
                account_scope=scope,
            )
        )

    def advance_target(self, target_ref: object, live_hash: object) -> Result[str]:
        """Move a live hash off the minted base (SCN-0019 Branch C)."""
        ref = _require_str("target_ref", target_ref)
        if is_refusal(ref):
            return ref
        hashed = _parse_fp1("live_hash", live_hash)
        if is_refusal(hashed):
            return hashed
        self._live_hashes[ref.value] = hashed.value.value
        return Ok(hashed.value.value)

    def mint(
        self,
        *,
        from_session: object,
        change_request_id: object,
        targets: object,
        patch: object,
        copied_private_memory: object = False,
        **extra: object,
    ) -> Result[ChangeRequest]:
        """App-use mints. Does not apply, edit source, or mutate v1."""
        stolen = sorted(key for key in extra if key.casefold() in _HASH_EXCLUDED)
        if stolen:
            return _invalid(
                "change_request",
                "validation verdict and apply evidence are not requester facts",
                extra=stolen,
            )
        transcript = sorted(key for key in extra if key.casefold() in _TRANSCRIPT_KEYS)
        if transcript:
            return _invalid(
                "change_request",
                "authoring opens with typed selected_refs, not the private transcript",
                extra=transcript,
                branch="D",
            )
        if extra:
            return _invalid(
                "change_request", "unknown ChangeRequest mint fields", extra=sorted(extra)
            )
        before = self.v1_snapshot()
        if is_refusal(before):
            return before
        session_id = _parse_psess("from_session", from_session)
        if is_refusal(session_id):
            return session_id
        loaded = self.sessions.get(session_id.value)
        if is_refusal(loaded):
            return loaded
        session = loaded.value
        if session.profile is not ProductSessionProfile.APP_USE:
            return _policy(
                "from_session",
                "only an app-use product_session may mint a ChangeRequest",
                profile=session.profile.value,
                branch="A",
            )
        source_instance_id = session.app_instance_id
        if source_instance_id is None:
            return _invalid(
                "app_instance_id",
                "app_instance_id is required when profile=app-use (DEC-0463; FR-PG-09)",
                profile=session.profile.value,
            )
        if source_instance_id != before.value.instance_id:
            return GrantWidenRefused.of(
                grant_id="",
                field="source_instance_id",
                branch="B",
                bound=before.value.instance_id,
                given=source_instance_id,
            )
        if session.account_scope != before.value.account_scope:
            return GrantWidenRefused.of(
                grant_id="",
                field="account_scope",
                branch="B",
            )
        ident = _parse_cr_id(change_request_id)
        if is_refusal(ident):
            return ident
        if ident.value in self._requests:
            return _invalid(
                "change_request_id",
                "ChangeRequest is immutable; duplicate mint does not rewrite bytes",
                given=ident.value,
            )
        parsed_targets = parse_change_targets(targets)
        if is_refusal(parsed_targets):
            return parsed_targets
        parsed_patch = _parse_patch(patch)
        if is_refusal(parsed_patch):
            return parsed_patch
        copied = _require_bool("copied_private_memory", copied_private_memory)
        if is_refusal(copied):
            return copied
        app_instance = {
            "package_id": before.value.package_id,
            "version": before.value.version,
        }
        preimage: dict[str, object] = {
            "app_instance": app_instance,
            "change_request_id": ident.value,
            "context_revision": session.context_revision,
            "copied_private_memory": copied.value,
            "from_session": session.product_session_id,
            "patch": dict(parsed_patch.value),
            "source_config_revision": session.context.config_revision,
            "source_instance_id": source_instance_id,
            "targets": [dict(item.to_payload()) for item in parsed_targets.value],
        }
        hashed = hash_change_request(preimage)
        if is_refusal(hashed):
            return hashed
        request = ChangeRequest(
            change_request_id=ident.value,
            from_session=session.product_session_id,
            source_instance_id=source_instance_id,
            source_config_revision=session.context.config_revision,
            context_revision=session.context_revision,
            app_instance=app_instance,
            targets=parsed_targets.value,
            patch=parsed_patch.value,
            request_hash=hashed.value,
            copied_private_memory=copied.value,
        )
        self._requests[ident.value] = request
        self._request_bytes[ident.value] = _dump(request.to_payload())
        after = self.v1_snapshot()
        if is_refusal(after):
            return after
        if dict(after.value.to_payload()) != dict(before.value.to_payload()):
            return _policy(
                "v1",
                "v1 instance, GrantRecords, and running jobs stay unchanged by the mint",
                branch="B",
            )
        return Ok(request)

    def request_bytes_unchanged(self, change_request_id: object) -> Result[bool]:
        loaded = self.get(change_request_id)
        if is_refusal(loaded):
            return loaded
        original = self._request_bytes[loaded.value.change_request_id]
        if _dump(loaded.value.to_payload()) != original:
            return _policy(
                "change_request",
                "validation and apply never rewrite the request bytes",
            )
        return Ok(True)

    def validate(
        self,
        *,
        change_request_id: object,
        authoring_session: object,
        validated_at: object,
    ) -> Result[ChangeValidationRecord]:
        """Authoring writes a separate validation record (SCN-0019 Then 1)."""
        loaded = self.get(change_request_id)
        if is_refusal(loaded):
            return loaded
        request = loaded.value
        session_id = _parse_psess("authoring_session", authoring_session)
        if is_refusal(session_id):
            return session_id
        session_row = self.sessions.get(session_id.value)
        if is_refusal(session_row):
            return session_row
        session = session_row.value
        if session.profile is ProductSessionProfile.APP_USE:
            return _policy(
                "authoring_session",
                "app-use never validates or applies (SCN-0019 Branch A)",
                profile="app-use",
                branch="A",
            )
        if session.profile is not ProductSessionProfile.AUTHORING:
            return _invalid(
                "authoring_session",
                "validation is an authoring product_session",
                profile=session.profile.value,
            )
        stamped = parse_utc_iso_z("validated_at", validated_at)
        if is_refusal(stamped):
            return stamped
        conflicts: list[dict[str, object]] = []
        rebase: list[dict[str, object]] = []
        for target in request.targets:
            live = self._live_hashes.get(target.target_ref)
            if live is None:
                conflicts.append(
                    {"base_hash": target.base_hash.value, "target_ref": target.target_ref}
                )
            elif live != target.base_hash.value:
                rebase.append(
                    {
                        "base_hash": target.base_hash.value,
                        "live_hash": live,
                        "target_ref": target.target_ref,
                    }
                )
        if conflicts:
            verdict = "conflict"
            rows: tuple[Mapping[str, object], ...] = tuple(conflicts)
        elif rebase:
            verdict = "rebase-required"
            rows = tuple(rebase)
        else:
            verdict = "valid"
            rows = ()
        record = ChangeValidationRecord(
            change_request_id=request.change_request_id,
            request_hash=request.request_hash,
            validator_principal=session.profile.value,
            verdict=verdict,
            validated_at=stamped.value[1],
            conflicts=rows,
        )
        self._validations.append(record)
        unchanged = self.request_bytes_unchanged(request.change_request_id)
        if is_refusal(unchanged):
            return unchanged
        return Ok(record)

    def apply(
        self,
        *,
        change_request_id: object,
        authoring_session: object,
        operator_principal: object,
        applied_at: object,
    ) -> Result[ChangeApplyRecord]:
        """Authoring + operator principal. App-use and stale bases refuse."""
        loaded = self.get(change_request_id)
        if is_refusal(loaded):
            return loaded
        request = loaded.value
        session_id = _parse_psess("authoring_session", authoring_session)
        if is_refusal(session_id):
            return session_id
        session_row = self.sessions.get(session_id.value)
        if is_refusal(session_row):
            return session_row
        session = session_row.value
        if session.profile is ProductSessionProfile.APP_USE:
            return _policy(
                "apply",
                "app-use mints only; applying is authoring + operator principal",
                branch="A",
                profile="app-use",
                applies=False,
            )
        if session.profile is not ProductSessionProfile.AUTHORING:
            return _invalid(
                "authoring_session",
                "apply requires an authoring product_session",
                profile=session.profile.value,
            )
        principal = _parse_principal_class(operator_principal)
        if is_refusal(principal):
            return principal
        if principal.value is not PrincipalClass.OPERATOR:
            return OperatorPrincipalRequired.of(
                command="change_request.apply",
                principal_class=principal.value.value,
            )
        stamped = parse_utc_iso_z("applied_at", applied_at)
        if is_refusal(stamped):
            return stamped
        latest = self._latest_validation(request.change_request_id)
        if latest is None or latest.verdict != "valid":
            verdict = latest.verdict if latest is not None else "conflict"
            return _policy(
                "apply",
                "stale base hashes yield conflict / rebase-required — they do not apply",
                branch="C",
                verdict=verdict,
            )
        for target in request.targets:
            live = self._live_hashes.get(target.target_ref)
            if live != target.base_hash.value:
                return _policy(
                    "apply",
                    "stale base hashes yield conflict / rebase-required — they do not apply",
                    branch="C",
                    verdict="rebase-required" if live is not None else "conflict",
                    target_ref=target.target_ref,
                )
        before = self.v1_snapshot()
        if is_refusal(before):
            return before
        applied_bases = tuple(item.base_hash.value for item in request.targets)
        result = content_address(
            {
                "applied_base_hashes": list(applied_bases),
                "patch": dict(request.patch),
                "request_hash": request.request_hash.value,
            }
        )
        if is_refusal(result):
            return result
        record = ChangeApplyRecord(
            change_request_id=request.change_request_id,
            request_hash=request.request_hash,
            applied_base_hashes=applied_bases,
            result_hashes=(result.value.value,),
            authoring_principal=session.profile.value,
            operator_principal=principal.value.value,
            applied_at=stamped.value[1],
            outcome="applied",
        )
        self._applies.append(record)
        unchanged = self.request_bytes_unchanged(request.change_request_id)
        if is_refusal(unchanged):
            return unchanged
        after = self.v1_snapshot()
        if is_refusal(after):
            return after
        if dict(after.value.to_payload()) != dict(before.value.to_payload()):
            return _policy(
                "v1",
                "apply produces v2 evidence; the v1 instance stays",
            )
        return Ok(record)

    def _latest_validation(self, change_request_id: str) -> ChangeValidationRecord | None:
        for record in reversed(self._validations):
            if record.change_request_id == change_request_id:
                return record
        return None

    def write_package_source(
        self,
        *,
        from_session: object,
        source: object = "package.py",
    ) -> Result[None]:
        """Branch A: app-use cannot write package source."""
        session_id = _parse_psess("from_session", from_session)
        if is_refusal(session_id):
            return session_id
        loaded = self.sessions.get(session_id.value)
        if is_refusal(loaded):
            return loaded
        return _policy(
            "package_source",
            "app-use must not edit package source or install code (SCN-0019 Branch A)",
            branch="A",
            profile=loaded.value.profile.value,
            writes_package_source=False,
            given=repr(source),
        )

    def widen_grants(
        self,
        *,
        from_session: object,
        grant_id: object,
    ) -> Result[None]:
        """Branch B: mint/apply cannot elevate grants."""
        token = _require_str("grant_id", grant_id)
        if is_refusal(token):
            return token
        session_id = _parse_psess("from_session", from_session)
        if is_refusal(session_id):
            return session_id
        loaded = self.sessions.get(session_id.value)
        if is_refusal(loaded):
            return loaded
        return GrantWidenRefused.of(
            grant_id=token.value,
            field="granted_ops",
            branch="B",
            profile=loaded.value.profile.value,
        )

    def retarget_account(
        self,
        *,
        from_session: object,
        account_scope: object,
        app_instance_id: object | None = None,
    ) -> Result[None]:
        """Branch B: cannot retarget accounts or substitute instance id."""
        session_id = _parse_psess("from_session", from_session)
        if is_refusal(session_id):
            return session_id
        loaded = self.sessions.get(session_id.value)
        if is_refusal(loaded):
            return loaded
        return GrantWidenRefused.of(
            grant_id="",
            field="account_scope" if app_instance_id is None else "app_instance_id",
            branch="B",
            given=repr(account_scope if app_instance_id is None else app_instance_id),
            profile=loaded.value.profile.value,
        )

    def promote(self, **_extra: object) -> Result[None]:
        """``promote`` remains L17 and is not this path."""
        return _policy(
            "promote",
            "promote remains L17 and is not the change-request path (SCN-0019 Then 2)",
            l17=True,
            change_path=False,
        )

    def tab_switch(
        self,
        *,
        product_session_id: object,
        tab_id: object,
        action: object = "open",
    ) -> Result[ProductSession]:
        """A tab change writes nothing (SCN-0019 Branch D)."""
        if PRODUCT_SESSION_TAB_WRITES:
            return refuse_tab_as_product_session(field="tab")
        action_token = _require_str("action", action)
        if is_refusal(action_token):
            return action_token
        before = self.sessions.get(product_session_id)
        if is_refusal(before):
            return before
        prior = dict(before.value.to_payload())
        if action_token.value == "close":
            switched = self.sessions.close_tab(tab_id, product_session_id=product_session_id)
        else:
            switched = self.sessions.open_tab(tab_id=tab_id, product_session_id=product_session_id)
        if is_refusal(switched):
            return switched
        after = dict(switched.value.to_payload())
        if after != prior:
            return refuse_tab_as_product_session(field="tab", branch="D")
        return Ok(switched.value)

    def reconnect(
        self,
        product_session_id: object,
        *,
        resume_cursor: object,
        cursor_generation: object,
        **extra: object,
    ) -> Result[ReconnectSnapshot]:
        """Reconnect is a query and never replays unacked intent (Story 55.2)."""
        if extra:
            return refuse_reconnect_replays_intent(fields=sorted(extra), branch="D")
        return self.sessions.reconnect(
            product_session_id,
            resume_cursor=resume_cursor,
            cursor_generation=cursor_generation,
        )

    def open_authoring_handoff(
        self,
        request: ChangeRequest,
        *,
        product_session_id: object = "psess:authoring-1",
        instance_id: object = "inst:authoring",
        principal: object = "operator",
        as_of: object = _DEFAULT_AS_OF,
        selected_refs: object | None = None,
        **extra: object,
    ) -> Result[ProductSession]:
        """New authoring session receives typed selected_refs, not transcript."""
        stolen = sorted(key for key in extra if key.casefold() in _TRANSCRIPT_KEYS)
        if stolen:
            return _invalid(
                "selected_refs",
                "authoring opens with typed selected_refs, not the private transcript "
                "and not layout/widget trees (SCN-0019 Then 4)",
                extra=stolen,
            )
        if extra:
            return _invalid(
                "authoring_session",
                "unknown authoring handoff fields",
                extra=sorted(extra),
            )
        refs: object = selected_refs
        if refs is None:
            refs = [{"kind": "artifact", "id": item.target_ref} for item in request.targets]
        parsed_refs = parse_selected_refs(refs)
        if is_refusal(parsed_refs):
            return parsed_refs
        minted = self.sessions.mint(
            product_session_id=product_session_id,
            profile=ProductSessionProfile.AUTHORING,
            principal=principal,
            contribution={
                "qualified_id": "analysis-backtest:qmb",
                "package_version": "0.1.0",
            },
            instance_id=instance_id,
            config_revision=0,
            as_of=as_of,
            selected_refs=[dict(item.to_payload()) for item in parsed_refs.value],
        )
        if is_refusal(minted):
            return minted
        if minted.value.profile is not ProductSessionProfile.AUTHORING:
            return _invalid("profile", "handoff session is authoring")
        v1 = self.v1_snapshot()
        if is_refusal(v1):
            return v1
        if minted.value.app_instance_id == v1.value.instance_id:
            return GrantWidenRefused.of(
                grant_id="",
                field="app_instance_id",
                branch="B",
                reason="authoring handoff must not retarget the v1 app_instance_id",
            )
        return Ok(minted.value)

    def selected_refs_for(self, request: ChangeRequest) -> tuple[SelectedRef, ...]:
        return tuple(SelectedRef(kind="artifact", id=item.target_ref) for item in request.targets)
