"""Single QMB door definitions (CT-47; AD-17; DEC-0316; FR-Q55).

Agent → QMA backtest tool → Backtesting Service → ``qmb`` door → QMB.
The door is a runtime CLI or MCP interaction. QMA places one ``qmb`` job per
ExecutionEnvironment (singleton per kind) and never imports the ``qmb``
package. QMB keeps intra-node parallelism, its run ledger, and its artifact
contract. Requests run against recorded evidence and ``world=replay`` only.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Protocol, cast, runtime_checkable

from qma.core.ontology import ActorId, Quant
from qma.core.ports.tools import ToolKind, ToolRecord, default_rung_for_kind
from qma.core.vocabulary.enums import ExecutionEnvironmentKind
from qma.core.vocabulary.handles import is_forbidden_live_money_path_target
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "ANALYSIS_BACKTEST_PLUGIN_ID",
    "QMB_BACKTEST_TOOL_ID",
    "QMB_BACKTEST_TOOL_LOCAL_ID",
    "QMB_CLI_ARGV",
    "QMB_CLI_PROGRAM",
    "QMB_DOOR_KINDS",
    "QMB_MCP_METHOD",
    "QMB_OWNED_CONCERNS",
    "QMB_ROUTE",
    "QMB_WORLD_REPLAY",
    "VENUE_ACCOUNT_REQUEST_FIELDS",
    "QmbBacktestRequest",
    "QmbDoorInvocation",
    "QmbDoorKind",
    "QmbDoorReceipt",
    "QmbDoorTransport",
    "admit_qmb_job",
    "build_qmb_door_invocation",
    "environment_kind_from_ref",
    "occupying_qmb_job",
    "parse_qmb_backtest_request",
    "qma_owns_backtest_concern",
    "qmb_backtest_tool_record",
    "refuse_qmb_import_edge",
    "refuse_qmb_owned_concern",
    "refuse_second_qmb_job",
    "refuse_venue_account_backtest",
    "release_qmb_job",
]


ANALYSIS_BACKTEST_PLUGIN_ID: Final[str] = "analysis-backtest"
QMB_BACKTEST_TOOL_LOCAL_ID: Final[str] = "qmb"
QMB_BACKTEST_TOOL_ID: Final[str] = f"{ANALYSIS_BACKTEST_PLUGIN_ID}:{QMB_BACKTEST_TOOL_LOCAL_ID}"
QMB_CLI_PROGRAM: Final[str] = "qmb"
QMB_CLI_ARGV: Final[tuple[str, ...]] = ("backtest", "run")
QMB_MCP_METHOD: Final[str] = "qmb.backtest.run"
QMB_WORLD_REPLAY: Final[str] = "replay"
QMB_ROUTE: Final[tuple[str, ...]] = (
    "agent",
    "qma_backtest_tool",
    "backtesting_service",
    "qmb_door",
    "qmb",
)
QMB_OWNED_CONCERNS: Final[frozenset[str]] = frozenset(
    {
        "intra_node_parallelism",
        "run_ledger",
        "artifact_contract",
    }
)
VENUE_ACCOUNT_REQUEST_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "account",
        "account_id",
        "account_role",
        "binding",
        "book_mode",
        "broker",
        "broker_id",
        "demo",
        "live",
        "live_account",
        "order",
        "paper",
        "paper_account",
        "position",
        "seat",
        "trading_account",
        "venue",
        "venue_account",
        "venue_id",
    }
)
_NON_REPLAY_WORLDS: Final[frozenset[str]] = frozenset(
    {
        "paper",
        "live",
        "demo",
        "simulated",
        "account",
    }
)


class QmbDoorKind(StrEnum):
    """Closed QMB door kinds. CLI ships first; MCP is the sibling door."""

    CLI = "cli"
    MCP = "mcp"


QMB_DOOR_KINDS: Final[tuple[QmbDoorKind, ...]] = tuple(QmbDoorKind)


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def refuse_second_qmb_job(
    *,
    environment_ref: str,
    occupying_job_id: str,
) -> TypedRefusal:
    """Second ``qmb`` job in one environment — parent policy rejection (CT-47)."""
    return _policy(
        "qmb_job",
        "placing more than one qmb job per environment is refused (CT-47; DEC-0316; FR-Q55)",
        environment_ref=environment_ref,
        occupying_job_id=occupying_job_id,
    )


def refuse_venue_account_backtest(
    *,
    field: str,
    given: object,
) -> TypedRefusal:
    """Backtests never target a venue account of any role, paper included."""
    return _policy(
        field,
        "a QMB door request runs only against recorded evidence and QMB replay, "
        "never against any venue account (CT-47; SCN-0014; FR-Q55)",
        given=repr(given),
        world=QMB_WORLD_REPLAY,
    )


def refuse_qmb_import_edge(*, given: object = "qmb") -> TypedRefusal:
    """The QMB door is a runtime interaction — no package-import edge."""
    return _policy(
        "import",
        "the QMB door is a runtime interaction with no package-import edge to QMB "
        "(CT-47; DEC-0347; FR-Q55)",
        given=repr(given),
    )


def refuse_qmb_owned_concern(*, concern: str) -> TypedRefusal:
    """QMA does not take QMB's parallelism, run ledger, or artifact contract."""
    return _policy(
        "qmb_owned",
        "QMB retains intra-node parallelism, its run ledger, and its artifact "
        "contract; the Backtesting Service holds no scheduling authority, "
        "parallelism, or durable backtest state of its own (CT-47; FR-Q55)",
        concern=concern,
        owner="qmb",
    )


