"""Exactly one terminal ledger record per replay job (Story 27.8 / E15-F01).

Replay jobs are admitted through the QMB orchestration seam (process-per-job,
cancel token, per-run limits, WriterId-scoped JSONL append-with-fsync). The
diagnostic diff stays ungoverned; this module ledgers the JOB outcome only.
A second differing terminal line is refused and never overwritten. Crash
recovery scans the run directory and the writer stream and appends the missing
line idempotently, or surfaces a storage failure requiring review.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, Literal, cast

from qmb.orchestrator.paths import (
    MAX_JSONL_BYTES,
    append_bytes_no_follow,
    read_contained_bytes,
    write_bytes_exclusive_no_follow,
)
from qmf.core import (
    Fingerprint,
    Ok,
    Result,
    TypedRefusal,
    World,
    WriterId,
    canonical_bytes,
    fingerprint,
    governed_namespace,
    is_ok,
    is_refusal,
)

from qmn.replay._refuse import clean_token, invalid, policy, storage
from qmn.replay.port import REPLAY_IMPORT_PORT
from qmn.replay.session import ReplayJobSpec, allocate_replay_writer

__all__ = [
    "FRAGMENT_FILENAME",
    "INTENT_NAME",
    "NEVER_REWRITE",
    "ONE_TERMINAL_PER_JOB",
    "OUTPUT_NAME",
    "REPLAY_LEDGER_ROLE",
    "REPLAY_TERMINAL_CLASS",
    "SPEC_NAME",
    "TERMINAL_ABORT",
    "TERMINAL_BOUND",
    "TERMINAL_CANCEL",
    "TERMINAL_COMPLETE",
    "TERMINAL_REFUSE",
    "TERMINAL_STATUSES",
    "TERMINAL_TEARDOWN",
    "TRANSACTION_BOUNDARY",
    "WRITER_NAME",
    "ReplayLedgerSink",
    "ReplayTerminalRecord",
    "mint_data_fingerprint",
    "mint_run_fingerprint",
    "read_intent",
    "read_writer_manifest",
    "write_intent",
]

TERMINAL_COMPLETE: Final[str] = "complete"
TERMINAL_REFUSE: Final[str] = "refuse"
TERMINAL_ABORT: Final[str] = "abort"
TERMINAL_CANCEL: Final[str] = "cancel"
TERMINAL_BOUND: Final[str] = "bound"
TERMINAL_TEARDOWN: Final[str] = "teardown"
TERMINAL_STATUSES: Final[tuple[str, ...]] = (
    TERMINAL_COMPLETE,
    TERMINAL_REFUSE,
    TERMINAL_ABORT,
    TERMINAL_CANCEL,
    TERMINAL_BOUND,
    TERMINAL_TEARDOWN,
)
TerminalStatus = Literal[
    "complete",
    "refuse",
    "abort",
    "cancel",
    "bound",
    "teardown",
]

REPLAY_TERMINAL_CLASS: Final[str] = "qmn-replay-terminal-line"
REPLAY_TERMINAL_FORMAT_VERSION: Final[int] = 1
REPLAY_JOB_CLASS: Final[str] = "qmn-replay-job"
REPLAY_INTERVAL_CLASS: Final[str] = "qmn-replay-sealed-interval"
REPLAY_LEDGER_ROLE: Final[str] = "replay-ledger"
FRAGMENT_FILENAME: Final[str] = "ledger.jsonl"
SPEC_NAME: Final[str] = "spec.json"
WRITER_NAME: Final[str] = "writer.json"
OUTPUT_NAME: Final[str] = "diff.json"
INTENT_NAME: Final[str] = "terminal-intent.json"
ONE_TERMINAL_PER_JOB: Final[bool] = True
NEVER_REWRITE: Final[bool] = True
TRANSACTION_BOUNDARY: Final[str] = "ordered-with-recovery"

_COLLISION_ID: Final[str] = "replay.ledger.collision"
_REWRITE_ID: Final[str] = "replay.ledger.rewrite"
_STORAGE_ID: Final[str] = "replay.ledger.storage"


@dataclass(frozen=True, slots=True)
class ReplayTerminalRecord:
    """One durable terminal line for one replay job. Never a stored verdict."""

    run_fp: Fingerprint
    config_fp: str
    data_fp: Fingerprint
    composition_fp: str
    interval: Mapping[str, int]
    status: str
    start_ns: int
    end_ns: int
    output_refs: Mapping[str, object]
    world: World = World.REPLAY
    refusal: Mapping[str, object] | None = None
    failure: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "interval", MappingProxyType(dict(self.interval)))
        object.__setattr__(self, "output_refs", MappingProxyType(dict(self.output_refs)))
        if self.refusal is not None:
            object.__setattr__(self, "refusal", MappingProxyType(dict(self.refusal)))
        if self.failure is not None:
            object.__setattr__(self, "failure", MappingProxyType(dict(self.failure)))

    def fp1_identity(self) -> dict[str, object]:
        """Identity-bearing fields. Job wall instants stay occurrence provenance."""
        content: dict[str, object] = {
            "class": REPLAY_TERMINAL_CLASS,
            "composition_fp": self.composition_fp,
            "config_fp": self.config_fp,
            "data_fp": self.data_fp.value,
            "format_version": REPLAY_TERMINAL_FORMAT_VERSION,
            "interval": dict(self.interval),
            "output_refs": dict(self.output_refs),
            "run_fp": self.run_fp.value,
            "status": self.status,
            "transaction_boundary": TRANSACTION_BOUNDARY,
            "world": self.world.value,
        }
        if self.refusal is not None:
            content["refusal"] = dict(self.refusal)
        if self.failure is not None:
            content["failure"] = dict(self.failure)
        return content

    def as_mapping(self) -> Mapping[str, object]:
        payload = self.fp1_identity()
        payload["start_ns"] = self.start_ns
        payload["end_ns"] = self.end_ns
        return MappingProxyType(payload)

    @classmethod
    def from_mapping(cls, raw: object) -> Result[ReplayTerminalRecord]:
        """Rebuild one terminal line from an fp1-canonical JSON object."""
        if not isinstance(raw, Mapping):
            return invalid(
                "terminal_line",
                "a replay terminal line is one fp1-canonical object",
                given=repr(type(raw).__name__),
            )
        body = cast("Mapping[str, object]", raw)
        if body.get("class") != REPLAY_TERMINAL_CLASS:
            return invalid(
                "class",
                "a replay terminal line names class qmn-replay-terminal-line",
                given=repr(body.get("class")),
            )
        if body.get("format_version") != REPLAY_TERMINAL_FORMAT_VERSION:
            return invalid(
                "format_version",
                "this reader understands replay terminal format version 1",
                given=repr(body.get("format_version")),
            )
        run_fp = _as_fingerprint(body.get("run_fp"), "run_fp")
        if is_refusal(run_fp):
            return run_fp
        data_fp = _as_fingerprint(body.get("data_fp"), "data_fp")
        if is_refusal(data_fp):
            return data_fp
        config_fp = clean_token(body.get("config_fp"))
        composition_fp = clean_token(body.get("composition_fp"))
        if config_fp is None or composition_fp is None:
            return invalid(
                "fingerprints",
                "a terminal line carries config and composition fingerprints",
            )
        status = _as_status(body.get("status"))
        if is_refusal(status):
            return status
        interval = _as_interval(body.get("interval"))
        if is_refusal(interval):
            return interval
        start_ns = _as_nonneg_int(body.get("start_ns"), field="start_ns")
        if is_refusal(start_ns):
            return start_ns
        end_ns = _as_nonneg_int(body.get("end_ns"), field="end_ns")
        if is_refusal(end_ns):
            return end_ns
        refs = body.get("output_refs")
        if not isinstance(refs, Mapping):
            return invalid(
                "output_refs",
                "a terminal line cites output references as an object",
                given=repr(type(refs).__name__),
            )
        world = _as_world(body.get("world"))
        if is_refusal(world):
            return world
        refusal = _optional_object(body.get("refusal") if "refusal" in body else None, "refusal")
        if is_refusal(refusal):
            return refusal
        failure = _optional_object(body.get("failure") if "failure" in body else None, "failure")
        if is_refusal(failure):
            return failure
        return Ok(
            cls(
                run_fp=run_fp.value,
                config_fp=config_fp,
                data_fp=data_fp.value,
                composition_fp=composition_fp,
                interval=interval.value,
                status=status.value,
                start_ns=start_ns.value,
                end_ns=end_ns.value,
                output_refs=cast("Mapping[str, object]", refs),
                world=world.value,
                refusal=refusal.value,
                failure=failure.value,
            )
        )


def mint_run_fingerprint(spec: ReplayJobSpec, *, output_dir: object) -> Result[Fingerprint]:
    """Occurrence-stable run fingerprint: spec identity plus the isolated run dir."""
    directory = _as_posix_dir(output_dir)
    if is_refusal(directory):
        return directory
    return fingerprint(
        {
            "class": REPLAY_JOB_CLASS,
            "composition_fp": spec.composition_fp,
            "interval": {"start_ns": spec.start_ns, "end_ns": spec.end_ns},
            "output_dir": directory.value,
            "prefix_id": spec.prefix_id,
            "room_role": spec.room_role,
            "source_world": spec.source_world.value,
        }
    )


def mint_data_fingerprint(spec: ReplayJobSpec) -> Result[Fingerprint]:
    """Fingerprint of the sealed-archive interval the job imported."""
    return fingerprint(
        {
            "class": REPLAY_INTERVAL_CLASS,
            "interval": {"start_ns": spec.start_ns, "end_ns": spec.end_ns},
            "port": REPLAY_IMPORT_PORT,
            "prefix_id": spec.prefix_id,
            "room_role": spec.room_role,
            "source_world": spec.source_world.value,
        }
    )


class ReplayLedgerSink:
    """WriterId-scoped JSONL append sink for replay-job terminal lines.

    Physically one fragment per ``(machine, replay-ledger, worker-slot)``.
    Concurrent processes never share a file. Each line is one fp1-canonical
    object, LF-terminated, appended with fsync through QMB's orchestrator I/O.
    """

    __slots__ = ("_boot_epoch_id", "_machine", "_root", "_slot", "_written")

    def __init__(
        self,
        root: Path,
        *,
        machine: str,
        worker_slot: str,
        boot_epoch_id: str,
    ) -> None:
        self._root = root
        self._machine = machine
        self._slot = worker_slot
        self._boot_epoch_id = boot_epoch_id
        self._written: set[str] = set()

    @classmethod
    def try_create(
        cls,
        root: object,
        *,
        machine: object,
        worker_slot: object = "slot-0",
        boot_epoch_id: object,
    ) -> Result[ReplayLedgerSink]:
        """Bind a sink to one worker-slot under a ledger directory."""
        base = _as_root(root, must_exist=False)
        if is_refusal(base):
            return base
        host = clean_token(machine)
        if host is None:
            return invalid("machine", "a replay ledger WriterId names a machine")
        slot = clean_token(worker_slot)
        if slot is None:
            return invalid("worker_slot", "a replay ledger names a non-empty worker-slot")
        boot = clean_token(boot_epoch_id)
        if boot is None:
            return invalid("boot_epoch_id", "a replay ledger WriterId carries a boot epoch")
        try:
            base.value.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return storage(
                "ledger_root",
                "the replay ledger directory could not be created",
                failure_id=_STORAGE_ID,
                given=type(exc).__name__,
                requiring_review=True,
            )
        return Ok(cls(base.value, machine=host, worker_slot=slot, boot_epoch_id=boot))

    @property
    def root(self) -> Path:
        """Ledger directory home (never a run directory)."""
        return self._root

    @property
    def worker_slot(self) -> str:
        """Worker-slot token. Concurrent processes never share a slot."""
        return self._slot

    def writer_id(self) -> Result[WriterId]:
        """Disjoint replay-namespace WriterId for this slot."""
        return allocate_replay_writer(
            machine=self._machine,
            role=REPLAY_LEDGER_ROLE,
            stream=f"replay:ledger:{self._slot}",
            boot_epoch_id=self._boot_epoch_id,
        )

    def fragment_path(self) -> Result[Path]:
        """World-and-role-scoped JSONL fragment for this WriterId."""
        writer = self.writer_id()
        if is_refusal(writer):
            return writer
        namespace = governed_namespace(World.REPLAY)
        if is_refusal(namespace):
            return namespace
        directory = (
            self._root
            / namespace.value
            / REPLAY_LEDGER_ROLE
            / f"{_safe_token(writer.value.machine)}__{_safe_token(writer.value.stream)}"
        )
        return Ok(directory / FRAGMENT_FILENAME)

    def scan(self) -> Result[tuple[ReplayTerminalRecord, ...]]:
        """Read committed terminal lines from this WriterId stream."""
        path = self.fragment_path()
        if is_refusal(path):
            return path
        return _scan_fragment(path.value, contain_within=self._root)

    def line_for(self, run_fp: object) -> Result[ReplayTerminalRecord | None]:
        """Return the existing terminal line for ``run_fp``, or None."""
        token = _run_fp_token(run_fp)
        if is_refusal(token):
            return token
        scanned = self.scan()
        if is_refusal(scanned):
            return scanned
        found = [line for line in scanned.value if line.run_fp.value == token.value]
        if len(found) > 1:
            return policy(
                "run_fp",
                "exactly one terminal ledger line per replay job — never two "
                "(E15-F01, CT-13/QMB ledger)",
                failure_id=_COLLISION_ID,
                run_fp=token.value,
                count=len(found),
                alarm=True,
            )
        if not found:
            return Ok(None)
        return Ok(found[0])

    def append(self, record: object) -> Result[ReplayTerminalRecord]:
        """Append exactly one fp1-canonical LF-terminated line with fsync.

        Byte-identical re-append of the same run is idempotent. A differing
        second line is a collision: refused, never overwritten.
        """
        if isinstance(record, ReplayTerminalRecord):
            parsed = record
        else:
            loaded = ReplayTerminalRecord.from_mapping(record)
            if is_refusal(loaded):
                return loaded
            parsed = loaded.value
        if parsed.world is not World.REPLAY:
            return policy(
                "world",
                "replay terminal lines occupy the replay governed namespace",
                world=parsed.world.value,
            )
        identity = fingerprint(parsed.fp1_identity())
        if is_refusal(identity):
            return identity
        canonical = canonical_bytes(dict(parsed.as_mapping()))
        if is_refusal(canonical):
            return canonical
        existing = self.line_for(parsed.run_fp)
        if is_refusal(existing):
            return existing
        if existing.value is not None:
            prior = existing.value
            prior_fp = fingerprint(prior.fp1_identity())
            if is_refusal(prior_fp):
                return prior_fp
            if prior_fp.value == identity.value:
                self._written.add(parsed.run_fp.value)
                return Ok(prior)
            return policy(
                "run_fp",
                "exactly one terminal ledger line per replay job — never two; "
                "a differing rewrite is refused, never overwritten (E15-F01, NFR-15)",
                failure_id=_REWRITE_ID,
                run_fp=parsed.run_fp.value,
                alarm=True,
                never_rewrite=NEVER_REWRITE,
            )
        if parsed.run_fp.value in self._written:
            return policy(
                "run_fp",
                "exactly one terminal ledger line per replay job — never two (E15-F01)",
                failure_id=_COLLISION_ID,
                run_fp=parsed.run_fp.value,
            )
        path = self.fragment_path()
        if is_refusal(path):
            return path
        try:
            path.value.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return storage(
                "ledger",
                "append-with-fsync of the WriterId-scoped replay terminal fragment failed",
                failure_id=_STORAGE_ID,
                given=type(exc).__name__,
                path=str(path.value),
                run_fp=parsed.run_fp.value,
                requiring_review=True,
            )
        appended = append_bytes_no_follow(
            path.value,
            canonical.value + b"\n",
            contain_within=self._root,
            field="ledger",
        )
        if is_refusal(appended):
            extra = dict(appended.context)
            extra["run_fp"] = parsed.run_fp.value
            extra["failure_id"] = extra.get("failure_id", _STORAGE_ID)
            extra["requiring_review"] = True
            return TypedRefusal(
                category=appended.category,
                retryability=appended.retryability,
                context=extra,
                after_condition_descriptor=appended.after_condition_descriptor,
            )
        self._written.add(parsed.run_fp.value)
        return Ok(parsed)


def write_intent(
    run_dir: object,
    record: ReplayTerminalRecord,
) -> Result[Path]:
    """Persist the decided terminal intent before the ledger append.

    Ordered-with-recovery: output (child) → intent (run dir) → terminal line
    (writer stream). Exclusive create so a decided status is never rewritten.
    """
    root = _as_run_dir(run_dir)
    if is_refusal(root):
        return root
    path = root.value / INTENT_NAME
    if path.exists():
        loaded = read_intent(root.value)
        if is_refusal(loaded):
            return loaded
        if loaded.value is None:
            return storage(
                "intent",
                "terminal-intent.json exists but is not a committed intent",
                failure_id=_STORAGE_ID,
                path=str(path),
                requiring_review=True,
            )
        prior = fingerprint(loaded.value.fp1_identity())
        if is_refusal(prior):
            return prior
        incoming = fingerprint(record.fp1_identity())
        if is_refusal(incoming):
            return incoming
        if prior.value != incoming.value:
            return policy(
                "intent",
                "a decided terminal intent is never rewritten (NFR-15)",
                failure_id=_REWRITE_ID,
                run_fp=record.run_fp.value,
                never_rewrite=NEVER_REWRITE,
            )
        return Ok(path)
    canonical = canonical_bytes(dict(record.as_mapping()))
    if is_refusal(canonical):
        return canonical
    written = write_bytes_exclusive_no_follow(
        path,
        canonical.value + b"\n",
        contain_within=root.value,
        field="intent",
    )
    if is_refusal(written):
        extra = dict(written.context)
        extra["failure_id"] = extra.get("failure_id", _STORAGE_ID)
        extra["requiring_review"] = True
        extra["run_fp"] = record.run_fp.value
        return TypedRefusal(
            category=written.category,
            retryability=written.retryability,
            context=extra,
            after_condition_descriptor=written.after_condition_descriptor,
        )
    return Ok(path)


def read_intent(run_dir: object) -> Result[ReplayTerminalRecord | None]:
    """Read a committed terminal intent from the run directory, if present."""
    root = _as_run_dir(run_dir)
    if is_refusal(root):
        return root
    path = root.value / INTENT_NAME
    if not path.exists():
        return Ok(None)
    loaded = read_contained_bytes(
        path, contain_within=root.value, max_bytes=MAX_JSONL_BYTES, field="intent"
    )
    if is_refusal(loaded):
        extra = dict(loaded.context)
        extra["failure_id"] = extra.get("failure_id", _STORAGE_ID)
        extra["requiring_review"] = True
        return TypedRefusal(
            category=loaded.category,
            retryability=loaded.retryability,
            context=extra,
            after_condition_descriptor=loaded.after_condition_descriptor,
        )
    raw = loaded.value.strip()
    if not raw:
        return Ok(None)
    try:
        parsed: object = json.loads(raw)
    except ValueError:
        return storage(
            "intent",
            "terminal-intent.json is one JSON object",
            failure_id=_STORAGE_ID,
            requiring_review=True,
        )
    parsed_line = ReplayTerminalRecord.from_mapping(parsed)
    if is_refusal(parsed_line):
        return parsed_line
    return Ok(parsed_line.value)


def read_writer_manifest(run_dir: object) -> Result[Mapping[str, object]]:
    """Read the writer.json occurrence stamp from a replay run directory."""
    root = _as_run_dir(run_dir)
    if is_refusal(root):
        return root
    path = root.value / WRITER_NAME
    loaded = read_contained_bytes(
        path, contain_within=root.value, max_bytes=MAX_JSONL_BYTES, field="writer"
    )
    if is_refusal(loaded):
        extra = dict(loaded.context)
        extra["failure_id"] = extra.get("failure_id", _STORAGE_ID)
        extra["requiring_review"] = True
        return TypedRefusal(
            category=loaded.category,
            retryability=loaded.retryability,
            context=extra,
            after_condition_descriptor=loaded.after_condition_descriptor,
        )
    try:
        parsed: object = json.loads(loaded.value)
    except ValueError:
        return storage(
            "writer",
            "writer.json is one JSON object",
            failure_id=_STORAGE_ID,
            requiring_review=True,
        )
    if not isinstance(parsed, Mapping):
        return invalid("writer", "writer.json is an object", given=type(parsed).__name__)
    return Ok(MappingProxyType(dict(cast("Mapping[str, object]", parsed))))


def _scan_fragment(path: Path, *, contain_within: Path) -> Result[tuple[ReplayTerminalRecord, ...]]:
    if not path.exists():
        return Ok(())
    loaded = read_contained_bytes(
        path, contain_within=contain_within, max_bytes=MAX_JSONL_BYTES, field="ledger"
    )
    if is_refusal(loaded):
        extra = dict(loaded.context)
        extra["failure_id"] = extra.get("failure_id", _STORAGE_ID)
        extra["requiring_review"] = True
        extra["path"] = str(path)
        return TypedRefusal(
            category=loaded.category,
            retryability=loaded.retryability,
            context=extra,
            after_condition_descriptor=loaded.after_condition_descriptor,
        )
    raw = loaded.value
    if not raw:
        return Ok(())
    chunks = raw.split(b"\n")
    lines: list[ReplayTerminalRecord] = []
    last = len(chunks) - 1
    for index, chunk in enumerate(chunks):
        if chunk == b"":
            continue
        if index == last and not raw.endswith(b"\n"):
            # Torn tail: fsync did not complete. Not a committed line.
            continue
        parsed = _line_from_bytes(chunk)
        if is_refusal(parsed):
            extra = dict(parsed.context)
            extra["path"] = str(path)
            extra["index"] = index
            extra["failure_id"] = extra.get("failure_id", _STORAGE_ID)
            extra["requiring_review"] = True
            return TypedRefusal(
                category=parsed.category,
                retryability=parsed.retryability,
                context=extra,
                after_condition_descriptor=parsed.after_condition_descriptor,
            )
        lines.append(parsed.value)
    return Ok(tuple(lines))


def _line_from_bytes(chunk: bytes) -> Result[ReplayTerminalRecord]:
    try:
        loaded: object = json.loads(chunk)
    except ValueError:
        return storage(
            "ledger",
            "a JSONL fragment line is one JSON object",
            failure_id=_STORAGE_ID,
            requiring_review=True,
        )
    line = ReplayTerminalRecord.from_mapping(loaded)
    if is_refusal(line):
        return line
    expected = canonical_bytes(dict(line.value.as_mapping()))
    if is_ok(expected) and expected.value != chunk:
        return policy(
            "ledger",
            "each terminal line is one fp1-canonical object; non-canonical bytes are refused",
            failure_id=_COLLISION_ID,
        )
    return line


def _as_root(value: object, *, must_exist: bool) -> Result[Path]:
    if isinstance(value, Path):
        root = value
    elif isinstance(value, str) and value.strip() != "":
        root = Path(value)
    else:
        return invalid(
            "ledger_root",
            "the replay ledger home is a named directory, never a run directory",
            given=repr(type(value).__name__),
        )
    if must_exist and not root.is_dir():
        return invalid(
            "ledger_root",
            "the replay ledger home is a named directory, never a run directory",
            given=str(root),
        )
    return Ok(root)


def _as_run_dir(value: object) -> Result[Path]:
    if isinstance(value, Path):
        root = value
    elif isinstance(value, str) and value.strip() != "":
        root = Path(value)
    else:
        return invalid(
            "run_dir",
            "recovery scans a named replay run directory",
            given=repr(type(value).__name__),
        )
    if not root.is_dir():
        return invalid("run_dir", "recovery scans a named replay run directory", given=str(root))
    return Ok(root)


def _as_posix_dir(value: object) -> Result[str]:
    if isinstance(value, Path):
        return Ok(value.as_posix())
    token = clean_token(value)
    if token is None:
        return invalid("output_dir", "a replay job names an isolated output directory")
    return Ok(Path(token).as_posix())


def _as_fingerprint(value: object, field: str) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    if isinstance(value, str):
        return Fingerprint.try_create(value)
    return invalid(field, "a fingerprint is the string fp1:sha256:<hex>", given=repr(value))


def _run_fp_token(value: object) -> Result[str]:
    parsed = _as_fingerprint(value, "run_fp")
    if is_refusal(parsed):
        return parsed
    return Ok(parsed.value.value)


def _as_status(value: object) -> Result[str]:
    token = clean_token(value)
    if token is None or token not in TERMINAL_STATUSES:
        return invalid(
            "status",
            "terminal status is complete, refuse, abort, cancel, bound, or teardown",
            given=repr(value),
            allowed=list(TERMINAL_STATUSES),
        )
    return Ok(token)


def _as_world(value: object) -> Result[World]:
    if isinstance(value, World):
        return Ok(value)
    token = clean_token(value)
    if token is None:
        return invalid("world", "world is replay", given=repr(value))
    try:
        world = World(token)
    except ValueError:
        return invalid("world", "world is replay", given=token)
    if world is not World.REPLAY:
        return policy("world", "replay terminal lines are world=replay", world=world.value)
    return Ok(world)


def _as_interval(value: object) -> Result[Mapping[str, int]]:
    if not isinstance(value, Mapping):
        return invalid(
            "interval", "interval is {start_ns, end_ns}", given=repr(type(value).__name__)
        )
    body = cast("Mapping[str, object]", value)
    start = _as_nonneg_int(body.get("start_ns"), field="start_ns")
    if is_refusal(start):
        return start
    end = _as_nonneg_int(body.get("end_ns"), field="end_ns")
    if is_refusal(end):
        return end
    return Ok({"start_ns": start.value, "end_ns": end.value})


def _as_nonneg_int(value: object, *, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return invalid(field, f"{field} is a non-negative int64", given=repr(value))
    return Ok(value)


def _optional_object(value: object, field: str) -> Result[Mapping[str, object] | None]:
    if value is None:
        return Ok(None)
    if not isinstance(value, Mapping):
        return invalid(field, f"{field} is an object", given=repr(type(value).__name__))
    return Ok(dict(cast("Mapping[str, object]", value)))


def _safe_token(token: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-._" else "-" for ch in token)
