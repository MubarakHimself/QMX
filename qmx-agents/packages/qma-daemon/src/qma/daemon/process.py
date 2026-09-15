"""Composed asyncio daemon process (Story 36.1 / 36.3; FR-W09; FR-W10; NFR-W04).

One long-running process from existing modules: the CT-40 loopback listener,
the Story 42.1 sole sqlite writer, the ExperimentSpec / Experiment Ledger /
CT-07 sqlite product truth, and the Epic 48 desk-pack roster. Connect, not a
sixth application: no new COMP, no HTTP experiment service, and no second
daemon runtime. QMB JSONL stays in QMB and is not merged into sqlite.
``analysis-backtest`` remains the Backtesting Service's daemon half.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final

from qma.core.plugins.packs import DESK_PLUGIN_PACK_IDS
from qma.core.ports.qmb import (
    ANALYSIS_BACKTEST_PLUGIN_ID,
    QMB_OWNED_CONCERNS,
    refuse_qmb_import_edge,
    refuse_qmb_owned_concern,
)
from qma.core.vocabulary.enums import PrincipalClass
from qma.daemon.backtest.service import BacktestingService
from qma.daemon.experiments import EXPERIMENT_SQLITE_TABLES, ExperimentSpecService
from qma.daemon.journal.authoritative import AuthoritativeJournal
from qma.daemon.journal.clock import InjectedUtcClock
from qma.daemon.ledgers.experiment import ExperimentLedgerStore
from qma.daemon.persistence.sqlite_writer import SingleSqliteWriter
from qma.daemon.persistence.substrate import PersistenceSubstrate
from qma.daemon.plugins.packs import DeskPluginRoster
from qma.wire.listener import (
    DEFAULT_BIND_HOST,
    ListenerBindConfig,
    ListenerPosture,
    validate_listener_startup,
)
from qma.wire.schemas import SCHEMA_FILES
from qma.wire.vocabulary import WIRE_VOCABULARY_OWNER
from qmf.core import Ok, Result, World, WriterId, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection, storage_failure

__all__ = [
    "COMP_EXP_MINTED",
    "DEFAULT_BIND_PORT",
    "HTTP_EXPERIMENT_SERVICE_MINTED",
    "QMB_JSONL_MERGED_INTO_SQLITE",
    "SIXTH_APPLICATION_MINTED",
    "BoundListener",
    "DaemonProcess",
]


COMP_EXP_MINTED: Final[bool] = False
HTTP_EXPERIMENT_SERVICE_MINTED: Final[bool] = False
SIXTH_APPLICATION_MINTED: Final[bool] = False
QMB_JSONL_MERGED_INTO_SQLITE: Final[bool] = False
DEFAULT_BIND_PORT: Final[int] = 8765

_QMB_SQLITE_TABLE_DENY: Final[frozenset[str]] = frozenset(
    {"qmb_jsonl", "qmb_ledger", "qmb_run_ledger", "ct32"}
)


class _ProcessGate:
    """In-process singleton — at most one composed DaemonProcess."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.holder: DaemonProcess | None = None


_process_gate = _ProcessGate()


@dataclass(frozen=True, slots=True)
class BoundListener:
    """Loopback CT-40 listener after asyncio bind. Not a second wire schema."""

    host: str
    port: int
    loopback: bool
    websocket_url_prefix: str
    query_url_prefix: str
    authentication_required: bool
    schema_owner: str = WIRE_VOCABULARY_OWNER
    http_experiment_service: bool = HTTP_EXPERIMENT_SERVICE_MINTED