def qma_owns_backtest_concern(concern: str) -> bool:
    """QMA never owns QMB backtest concerns. ``concern`` is accepted for callers."""
    _ = concern
    return False


def environment_kind_from_ref(value: object) -> Result[str]:
    """Resolve an environment ref onto the ExecutionEnvironment kind token."""
    if not isinstance(value, str) or value.strip() == "":
        return _invalid("environment_ref", "QMB door request requires environment_ref")
    token = value.strip()
    if token.startswith("env:"):
        token = token[4:]
    for kind in ExecutionEnvironmentKind:
        if token == kind.value:
            return Ok(kind.value)
        if token.startswith(f"{kind.value}-") or token.startswith(f"{kind.value}:"):
            return Ok(kind.value)
    return Ok(token)


def occupying_qmb_job(
    occupancy: Mapping[str, str],
    occupancy_key: str,
) -> str | None:
    """Return the occupying ``qmb`` job id for one environment, if any."""
    return occupancy.get(occupancy_key)


def admit_qmb_job(
    occupancy: Mapping[str, str],
    *,
    occupancy_key: str,
    job_id: str,
) -> Result[dict[str, str]]:
    """Admit one ``qmb`` job per environment; a second job is refused."""
    existing = occupancy.get(occupancy_key)
    if existing is not None:
        return refuse_second_qmb_job(
            environment_ref=occupancy_key,
            occupying_job_id=existing,
        )
    nxt = dict(occupancy)
    nxt[occupancy_key] = job_id
    return Ok(nxt)


def release_qmb_job(
    occupancy: Mapping[str, str],
    *,
    occupancy_key: str,
    job_id: str,
) -> dict[str, str]:
    """Drop occupancy when the occupying job id still matches."""
    nxt = dict(occupancy)
    if nxt.get(occupancy_key) == job_id:
        del nxt[occupancy_key]
    return nxt


def qmb_backtest_tool_record() -> ToolRecord:
    """The one Tool Registry entry for the analysis-backtest daemon half."""
    return ToolRecord(
        tool_id=QMB_BACKTEST_TOOL_ID,
        kind=ToolKind.BACKTEST,
        capability_rung=default_rung_for_kind(ToolKind.BACKTEST),
        schema={
            "name": QMB_BACKTEST_TOOL_LOCAL_ID,
            "door": [kind.value for kind in QMB_DOOR_KINDS],
            "world": QMB_WORLD_REPLAY,
            "route": list(QMB_ROUTE),
            "plugin_id": ANALYSIS_BACKTEST_PLUGIN_ID,
        },
        acts=frozenset({"backtest"}),
        tags=frozenset({"qmb_door", "replay_only", "recorded_evidence"}),
        plugin_id=ANALYSIS_BACKTEST_PLUGIN_ID,
    )


def _parse_owner(owner: object) -> Result[ActorId]:
    if isinstance(owner, ActorId):
        return Ok(owner)
    if isinstance(owner, Quant):
        return Ok(owner.actor_id)
    return ActorId.try_create(owner)


