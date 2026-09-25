"""Story 58.5 / SCN-0022 — pack lifecycle fixture, export oracle, unsupported_door.

Thin honesty fixture: journaled ``PackTransition`` with CAS on
``roster_generation``; roster publication is stage / fsync / swap and publishes
``availability_revision``. Missing dependencies are a hard error at enable, not
warning-and-continue. Manifest ``exports_secrets: false`` is a request — an
independent ``ExportScanReport`` is the oracle. Unsupported door is typed
``unsupported_door``; QMB remains the only operator CLI. Pin/invoke reuses
Story 53.3. Does not close GAP-0098. No new sqlite class.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Final, Literal, cast

from qma.core.content import content_address
from qma.core.operations.catalog import public_operation_descriptors
from qma.core.operations.descriptor import SupportedDoor
from qma.core.operations.doors import (
    FORBIDDEN_OPERATOR_CLI_ADAPTERS,
    QMA_OPERATOR_CLI,
    QMN_OPERATOR_CLI,
    admit_operation_door,
    descriptor_for,
)
from qma.core.plugins.context import PluginContext
from qma.core.plugins.secret_schema import FORBIDDEN_SECRET_PAYLOAD_KEYS
from qma.core.refusals.variants import UnsupportedDoor
from qma.core.vocabulary.enums import PrincipalClass
from qma.daemon.journal.stores import CLOSED_STORE_NAMES, DEFINITION_STORE_MEMBERS
from qma.daemon.plugins.context import DaemonPluginContext, PluginContextError
from qma.daemon.plugins.loader import PluginActivator, PluginLoader, PublishedContribution
from qma.daemon.plugins.pins import (
    PIN_LEASE_STORE,
    ContributionPinService,
    PackDepartureReceipt,
    PinInvokeAdmission,
)
from qma.wire.contribution_pin import ContributionPin
from qma.wire.federated_discovery import ContributionHit
from qma.wire.invocation_envelope import parse_utc_iso_z
from qmf.core import Ok, Result, is_ok, is_refusal
from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import TypedRefusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "COMPOSITION_MODES",
    "COMPOSITION_MODES_REQUIRE_CORE_EDITS",
    "E2E_ADOPTION_CLOSED",
    "EXPORTS_SECRETS_AUTHORIZES_EXPORT",
    "EXPORT_SCAN_DETECTORS",
    "EXPORT_SCAN_RESULTS",
    "EXPORT_THREAT_CLASSES",
    "GAP_0098_ID",
    "GAP_0098_STATUS",
    "LEGAL_PACK_TRANSITIONS",
    "MIGRATION_MODES",
    "MIGRATION_PHASES",
    "MISSING_DEP_WARN_AND_CONTINUE",
    "P2_INT_001",
    "PACK_LIFECYCLE_INSPECT_SHA",
    "PACK_LIFECYCLE_SIXTH_STORE_MINTED",
    "PACK_LIFECYCLE_STORE",
    "PACK_LIFECYCLE_WIRED_AT_INSPECT_SHA",
    "PACK_STATES",
    "QMA_OPERATOR_CLI",
    "QMN_OPERATOR_CLI",
    "SESSION_GRANTED_IS_PACK_STATE",
    "AtomicRoster",
    "DoorParityReport",
    "ExportBundle",
    "ExportScanCoverage",
    "ExportScanFinding",
    "ExportScanReport",
    "ExportScanRewrite",
    "PackLifecycleFixture",
    "PackMigrationRecord",
    "PackRecord",
    "PackTransition",
    "claim_gap_0098_closed",
]


PACK_STATES: Final[tuple[str, ...]] = (
    "downloaded",
    "installed",
    "validated",
    "enabled",
    "disabled",
    "uninstalled",
)
LEGAL_PACK_TRANSITIONS: Final[frozenset[tuple[str | None, str]]] = frozenset(
    {
        (None, "downloaded"),
        ("downloaded", "installed"),
        ("installed", "validated"),
        ("validated", "enabled"),
        ("enabled", "disabled"),
        ("disabled", "enabled"),
        ("disabled", "uninstalled"),
    }
)
MIGRATION_MODES: Final[frozenset[str]] = frozenset({"down", "forward_only"})
MIGRATION_PHASES: Final[frozenset[str]] = frozenset({"prepare", "commit", "rollback"})
EXPORT_THREAT_CLASSES: Final[tuple[str, ...]] = (
    "secret_values",
    "private_paths",
    "transcripts",
)
EXPORT_SCAN_DETECTORS: Final[tuple[str, ...]] = (
    "secret-regex-v3",
    "path-allowlist-v1",
    "transcript-marker-v1",
)
EXPORT_SCAN_RESULTS: Final[frozenset[str]] = frozenset({"fail-closed-pass", "fail-closed-fail"})
COMPOSITION_MODES: Final[tuple[str, ...]] = (
    "consume_artifact_fp1",
    "invoke_exported_op_through_envelope",
    "graph_template_coordinates_two_apps",
    "composite_app_cites_contribution_ids",
)
COMPOSITION_MODES_REQUIRE_CORE_EDITS: Final[bool] = False
SESSION_GRANTED_IS_PACK_STATE: Final[bool] = False
EXPORTS_SECRETS_AUTHORIZES_EXPORT: Final[bool] = False
MISSING_DEP_WARN_AND_CONTINUE: Final[bool] = False
PACK_LIFECYCLE_SIXTH_STORE_MINTED: Final[bool] = False
PACK_LIFECYCLE_STORE: Final[str] = PIN_LEASE_STORE
PACK_LIFECYCLE_WIRED_AT_INSPECT_SHA: Final[bool] = False
PACK_LIFECYCLE_INSPECT_SHA: Final[str] = "270e992995c2378ca63cf6343254ef8140a8c97e"
GAP_0098_ID: Final[str] = "GAP-0098"
GAP_0098_STATUS: Final[str] = "open"
P2_INT_001: Final[str] = "P2-INT-001"
E2E_ADOPTION_CLOSED: Final[bool] = False

_SECRET_INLINE = re.compile(r"(?i)\b(secret|password|token|api[_-]?key|bearer)\s*[:=]\s*(\S+)")
_PRIVATE_PATH = re.compile(r"(?i)(?:[A-Za-z]:\\Users\\|/home/|/Users/|~/)")
_TRANSCRIPT_MARKERS: Final[tuple[str, ...]] = (
    "transcript",
    "conversation",
    "chat_log",
    "private_transcript",
)
PackState = Literal["downloaded", "installed", "validated", "enabled", "disabled", "uninstalled"]
MigrationMode = Literal["down", "forward_only"]
MigrationPhase = Literal["prepare", "commit", "rollback"]
ExportScanResult = Literal["fail-closed-pass", "fail-closed-fail"]


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


def _dump(payload: Mapping[str, object]) -> bytes:
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")


def claim_gap_0098_closed() -> TypedRefusal:
    """Thin fixtures must not claim or close GAP-0098 / P2-INT-001 (FR-WF-66)."""
    return _policy(
        "gap",
        "package tests are not e2e adoption; GAP-0098 / P2-INT-001 stay open (DEC-0450)",
        gap=GAP_0098_ID,
        gap_status=GAP_0098_STATUS,
        p2=P2_INT_001,
        e2e_adoption_closed=False,
        wired_at_inspect_sha=False,
        inspect_sha=PACK_LIFECYCLE_INSPECT_SHA,
    )


def _default_activator(contributes: Sequence[Mapping[str, object]]) -> PluginActivator:
    rows = tuple(dict(item) for item in contributes)

    def activate(ctx: PluginContext) -> None:
        if not isinstance(ctx, DaemonPluginContext):
            raise PluginContextError("pack activator requires DaemonPluginContext")
        for item in rows:
            point = item.get("point")
            local_id = item.get("local_id")
            if point == "tool" and isinstance(local_id, str):
                ctx.register_tool(local_id, {"name": local_id})

    return activate


@dataclass(frozen=True, slots=True)
class PackTransition:
    """Journaled pack state change with CAS on ``roster_generation`` (RC-14)."""

    package_id: str
    from_state: str | None
    to_state: str
    roster_generation: int
    cas_token: str
    transitioned_at: str
    principal: str

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "cas_token": self.cas_token,
                "from_state": self.from_state,
                "package_id": self.package_id,
                "principal": self.principal,
                "roster_generation": self.roster_generation,
                "to_state": self.to_state,
                "transitioned_at": self.transitioned_at,
            }
        )


@dataclass(frozen=True, slots=True)
class PackMigrationRecord:
    """Prepare / commit / rollback migration with down or forward_only mode."""

    package_id: str
    from_version: str
    to_version: str
    mode: str
    phase: str
    outcome: str
    recovery: str | None = None

    def to_payload(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "from_version": self.from_version,
            "mode": self.mode,
            "outcome": self.outcome,
            "package_id": self.package_id,
            "phase": self.phase,
            "to_version": self.to_version,
        }
        if self.recovery is not None:
            body["recovery"] = self.recovery
        return MappingProxyType(body)


@dataclass(frozen=True, slots=True)
class ExportScanFinding:
    """Typed scanner finding. Unhandled findings fail the export closed."""

    threat_class: str
    path: str
    action: str

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {"action": self.action, "class": self.threat_class, "path": self.path}
        )


@dataclass(frozen=True, slots=True)
class ExportScanRewrite:
    """Secret value rewritten to a typed credential ref."""

    path: str
    from_hash: str
    to_ref: str
    to_hash: str

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "from_hash": self.from_hash,
                "path": self.path,
                "to_hash": self.to_hash,
                "to_ref": self.to_ref,
            }
        )


@dataclass(frozen=True, slots=True)
class ExportScanCoverage:
    """Scanner coverage. Incomplete coverage is fail-closed-fail."""

    files_scanned: int
    bytes_scanned: int
    complete: bool

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "bytes_scanned": self.bytes_scanned,
                "complete": self.complete,
                "files_scanned": self.files_scanned,
            }
        )


@dataclass(frozen=True, slots=True)
class ExportScanReport:
    """Independent versioned export oracle (SCN-0022 Then 3; FR-WF-65)."""

    report_version: int
    package_id: str
    package_version: str
    threat_model: Mapping[str, object]
    detectors: tuple[str, ...]
    coverage: ExportScanCoverage
    findings: tuple[ExportScanFinding, ...]
    rewrite_map: tuple[ExportScanRewrite, ...]
    post_rewrite_hash: Fingerprint
    post_rewrite_signature: str
    result: str

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "coverage": dict(self.coverage.to_payload()),
                "detectors": list(self.detectors),
                "findings": [dict(item.to_payload()) for item in self.findings],
                "package_id": self.package_id,
                "package_version": self.package_version,
                "post_rewrite_hash": self.post_rewrite_hash.value,
                "post_rewrite_signature": self.post_rewrite_signature,
                "report_version": self.report_version,
                "result": self.result,
                "rewrite_map": [dict(item.to_payload()) for item in self.rewrite_map],
                "threat_model": dict(self.threat_model),
            }
        )


@dataclass(frozen=True, slots=True)
class ExportBundle:
    """Rewritten export bytes plus the oracle that authorized them."""

    files: Mapping[str, str]
    report: ExportScanReport

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {"files": dict(self.files), "report": dict(self.report.to_payload())}
        )


@dataclass(frozen=True, slots=True)
class DoorParityReport:
    """Supported-door deep behaviour is identical for one ``op_id`` + version."""

    op_id: str
    version: int
    effect_class: str
    adapters: tuple[str, ...]

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "adapters": list(self.adapters),
                "effect_class": self.effect_class,
                "op_id": self.op_id,
                "version": self.version,
            }
        )


@dataclass
class PackRecord:
    """Fixture-owned pack row. Session-granted is not a field here."""

    package_id: str
    version: str
    state: str
    raw: dict[str, object]
    contributes: tuple[Mapping[str, object], ...]
    dependencies: tuple[str, ...]
    exports_secrets: bool
    exports_transcripts: bool
    files: dict[str, str]
    custom: bool


@dataclass
class AtomicRoster:
    """Stage, fsync, swap publication of the live pack roster (AD-30)."""

    root: Path
    live_name: str = "roster.json"

    @property
    def live_path(self) -> Path:
        return self.root / self.live_name

    @property
    def stage_path(self) -> Path:
        return self.root / f"{self.live_name}.stage"

    def publish(self, payload: Mapping[str, object]) -> Result[Path]:
        """Write staged bytes, fsync, then replace the live roster."""
        self.root.mkdir(parents=True, exist_ok=True)
        encoded = _dump(payload)
        staged = self.stage_path
        live = self.live_path
        try:
            with staged.open("wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(staged, live)
        except OSError as exc:
            return _policy(
                "roster",
                "atomic roster publication failed; last usable roster is unchanged",
                error=str(exc),
                branch="E",
            )
        try:
            dir_fd = os.open(str(self.root), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
        return Ok(live)

    def load(self) -> Result[Mapping[str, object]]:
        live = self.live_path
        if not live.is_file():
            return Ok(
                MappingProxyType(
                    {
                        "availability_revision": 0,
                        "packages": [],
                        "published": [],
                        "roster_generation": 0,
                    }
                )
            )
        try:
            loaded = json.loads(live.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return _invalid("roster", "live roster is unreadable", error=str(exc))
        if not isinstance(loaded, dict):
            return _invalid("roster", "live roster must be an object")
        return Ok(MappingProxyType(cast("dict[str, object]", loaded)))


def _file_bytes(body: str) -> int:
    return len(body.encode("utf-8"))


def _looks_transcript(path: str, body: str) -> bool:
    folded = f"{path}\n{body}".casefold()
    return any(marker in folded for marker in _TRANSCRIPT_MARKERS)


def _json_object(body: str) -> Mapping[str, object] | None:
    try:
        loaded = json.loads(body)
    except json.JSONDecodeError:
        return None
    if isinstance(loaded, dict):
        return cast("dict[str, object]", loaded)
    return None


def _rewrite_secrets(
    package_id: str,
    path: str,
    body: str,
) -> tuple[str, tuple[ExportScanFinding, ...], tuple[ExportScanRewrite, ...]]:
    findings: list[ExportScanFinding] = []
    rewrites: list[ExportScanRewrite] = []
    rewritten = body
    parsed = _json_object(body)
    if parsed is not None:
        changed = dict(parsed)
        dirty = False
        for key, value in parsed.items():
            if key.casefold() not in FORBIDDEN_SECRET_PAYLOAD_KEYS:
                continue
            if not isinstance(value, str):
                continue
            findings.append(
                ExportScanFinding(threat_class="secret_values", path=path, action="rewrite")
            )
            ref = f"cred:{package_id}:{path}:{key}"
            before = content_address({"path": path, "key": key, "value": value})
            after = content_address({"path": path, "key": key, "value": ref})
            if is_ok(before) and is_ok(after):
                rewrites.append(
                    ExportScanRewrite(
                        path=path,
                        from_hash=before.value.value,
                        to_ref=ref,
                        to_hash=after.value.value,
                    )
                )
            changed[key] = ref
            dirty = True
        if dirty:
            rewritten = json.dumps(changed, sort_keys=True, separators=(",", ":"))
        return rewritten, tuple(findings), tuple(rewrites)
    for match in _SECRET_INLINE.finditer(rewritten):
        token = match.group(2).strip("\"'")
        if token.startswith("cred:"):
            continue
        findings.append(
            ExportScanFinding(threat_class="secret_values", path=path, action="rewrite")
        )
        ref = f"cred:{package_id}:{path}"
        before = content_address({"path": path, "value": token})
        after = content_address({"path": path, "value": ref})
        if is_ok(before) and is_ok(after):
            rewrites.append(
                ExportScanRewrite(
                    path=path,
                    from_hash=before.value.value,
                    to_ref=ref,
                    to_hash=after.value.value,
                )
            )
        rewritten = rewritten.replace(match.group(2), ref, 1)
    return rewritten, tuple(findings), tuple(rewrites)


def scan_export_bundle(
    *,
    package_id: str,
    package_version: str,
    files: Mapping[str, str],
    complete: bool = True,
) -> Result[tuple[dict[str, str], ExportScanReport]]:
    """Independent scanner. Manifest flags are not consulted."""
    rewritten: dict[str, str] = {}
    findings: list[ExportScanFinding] = []
    rewrites: list[ExportScanRewrite] = []
    bytes_scanned = 0
    unhandled = False
    for path, body in files.items():
        if path.strip() == "":
            return _invalid("files", "export paths are non-empty relative strings")
        bytes_scanned += _file_bytes(body)
        private = bool(_PRIVATE_PATH.search(path) or _PRIVATE_PATH.search(body))
        transcript = _looks_transcript(path, body)
        blocked_secret = "BEGIN " in body and "PRIVATE KEY" in body
        cleaned, secret_findings, secret_rewrites = _rewrite_secrets(package_id, path, body)
        findings.extend(secret_findings)
        rewrites.extend(secret_rewrites)
        if blocked_secret:
            findings.append(
                ExportScanFinding(threat_class="secret_values", path=path, action="block")
            )
            unhandled = True
            rewritten[path] = body
            continue
        if private:
            findings.append(
                ExportScanFinding(threat_class="private_paths", path=path, action="drop")
            )
            continue
        if transcript:
            findings.append(ExportScanFinding(threat_class="transcripts", path=path, action="drop"))
            continue
        if _SECRET_INLINE.search(cleaned) and "cred:" not in cleaned:
            unhandled = True
        rewritten[path] = cleaned
    coverage = ExportScanCoverage(
        files_scanned=len(files) if complete else max(0, len(files) - 1),
        bytes_scanned=bytes_scanned,
        complete=complete,
    )
    hashed = content_address({"files": rewritten, "package_id": package_id})
    if is_refusal(hashed):
        return hashed
    signed = content_address(
        {
            "package_id": package_id,
            "package_version": package_version,
            "post_rewrite_hash": hashed.value.value,
        }
    )
    if is_refusal(signed):
        return signed
    handled_actions = {"rewrite", "drop"}
    unhandled = unhandled or any(item.action not in handled_actions for item in findings)
    result: ExportScanResult = (
        "fail-closed-fail" if (not coverage.complete) or unhandled else "fail-closed-pass"
    )
    report = ExportScanReport(
        report_version=1,
        package_id=package_id,
        package_version=package_version,
        threat_model={
            "classes": list(EXPORT_THREAT_CLASSES),
            "scope": "export-bundle",
        },
        detectors=EXPORT_SCAN_DETECTORS,
        coverage=coverage,
        findings=tuple(findings),
        rewrite_map=tuple(rewrites),
        post_rewrite_hash=hashed.value,
        post_rewrite_signature=f"sig:{signed.value.value}",
        result=result,
    )
    return Ok((rewritten, report))


@dataclass
class PackLifecycleFixture:
    """Atomic roster, export-scan oracle, door parity, pin honesty (SCN-0022)."""

    root: Path
    loader: PluginLoader = field(default_factory=PluginLoader)
    pins: ContributionPinService | None = None
    _packs: dict[str, PackRecord] = field(default_factory=dict[str, PackRecord], init=False)
    _transitions: list[PackTransition] = field(default_factory=list[PackTransition], init=False)
    _migrations: list[PackMigrationRecord] = field(
        default_factory=list[PackMigrationRecord], init=False
    )
    _generation: int = field(default=0, init=False)
    _issued_scan_signatures: set[str] = field(default_factory=set[str], init=False)
    _grant_ids: list[str] = field(default_factory=list[str], init=False)

    def __post_init__(self) -> None:
        if self.pins is None:
            self.pins = ContributionPinService(self.loader)
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def roster(self) -> AtomicRoster:
        return AtomicRoster(self.root)

    @property
    def roster_generation(self) -> int:
        return self._generation

    @property
    def sixth_store_minted(self) -> bool:
        return PACK_LIFECYCLE_SIXTH_STORE_MINTED

    @property
    def store(self) -> str:
        return PACK_LIFECYCLE_STORE

    @property
    def qma_operator_cli(self) -> bool:
        return QMA_OPERATOR_CLI

    @property
    def qmn_operator_cli(self) -> bool:
        return QMN_OPERATOR_CLI

    def transitions(self) -> tuple[PackTransition, ...]:
        return tuple(self._transitions)

    def migrations(self) -> tuple[PackMigrationRecord, ...]:
        return tuple(self._migrations)

    def pack(self, package_id: str) -> PackRecord | None:
        return self._packs.get(package_id)

    def grant_ids(self) -> tuple[str, ...]:
        """Session GrantRecord ids. Install/enable never append here (Story 60.1)."""
        return tuple(self._grant_ids)

    def composition_modes(self) -> tuple[str, ...]:
        return COMPOSITION_MODES

    def _pin_service(self) -> ContributionPinService:
        service = self.pins
        if service is None:
            service = ContributionPinService(self.loader)
            self.pins = service
        return service

    def _cas(self, expected_generation: object | None) -> Result[int]:
        if expected_generation is None:
            return Ok(self._generation)
        parsed = _require_int("roster_generation", expected_generation, minimum=0)
        if is_refusal(parsed):
            return parsed
        if parsed.value != self._generation:
            return _policy(
                "roster_generation",
                "PackTransition CAS lost; last usable roster is unchanged",
                expected=parsed.value,
                current=self._generation,
                branch="E",
            )
        return Ok(self._generation)

    def _append_transition(
        self,
        *,
        package_id: str,
        from_state: str | None,
        to_state: str,
        transitioned_at: str,
        principal: str,
    ) -> Result[PackTransition]:
        edge = (from_state, to_state)
        if edge not in LEGAL_PACK_TRANSITIONS:
            return _invalid(
                "to_state",
                "illegal pack lifecycle transition",
                from_state=from_state,
                to_state=to_state,
            )
        if to_state == "session-granted":
            return _policy(
                "to_state",
                "session-granted is AD-8, not a pack state (DEC-0443)",
            )
        self._generation += 1
        row = PackTransition(
            package_id=package_id,
            from_state=from_state,
            to_state=to_state,
            roster_generation=self._generation,
            cas_token=f"roster:{self._generation}",
            transitioned_at=transitioned_at,
            principal=principal,
        )
        self._transitions.append(row)
        journal = self.root / "pack_transitions.jsonl"
        try:
            with journal.open("ab") as handle:
                handle.write(_dump(row.to_payload()) + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            self._transitions.pop()
            self._generation -= 1
            return _policy("journal", "pack transition journal fsync failed", error=str(exc))
        return Ok(row)

    def _snapshot_loader(
        self,
    ) -> tuple[tuple[PublishedContribution, ...], int, tuple[str, ...]]:
        published, revision = self.loader.snapshot_published_roster()
        return published, revision, self.loader.loaded_ids()

    def _publish_roster(self) -> Result[Path]:
        packages = [
            {
                "dependencies": list(row.dependencies),
                "exports_secrets": row.exports_secrets,
                "package_id": row.package_id,
                "state": row.state,
                "version": row.version,
            }
            for row in self._packs.values()
            if row.state != "uninstalled"
        ]
        payload = {
            "availability_revision": self.loader.availability_revision(),
            "packages": packages,
            "published": [
                dict(item.to_payload()) for item in self.loader.published_contributions()
            ],
            "roster_generation": self._generation,
        }
        return self.roster.publish(payload)

    def _parse_at(self, transitioned_at: object) -> Result[str]:
        stamped = parse_utc_iso_z("transitioned_at", transitioned_at)
        if is_refusal(stamped):
            return stamped
        return Ok(stamped.value[1])

    def _principal(self, principal: object) -> Result[str]:
        if principal is None:
            return Ok(PrincipalClass.OPERATOR.value)
        token = _require_str("principal", principal)
        if is_refusal(token):
            return token
        return Ok(token.value)

    def download(
        self,
        raw: Mapping[str, object],
        *,
        files: Mapping[str, str] | None = None,
        custom: bool = False,
        transitioned_at: object,
        principal: object = "operator",
        expected_generation: object | None = None,
    ) -> Result[PackTransition]:
        cas = self._cas(expected_generation)
        if is_refusal(cas):
            return cas
        package_id = _require_str("package_id", raw.get("id") or raw.get("package_id"))
        if is_refusal(package_id):
            return package_id
        version = _require_str("version", raw.get("version"))
        if is_refusal(version):
            return version
        stamped = self._parse_at(transitioned_at)
        if is_refusal(stamped):
            return stamped
        actor = self._principal(principal)
        if is_refusal(actor):
            return actor
        contributes_raw = raw.get("contributes", raw.get("contributions", ()))
        contribs: list[Mapping[str, object]] = []
        if isinstance(contributes_raw, Sequence) and not isinstance(contributes_raw, (str, bytes)):
            for item in cast("Sequence[object]", contributes_raw):
                if isinstance(item, Mapping):
                    contribs.append(dict(cast("Mapping[str, object]", item)))
        deps_raw = raw.get("dependencies", ())
        deps: tuple[str, ...]
        if isinstance(deps_raw, Sequence) and not isinstance(deps_raw, (str, bytes)):
            deps = tuple(str(item) for item in cast("Sequence[object]", deps_raw))
        else:
            deps = ()
        exports_secrets = raw.get("exports_secrets", False)
        if not isinstance(exports_secrets, bool):
            return _invalid("exports_secrets", "exports_secrets is a boolean request")
        self._packs[package_id.value] = PackRecord(
            package_id=package_id.value,
            version=version.value,
            state="downloaded",
            raw=dict(raw),
            contributes=tuple(contribs),
            dependencies=deps,
            exports_secrets=exports_secrets,
            exports_transcripts=bool(raw.get("exports_transcripts", False)),
            files=dict(files or {}),
            custom=custom,
        )
        return self._append_transition(
            package_id=package_id.value,
            from_state=None,
            to_state="downloaded",
            transitioned_at=stamped.value,
            principal=actor.value,
        )

    def _advance(
        self,
        package_id: object,
        *,
        to_state: PackState,
        transitioned_at: object,
        principal: object,
        expected_generation: object | None,
    ) -> Result[PackTransition]:
        cas = self._cas(expected_generation)
        if is_refusal(cas):
            return cas
        ident = _require_str("package_id", package_id)
        if is_refusal(ident):
            return ident
        pack = self._packs.get(ident.value)
        if pack is None:
            return _invalid("package_id", "pack is not downloaded", given=ident.value)
        stamped = self._parse_at(transitioned_at)
        if is_refusal(stamped):
            return stamped
        actor = self._principal(principal)
        if is_refusal(actor):
            return actor
        moved = self._append_transition(
            package_id=ident.value,
            from_state=pack.state,
            to_state=to_state,
            transitioned_at=stamped.value,
            principal=actor.value,
        )
        if is_refusal(moved):
            return moved
        pack.state = to_state
        return moved

    def install(
        self,
        package_id: object,
        *,
        transitioned_at: object,
        principal: object = "operator",
        expected_generation: object | None = None,
        fail: bool = False,
    ) -> Result[PackTransition]:
        if fail:
            cas = self._cas(expected_generation)
            if is_refusal(cas):
                return cas
            return _policy(
                "install",
                "partial install rolls back to the last usable roster",
                branch="E",
                last_usable_generation=self._generation,
            )
        return self._advance(
            package_id,
            to_state="installed",
            transitioned_at=transitioned_at,
            principal=principal,
            expected_generation=expected_generation,
        )

    def validate(
        self,
        package_id: object,
        *,
        transitioned_at: object,
        principal: object = "operator",
        expected_generation: object | None = None,
        fail: bool = False,
    ) -> Result[PackTransition]:
        if fail:
            cas = self._cas(expected_generation)
            if is_refusal(cas):
                return cas
            return _policy(
                "validate",
                "failed validation restores the last usable roster",
                branch="E",
                last_usable_generation=self._generation,
            )
        return self._advance(
            package_id,
            to_state="validated",
            transitioned_at=transitioned_at,
            principal=principal,
            expected_generation=expected_generation,
        )

    def enable(
        self,
        package_id: object,
        *,
        transitioned_at: object,
        principal: object = "operator",
        expected_generation: object | None = None,
        activator: PluginActivator | None = None,
        warn_and_continue: bool = False,
        operator_enable: bool = True,
    ) -> Result[PackTransition]:
        cas = self._cas(expected_generation)
        if is_refusal(cas):
            return cas
        ident = _require_str("package_id", package_id)
        if is_refusal(ident):
            return ident
        pack = self._packs.get(ident.value)
        if pack is None:
            return _invalid("package_id", "pack is not present", given=ident.value)
        if (pack.state, "enabled") not in LEGAL_PACK_TRANSITIONS:
            return _invalid(
                "to_state",
                "illegal pack lifecycle transition",
                from_state=pack.state,
                to_state="enabled",
            )
        if warn_and_continue or MISSING_DEP_WARN_AND_CONTINUE:
            return _policy(
                "dependencies",
                "missing dependency is a hard error at enable, not warning-and-continue",
                branch="A",
                warn_and_continue=False,
                hermes_advisory=False,
            )
        if pack.custom and not operator_enable:
            return _policy(
                "enable",
                "custom packs are explicit operator enable (DEC-0431)",
                package_id=ident.value,
            )
        missing = [dep for dep in pack.dependencies if dep not in self.loader.loaded_ids()]
        if missing:
            return _policy(
                "dependencies",
                "missing dependency is a hard error at enable, not warning-and-continue",
                branch="A",
                missing=missing,
                package_id=ident.value,
                warn_and_continue=False,
                hermes_advisory=False,
                last_usable_generation=self._generation,
            )
        stamped = self._parse_at(transitioned_at)
        if is_refusal(stamped):
            return stamped
        actor = self._principal(principal)
        if is_refusal(actor):
            return actor
        snapshot = self._snapshot_loader()
        act = activator if activator is not None else _default_activator(pack.contributes)
        loaded = self.loader.enable(pack.raw, activator=act, principal=actor.value)
        if is_refusal(loaded):
            self.loader.restore_published_roster((snapshot[0], snapshot[1]))
            extra = dict(loaded.context)
            extra["branch"] = extra.get(
                "branch", "A" if extra.get("field") == "dependencies" else "E"
            )
            extra["warn_and_continue"] = False
            extra["last_usable_generation"] = self._generation
            return TypedRefusal(
                category=loaded.category,
                retryability=loaded.retryability,
                context=MappingProxyType(extra),
            )
        moved = self._append_transition(
            package_id=ident.value,
            from_state=pack.state,
            to_state="enabled",
            transitioned_at=stamped.value,
            principal=actor.value,
        )
        if is_refusal(moved):
            self.loader.unload(ident.value)
            self.loader.restore_published_roster((snapshot[0], snapshot[1]))
            return moved
        pack.state = "enabled"
        published = self._publish_roster()
        if is_refusal(published):
            pack.state = moved.value.from_state or pack.state
            self._transitions.pop()
            self._generation -= 1
            self.loader.unload(ident.value)
            self.loader.restore_published_roster((snapshot[0], snapshot[1]))
            return published
        return moved

    def disable(
        self,
        package_id: object,
        *,
        transitioned_at: object,
        principal: object = "operator",
        expected_generation: object | None = None,
    ) -> Result[PackTransition]:
        cas = self._cas(expected_generation)
        if is_refusal(cas):
            return cas
        ident = _require_str("package_id", package_id)
        if is_refusal(ident):
            return ident
        pack = self._packs.get(ident.value)
        if pack is None:
            return _invalid("package_id", "pack is not present", given=ident.value)
        if (pack.state, "disabled") not in LEGAL_PACK_TRANSITIONS:
            return _invalid(
                "to_state",
                "illegal pack lifecycle transition",
                from_state=pack.state,
                to_state="disabled",
            )
        stamped = self._parse_at(transitioned_at)
        if is_refusal(stamped):
            return stamped
        actor = self._principal(principal)
        if is_refusal(actor):
            return actor
        departed = self._pin_service().disable(ident.value, principal=actor.value)
        if is_refusal(departed):
            return departed
        moved = self._append_transition(
            package_id=ident.value,
            from_state=pack.state,
            to_state="disabled",
            transitioned_at=stamped.value,
            principal=actor.value,
        )
        if is_refusal(moved):
            return moved
        pack.state = "disabled"
        published = self._publish_roster()
        if is_refusal(published):
            return published
        return moved

    def uninstall(
        self,
        package_id: object,
        *,
        transitioned_at: object,
        principal: object = "operator",
        expected_generation: object | None = None,
    ) -> Result[tuple[PackTransition, PackDepartureReceipt]]:
        cas = self._cas(expected_generation)
        if is_refusal(cas):
            return cas
        ident = _require_str("package_id", package_id)
        if is_refusal(ident):
            return ident
        pack = self._packs.get(ident.value)
        if pack is None:
            return _invalid("package_id", "pack is not present", given=ident.value)
        if pack.state != "disabled":
            return _invalid(
                "from_state",
                "uninstall is from disabled; enabled packs disable first",
                from_state=pack.state,
            )
        stamped = self._parse_at(transitioned_at)
        if is_refusal(stamped):
            return stamped
        actor = self._principal(principal)
        if is_refusal(actor):
            return actor
        departed = self._pin_service().uninstall(ident.value, principal=actor.value)
        if is_refusal(departed):
            return departed
        moved = self._append_transition(
            package_id=ident.value,
            from_state=pack.state,
            to_state="uninstalled",
            transitioned_at=stamped.value,
            principal=actor.value,
        )
        if is_refusal(moved):
            return moved
        pack.state = "uninstalled"
        published = self._publish_roster()
        if is_refusal(published):
            return published
        return Ok((moved.value, departed.value))

    def migrate(
        self,
        package_id: object,
        *,
        from_version: object,
        to_version: object,
        mode: object,
        phase: object,
        operator_confirmed: bool = False,
        fail: bool = False,
        expected_generation: object | None = None,
    ) -> Result[PackMigrationRecord]:
        cas = self._cas(expected_generation)
        if is_refusal(cas):
            return cas
        ident = _require_str("package_id", package_id)
        if is_refusal(ident):
            return ident
        pack = self._packs.get(ident.value)
        if pack is None:
            return _invalid("package_id", "pack is not present", given=ident.value)
        src = _require_str("from_version", from_version)
        if is_refusal(src):
            return src
        dest = _require_str("to_version", to_version)
        if is_refusal(dest):
            return dest
        mode_token = _require_str("mode", mode)
        if is_refusal(mode_token):
            return mode_token
        if mode_token.value not in MIGRATION_MODES:
            return _invalid("mode", "mode is down | forward_only", given=mode_token.value)
        phase_token = _require_str("phase", phase)
        if is_refusal(phase_token):
            return phase_token
        if phase_token.value not in MIGRATION_PHASES:
            return _invalid(
                "phase", "phase is prepare | commit | rollback", given=phase_token.value
            )
        if mode_token.value == "forward_only" and not operator_confirmed:
            return _policy(
                "forward_only",
                "forward_only recovery requires operator confirmation (RC-14)",
                package_id=ident.value,
            )
        if fail and phase_token.value in {"prepare", "commit"}:
            recovery = "forward_only" if mode_token.value == "forward_only" else None
            record = PackMigrationRecord(
                package_id=ident.value,
                from_version=src.value,
                to_version=dest.value,
                mode=mode_token.value,
                phase=phase_token.value,
                outcome="failed",
                recovery=recovery,
            )
            self._migrations.append(record)
            return _policy(
                "migrations",
                "failed prepare/commit restores the last usable roster",
                branch="E",
                last_usable_generation=self._generation,
                recovery=recovery,
                report=dict(record.to_payload()),
            )
        record = PackMigrationRecord(
            package_id=ident.value,
            from_version=src.value,
            to_version=dest.value,
            mode=mode_token.value,
            phase=phase_token.value,
            outcome="ok",
            recovery="forward_only" if mode_token.value == "forward_only" else None,
        )
        self._migrations.append(record)
        if phase_token.value == "commit" and not fail:
            pack.version = dest.value
            pack.raw["version"] = dest.value
        return Ok(record)

    def scan(
        self,
        package_id: object,
        files: Mapping[str, str] | None = None,
        *,
        complete: bool = True,
    ) -> Result[ExportScanReport]:
        ident = _require_str("package_id", package_id)
        if is_refusal(ident):
            return ident
        pack = self._packs.get(ident.value)
        if pack is None:
            return _invalid("package_id", "pack is not present", given=ident.value)
        bundle = files if files is not None else pack.files
        scanned = scan_export_bundle(
            package_id=ident.value,
            package_version=pack.version,
            files=bundle,
            complete=complete,
        )
        if is_refusal(scanned):
            return scanned
        _rewritten, report = scanned.value
        self._issued_scan_signatures.add(report.post_rewrite_signature)
        return Ok(report)

    def export(
        self,
        package_id: object,
        files: Mapping[str, str] | None = None,
        *,
        trust_manifest: bool = False,
        complete: bool = True,
        report: ExportScanReport | None = None,
    ) -> Result[ExportBundle]:
        """Export is authorized only by a passing independent scan."""
        ident = _require_str("package_id", package_id)
        if is_refusal(ident):
            return ident
        pack = self._packs.get(ident.value)
        if pack is None:
            return _invalid("package_id", "pack is not present", given=ident.value)
        if trust_manifest or EXPORTS_SECRETS_AUTHORIZES_EXPORT:
            return _policy(
                "exports_secrets",
                "manifest exports_secrets: false is not evidence; scanner is the oracle",
                branch="B",
                exports_secrets=pack.exports_secrets,
                scanner_is_oracle=True,
            )
        if report is not None:
            if report.post_rewrite_signature not in self._issued_scan_signatures:
                return _policy(
                    "export_scan",
                    "self-asserted ExportScanReport cannot authorize export",
                    branch="B",
                    scanner_is_oracle=True,
                )
            if report.result != "fail-closed-pass":
                return _policy(
                    "export_scan",
                    "incomplete coverage or unhandled finding is fail-closed-fail",
                    branch="C",
                    result=report.result,
                )
            bundle = files if files is not None else pack.files
            scanned = scan_export_bundle(
                package_id=ident.value,
                package_version=pack.version,
                files=bundle,
                complete=True,
            )
            if is_refusal(scanned):
                return scanned
            rewritten, replayed = scanned.value
            if replayed.post_rewrite_hash.value != report.post_rewrite_hash.value:
                return _policy(
                    "export_scan",
                    "presented scan does not match the independent scanner",
                    branch="B",
                )
            return Ok(ExportBundle(files=MappingProxyType(rewritten), report=report))
        bundle = files if files is not None else pack.files
        scanned = scan_export_bundle(
            package_id=ident.value,
            package_version=pack.version,
            files=bundle,
            complete=complete,
        )
        if is_refusal(scanned):
            return scanned
        rewritten, produced = scanned.value
        self._issued_scan_signatures.add(produced.post_rewrite_signature)
        if produced.result != "fail-closed-pass":
            return _policy(
                "export_scan",
                "incomplete coverage or unhandled finding is fail-closed-fail",
                branch="C",
                result=produced.result,
                findings=[dict(item.to_payload()) for item in produced.findings],
                coverage=dict(produced.coverage.to_payload()),
            )
        return Ok(ExportBundle(files=MappingProxyType(rewritten), report=produced))

    def live_hit(self, package_id: str) -> Result[ContributionHit]:
        rows = [
            row
            for row in self.loader.published_contributions()
            if row.plugin_id == package_id and row.qualified_id
        ]
        if not rows:
            return _invalid(
                "package_id", "no published contribution for pack", package_id=package_id
            )
        row = rows[0]
        return ContributionHit.try_create(
            plugin_id=row.plugin_id,
            point=row.point,
            qualified_id=row.qualified_id,
            package_id=row.package_id,
            package_version=row.package_version,
            availability_revision=row.availability_revision,
            availability=row.availability,
        )

    def pin(self, package_id: str) -> Result[ContributionPin]:
        hit = self.live_hit(package_id)
        if is_refusal(hit):
            return hit
        return self._pin_service().pin(hit.value)

    def invoke_pin(self, pin: ContributionPin) -> Result[PinInvokeAdmission]:
        return self._pin_service().invoke(pin)

    def invoke_door(
        self,
        *,
        op_id: str,
        version: int,
        adapter: object,
        door: str | None = None,
    ) -> Result[SupportedDoor]:
        """Admit one door. Unsupported → typed unsupported_door (FR-WF-26)."""
        adapter_token = adapter if isinstance(adapter, str) else str(adapter)
        if adapter_token in FORBIDDEN_OPERATOR_CLI_ADAPTERS:
            return UnsupportedDoor.of(
                op_id=op_id,
                version=version,
                adapter=adapter_token,
                door=door,
            )
        return admit_operation_door(
            public_operation_descriptors(),
            op_id=op_id,
            version=version,
            adapter=adapter,
            door=door,
        )

    def mint_operator_cli(self, owner: object) -> TypedRefusal:
        return _policy(
            "adapter",
            "unsupported door is typed unsupported_door; never mint a qma/qmn CLI",
            branch="D",
            owner=owner,
            qma_operator_cli=False,
            qmn_operator_cli=False,
            operator_cli="qmb",
        )

    def supported_door_parity(
        self,
        *,
        op_id: str,
        version: int,
    ) -> Result[DoorParityReport]:
        descriptor = descriptor_for(public_operation_descriptors(), op_id=op_id, version=version)
        if descriptor is None:
            return _invalid("op_id", "no published descriptor for op_id+version")
        adapters: list[str] = []
        for supported in descriptor.supported_doors:
            admitted = admit_operation_door(
                public_operation_descriptors(),
                op_id=op_id,
                version=version,
                adapter=supported.adapter,
                door=supported.door,
            )
            if is_refusal(admitted):
                return admitted
            if admitted.value.adapter is not supported.adapter:
                return _policy(
                    "supported_doors",
                    "supported-door behaviour must be identical across doors",
                    op_id=op_id,
                    version=version,
                )
            adapters.append(supported.adapter.value)
        return Ok(
            DoorParityReport(
                op_id=descriptor.op_id,
                version=descriptor.version,
                effect_class=descriptor.effect_class.value,
                adapters=tuple(adapters),
            )
        )

    def assert_store_closed(self) -> bool:
        return (
            PACK_LIFECYCLE_STORE in DEFINITION_STORE_MEMBERS
            and PACK_LIFECYCLE_STORE in CLOSED_STORE_NAMES
            and "pack_lifecycle" not in CLOSED_STORE_NAMES
            and not PACK_LIFECYCLE_SIXTH_STORE_MINTED
        )
