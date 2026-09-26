"""Story 28.6 — machine-readable closure matrix for named node QA debt.

The paper-milestone gate resolves a separate story and evidence link for every
node QA-debt ID. A missing link fails; inherited or implicit coverage is
refused. Foundation debt stays foundation. The permanent battery is catalogued
with evidence; ruff / pyright / pytest are the factory gate. Nightly mutmut
covers the node money-path modules and is not a factory gate — a
zero-classified-mutant run fails closed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, cast

import tomllib
from qmf.core import Fingerprint, Ok, Result, TypedRefusal, fingerprint, is_refusal

from qmn.host._refuse import invalid, policy

__all__ = [
    "FACTORY_GATES",
    "FOUNDATION_DEBT_IDS",
    "MUTATION_MONEY_PATH_MODULES",
    "MUTMUT_CONFIG_RELATIVE",
    "MUTMUT_IS_FACTORY_GATE",
    "NODE_QA_DEBT_IDS",
    "NODE_QA_DEBT_ROWS",
    "PERMANENT_BATTERY_ITEMS",
    "QA_DEBT_MATRIX_CLASS",
    "QA_DEBT_MATRIX_FORMAT_VERSION",
    "QA_DEBT_MATRIX_SURFACE",
    "ZERO_CLASSIFIED_MUTANT_FAILS_CLOSED",
    "BatteryItem",
    "MutationStatus",
    "QaDebtClosureMatrix",
    "QaDebtGateInputs",
    "QaDebtRow",
    "evaluate_mutation_verdict",
    "refuse_foundation_reclassified",
    "refuse_inherited_or_implicit",
    "refuse_missing_qa_debt_link",
    "refuse_zero_classified_mutants",
    "run_paper_milestone_qa_debt_gate",
    "workspace_root",
]

QA_DEBT_MATRIX_SURFACE: Final[str] = "qmn.host.qa_debt_matrix"
QA_DEBT_MATRIX_CLASS: Final[str] = "paper-milestone-qa-debt-closure-matrix"
QA_DEBT_MATRIX_FORMAT_VERSION: Final[int] = 1
MUTMUT_IS_FACTORY_GATE: Final[bool] = False
ZERO_CLASSIFIED_MUTANT_FAILS_CLOSED: Final[bool] = True
MUTMUT_CONFIG_RELATIVE: Final[str] = "qa/_trace/battery/mutmut/qmn_mutmut_config.toml"

FACTORY_GATES: Final[tuple[str, ...]] = ("ruff", "pyright-strict", "pytest")

NODE_QA_DEBT_IDS: Final[tuple[str, ...]] = (
    "QMX-F045",
    "QMX-F046",
    "QMX-F062",
    "QMX-F063",
    "QMX-F064",
    "QMX-F067",
    "QMX-F068",
    "QMX-F069",
    "QMX-F102",
    "D008",
    "D010",
    "E15-F01",
    "E15-F02",
    "E15-F03",
    "E7-R28",
    "E9-F04",
    "E12-F01",
    "E12-F04",
    "E12-F05",
)

FOUNDATION_DEBT_IDS: Final[tuple[str, ...]] = (
    "QMX-F085",
    "QMX-F053",
    "QMX-F054",
    "QMX-F055",
    "QMX-F056",
    "QMX-F057",
    "QMX-F030",
    "QMX-F107",
    "E11-F04",
    "E11-F05",
    "E11-F06",
)

# Area -> repo-relative money-path module (AR-86 / DEC-0208).
MUTATION_MONEY_PATH_MODULES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "command_mint": "qmn/src/qmn/order/path.py",
        "door_wiring": "qmn/src/qmn/order/door.py",
        "drift_decomposition": "qmn/src/qmn/reconcile/residuals.py",
        "equity_derivation": "qmn/src/qmn/ledger/binding_ledger.py",
        "sizing": "qmn/src/qmn/capital/kill_line.py",
        "virtual_ledger_folds": "qmn/src/qmn/ledger/virtual.py",
    }
)

_STATUS_CLOSED: Final[str] = "closed"
_STATUS_LINKED: Final[str] = "linked"
_ALLOWED_STATUSES: Final[frozenset[str]] = frozenset({_STATUS_CLOSED, _STATUS_LINKED})
_FORBIDDEN_STATUSES: Final[frozenset[str]] = frozenset({"inherited", "implicit"})

_ID_INPUTS = "qa_debt.inputs"
_ID_MISSING = "qa_debt.missing_link"
_ID_INHERITED = "qa_debt.inherited_or_implicit"
_ID_FOUNDATION = "qa_debt.foundation_reclassified"
_ID_BATTERY = "qa_debt.battery"
_ID_ROSTER = "qa_debt.roster"
_ID_MUT_ZERO = "qa_debt.mutation_zero"
_ID_MUT_TRIAGE = "qa_debt.mutation_untriaged"
_ID_MUT_ROSTER = "qa_debt.mutation_roster"

_ALIASES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "F045": "QMX-F045",
        "F046": "QMX-F046",
        "F062": "QMX-F062",
        "F063": "QMX-F063",
        "F064": "QMX-F064",
        "F067": "QMX-F067",
        "F068": "QMX-F068",
        "F069": "QMX-F069",
        "F102": "QMX-F102",
        "F030": "QMX-F030",
        "F053": "QMX-F053",
        "F054": "QMX-F054",
        "F055": "QMX-F055",
        "F056": "QMX-F056",
        "F057": "QMX-F057",
        "F085": "QMX-F085",
        "F107": "QMX-F107",
    }
)


def workspace_root() -> Path:
    """Repository root that owns ``qmn/`` and ``qa/``."""
    return Path(__file__).resolve().parents[4]


def _posix(relative: str) -> str:
    return relative.replace("\\", "/")


def _resolve(root: Path, relative: str) -> Path:
    return root.joinpath(*_posix(relative).split("/"))


@dataclass(frozen=True, slots=True)
class QaDebtRow:
    """One named node QA-debt ID with a distinct story and evidence link."""

    debt_id: str
    story: str
    story_title: str
    evidence: tuple[str, ...]
    status: str
    closure_owner: str
    inherited: bool = False
    implicit: bool = False

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "closure_owner": self.closure_owner,
                "debt_id": self.debt_id,
                "evidence": list(self.evidence),
                "implicit": self.implicit,
                "inherited": self.inherited,
                "status": self.status,
                "story": self.story,
                "story_title": self.story_title,
            }
        )


@dataclass(frozen=True, slots=True)
class BatteryItem:
    """One permanent-battery gate with on-disk evidence."""

    name: str
    evidence: tuple[str, ...]
    factory_gate: bool = False

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "evidence": list(self.evidence),
                "factory_gate": self.factory_gate,
                "name": self.name,
            }
        )


@dataclass(frozen=True, slots=True)
class MutationStatus:
    """Nightly mutmut verdict for node money-path modules (AR-86)."""

    modules: Mapping[str, str]
    zero_classified_fails_closed: bool
    classified_killed: int | None
    classified_survived: int | None
    triaged_survivors: tuple[str, ...]
    status: str
    ran_in_factory: bool = False
    config_path: str = MUTMUT_CONFIG_RELATIVE

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "config_path": self.config_path,
            "modules": dict(self.modules),
            "ran_in_factory": self.ran_in_factory,
            "status": self.status,
            "triaged_survivors": list(self.triaged_survivors),
            "zero_classified_fails_closed": self.zero_classified_fails_closed,
        }
        if self.classified_killed is not None:
            body["classified_killed"] = self.classified_killed
        if self.classified_survived is not None:
            body["classified_survived"] = self.classified_survived
        return MappingProxyType(body)


@dataclass(frozen=True, slots=True)
class QaDebtClosureMatrix:
    """Fingerprinted machine-readable closure matrix (Story 28.6)."""

    format_version: int
    fingerprint: Fingerprint
    rows: tuple[QaDebtRow, ...]
    battery: tuple[BatteryItem, ...]
    mutation: MutationStatus
    foundation_debt: tuple[str, ...]
    factory_gates: tuple[str, ...]
    mutmut_is_factory_gate: bool
    ok: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "battery": [dict(item.as_mapping()) for item in self.battery],
            "class": QA_DEBT_MATRIX_CLASS,
            "debt_ids": [row.debt_id for row in self.rows],
            "factory_gates": list(self.factory_gates),
            "format_version": self.format_version,
            "foundation_debt": list(self.foundation_debt),
            "mutation": dict(self.mutation.as_mapping()),
            "mutmut_is_factory_gate": self.mutmut_is_factory_gate,
            "ok": self.ok,
            "rows": [dict(row.as_mapping()) for row in self.rows],
            "surface": QA_DEBT_MATRIX_SURFACE,
        }

    def as_mapping(self) -> Mapping[str, object]:
        body = self.fp1_identity()
        body["fingerprint"] = self.fingerprint.value
        return MappingProxyType(body)

    def to_json(self) -> str:
        """Stable JSON document for the paper-milestone gate."""
        return json.dumps(dict(self.as_mapping()), indent=2, sort_keys=True)


@dataclass(frozen=True, slots=True)
class QaDebtGateInputs:
    """Optional overrides for the paper-milestone QA-debt gate."""

    workspace: Path | None = None
    rows: tuple[QaDebtRow, ...] | None = None
    battery: tuple[BatteryItem, ...] | None = None
    mutation_killed: int | None = None
    mutation_survived: int | None = None
    triaged_survivors: tuple[str, ...] = ()
    reclassify_foundation: bool = False
    mark_inherited: bool = False
    mark_implicit: bool = False


def refuse_missing_qa_debt_link(**extra: object) -> TypedRefusal:
    """A named ID with no distinct story/evidence link fails the gate (AR-85)."""
    return policy(
        "qa_debt",
        "a missing story or evidence link fails the paper-milestone gate "
        "rather than marking the ID inherited or implicit (AR-85; FR-076)",
        failure_id=_ID_MISSING,
        **extra,
    )


def refuse_inherited_or_implicit(**extra: object) -> TypedRefusal:
    """Inherited or implicit coverage is not a discharge."""
    return policy(
        "qa_debt",
        "named node QA-debt IDs must carry their own story and evidence; "
        "inherited or implicit coverage is refused (AR-85)",
        failure_id=_ID_INHERITED,
        **extra,
    )


def refuse_foundation_reclassified(**extra: object) -> TypedRefusal:
    """Foundation debt stays foundation (DEC-0208 / NFR-21)."""
    return policy(
        "qa_debt",
        "foundation debt is not reclassified as node debt (DEC-0208; NFR-21)",
        failure_id=_ID_FOUNDATION,
        **extra,
    )


def refuse_zero_classified_mutants(**extra: object) -> TypedRefusal:
    """A zero-classified-mutant execution fails closed (AR-86)."""
    return policy(
        "mutation",
        "a zero-classified-mutant mutmut run fails closed and alerts rather "
        "than passing vacuously (AR-86; DEC-0208)",
        failure_id=_ID_MUT_ZERO,
        **extra,
    )


def evaluate_mutation_verdict(
    *,
    classified_killed: int,
    classified_survived: int,
    triaged_survivors: Sequence[str] = (),
) -> Result[str]:
    """Triage classified survivors; zero classified mutants fail closed."""
    if classified_killed < 0 or classified_survived < 0:
        return invalid(
            "mutation",
            "classified mutant counts cannot be negative",
            killed=classified_killed,
            survived=classified_survived,
            failure_id=_ID_INPUTS,
        )
    total = classified_killed + classified_survived
    if total == 0:
        return refuse_zero_classified_mutants(
            classified_killed=classified_killed,
            classified_survived=classified_survived,
        )
    triaged = frozenset(triaged_survivors)
    if classified_survived > 0 and len(triaged) < classified_survived:
        return policy(
            "mutation",
            "classified mutmut survivors must be triaged with evidence (AR-86)",
            failure_id=_ID_MUT_TRIAGE,
            classified_survived=classified_survived,
            triaged=len(triaged),
        )
    return Ok("pass")


def _row(
    debt_id: str,
    story: str,
    title: str,
    evidence: tuple[str, ...],
    *,
    status: str = _STATUS_CLOSED,
    closure_owner: str | None = None,
) -> QaDebtRow:
    owner = closure_owner if closure_owner is not None else story
    return QaDebtRow(
        debt_id=debt_id,
        story=story,
        story_title=title,
        evidence=evidence,
        status=status,
        closure_owner=owner,
    )


NODE_QA_DEBT_ROWS: Final[tuple[QaDebtRow, ...]] = (
    _row(
        "QMX-F045",
        "25.7",
        "Enforce human-only signers at the powers transport",
        (
            "qmn/src/qmn/doors/http/powers.py",
            "qmn/tests/test_qmn_powers.py",
            "qmn/src/qmn/host/security_probes.py",
            "qmn/tests/test_qmn_security_probes.py",
        ),
    ),
    _row(
        "QMX-F046",
        "26.10",
        "Persist promotion and activation through their closed journal paths",
        (
            "qmn/src/qmn/promotion/journal.py",
            "qmn/tests/test_qmn_promotion.py",
        ),
    ),
    _row(
        "QMX-F062",
        "24.6",
        "Enforce UNKNOWN at the exact command-stream boundary",
        (
            "qmn/src/qmn/order/unknown.py",
            "qmn/tests/test_qmn_unknown.py",
        ),
    ),
    _row(
        "QMX-F063",
        "24.7",
        "Prove amendment atomicity and preserve every tightening act",
        (
            "qmn/src/qmn/order/amend.py",
            "qmn/tests/test_qmn_amend.py",
        ),
    ),
    _row(
        "QMX-F064",
        "25.13",
        "Gate runtime hygiene, parameters, secrets, and boot reset",
        (
            "qmn/tests/test_qmn_hygiene.py",
            "qa/tests/epic_08/test_l0_f064_hygiene.py",
        ),
    ),
    _row(
        "QMX-F067",
        "26.11",
        "Prove runtime risk population, windows, shakedown, and cardinality",
        (
            "qmn/src/qmn/host/risk_population.py",
            "qmn/tests/test_qmn_risk_admission.py",
        ),
    ),
    _row(
        "QMX-F068",
        "26.12",
        "Enforce frozen R on the actual door path",
        (
            "qmn/src/qmn/order/door.py",
            "qmn/tests/test_qmn_order_door.py",
        ),
    ),
    _row(
        "QMX-F069",
        "26.13",
        "Gate failure completeness and journal-before-dispatch",
        (
            "qmn/src/qmn/observability/failures_gate.py",
            "qmn/tests/test_qmn_failures_gate.py",
            "qmn/src/qmn/journal_dispatch.py",
            "qmn/tests/test_qmn_journal_dispatch.py",
        ),
    ),
    _row(
        "QMX-F102",
        "27.5",
        "Close backup numerics, crypto, cadence, and custody debt",
        (
            "qmn/src/qmn/data/backup.py",
            "qmn/tests/test_qmn_backup.py",
        ),
    ),
    _row(
        "D008",
        "24.2",
        "Verify every live venue fact before use",
        (
            "qmn/src/qmn/venue/verify.py",
            "qmn/tests/test_qmn_verify.py",
        ),
    ),
    _row(
        "D010",
        "26.14",
        "Verify the complete runtime risk gate",
        (
            "qmn/src/qmn/host/runtime_risk_gate.py",
            "qmn/tests/test_qmn_runtime_risk_gate.py",
        ),
    ),
    _row(
        "E15-F01",
        "27.8",
        "Append exactly one terminal ledger record for every replay job",
        (
            "qmn/src/qmn/replay/ledger.py",
            "qmn/tests/test_qmn_replay_ledger.py",
        ),
    ),
    _row(
        "E15-F02",
        "26.19",
        "Prove seat concurrency and end-to-end backpressure",
        (
            "qmn/src/qmn/host/seat_concurrency.py",
            "qmn/tests/test_qmn_host_seat_concurrency.py",
        ),
    ),
    _row(
        "E15-F03",
        "26.16",
        "State the V1 seat-containment limit honestly",
        (
            "qmn/src/qmn/seats/containment_limit.py",
            "qmn/tests/test_qmn_seat_containment_limit.py",
        ),
    ),
    _row(
        "E7-R28",
        "25.14",
        "Enforce light/heavy claims at the composition root",
        (
            "qmn/src/qmn/host/light_heavy.py",
            "qmn/tests/test_qmn_light_heavy.py",
        ),
    ),
    _row(
        "E9-F04",
        "28.7",
        "Establish first-hours VPS and storage baselines",
        (
            "qmn/src/qmn/bench/baselines.py",
            "qmn/src/qmn/bench/schema.py",
            "qmn/src/qmn/bench/harness.py",
            "qmn/tests/test_qmn_bench.py",
            "qmn/tests/test_qmn_first_hours.py",
        ),
    ),
    _row(
        "E12-F01",
        "25.3",
        "Mint composition-root registry records once",
        (
            "qmn/src/qmn/host/registry_mint.py",
            "qmn/tests/test_qmn_host_registry.py",
        ),
    ),
    _row(
        "E12-F04",
        "25.4",
        "Persist composition lineage and occurrence evidence",
        (
            "qmn/src/qmn/host/lineage_persist.py",
            "qmn/tests/test_qmn_host_lineage.py",
        ),
    ),
    _row(
        "E12-F05",
        "26.15",
        "Prevent the ungoverned Python-bot tunnel from bypassing gates",
        (
            "qmn/src/qmn/seats/admission.py",
            "qmn/tests/test_qmn_seat_tunnel.py",
        ),
    ),
)

PERMANENT_BATTERY_ITEMS: Final[tuple[BatteryItem, ...]] = (
    BatteryItem("ruff", ("pyproject.toml",), factory_gate=True),
    BatteryItem("pyright-strict", ("pyproject.toml",), factory_gate=True),
    BatteryItem("pytest", ("pyproject.toml", "qmn/tests"), factory_gate=True),
    BatteryItem("coverage", ("pyproject.toml", "tools/coverage_report.py")),
    BatteryItem(
        "isolated-contract-suites",
        ("tools/isolated_build_check.py", "qmn/tests/test_qmn_port_contract.py"),
    ),
    BatteryItem("secret-scan", ("tools/secret_scan.py",)),
    BatteryItem("money-path-scan", ("tools/money_path_scan.py",)),
    BatteryItem("ambient-scan", ("tools/ambient_scan.py",)),
    BatteryItem("isolated-build", ("tools/isolated_build_check.py",)),
    BatteryItem("mock-data-scan", ("tools/mock_data_scan.py",)),
    BatteryItem(
        "skylos-iac",
        (".github/workflows/skylos.yml", "qmn/deploy/ci_lane.py", "pyproject.toml"),
    ),
    BatteryItem(
        "vulture",
        ("tools/vulture_gate.py", "qa/_trace/battery/vulture/gate-baseline-min80.txt"),
    ),
    BatteryItem("qa-requirements-first", ("qa/run_qa_verify.py", "qa/tests")),
    BatteryItem(
        "ubuntu-24.04",
        (".github/workflows/qmn-ubuntu-24.04.yml", "qmn/deploy/ci_lane.py"),
    ),
    BatteryItem(
        "systemd-check-mode",
        ("qmn/deploy/install.py", "qmn/deploy/justfile-recipes/node.just"),
    ),
    BatteryItem(
        "conformance",
        ("qmn/src/qmn/venue/conformance.py", "qmn/tests/test_qmn_conformance.py"),
    ),
    BatteryItem(
        "replay",
        ("qmn/src/qmn/replay/session.py", "qmn/tests/test_qmn_replay_day.py"),
    ),
    BatteryItem(
        "failure-register",
        ("qmn/FAILURES.md", "qmn/tests/test_qmn_failures_gate.py"),
    ),
    BatteryItem(
        "scenario-gates",
        ("qmn/src/qmn/host/golden_scenarios.py", "qmn/tests/test_qmn_golden_scenarios.py"),
    ),
)


def _canonical(debt_id: str) -> str:
    token = debt_id.strip()
    return _ALIASES.get(token, token)


def _missing_paths(root: Path, relatives: Sequence[str]) -> tuple[str, ...]:
    missing: list[str] = []
    for relative in relatives:
        path = _resolve(root, relative)
        if not path.exists():
            missing.append(_posix(relative))
    return tuple(missing)


def _mutation_config_modules(root: Path) -> Result[frozenset[str]]:
    path = _resolve(root, MUTMUT_CONFIG_RELATIVE)
    if not path.is_file():
        return policy(
            "mutation",
            "nightly mutmut config for node money-path modules is missing (AR-86)",
            failure_id=_ID_MUT_ROSTER,
            path=MUTMUT_CONFIG_RELATIVE,
        )
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return invalid(
            "mutation",
            "nightly mutmut config is unreadable",
            failure_id=_ID_MUT_ROSTER,
            path=MUTMUT_CONFIG_RELATIVE,
            error=type(exc).__name__,
        )
    mutate = payload.get("tool", {}).get("mutmut", {}).get("only_mutate")
    if not isinstance(mutate, list) or not mutate:
        return policy(
            "mutation",
            "nightly mutmut config must list node money-path only_mutate paths",
            failure_id=_ID_MUT_ROSTER,
            path=MUTMUT_CONFIG_RELATIVE,
        )
    normalized: set[str] = set()
    for item in cast("list[object]", mutate):
        if not isinstance(item, str) or item.strip() == "":
            continue
        token = _posix(item)
        if token.startswith("src/"):
            token = f"qmn/{token}"
        normalized.add(token)
    return Ok(frozenset(normalized))


def run_paper_milestone_qa_debt_gate(
    inputs: QaDebtGateInputs | None = None,
) -> Result[QaDebtClosureMatrix]:
    """Resolve every named node QA-debt ID plus the permanent battery."""
    spec = inputs if inputs is not None else QaDebtGateInputs()
    if spec.mark_inherited is True or spec.mark_implicit is True:
        return refuse_inherited_or_implicit(
            inherited=spec.mark_inherited,
            implicit=spec.mark_implicit,
        )
    if spec.reclassify_foundation is True:
        return refuse_foundation_reclassified(attempted=list(FOUNDATION_DEBT_IDS))

    root = spec.workspace if spec.workspace is not None else workspace_root()
    if not root.is_dir():
        return invalid(
            "workspace",
            "the QA-debt gate needs a workspace directory",
            given=str(root),
            failure_id=_ID_INPUTS,
        )

    rows = spec.rows if spec.rows is not None else NODE_QA_DEBT_ROWS
    battery = spec.battery if spec.battery is not None else PERMANENT_BATTERY_ITEMS
    if not rows:
        return refuse_missing_qa_debt_link(missing=list(NODE_QA_DEBT_IDS))

    seen: dict[str, QaDebtRow] = {}
    for row in rows:
        canonical = _canonical(row.debt_id)
        if canonical in FOUNDATION_DEBT_IDS:
            return refuse_foundation_reclassified(debt_id=canonical)
        if row.inherited is True or row.implicit is True:
            return refuse_inherited_or_implicit(
                debt_id=canonical,
                inherited=row.inherited,
                implicit=row.implicit,
            )
        if row.status in _FORBIDDEN_STATUSES:
            return refuse_inherited_or_implicit(debt_id=canonical, status=row.status)
        if row.status not in _ALLOWED_STATUSES:
            return refuse_missing_qa_debt_link(debt_id=canonical, status=row.status)
        if row.story.strip() == "" or not row.evidence:
            return refuse_missing_qa_debt_link(
                debt_id=canonical,
                story=row.story,
                evidence=list(row.evidence),
            )
        missing = _missing_paths(root, row.evidence)
        if missing:
            return refuse_missing_qa_debt_link(debt_id=canonical, missing_evidence=missing)
        seen[canonical] = row

    missing_ids = [debt_id for debt_id in NODE_QA_DEBT_IDS if debt_id not in seen]
    if missing_ids:
        return refuse_missing_qa_debt_link(missing=missing_ids)
    extra = sorted(debt_id for debt_id in seen if debt_id not in NODE_QA_DEBT_IDS)
    if extra:
        return policy(
            "qa_debt",
            "the node QA-debt roster is closed; extra IDs are refused",
            failure_id=_ID_ROSTER,
            extra=extra,
        )

    ordered = tuple(seen[debt_id] for debt_id in NODE_QA_DEBT_IDS)
    factory_names = {item.name for item in battery if item.factory_gate}
    if factory_names != set(FACTORY_GATES):
        return policy(
            "battery",
            "factory gates are ruff, pyright-strict, and pytest; mutmut is not",
            failure_id=_ID_BATTERY,
            factory_gates=sorted(factory_names),
            required=list(FACTORY_GATES),
        )
    mutmut_named = any(
        item.name in {"mutmut", "nightly-mutmut"} and item.factory_gate for item in battery
    )
    if mutmut_named or MUTMUT_IS_FACTORY_GATE:
        return policy(
            "battery",
            "mutmut is not a factory gate (AR-86)",
            failure_id=_ID_BATTERY,
        )

    battery_names = [item.name for item in battery]
    if len(set(battery_names)) != len(battery_names):
        return policy(
            "battery",
            "permanent battery item names must be unique",
            failure_id=_ID_BATTERY,
        )
    for item in battery:
        if not item.evidence:
            return policy(
                "battery",
                "every permanent battery item needs an evidence link",
                failure_id=_ID_BATTERY,
                name=item.name,
            )
        missing = _missing_paths(root, item.evidence)
        if missing:
            return policy(
                "battery",
                "permanent battery evidence is missing",
                failure_id=_ID_BATTERY,
                name=item.name,
                missing_evidence=missing,
            )

    configured = _mutation_config_modules(root)
    if is_refusal(configured):
        return configured
    expected = frozenset(MUTATION_MONEY_PATH_MODULES.values())
    if not expected <= configured.value:
        return policy(
            "mutation",
            "nightly mutmut must cover door wiring, command mint, equity, "
            "drift, sizing, and virtual-ledger folds (AR-86)",
            failure_id=_ID_MUT_ROSTER,
            missing=sorted(expected - configured.value),
        )
    module_missing = _missing_paths(root, tuple(MUTATION_MONEY_PATH_MODULES.values()))
    if module_missing:
        return policy(
            "mutation",
            "money-path mutation modules are missing on disk",
            failure_id=_ID_MUT_ROSTER,
            missing_evidence=module_missing,
        )

    killed = spec.mutation_killed
    survived = spec.mutation_survived
    if killed is not None or survived is not None:
        if killed is None or survived is None:
            return invalid(
                "mutation",
                "classified killed and survived counts must be supplied together",
                failure_id=_ID_INPUTS,
            )
        verdict = evaluate_mutation_verdict(
            classified_killed=killed,
            classified_survived=survived,
            triaged_survivors=spec.triaged_survivors,
        )
        if is_refusal(verdict):
            return verdict
        mutation_state = verdict.value
    else:
        mutation_state = "configured"

    mutation = MutationStatus(
        modules=MappingProxyType(dict(MUTATION_MONEY_PATH_MODULES)),
        zero_classified_fails_closed=ZERO_CLASSIFIED_MUTANT_FAILS_CLOSED,
        classified_killed=killed,
        classified_survived=survived,
        triaged_survivors=tuple(spec.triaged_survivors),
        status=mutation_state,
        ran_in_factory=False,
    )
    identity = {
        "battery": [dict(item.as_mapping()) for item in battery],
        "class": QA_DEBT_MATRIX_CLASS,
        "debt_ids": [row.debt_id for row in ordered],
        "factory_gates": list(FACTORY_GATES),
        "format_version": QA_DEBT_MATRIX_FORMAT_VERSION,
        "foundation_debt": list(FOUNDATION_DEBT_IDS),
        "mutation": dict(mutation.as_mapping()),
        "mutmut_is_factory_gate": MUTMUT_IS_FACTORY_GATE,
        "ok": True,
        "rows": [dict(row.as_mapping()) for row in ordered],
        "surface": QA_DEBT_MATRIX_SURFACE,
    }
    stamped = fingerprint(identity)
    if is_refusal(stamped):
        return stamped
    return Ok(
        QaDebtClosureMatrix(
            format_version=QA_DEBT_MATRIX_FORMAT_VERSION,
            fingerprint=stamped.value,
            rows=ordered,
            battery=battery,
            mutation=mutation,
            foundation_debt=FOUNDATION_DEBT_IDS,
            factory_gates=FACTORY_GATES,
            mutmut_is_factory_gate=MUTMUT_IS_FACTORY_GATE,
            ok=True,
        )
    )