def _venue_field_hits(extra: Mapping[str, object] | None) -> tuple[str, ...]:
    if extra is None:
        return ()
    return tuple(key for key in extra if key in VENUE_ACCOUNT_REQUEST_FIELDS)


@dataclass(frozen=True, slots=True)
class QmbBacktestRequest:
    """Agent-facing QMA backtest tool request. Replay + recorded evidence only."""

    owner: ActorId
    task_id: str
    environment_ref: str
    experiment_spec_fp1: str
    evidence_ref: str
    occupancy_key: str
    world: str = QMB_WORLD_REPLAY
    door: QmbDoorKind = QmbDoorKind.CLI
    recorded: bool = True
    tool_id: str = QMB_BACKTEST_TOOL_ID

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "owner": self.owner.value,
                "task_id": self.task_id,
                "environment_ref": self.environment_ref,
                "occupancy_key": self.occupancy_key,
                "experiment_spec_fp1": self.experiment_spec_fp1,
                "evidence_ref": self.evidence_ref,
                "world": self.world,
                "door": self.door.value,
                "recorded": self.recorded,
                "tool_id": self.tool_id,
                "route": list(QMB_ROUTE),
            }
        )

    @classmethod
    def try_create(
        cls,
        *,
        owner: object,
        task_id: object,
        environment_ref: object,
        experiment_spec_fp1: object,
        evidence_ref: object,
        world: object = QMB_WORLD_REPLAY,
        door: object = QmbDoorKind.CLI,
        recorded: object = True,
        tool_id: object = QMB_BACKTEST_TOOL_ID,
        extra: Mapping[str, object] | None = None,
        account: object = None,
        venue: object = None,
        paper: object = None,
        live: object = None,
    ) -> Result[QmbBacktestRequest]:
        for field, given in (
            ("account", account),
            ("venue", venue),
            ("paper", paper),
            ("live", live),
        ):
            if given is not None:
                return refuse_venue_account_backtest(field=field, given=given)
        hits = _venue_field_hits(extra)
        if hits:
            return refuse_venue_account_backtest(field=hits[0], given=extra)
        if not isinstance(task_id, str) or task_id.strip() == "":
            return _invalid("task_id", "QMB door request requires a task_id")
        if not isinstance(experiment_spec_fp1, str) or experiment_spec_fp1.strip() == "":
            return _invalid(
                "experiment_spec_fp1",
                "QMB door request requires a recorded ExperimentSpec fp1",
            )
        if not isinstance(evidence_ref, str) or evidence_ref.strip() == "":
            return _invalid(
                "evidence_ref",
                "QMB door request requires a recorded evidence reference",
            )
        if is_forbidden_live_money_path_target(evidence_ref):
            return refuse_venue_account_backtest(field="evidence_ref", given=evidence_ref)
        if recorded is not True:
            return refuse_venue_account_backtest(field="recorded", given=recorded)
        if world != QMB_WORLD_REPLAY:
            field = "world"
            if isinstance(world, str) and world.strip().casefold() in _NON_REPLAY_WORLDS:
                return refuse_venue_account_backtest(field=field, given=world)
            return _invalid(
                "world",
                "QMB door requests run world=replay only (CT-47; FR-Q55)",
                given=repr(world),
            )
        if tool_id != QMB_BACKTEST_TOOL_ID:
            return _invalid(
                "tool_id",
                "the Backtesting Service exposes one Tool Registry entry "
                f"{QMB_BACKTEST_TOOL_ID} (CT-47; FR-Q55)",
                given=repr(tool_id),
            )
        parsed_owner = _parse_owner(owner)
        if not isinstance(parsed_owner, Ok):
            return parsed_owner
        parsed_env = environment_kind_from_ref(environment_ref)
        if not isinstance(parsed_env, Ok):
            return parsed_env
        try:
            resolved_door = (
                door if isinstance(door, QmbDoorKind) else parse_closed(QmbDoorKind, door)
            )
        except VocabularyError as exc:
            return _invalid("door", str(exc), given=repr(door))
        env_ref = environment_ref.strip() if isinstance(environment_ref, str) else parsed_env.value
        return Ok(
            cls(
                owner=parsed_owner.value,
                task_id=task_id.strip(),
                environment_ref=env_ref,
                experiment_spec_fp1=experiment_spec_fp1.strip(),
                evidence_ref=evidence_ref.strip(),
                occupancy_key=parsed_env.value,
                world=QMB_WORLD_REPLAY,
                door=resolved_door,
                recorded=True,
                tool_id=QMB_BACKTEST_TOOL_ID,
            )
        )


