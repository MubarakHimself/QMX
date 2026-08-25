"""Compose fill, slippage, cost, and financing from one resolved run-config (B-6).

Binding happens only from the resolved, read-only run-config — never by ambient
discovery or a code change (B-3, B-1). Composition order is fill → slippage →
cost. Financing is a scheduled position-level cash event, not an order fill.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final, Protocol, cast, runtime_checkable

from qmf.core.chrono import Duration
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal

from qmb._refuse import clean_token, invalid
from qmb.config.compiler import (
    CLOCK_REPLAY,
    PROVENANCE_SYNTHETIC_TAINTED,
    ResolvedRunConfig,
)
from qmb.execution.adapters import (
    AMBIENT_DISCOVERY,
    COST_ADAPTER_CATALOG,
    FILL_ADAPTER_CATALOG,
    FINANCING_ADAPTER_SCHEDULED,
    SLIPPAGE_ADAPTER_CATALOG,
    DeclaredPathFillAdapter,
    FinancingScheduler,
)
from qmb.execution.fidelity import FidelityIdentity, RunFidelity, compute_run_fidelity
from qmb.execution.fill import (
    FILL_BASES,
    FILL_BASIS_KEY,
    FILL_BASIS_WORST_CASE,
    STALE_PRICE_SPAN_KEY,
)
from qmb.execution.ports import (
    COMPOSITION_ORDER,
    COMPOSITION_VERSION,
    PORT_ROLES,
    TAINT_OPTIMISTIC,
    CostedFill,
    ExecutionPorts,
    NoFill,
    execute_authorized,
    refuse_optimistic_edge_claim,
    refuse_store_synthetic_governed_evidence,
    require_authorized_intent,
)
from qmb.execution.slippage import (
    SLIPPAGE_APPLY_TO_PASSIVE_KEY,
    SLIPPAGE_CALIBRATION_KEY,
    SLIPPAGE_SEED_KEY,
    SlippageCalibration,
    derive_slippage_seed,
)

__all__ = [
    "AMBIENT_DISCOVERY",
    "BOUND_FROM_RESOLVED_CONFIG",
    "COST_ADAPTER_KEY",
    "FILL_ADAPTER_KEY",
    "FINANCING_SCHEDULE_KEY",
    "SLIPPAGE_ADAPTER_KEY",
    "BoundExecution",
    "bind_execution_ports",
    "composition_identity",
    "fingerprint_composition",
]

BOUND_FROM_RESOLVED_CONFIG: Final[bool] = True
FILL_ADAPTER_KEY: Final[str] = "fill_adapter"
SLIPPAGE_ADAPTER_KEY: Final[str] = "slippage_adapter"
COST_ADAPTER_KEY: Final[str] = "cost_adapter"
FINANCING_SCHEDULE_KEY: Final[str] = "financing_schedule"


def composition_identity() -> dict[str, object]:
    """Identity-bearing binder fields. Package SemVer is omitted."""
    return {
        "ambient_discovery": AMBIENT_DISCOVERY,
        "bound_from": "resolved-run-config",
        "composition_order": COMPOSITION_ORDER,
        "composition_version": COMPOSITION_VERSION,
        "cost_adapter_ids": tuple(sorted(COST_ADAPTER_CATALOG)),
        "cost_adapter_key": COST_ADAPTER_KEY,
        "fill_adapter_ids": tuple(sorted(FILL_ADAPTER_CATALOG)),
        "fill_adapter_key": FILL_ADAPTER_KEY,
        "financing_adapter": FINANCING_ADAPTER_SCHEDULED,
        "financing_schedule_key": FINANCING_SCHEDULE_KEY,
        "port_roles": PORT_ROLES,
        "slippage_adapter_ids": tuple(sorted(SLIPPAGE_ADAPTER_CATALOG)),
        "slippage_adapter_key": SLIPPAGE_ADAPTER_KEY,
        "taint_field": TAINT_OPTIMISTIC,
    }


def fingerprint_composition() -> Result[Fingerprint]:
    """``fp1`` over :func:`composition_identity`."""
    return fingerprint(composition_identity())


@dataclass(frozen=True, slots=True)
class BoundExecution:
    """The four bound ports plus the run's fidelity identity."""

    config: ResolvedRunConfig
    ports: ExecutionPorts
    fidelity: RunFidelity
    fill_adapter_id: str
    slippage_adapter_id: str
    cost_adapter_id: str
    financing_schedule_ref: str
    composition_version: int = COMPOSITION_VERSION

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Taint is omitted (DEC-0164)."""
        return {
            "bound_from": "resolved-run-config",
            "class": "bound-execution",
            "composition_order": list(COMPOSITION_ORDER),
            "composition_version": self.composition_version,
            "config_fp1": self.config.fingerprint.value,
            "cost_adapter_id": self.cost_adapter_id,
            "fill_adapter_id": self.fill_adapter_id,
            "fidelity": self.fidelity.fp1_identity(),
            "financing_schedule_ref": self.financing_schedule_ref,
            "slippage_adapter_id": self.slippage_adapter_id,
        }

    def execute(
        self,
        *,
        intent: object,
        path: object,
        requested_quantity: object,
        position_cap: object,
        lot_step: object,
        entry_price: object = None,
        exit_logic_ref: object = None,
        module: object = None,
        book_resolved_requested_r: object = None,
        order: object = None,
    ) -> Result[CostedFill | NoFill]:
        """CT-23 authorized intent only; full-loss before open; exits skip a new full-loss."""
        authorized = require_authorized_intent(intent)
        if is_refusal(authorized):
            return authorized
        claimed = refuse_optimistic_edge_claim(taint=self.fidelity.taint)
        if is_refusal(claimed):
            return claimed
        return execute_authorized(
            self.config.replay_binding,
            intent=authorized.value,
            ports=self.ports,
            path=path,
            requested_quantity=requested_quantity,
            position_cap=position_cap,
            lot_step=lot_step,
            data_provenance=self.config.data_provenance,
            entry_price=entry_price,
            exit_logic_ref=exit_logic_ref,
            module=module,
            book_resolved_requested_r=book_resolved_requested_r,
            order=order,
        )


def bind_execution_ports(config: object) -> Result[BoundExecution]:
    """Bind fill, slippage, cost, and financing from one resolved run-config.

    Adapter ids are looked up in the closed catalog. There is no ambient
    discovery. ``world=simulated`` is a policy rejection; replay-on-synthetic
    is invalid input (B-7, SC-06).
    """
    resolved = _require_config(config)
    if is_refusal(resolved):
        return resolved
    gated = _refuse_world(resolved.value)
    if is_refusal(gated):
        return gated
    claimed = refuse_optimistic_edge_claim()
    if is_refusal(claimed):
        return claimed
    fill_id = _require_adapter_id(resolved.value, FILL_ADAPTER_KEY, FILL_ADAPTER_CATALOG)
    if is_refusal(fill_id):
        return fill_id
    slip_id = _require_adapter_id(resolved.value, SLIPPAGE_ADAPTER_KEY, SLIPPAGE_ADAPTER_CATALOG)
    if is_refusal(slip_id):
        return slip_id
    cost_id = _require_adapter_id(resolved.value, COST_ADAPTER_KEY, COST_ADAPTER_CATALOG)
    if is_refusal(cost_id):
        return cost_id
    schedule = _require_schedule_ref(resolved.value)
    if is_refusal(schedule):
        return schedule
    fill = _build_fill(fill_id.value, resolved.value)
    if is_refusal(fill):
        return fill
    slippage = _build_slippage(slip_id.value, resolved.value)
    if is_refusal(slippage):
        return slippage
    cost = COST_ADAPTER_CATALOG[cost_id.value]()
    financing = FinancingScheduler(schedule_ref=schedule.value)
    ports = ExecutionPorts.try_create(fill.value, slippage.value, cost, financing)
    if is_refusal(ports):
        return ports
    identities = _stamp_bound(
        fill=fill.value,
        slippage=slippage.value,
        cost=cost,
        financing=financing,
    )
    if is_refusal(identities):
        return identities
    fidelity = compute_run_fidelity(identities.value)
    if is_refusal(fidelity):
        return fidelity
    return Ok(
        BoundExecution(
            config=resolved.value,
            ports=ports.value,
            fidelity=fidelity.value,
            fill_adapter_id=fill_id.value,
            slippage_adapter_id=slip_id.value,
            cost_adapter_id=cost_id.value,
            financing_schedule_ref=schedule.value,
        )
    )


def _build_fill(adapter_id: str, config: ResolvedRunConfig) -> Result[object]:
    cls = FILL_ADAPTER_CATALOG[adapter_id]
    basis = config.keys.get(FILL_BASIS_KEY, FILL_BASIS_WORST_CASE)
    token = basis if isinstance(basis, str) else clean_token(basis)
    if token is None:
        token = FILL_BASIS_WORST_CASE
    if token not in FILL_BASES:
        return invalid(
            FILL_BASIS_KEY,
            "fill basis is worst-case or optimistic-exact (FILL-4)",
            given=token,
            allowed=list(FILL_BASES),
        )
    span = config.keys.get(STALE_PRICE_SPAN_KEY)
    duration = span if isinstance(span, Duration) else None
    if cls is DeclaredPathFillAdapter:
        return Ok(DeclaredPathFillAdapter(fill_basis=token, stale_price_span=duration))
    return Ok(cls())


def _build_slippage(adapter_id: str, config: ResolvedRunConfig) -> Result[object]:
    raw = config.keys.get(SLIPPAGE_CALIBRATION_KEY)
    calibration = raw if isinstance(raw, SlippageCalibration) else None
    apply_passive = config.keys.get(SLIPPAGE_APPLY_TO_PASSIVE_KEY, False) is True
    seed_raw = config.keys.get(SLIPPAGE_SEED_KEY)
    seed: int | None = None
    if isinstance(seed_raw, int) and not isinstance(seed_raw, bool):
        seed = seed_raw
    else:
        derived = derive_slippage_seed(config.fingerprint)
        if not is_refusal(derived):
            seed = derived.value
    factory = cast(Any, SLIPPAGE_ADAPTER_CATALOG[adapter_id])
    return Ok(
        factory(
            calibration=calibration,
            apply_to_passive_limits=apply_passive,
            seed=seed,
        )
    )


def _require_config(value: object) -> Result[ResolvedRunConfig]:
    if isinstance(value, ResolvedRunConfig):
        return Ok(value)
    return invalid(
        "config",
        "execution binds only from a resolved, read-only run-config (B-3, B-6)",
        given=repr(type(value).__name__),
    )


def _refuse_world(config: ResolvedRunConfig) -> Result[World]:
    if config.clock == CLOCK_REPLAY and config.data_provenance == PROVENANCE_SYNTHETIC_TAINTED:
        return invalid(
            "clock",
            "a replay clock bound to synthetic-tainted data is invalid input; "
            "world is provenance-derived and B-7 wins (FM-3, DEC-0164)",
            clock=config.clock,
            data_provenance=config.data_provenance,
        )
    return refuse_store_synthetic_governed_evidence(config)


def _require_adapter_id(
    config: ResolvedRunConfig,
    key: str,
    catalog: Mapping[str, object],
) -> Result[str]:
    raw = config.keys.get(key)
    token = clean_token(raw)
    if token is None:
        return invalid(
            key,
            "adapters bind by adapter-id from the resolved run-config, never by "
            "passing a port object or ambient discovery (B-3, B-1, B-6)",
            given=repr(raw) if raw is None or isinstance(raw, str) else repr(type(raw).__name__),
            known=sorted(catalog),
        )
    if token not in catalog:
        return invalid(
            key,
            "unknown adapter-id; adapters bind only from the closed resolved-config "
            "catalog, never by ambient discovery (B-3, B-1)",
            given=token,
            known=sorted(catalog),
        )
    return Ok(token)


def _require_schedule_ref(config: ResolvedRunConfig) -> Result[str]:
    raw = config.keys.get(FINANCING_SCHEDULE_KEY)
    if raw is not None and not isinstance(raw, str):
        value = getattr(raw, "value", None)
        token = clean_token(value) if value is not None else None
        if token is not None:
            return Ok(token)
        return invalid(
            FINANCING_SCHEDULE_KEY,
            "a financing-schedule reference is a non-empty token on the resolved "
            "run-config, never an ambient lookup (B-6)",
            given=repr(type(raw).__name__),
        )
    token = clean_token(raw)
    if token is None:
        return invalid(
            FINANCING_SCHEDULE_KEY,
            "a resolved run-config names fill, slippage, and cost adapter ids "
            "plus a financing-schedule reference (B-6, AR-56)",
            given=repr(raw),
        )
    return Ok(token)


@runtime_checkable
class _FidelityStamper(Protocol):
    def fidelity(self) -> Result[FidelityIdentity]:
        """Stamp adapter-id + composition-version + taint."""
        ...


def _stamp_bound(
    *,
    fill: object,
    slippage: object,
    cost: object,
    financing: object,
) -> Result[tuple[FidelityIdentity, ...]]:
    stamped: list[FidelityIdentity] = []
    for role, adapter in (
        ("fill", fill),
        ("slippage", slippage),
        ("cost", cost),
        ("financing", financing),
    ):
        if not isinstance(adapter, _FidelityStamper):
            return invalid(
                role,
                "each bound adapter stamps a fidelity identity (B-6)",
                given=repr(type(adapter).__name__),
            )
        labelled = adapter.fidelity()
        if is_refusal(labelled):
            return labelled
        stamped.append(labelled.value)
    return Ok(tuple(stamped))
