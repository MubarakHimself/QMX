"""GrantRecord rows beside product_session (Story 55.2).

``product_session.granted_ops`` stores grant_ids. The host resolves
GrantRecord from the ledger on the existing daemon sqlite (not a new store
class). Envelope grant_id / op / effect / contribution / instance that do
not match the bound GrantRecord are GRANT_MISMATCH before execution.
Revoke or expiry: already-accepted work may finish; new dispatch is
refused. Upgrade cannot widen or retarget without an explicit re-grant
that bumps context_revision. Manifests request; the host grants.
Does not rewrite Story 44.3 Tool Registry.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qma.core.refusals.variants import GrantMismatch
from qma.core.vocabulary.enums import GrantEvaluationMoment
from qma.daemon.persistence.sqlite_writer import SingleSqliteWriter
from qma.wire.grant_record import (
    GRANT_ID_PREFIX,
    GrantRecord,
    GrantRevocation,
    parse_grant_record,
    parse_grant_revocation,
)
from qma.wire.invocation_envelope import (
    BoundInvocation,
    InvocationEnvelope,
    PublicCallTransport,
    parse_invocation_envelope,
)
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal
from qmf.data.store.refusals import invalid_input, storage_failure

__all__ = [
    "GRANT_ACCEPTED_TABLE",
    "GRANT_RECORD_TABLE",
    "GRANT_REVOCATION_TABLE",
    "GRANT_SIXTH_STORE_MINTED",
    "TOOL_REGISTRY_REWRITTEN",
    "BoundSessionGrant",
    "GrantSqliteStore",
    "compare_envelope_to_grant",
    "moment_for_transport",
]


GRANT_RECORD_TABLE: Final[str] = "grant_record"
GRANT_REVOCATION_TABLE: Final[str] = "grant_revocation"
GRANT_ACCEPTED_TABLE: Final[str] = "grant_accepted"
GRANT_SIXTH_STORE_MINTED: Final[bool] = False
TOOL_REGISTRY_REWRITTEN: Final[bool] = False
_SCHEMA_SQL: Final[str] = """
CREATE TABLE IF NOT EXISTS grant_record (
    grant_id TEXT PRIMARY KEY NOT NULL,
    payload TEXT NOT NULL,
    journal_seq INTEGER NOT NULL,
    recorded_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS grant_revocation (
    journal_seq INTEGER PRIMARY KEY NOT NULL,
    grant_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    recorded_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS grant_accepted (
    logical_invocation_id TEXT PRIMARY KEY NOT NULL,
    grant_id TEXT NOT NULL
);
"""


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    return invalid_input(field, reason, **extra)


def _dump(payload: Mapping[str, object]) -> str:
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))


def _load_object(raw: object, *, field: str) -> Result[dict[str, object]]:
    if not isinstance(raw, str):
        return storage_failure(
            f"{field} sqlite payload is not JSON text",
            context={"field": field},
        )
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return storage_failure(
            f"{field} sqlite payload is not JSON: {exc}",
            context={"field": field},
        )
    if not isinstance(parsed, dict):
        return _invalid(field, f"{field} sqlite payload is a JSON object")
    return Ok(cast("dict[str, object]", parsed))


def moment_for_transport(transport: object) -> GrantEvaluationMoment:
    """Nested public calls evaluate at nested_call; others at dispatch."""
    if transport is PublicCallTransport.NESTED or transport == PublicCallTransport.NESTED.value:
        return GrantEvaluationMoment.NESTED_CALL
    return GrantEvaluationMoment.DISPATCH


def compare_envelope_to_grant(
    envelope: object,
    grant: GrantRecord,
) -> Result[GrantRecord]:
    """Envelope grant_id / op / effect / contribution / instance vs GrantRecord.

    Mismatch is GRANT_MISMATCH before execution (Story 55.2; FR-WF-18).
    """
    parsed = parse_invocation_envelope(envelope)
    if is_refusal(parsed):
        return parsed
    env = parsed.value
    if grant.grant_id != env.grant_id:
        return GrantMismatch.of(field="grant_id", grant_id=env.grant_id)
    if grant.op_id != env.op_id:
        return GrantMismatch.of(
            field="op_id",
            grant_id=env.grant_id,
            bound=env.op_id,
            granted=grant.op_id,
        )
    if grant.op_version != env.op_version:
        return GrantMismatch.of(
            field="op_version",
            grant_id=env.grant_id,
            bound=env.op_version,
            granted=grant.op_version,
        )
    if grant.effect_class is not env.effect_class:
        return GrantMismatch.of(
            field="effect_class",
            grant_id=env.grant_id,
            bound=env.effect_class.value,
            granted=grant.effect_class.value,
        )
    if grant.contribution.as_tuple() != env.contribution.as_tuple():
        return GrantMismatch.of(
            field="contribution",
            grant_id=env.grant_id,
            bound=list(env.contribution.as_tuple()),
            granted=list(grant.contribution.as_tuple()),
        )
    if grant.instance_id != env.instance_id:
        return GrantMismatch.of(
            field="instance_id",
            grant_id=env.grant_id,
            bound=env.instance_id,
            granted=grant.instance_id,
        )
    if grant.config_revision != env.config_revision:
        return GrantMismatch.of(
            field="config_revision",
            grant_id=env.grant_id,
            bound=env.config_revision,
            granted=grant.config_revision,
        )
    return Ok(grant)


@dataclass(frozen=True, slots=True)
class BoundSessionGrant:
    """Session-resolved GrantRecord compared to the envelope. Not authority."""

    grant: GrantRecord
    envelope: InvocationEnvelope
    grant_ids: tuple[str, ...]
    invocation: BoundInvocation | None = None
    is_authority: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "grant_ids", tuple(self.grant_ids))
        object.__setattr__(self, "is_authority", False)

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "envelope": dict(self.envelope.to_payload()),
            "grant": dict(self.grant.to_payload()),
            "granted_ops": list(self.grant_ids),
            "is_authority": False,
        }
        if self.invocation is not None:
            payload["transport"] = self.invocation.transport.value
        return MappingProxyType(payload)


class GrantSqliteStore:
    """GrantRecord / GrantRevocation fold materialization on daemon sqlite."""

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

    def put_grant(self, record: GrantRecord, *, journal_seq: int, recorded_at: int) -> None:
        self.ensure_schema()
        self._sqlite.execute(
            "INSERT OR REPLACE INTO grant_record "
            "(grant_id, payload, journal_seq, recorded_at) VALUES (?, ?, ?, ?)",
            (record.grant_id, _dump(record.to_payload()), journal_seq, recorded_at),
        )

    def list_grants(self) -> Result[tuple[GrantRecord, ...]]:
        self.ensure_schema()
        rows = self._sqlite.execute("SELECT payload FROM grant_record ORDER BY journal_seq ASC")
        collected: list[GrantRecord] = []
        for row in rows:
            loaded = _load_object(row[0], field="grant_record")
            if is_refusal(loaded):
                return loaded
            parsed = parse_grant_record(loaded.value)
            if is_refusal(parsed):
                return parsed
            collected.append(parsed.value)
        return Ok(tuple(collected))

    def append_revocation(
        self,
        revocation: GrantRevocation,
        *,
        journal_seq: int,
        recorded_at: int,
    ) -> None:
        self.ensure_schema()
        self._sqlite.execute(
            "INSERT OR REPLACE INTO grant_revocation "
            "(journal_seq, grant_id, payload, recorded_at) VALUES (?, ?, ?, ?)",
            (
                journal_seq,
                revocation.grant_id,
                _dump(revocation.to_payload()),
                recorded_at,
            ),
        )

    def list_revocations(self) -> Result[tuple[GrantRevocation, ...]]:
        self.ensure_schema()
        rows = self._sqlite.execute("SELECT payload FROM grant_revocation ORDER BY journal_seq ASC")
        collected: list[GrantRevocation] = []
        for row in rows:
            loaded = _load_object(row[0], field="grant_revocation")
            if is_refusal(loaded):
                return loaded
            parsed = parse_grant_revocation(loaded.value)
            if is_refusal(parsed):
                return parsed
            collected.append(parsed.value)
        return Ok(tuple(collected))

    def put_accepted(self, *, logical_invocation_id: str, grant_id: str) -> None:
        self.ensure_schema()
        self._sqlite.execute(
            "INSERT OR REPLACE INTO grant_accepted (logical_invocation_id, grant_id) VALUES (?, ?)",
            (logical_invocation_id, grant_id),
        )

    def list_accepted(self) -> Result[tuple[tuple[str, str], ...]]:
        self.ensure_schema()
        rows = self._sqlite.execute("SELECT logical_invocation_id, grant_id FROM grant_accepted")
        collected: list[tuple[str, str]] = []
        for row in rows:
            invocation = row[0]
            grant_id = row[1]
            if not isinstance(invocation, str) or not isinstance(grant_id, str):
                return storage_failure(
                    "grant_accepted sqlite row is not text",
                    context={"field": "grant_accepted"},
                )
            if not grant_id.startswith(GRANT_ID_PREFIX):
                return invalid_input(
                    "granted_ops",
                    "granted_ops stores grant_ids, not bare op-id strings (FR-WF-30)",
                    given=grant_id,
                )
            collected.append((invocation, grant_id))
        return Ok(tuple(collected))


def require_session_grant_id(
    granted_ops: Sequence[str],
    grant_id: object,
) -> Result[str]:
    """grant_id must be a session-granted grant: token, never a bare op-id."""
    if not isinstance(grant_id, str) or grant_id.strip() == "":
        return invalid_input(
            "grant_id",
            "grant_id is a grant: token, never a bare op-id string",
            given=repr(grant_id),
        )
    token = grant_id.strip()
    if not token.startswith(GRANT_ID_PREFIX) or token == GRANT_ID_PREFIX:
        return invalid_input(
            "grant_id",
            "granted_ops stores grant_ids, not bare op-id strings (FR-WF-30)",
            given=token,
            granted_ops_store_grant_ids=True,
            granted_ops_store_bare_op_ids=False,
        )
    if token not in granted_ops:
        return GrantMismatch.of(
            field="grant_id",
            grant_id=token,
            live=False,
            session_granted=False,
        )
    return Ok(token)