def parse_qmb_backtest_request(**fields: object) -> Result[QmbBacktestRequest]:
    """Result-returning QMB door request constructor (CT-47; FR-Q55)."""
    extra_raw = fields.get("extra")
    extra: Mapping[str, object] | None
    if extra_raw is None:
        extra = None
    elif isinstance(extra_raw, Mapping):
        mapping = cast("Mapping[object, object]", extra_raw)
        extra = {str(key): value for key, value in mapping.items()}
    else:
        return _invalid("extra", "extra must be an object when present")
    return QmbBacktestRequest.try_create(
        owner=fields.get("owner"),
        task_id=fields.get("task_id"),
        environment_ref=fields.get("environment_ref"),
        experiment_spec_fp1=fields.get("experiment_spec_fp1"),
        evidence_ref=fields.get("evidence_ref"),
        world=fields.get("world", QMB_WORLD_REPLAY),
        door=fields.get("door", QmbDoorKind.CLI),
        recorded=fields.get("recorded", True),
        tool_id=fields.get("tool_id", QMB_BACKTEST_TOOL_ID),
        extra=extra,
        account=fields.get("account"),
        venue=fields.get("venue"),
        paper=fields.get("paper"),
        live=fields.get("live"),
    )


@dataclass(frozen=True, slots=True)
class QmbDoorInvocation:
    """Runtime interaction with the ``qmb`` CLI or MCP door. Never an import."""

    program: str
    kind: QmbDoorKind
    argv: tuple[str, ...]
    payload: Mapping[str, object]
    import_edge: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))
        object.__setattr__(self, "argv", tuple(self.argv))

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "program": self.program,
                "kind": self.kind.value,
                "argv": list(self.argv),
                "payload": dict(self.payload),
                "import_edge": self.import_edge,
            }
        )


@dataclass(frozen=True, slots=True)
class QmbDoorReceipt:
    """Acknowledgement that the door accepted a runtime interaction."""

    job_id: str
    environment_ref: str
    occupancy_key: str
    door: QmbDoorKind
    program: str
    argv: tuple[str, ...]
    world: str = QMB_WORLD_REPLAY
    route: tuple[str, ...] = QMB_ROUTE
    import_edge: bool = False

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "job_id": self.job_id,
                "environment_ref": self.environment_ref,
                "occupancy_key": self.occupancy_key,
                "door": self.door.value,
                "program": self.program,
                "argv": list(self.argv),
                "world": self.world,
                "route": list(self.route),
                "import_edge": self.import_edge,
            }
        )


def build_qmb_door_invocation(
    request: QmbBacktestRequest,
    *,
    job_id: str,
) -> Result[QmbDoorInvocation]:
    """Build a CLI/MCP invocation. Payload carries refs; QMA does not re-specify QMB."""
    if not job_id.strip():
        return _invalid("job_id", "QMB door invocation requires a job id")
    argv = QMB_CLI_ARGV if request.door is QmbDoorKind.CLI else (QMB_MCP_METHOD,)
    payload: dict[str, object] = {
        "job_id": job_id,
        "experiment_spec_fp1": request.experiment_spec_fp1,
        "evidence_ref": request.evidence_ref,
        "environment_ref": request.environment_ref,
        "occupancy_key": request.occupancy_key,
        "world": QMB_WORLD_REPLAY,
        "recorded": True,
        "import_edge": False,
        "owned_by": "qmb",
        "qma_re_specifies": False,
        "qmb_owned": sorted(QMB_OWNED_CONCERNS),
        "route": list(QMB_ROUTE),
    }
    if request.door is QmbDoorKind.MCP:
        payload["method"] = QMB_MCP_METHOD
    return Ok(
        QmbDoorInvocation(
            program=QMB_CLI_PROGRAM,
            kind=request.door,
            argv=argv,
            payload=payload,
            import_edge=False,
        )
    )


@runtime_checkable
class QmbDoorTransport(Protocol):
    """Runtime door. Implementations must not import the ``qmb`` package."""

    def submit(self, invocation: QmbDoorInvocation) -> Result[QmbDoorReceipt]:
        """Deliver one invocation over CLI argv or MCP. Never ``import qmb``."""
        ...
