"""WriterId-scoped JSONL ledger fragments. Orchestrator-only writes (B-4, AR-53).

Physically one fragment file per ``(machine, role, worker-slot)``. Concurrent
processes never share a file. Each line is one fp1-canonical object,
LF-terminated, appended with fsync. Reads are a world-and-role-scoped merge
view; the Book-bar read selects ``role=confirmation`` only.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Final

from qmf.core.chrono import WriterId
from qmf.core.fingerprint import World, canonical_bytes, fingerprint, governed_namespace
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok, is_refusal

from qmb._refuse import clean_token, invalid, policy, storage
from qmb.config.compiler import ResolvedRunConfig
from qmb.ledger.line import (
    BOOK_BAR_READ_ROLE,
    LEDGER_LINE_CLASS,
    ROLE_ABORTED,
    ROLE_CONFIRMATION,
    LedgerLine,
    book_bar_lines,
    merge_ledger_lines,
    mint_aborted_line,
    mint_completed_line,
)
from qmb.orchestrator.spawn import IsolatedRun, LiveSpawn, collect_run

__all__ = [
    "FACTORY_SANDBOX_ENV",
    "FRAGMENT_FILENAME",
    "LedgerSink",
    "finish_run",
    "fragment_path",
    "is_factory_sandbox",
    "mint_writer_id",
    "read_book_bar",
    "read_merge_view",
    "writer_slot_token",
]

FACTORY_SANDBOX_ENV: Final[str] = "QMB_FACTORY_SANDBOX"
FRAGMENT_FILENAME: Final[str] = "ledger.jsonl"
_FACTORY_TRUE: Final[frozenset[str]] = frozenset({"1", "true", "yes", "sandbox"})


def is_factory_sandbox(explicit: object = None) -> bool:
    """Factory-sandbox runs stamp ``provenance=sandbox`` on the AD-12 label."""
    if explicit is True:
        return True
    if explicit is False:
        return False
    token = os.environ.get(FACTORY_SANDBOX_ENV, "")
    return token.strip().casefold() in _FACTORY_TRUE


def writer_slot_token(worker_slot: object) -> Result[str]:
    """Filesystem-safe worker-slot token. Colon is illegal on Windows."""
    if isinstance(worker_slot, bool) or not isinstance(worker_slot, int):
        token = clean_token(worker_slot)
        if token is None:
            return invalid(
                "worker_slot",
                "a WriterId-scoped fragment names a non-empty worker-slot",
                given=repr(worker_slot),
            )
        return Ok(_safe_token(token))
    if worker_slot < 0:
        return invalid(
            "worker_slot",
            "a worker-slot index is a non-negative integer",
            given=worker_slot,
        )
    return Ok(f"slot-{worker_slot}")


def mint_writer_id(
    *,
    machine: object,
    role: object,
    worker_slot: object,
    boot_epoch_id: object,
) -> Result[WriterId]:
    """Durable WriterId per ``(machine, role, worker-slot)`` (AD-8, B-4)."""
    slot = writer_slot_token(worker_slot)
    if is_refusal(slot):
        return slot
    return WriterId.try_create(machine, role, slot.value, boot_epoch_id)


def fragment_path(
    root: object,
    writer: object,
    *,
    world: object,
    role: object,
) -> Result[Path]:
    """World-and-role-scoped fragment path for one WriterId. Never a run directory."""
    base = _as_root(root)
    if is_refusal(base):
        return base
    if not isinstance(writer, WriterId):
        return invalid(
            "writer",
            "a ledger fragment is WriterId-scoped",
            given=repr(type(writer).__name__),
        )
    parsed_world = _as_world(world)
    if is_refusal(parsed_world):
        return parsed_world
    namespace = governed_namespace(parsed_world.value)
    if is_refusal(namespace):
        return namespace
    role_token = clean_token(role)
    if role_token is None:
        return invalid(
            "role",
            "the fragment directory is world-and-role-scoped",
            given=repr(role),
        )
    directory = (
        base.value
        / namespace.value
        / role_token
        / f"{_safe_token(writer.machine)}__{_safe_token(writer.stream)}"
    )
    return Ok(directory / FRAGMENT_FILENAME)


class LedgerSink:
    """One-writer append sink bound to ``(machine, worker-slot)``. Impure.

    The run role completes the WriterId at append time, so confirmation and
    aborted lines of the same slot never share a file.
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
        worker_slot: object,
        boot_epoch_id: object,
    ) -> Result[LedgerSink]:
        """Bind a sink to one worker-slot under a ledger directory."""
        base = _as_root(root, must_exist=False)
        if is_refusal(base):
            return base
        machine_token = clean_token(machine)
        if machine_token is None:
            return invalid(
                "machine",
                "a WriterId names a non-empty machine",
                given=repr(machine),
            )
        slot = writer_slot_token(worker_slot)
        if is_refusal(slot):
            return slot
        boot = clean_token(boot_epoch_id)
        if boot is None:
            return invalid(
                "boot_epoch_id",
                "a writer id carries a non-empty boot/epoch id so restarts are visible",
                given=repr(boot_epoch_id),
            )
        try:
            base.value.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return storage(
                "ledger_root",
                "the orchestrator could not create the world-and-role-scoped ledger directory",
                given=type(exc).__name__,
            )
        return Ok(
            cls(
                base.value,
                machine=machine_token,
                worker_slot=slot.value,
                boot_epoch_id=boot,
            )
        )

    @property
    def machine(self) -> str:
        """Machine token of this WriterId-scoped sink."""
        return self._machine

    @property
    def worker_slot(self) -> str:
        """Worker-slot token. Concurrent processes never share a slot."""
        return self._slot

    @property
    def root(self) -> Path:
        """Ledger directory home (not a run directory)."""
        return self._root

    def writer_id(self, role: object) -> Result[WriterId]:
        """WriterId for this slot under one discriminated run role."""
        return mint_writer_id(
            machine=self._machine,
            role=role,
            worker_slot=self._slot,
            boot_epoch_id=self._boot_epoch_id,
        )

    def append(self, line: object) -> Result[LedgerLine]:
        """Append exactly one fp1-canonical LF-terminated line with fsync."""
        if isinstance(line, LedgerLine):
            parsed = line
        else:
            loaded = LedgerLine.from_mapping(line)
            if is_refusal(loaded):
                return loaded
            parsed = loaded.value
        namespace = governed_namespace(parsed.world)
        if is_refusal(namespace):
            return namespace
        identity = fingerprint(parsed.fp1_identity())
        if is_refusal(identity):
            return identity
        canonical = canonical_bytes(parsed.fp1_identity())
        if is_refusal(canonical):
            return canonical
        writer = self.writer_id(parsed.role)
        if is_refusal(writer):
            return writer
        path = fragment_path(
            self._root,
            writer.value,
            world=parsed.world,
            role=parsed.role,
        )
        if is_refusal(path):
            return path
        existing = _scan_fragment(path.value)
        if is_refusal(existing):
            return existing
        for prior in existing.value:
            if prior.run_id != parsed.run_id:
                continue
            prior_fp = fingerprint(prior.fp1_identity())
            if is_refusal(prior_fp):
                return prior_fp
            if prior_fp.value == identity.value:
                self._written.add(parsed.run_id.value)
                return Ok(prior)
            return policy(
                "run_id",
                "exactly one ledger line per run — never two; a differing rewrite "
                "is refused, never overwritten (AR-51, B-4)",
                run_id=parsed.run_id.value,
                alarm=True,
            )
        if parsed.run_id.value in self._written:
            return policy(
                "run_id",
                "exactly one ledger line per run — never two (AR-51, B-4)",
                run_id=parsed.run_id.value,
            )
        try:
            path.value.parent.mkdir(parents=True, exist_ok=True)
            with path.value.open("ab") as handle:
                handle.write(canonical.value + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            return storage(
                "ledger",
                "append-with-fsync of the WriterId-scoped JSONL fragment failed",
                given=type(exc).__name__,
                path=str(path.value),
                run_id=parsed.run_id.value,
            )
        self._written.add(parsed.run_id.value)
        return Ok(parsed)


def finish_run(
    live: object,
    *,
    config: object,
    ledger: object,
    role: object = ROLE_CONFIRMATION,
    factory_sandbox: object = None,
) -> Result[IsolatedRun]:
    """Collect one spawned run and append exactly one ledger line (B-4).

    Completed runs ledger ``confirmation | trial | replicate``. Observed dead
    or cancelled processes ledger ``aborted`` with refusal context. Direct
    library ``run()`` never calls this.
    """
    if not isinstance(live, LiveSpawn):
        return invalid(
            "live",
            "finish_run collects a LiveSpawn started by start_run",
            given=repr(type(live).__name__),
        )
    if not isinstance(config, ResolvedRunConfig):
        return invalid(
            "config",
            "the orchestrator writes the ledger line from the resolved run-config",
            given=repr(type(config).__name__),
        )
    if not isinstance(ledger, LedgerSink):
        return invalid(
            "ledger",
            "ledger writes are owned by the orchestrator through a LedgerSink",
            given=repr(type(ledger).__name__),
        )
    if live.run_id != config.fingerprint:
        return invalid(
            "run_id",
            "the ledger key is the resolved-config fingerprint of this live run",
            live=live.run_id.value,
            config=config.fingerprint.value,
        )
    sandbox = is_factory_sandbox(factory_sandbox)
    collected = collect_run(live)
    if is_refusal(collected):
        return _append_aborted(ledger, config, collected, factory_sandbox=sandbox)
    minted = mint_completed_line(
        config,
        outcome_identity=collected.value.outcome_identity,
        ct32_fingerprint=collected.value.ct32_fingerprint,
        role=role,
        factory_sandbox=sandbox,
    )
    if is_refusal(minted):
        return _append_aborted(ledger, config, minted, factory_sandbox=sandbox)
    appended = ledger.append(minted.value)
    if is_refusal(appended):
        return appended
    return collected


def read_merge_view(
    root: object,
    *,
    world: object,
    role: object,
) -> Result[tuple[LedgerLine, ...]]:
    """Merge every WriterId fragment in one world-and-role-scoped namespace."""
    parsed_world = _as_world(world)
    if is_refusal(parsed_world):
        return parsed_world
    namespace = governed_namespace(parsed_world.value)
    if is_refusal(namespace):
        return namespace
    role_token = clean_token(role)
    if role_token is None:
        return invalid(
            "role",
            "the merge view is world-and-role-scoped",
            given=repr(role),
        )
    base = _as_root(root)
    if is_refusal(base):
        return base
    directory = base.value / namespace.value / role_token
    loaded = _load_namespace(directory)
    if is_refusal(loaded):
        return loaded
    return merge_ledger_lines(loaded.value, world=parsed_world.value, role=role_token)


def read_book_bar(root: object, *, world: object) -> Result[tuple[LedgerLine, ...]]:
    """Book-bar read: confirmation lines only (B-4, FM-8)."""
    merged = read_merge_view(root, world=world, role=BOOK_BAR_READ_ROLE)
    if is_refusal(merged):
        return merged
    return book_bar_lines(merged.value, world=world)


def _append_aborted(
    ledger: LedgerSink,
    config: ResolvedRunConfig,
    refusal: TypedRefusal,
    *,
    factory_sandbox: bool,
) -> TypedRefusal:
    minted = mint_aborted_line(config, refusal, factory_sandbox=factory_sandbox)
    if is_refusal(minted):
        return minted
    appended = ledger.append(minted.value)
    if is_refusal(appended):
        return appended
    extra = dict(refusal.context)
    extra["writes_ledger"] = True
    extra["ledger_role"] = ROLE_ABORTED
    extra["ledger_line_class"] = LEDGER_LINE_CLASS
    extra["aborted_line_absent"] = False
    return TypedRefusal(
        category=refusal.category,
        retryability=refusal.retryability,
        context=extra,
        after_condition_descriptor=refusal.after_condition_descriptor,
    )


def _load_namespace(directory: Path) -> Result[tuple[LedgerLine, ...]]:
    if not directory.is_dir():
        return Ok(())
    lines: list[LedgerLine] = []
    try:
        fragments = sorted(
            path
            for path in directory.rglob(FRAGMENT_FILENAME)
            if path.is_file() and not path.is_symlink()
        )
    except OSError as exc:
        return storage(
            "ledger",
            "the merge view could not list WriterId-scoped fragments",
            given=type(exc).__name__,
            path=str(directory),
        )
    for path in fragments:
        scanned = _scan_fragment(path)
        if is_refusal(scanned):
            return scanned
        lines.extend(scanned.value)
    return Ok(tuple(lines))


def _scan_fragment(path: Path) -> Result[tuple[LedgerLine, ...]]:
    if not path.exists():
        return Ok(())
    if path.is_symlink() or not path.is_file():
        return storage(
            "ledger",
            "refusing to read a ledger fragment that is not a regular file",
            path=str(path),
        )
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return storage(
            "ledger",
            "the merge view could not read a WriterId-scoped JSONL fragment",
            given=type(exc).__name__,
            path=str(path),
        )
    if not raw:
        return Ok(())
    chunks = raw.split(b"\n")
    lines: list[LedgerLine] = []
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
            return TypedRefusal(
                category=parsed.category,
                retryability=parsed.retryability,
                context=extra,
                after_condition_descriptor=parsed.after_condition_descriptor,
            )
        lines.append(parsed.value)
    return Ok(tuple(lines))


def _line_from_bytes(chunk: bytes) -> Result[LedgerLine]:
    try:
        loaded: object = json.loads(chunk)
    except ValueError:
        return storage(
            "ledger",
            "a JSONL fragment line is one JSON object",
        )
    line = LedgerLine.from_mapping(loaded)
    if is_refusal(line):
        return line
    expected = canonical_bytes(line.value.fp1_identity())
    if is_ok(expected) and expected.value != chunk:
        return policy(
            "ledger",
            "each ledger line is one fp1-canonical object; non-canonical bytes are refused",
        )
    return line


def _as_root(value: object, *, must_exist: bool = True) -> Result[Path]:
    if isinstance(value, Path):
        root = value
    elif isinstance(value, str) and value.strip() != "":
        root = Path(value)
    else:
        return invalid(
            "ledger_root",
            "the ledger home is a named directory, never a run directory",
            given=repr(type(value).__name__),
        )
    if must_exist and not root.is_dir():
        return invalid(
            "ledger_root",
            "the ledger home is a named directory, never a run directory",
            given=str(root),
        )
    return Ok(root)


def _as_world(value: object) -> Result[World]:
    if isinstance(value, World):
        return Ok(value)
    token = clean_token(value)
    if token is None:
        return invalid("world", "world is live, replay, or simulated", given=repr(value))
    try:
        return Ok(World(token))
    except ValueError:
        return invalid("world", "world is live, replay, or simulated", given=token)


def _safe_token(token: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-._" else "-" for ch in token)
