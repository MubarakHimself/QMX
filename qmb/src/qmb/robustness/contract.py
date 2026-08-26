"""The versioned statistical-procedure contract for the B-14 robustness ladder (AC1, AC5, AC6).

Every ladder procedure (22.2-22.5) — Monte Carlo trade-shuffle, Monte Carlo
candle-perturbation, the rule-significance gate, and walk-forward — is a **pure
library function under B-4**: it consumes a resolved run-config plus data reads,
RETURNS its result, and writes no log and no ledger line (the Epic 15 orchestrator
owns every append). No module-global mutable state exists anywhere in the module.

Each procedure's exact mechanics are pinned by a versioned contract that stamps its
own AD-5 integer format version (:data:`ROBUSTNESS_CONTRACT_FORMAT_VERSION`, format
version 1). The stamp is what keeps every old ledger entry readable forever: a later
build that changes a procedure's mechanics mints a new format version rather than
silently redefining the old one (AD-5, AC1).

Every procedure produces **robustness or infra-stress** evidence only. Its claim
class is never edge (L20, B-7), and no output can gate live money or spend split
budget while the GAP-0048 fidelity seam is open (SC-06, AC6). Every threshold and
every iteration / scenario / block-length / minimum-observation input is a
UI-editable configurable carrying no ratified platform value; the module ships no
invented default, and an unset required input is a typed ``invalid input`` refusal
rather than a silently-applied number (NFR-07, AR-13, SC-07, AC5).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal

from qmb._refuse import clean_token, invalid, policy

__all__ = [
    "CLAIM_CLASS_EDGE",
    "CLAIM_CLASS_INFRA_STRESS",
    "CLAIM_CLASS_ROBUSTNESS",
    "CLAIM_GATED_BEHIND",
    "CONFIGURABLE_INPUTS_HAVE_RATIFIED_VALUE",
    "CONFIGURABLE_INPUT_DIMENSIONS",
    "MODULE_HAS_GLOBAL_MUTABLE_STATE",
    "MODULE_SHIPS_INVENTED_DEFAULT",
    "PROCEDURE_GATES_LIVE_MONEY",
    "PROCEDURE_IS_PURE_LIBRARY_FUNCTION",
    "PROCEDURE_MAKES_EDGE_CLAIM",
    "PROCEDURE_MC_CANDLE_PERTURBATION",
    "PROCEDURE_MC_TRADE_SHUFFLE",
    "PROCEDURE_RULE_SIGNIFICANCE",
    "PROCEDURE_SPENDS_SPLIT_BUDGET",
    "PROCEDURE_WALK_FORWARD",
    "PROCEDURE_WRITES_LEDGER_LINE",
    "PROCEDURE_WRITES_LOG",
    "ROBUSTNESS_CLAIM_CLASSES",
    "ROBUSTNESS_CONTRACT_FORMAT_VERSION",
    "ROBUSTNESS_PROCEDURES",
    "THRESHOLDS_DEFERRED_TO",
    "StatisticalProcedureContract",
    "contract_identity",
    "procedure_contract",
    "refuse_edge_claim",
    "refuse_live_money_gate",
    "require_configurable",
    "require_positive_int",
]

# AD-5 integer format version stamped on every procedure contract. Format version 1
# pins the ladder's exact mechanics; a later mechanics change mints a new version
# rather than redefining this one, so every old ledger entry stays readable forever.
ROBUSTNESS_CONTRACT_FORMAT_VERSION: Final[int] = 1

# The four B-14 robustness rungs, each exposed (22.2-22.5) as a pure library
# function. Names are the identity-bearing procedure keys the contract pins.
PROCEDURE_MC_TRADE_SHUFFLE: Final[str] = "monte-carlo-trade-shuffle"
PROCEDURE_MC_CANDLE_PERTURBATION: Final[str] = "monte-carlo-candle-perturbation"
PROCEDURE_RULE_SIGNIFICANCE: Final[str] = "rule-significance"
PROCEDURE_WALK_FORWARD: Final[str] = "walk-forward"
ROBUSTNESS_PROCEDURES: Final[tuple[str, ...]] = (
    PROCEDURE_MC_TRADE_SHUFFLE,
    PROCEDURE_MC_CANDLE_PERTURBATION,
    PROCEDURE_RULE_SIGNIFICANCE,
    PROCEDURE_WALK_FORWARD,
)

# The B-4 purity guarantee, shared by every rung: a procedure is a pure function
# that returns its result and appends nothing. All impurity stays in the Epic 15
# orchestrator, and no module-global mutable state exists in the module.
PROCEDURE_IS_PURE_LIBRARY_FUNCTION: Final[bool] = True
PROCEDURE_WRITES_LEDGER_LINE: Final[bool] = False
PROCEDURE_WRITES_LOG: Final[bool] = False
MODULE_HAS_GLOBAL_MUTABLE_STATE: Final[bool] = False

# The claim-class law (L20, B-7, SC-06). A robustness procedure produces robustness
# or infra-stress evidence only; it never claims edge, never gates live money, and
# never spends split budget while the GAP-0048 fidelity seam is open.
CLAIM_CLASS_ROBUSTNESS: Final[str] = "robustness"
CLAIM_CLASS_INFRA_STRESS: Final[str] = "infra-stress"
CLAIM_CLASS_EDGE: Final[str] = "edge"
ROBUSTNESS_CLAIM_CLASSES: Final[tuple[str, ...]] = (
    CLAIM_CLASS_ROBUSTNESS,
    CLAIM_CLASS_INFRA_STRESS,
)
PROCEDURE_MAKES_EDGE_CLAIM: Final[bool] = False
PROCEDURE_GATES_LIVE_MONEY: Final[bool] = False
PROCEDURE_SPENDS_SPLIT_BUDGET: Final[bool] = False
CLAIM_GATED_BEHIND: Final[str] = "GAP-0048"

# The threshold-and-battery deferral (SC-07). Every threshold value and every pass
# battery (the MC-1000 / PBO / CSCV candidates) is deferred; nothing is invented here.
THRESHOLDS_DEFERRED_TO: Final[str] = "GAP-0048/GAP-0049"

# The UI-editable configurable inputs every ladder procedure declares (NFR-07). Each
# carries NO ratified platform value; the module ships no invented default, and an
# unset required input is a typed refusal (AR-13). These names describe the input
# dimensions the rungs resolve through :func:`require_positive_int`.
CONFIGURABLE_INPUT_DIMENSIONS: Final[tuple[str, ...]] = (
    "block_length",
    "iterations",
    "minimum_observations",
    "scenarios",
    "threshold",
)
CONFIGURABLE_INPUTS_HAVE_RATIFIED_VALUE: Final[bool] = False
MODULE_SHIPS_INVENTED_DEFAULT: Final[bool] = False

_PROCEDURE_CONTRACT_CLASS: Final[str] = "qmb-statistical-procedure-contract"


@dataclass(frozen=True, slots=True)
class StatisticalProcedureContract:
    """One versioned statistical-procedure contract pinning a rung's mechanics (AC1).

    Identity is the procedure key plus the AD-5 format version and the shared
    purity / claim-class declarations. Package SemVer is never in identity.
    """

    procedure: str
    contract_format_version: int

    def fp1_identity(self) -> dict[str, object]:
        """The identity-bearing contract content. Package SemVer is excluded."""
        return {
            "claim_classes": ROBUSTNESS_CLAIM_CLASSES,
            "class": _PROCEDURE_CONTRACT_CLASS,
            "contract_format_version": self.contract_format_version,
            "gated_behind": CLAIM_GATED_BEHIND,
            "gates_live_money": PROCEDURE_GATES_LIVE_MONEY,
            "makes_edge_claim": PROCEDURE_MAKES_EDGE_CLAIM,
            "procedure": self.procedure,
            "pure_library_function": PROCEDURE_IS_PURE_LIBRARY_FUNCTION,
            "spends_split_budget": PROCEDURE_SPENDS_SPLIT_BUDGET,
            "writes_ledger_line": PROCEDURE_WRITES_LEDGER_LINE,
            "writes_log": PROCEDURE_WRITES_LOG,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """The qmf-core ``fp1`` over :meth:`fp1_identity`."""
        return fingerprint(self.fp1_identity())


def procedure_contract(procedure: object) -> Result[StatisticalProcedureContract]:
    """Build the versioned contract for one B-14 rung, value-or-refusal (AC1).

    A procedure key outside :data:`ROBUSTNESS_PROCEDURES` is a typed ``invalid
    input`` refusal — the roster is closed, and no unknown rung is contracted.
    """
    token = clean_token(procedure)
    if token is None or token not in ROBUSTNESS_PROCEDURES:
        return invalid(
            "procedure",
            "a robustness procedure contract names one of the four B-14 ladder rungs",
            given=repr(procedure),
            roster=ROBUSTNESS_PROCEDURES,
        )
    return Ok(
        StatisticalProcedureContract(
            procedure=token,
            contract_format_version=ROBUSTNESS_CONTRACT_FORMAT_VERSION,
        )
    )


def refuse_edge_claim(procedure: object) -> Result[None]:
    """Refuse reading an edge claim out of a robustness procedure (L20, B-7, AC6).

    A B-14 procedure produces robustness or infra-stress evidence only. Any attempt
    to label its output ``edge`` is a ``policy rejection`` — synthetic and perturbed
    evidence never validates edge, and the claim class is a label field distinct
    from world.
    """
    token = clean_token(procedure)
    if token is None:
        return invalid(
            "procedure",
            "a procedure name is required to refuse an edge claim",
            given=repr(procedure),
        )
    return policy(
        "claim_class",
        "a B-14 robustness procedure produces robustness or infra-stress evidence only; "
        "it never claims edge (L20, B-7)",
        procedure=token,
        allowed_claim_classes=ROBUSTNESS_CLAIM_CLASSES,
        forbidden_claim_class=CLAIM_CLASS_EDGE,
        gated_behind=CLAIM_GATED_BEHIND,
    )


def refuse_live_money_gate(procedure: object) -> Result[None]:
    """Refuse gating live money or spending split budget on a robustness output (SC-06, AC6).

    No robustness or infra-stress result can gate live money or spend split budget
    while the GAP-0048 fidelity seam is open — a ``policy rejection``, returned never
    raised.
    """
    token = clean_token(procedure)
    if token is None:
        return invalid(
            "procedure",
            "a procedure name is required to refuse a live-money gate",
            given=repr(procedure),
        )
    return policy(
        "authority",
        "a B-14 robustness procedure output cannot gate live money or spend split budget "
        "while the GAP-0048 fidelity seam is open (SC-06)",
        procedure=token,
        gated_behind=CLAIM_GATED_BEHIND,
    )


def require_configurable(config: object, key: object) -> Result[object]:
    """Resolve one required UI-editable configurable, value-or-refusal (NFR-07, AR-13, AC5).

    Reads ``config`` — a resolved run-config (its ``keys`` mapping) or a plain
    key->value mapping. An unset input (absent, or explicitly ``None``) is a typed
    ``invalid input`` refusal naming the configurable: the module ships no invented
    default and applies no silent number. The resolved value is returned verbatim.
    """
    token = clean_token(key)
    if token is None:
        return invalid(
            "key",
            "a configurable key is a non-blank string",
            given=repr(key),
        )
    resolved = _keys_of(config)
    if is_refusal(resolved):
        return resolved
    value = resolved.value.get(token)
    if value is None:
        return invalid(
            "configurable",
            "this required robustness input is a UI-editable configurable with no ratified "
            "platform value; unset, it is a typed invalid-input refusal, never a "
            "silently-applied default (NFR-07, AR-13, SC-07)",
            configurable=token,
            deferred_to=THRESHOLDS_DEFERRED_TO,
        )
    return Ok(value)


def require_positive_int(config: object, key: object) -> Result[int]:
    """Resolve a required positive-integer count configurable (AC5).

    The shared resolver for every iteration / scenario / block-length /
    minimum-observation input. Unset is an ``invalid input`` refusal (AR-13); a
    non-integer, a boolean, a float, or a non-positive value is likewise refused —
    no fractional or float count is invented.
    """
    resolved = require_configurable(config, key)
    if is_refusal(resolved):
        return resolved
    token = cast("str", clean_token(key))
    value = resolved.value
    if isinstance(value, bool) or not isinstance(value, int):
        return invalid(
            "configurable",
            "a robustness iteration / scenario / block-length / minimum-observation input is a "
            "positive exact integer; no fractional or float count is invented",
            configurable=token,
            given=repr(value),
        )
    if value <= 0:
        return invalid(
            "configurable",
            "a robustness count configurable is a positive integer",
            configurable=token,
            given=value,
        )
    return Ok(value)


def contract_identity() -> dict[str, object]:
    """Identity-bearing procedure-contract-layer fields. Package SemVer is omitted."""
    return {
        "claim_classes": ROBUSTNESS_CLAIM_CLASSES,
        "configurable_input_dimensions": CONFIGURABLE_INPUT_DIMENSIONS,
        "configurable_inputs_have_ratified_value": CONFIGURABLE_INPUTS_HAVE_RATIFIED_VALUE,
        "format_version": ROBUSTNESS_CONTRACT_FORMAT_VERSION,
        "gated_behind": CLAIM_GATED_BEHIND,
        "makes_edge_claim": PROCEDURE_MAKES_EDGE_CLAIM,
        "module_has_global_mutable_state": MODULE_HAS_GLOBAL_MUTABLE_STATE,
        "procedures": ROBUSTNESS_PROCEDURES,
        "pure_library_function": PROCEDURE_IS_PURE_LIBRARY_FUNCTION,
        "ships_invented_default": MODULE_SHIPS_INVENTED_DEFAULT,
        "thresholds_deferred_to": THRESHOLDS_DEFERRED_TO,
    }


def _keys_of(config: object) -> Result[Mapping[str, object]]:
    if isinstance(config, Mapping):
        return Ok(cast("Mapping[str, object]", config))
    keys = getattr(config, "keys", None)
    if isinstance(keys, Mapping):
        return Ok(cast("Mapping[str, object]", keys))
    return invalid(
        "config",
        "a configurable resolves from a resolved run-config (its keys mapping) or a "
        "key->value mapping",
        given=repr(type(config).__name__),
    )