class DaemonProcess:
    """One asyncio process: loopback listener + sole sqlite writer + pack roster."""

    def __init__(
        self,
        *,
        substrate: PersistenceSubstrate,
        roster: DeskPluginRoster,
        posture: ListenerPosture,
        bind_port: int,
        journal: AuthoritativeJournal,
        experiments: ExperimentSpecService,
    ) -> None:
        self._substrate = substrate
        self._roster = roster
        self._posture = posture
        self._bind_port = bind_port
        self._journal = journal
        self._experiments = experiments
        self._server: asyncio.Server | None = None
        self._bound: BoundListener | None = None
        self._accepted = 0
        self._closed = False

    @classmethod
    def compose(
        cls,
        root: Path | str,
        *,
        machine: str,
        boot_epoch_id: str,
        listener: ListenerBindConfig | None = None,
        bind_port: object = 0,
        plugins_root: Path | None = None,
        world: World = World.LIVE,
    ) -> Result[DaemonProcess]:
        """Compose the daemon from existing modules. Does not mint a new COMP."""
        if COMP_EXP_MINTED or SIXTH_APPLICATION_MINTED or HTTP_EXPERIMENT_SERVICE_MINTED:
            return policy_rejection(
                "daemon_runtime",
                "a sixth application, COMP-EXP, or HTTP experiment service is not minted "
                "(FR-W01; DEC-0269)",
            )
        if isinstance(bind_port, bool) or not isinstance(bind_port, int) or bind_port < 0:
            return invalid_input(
                "bind_port",
                "bind_port must be a non-negative int (0 selects an ephemeral port)",
                given=repr(bind_port),
            )
        port = bind_port

        if listener is None:
            created = ListenerBindConfig.try_create()
            if is_refusal(created):
                return created
            bind_config = created.value
        else:
            bind_config = listener

        posture = validate_listener_startup(bind_config)
        if is_refusal(posture):
            return posture

        with _process_gate.lock:
            holder = _process_gate.holder
            if holder is not None and not holder._closed:
                return policy_rejection(
                    "daemon_runtime",
                    "exactly one Python asyncio daemon process may run; a second "
                    "daemon runtime is refused (FR-W09; FR-W01; FR-Q22; AD-4)",
                    holder_root=str(holder.root),
                    attempted_root=str(root),
                )

            opened = PersistenceSubstrate.open(
                root,
                machine=machine,
                boot_epoch_id=boot_epoch_id,
                world=world,
            )
            if is_refusal(opened):
                return opened
            substrate = opened.value

            journal_bound = AuthoritativeJournal.bind(
                substrate,
                clock=InjectedUtcClock(boot_epoch_id),
            )
            if is_refusal(journal_bound):
                substrate.close()
                return journal_bound
            journal = journal_bound.value

            lineage_writer = WriterId.try_create(
                machine, "authoring", "experiment-lineage", boot_epoch_id
            )
            if is_refusal(lineage_writer):
                journal.close()
                substrate.close()
                return lineage_writer

            experiments = ExperimentSpecService(
                writer=lineage_writer.value,
                ledgers=ExperimentLedgerStore(_journal=journal),
            )
            restored = experiments.bind_durable(
                sqlite=substrate.sqlite,
                journal=journal,
            )
            if is_refusal(restored):
                journal.close()
                substrate.close()
                return restored

            roster = DeskPluginRoster(plugins_root=plugins_root)
            activated = roster.activate(
                principal=PrincipalClass.OPERATOR,
                correlation_id=f"daemon-process:{boot_epoch_id}",
            )
            if is_refusal(activated):
                journal.close()
                substrate.close()
                return activated

            process = cls(
                substrate=substrate,
                roster=roster,
                posture=posture.value,
                bind_port=port,
                journal=journal,
                experiments=experiments,
            )
            _process_gate.holder = process
            return Ok(process)

    @property
    def root(self) -> Path:
        return self._substrate.root

    @property
    def substrate(self) -> PersistenceSubstrate:
        return self._substrate

    @property
    def sqlite(self) -> SingleSqliteWriter:
        return self._substrate.sqlite

    @property
    def journal(self) -> AuthoritativeJournal:
        return self._journal

    @property
    def experiments(self) -> ExperimentSpecService:
        return self._experiments

    @property
    def roster(self) -> DeskPluginRoster:
        return self._roster

    @property
    def backtesting(self) -> BacktestingService:
        return self._roster.backtesting

    @property
    def posture(self) -> ListenerPosture:
        return self._posture

    @property
    def bound(self) -> BoundListener | None:
        return self._bound

    @property
    def accepted_connections(self) -> int:
        return self._accepted

    @property
    def wire_schema_owner(self) -> str:
        return WIRE_VOCABULARY_OWNER

    @property
    def wire_schema_files(self) -> Mapping[str, str]:
        return MappingProxyType(dict(SCHEMA_FILES))

    def sqlite_connection_count(self) -> int:
        """Story 42.1: exactly one writable connection in one writer thread."""
        return self._substrate.sqlite.connection_count_evidence()

    def start_http_experiment_service(self) -> Result[None]:
        """Refused — CT-40 queries are not a COMP-EXP HTTP experiment service."""
        return policy_rejection(
            "http_experiment_service",
            "no HTTP experiment service is minted; the composed process is "
            "qma-daemon over existing CT-40 modules, not COMP-EXP (FR-W01; DEC-0269)",
            minted=HTTP_EXPERIMENT_SERVICE_MINTED,
            sixth_application=SIXTH_APPLICATION_MINTED,
        )

    def merge_qmb_jsonl(self, path: object = None) -> Result[None]:
        """Refused — QMB JSONL stays WriterId-scoped and is never merged here."""
        return policy_rejection(
            "qmb_jsonl",
            "QMB JSONL remains WriterId-scoped in QMB; it is not merged into "
            "the daemon sqlite store (NFR-W04; DEC-0305)",
            merged=QMB_JSONL_MERGED_INTO_SQLITE,
            path=repr(path),
            qmb_owned=sorted(QMB_OWNED_CONCERNS),
        )

    def import_qmb_package(self) -> Result[None]:
        """The QMB door stays a runtime interaction — no package-import edge."""
        return refuse_qmb_import_edge()

    def take_qmb_owned_concern(self, concern: str) -> Result[None]:
        """QMB keeps its run ledger, parallelism, and artifact contract."""
        return refuse_qmb_owned_concern(concern=concern)

    async def bind(self) -> Result[BoundListener]:
        """Bind the loopback listener. Does not start an HTTP experiment service."""
        if self._closed:
            return policy_rejection(
                "daemon_runtime",
                "composed daemon process is closed",
            )
        if self._bound is not None and self._server is not None:
            return Ok(self._bound)
        try:
            server = await asyncio.start_server(
                self._handle_client,
                host=self._posture.host,
                port=self._bind_port,
            )
        except OSError as exc:
            return storage_failure(
                f"could not bind the loopback listener: {exc}",
                context={
                    "field": "listener",
                    "host": self._posture.host,
                    "port": self._bind_port,
                },
            )
        sockets = server.sockets
        if not sockets:
            server.close()
            await server.wait_closed()
            return storage_failure(
                "loopback listener bound with no sockets",
                context={"field": "listener", "host": self._posture.host},
            )
        sockname = sockets[0].getsockname()
        bound = BoundListener(
            host=str(sockname[0]),
            port=int(sockname[1]),
            loopback=self._posture.loopback,
            websocket_url_prefix=self._posture.websocket_url_prefix,
            query_url_prefix=self._posture.query_url_prefix,
            authentication_required=self._posture.authentication_required,
        )
        self._server = server
        self._bound = bound
        return Ok(bound)

    async def serve(self) -> Result[None]:
        """Bind if needed and serve until cancelled. One inbound listener."""
        bound = await self.bind()
        if is_refusal(bound):
            return bound
        server = self._server
        if server is None:
            return policy_rejection("listener", "loopback listener is not bound")
        try:
            async with server:
                await server.serve_forever()
        except asyncio.CancelledError:
            return Ok(None)
        return Ok(None)

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        self._accepted += 1
        try:
            while not reader.at_eof():
                chunk = await reader.read(65536)
                if not chunk:
                    break
        finally:
            if not writer.is_closing():
                writer.close()
            await writer.wait_closed()

    def sqlite_table_names(self) -> frozenset[str]:
        rows = self._substrate.sqlite.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return frozenset(str(row[0]) for row in rows)

    def qmb_jsonl_tables_present(self) -> frozenset[str]:
        """Names that would mean QMB JSONL was merged into daemon sqlite."""
        return self.sqlite_table_names() & _QMB_SQLITE_TABLE_DENY

    def snapshot(self) -> Mapping[str, object]:
        bound = self._bound
        return MappingProxyType(
            {
                "component": "COMP-QMA-DAEMON",
                "sixth_application": SIXTH_APPLICATION_MINTED,
                "comp_exp": COMP_EXP_MINTED,
                "http_experiment_service": HTTP_EXPERIMENT_SERVICE_MINTED,
                "qmb_jsonl_merged": QMB_JSONL_MERGED_INTO_SQLITE,
                "wire_schema_owner": WIRE_VOCABULARY_OWNER,
                "wire_schema_files": dict(SCHEMA_FILES),
                "default_bind_host": DEFAULT_BIND_HOST,
                "listener_loopback": self._posture.loopback,
                "listener_host": self._posture.host,
                "sqlite_connections": self.sqlite_connection_count(),
                "sqlite_thread": self._substrate.sqlite.thread_name,
                "sqlite_tables": sorted(self.sqlite_table_names()),
                "experiment_sqlite_tables": sorted(
                    self.sqlite_table_names() & EXPERIMENT_SQLITE_TABLES
                ),
                "experiment_product_truth": self._experiments.product_truth,
                "pack_ids": list(self._roster.loader.loaded_ids()),
                "expected_pack_ids": list(DESK_PLUGIN_PACK_IDS),
                "analysis_backtest_plugin_id": self.backtesting.plugin_id,
                "expected_analysis_backtest_plugin_id": ANALYSIS_BACKTEST_PLUGIN_ID,
                "qmb_jsonl_tables": sorted(self.qmb_jsonl_tables_present()),
                "backtesting_service": type(self.backtesting).__name__,
                "qmb_door_transport": type(self.backtesting.transport).__name__,
                "qmb_door_production": bool(
                    getattr(self.backtesting.transport, "production", False)
                ),
                "scheduling_authority": self.backtesting.scheduling_authority,
                "parallelism": self.backtesting.parallelism,
                "backtest_state": self.backtesting.backtest_state,
                "bound_host": None if bound is None else bound.host,
                "bound_port": None if bound is None else bound.port,
            }
        )

    def close(self) -> None:
        """Release the listener sockets and the sole-writer substrate."""
        server = self._server
        self._server = None
        if server is not None:
            server.close()
        self._release()

    async def aclose(self) -> None:
        server = self._server
        self._server = None
        if server is not None:
            server.close()
            await server.wait_closed()
        self._release()

    def _release(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._bound = None
        self._journal.close()
        closer = getattr(self.backtesting.transport, "close", None)
        try:
            if callable(closer):
                closer()
        finally:
            self._substrate.close()
            with _process_gate.lock:
                if _process_gate.holder is self:
                    _process_gate.holder = None

    def __enter__(self) -> DaemonProcess:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
