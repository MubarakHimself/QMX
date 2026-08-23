"""Story 10.3 — three-layer admission and the admission bar (COMP-QMF-RISK).

A new Book or BMS proves itself in **strictly three ordered layers ending in the
operator's signature**, and **no trial period, probation window, or paper-performance
gate exists** — redemption loops stay dead (AD-32; DEC-0146):

* **Layer 1 — machine linters at registration** (:func:`run_layer1_linters`):
  completeness against the declared contract format version; **unit-kind coverage on
  every declared variable** (every number an exact rational or scaled integer, no
  binary float); **worked-example arithmetic recomputed by invoking the cited producer
  contracts themselves** (:func:`check_worked_examples` — never linter-local
  arithmetic, which would be a second implementation of a governed formula); and
  **control-rank uniqueness** (two control-action kinds sharing a rank is ``invalid
  input``). When the admission gates a live binding, the Layer-1 policy check that **no
  paper role gates live money** also runs (AC4).
* **Layer 2 — technical shakedown on a demo/paper binding**
  (:func:`run_layer2_shakedown`): connect, register a bot, execute — it proves the
  machinery works and proves nothing about edge; its two named prerequisites (a
  recorded live-path rung baseline on the declared ``(OS, CPU-class)`` tuple, and a
  present baseline artifact for every sensor the Book's doors read) surface a bring-up
  deadlock here and never at the first tick.
* **Layer 3 — one operator signature on one assembled page**
  (:func:`assemble_admission_page` then :func:`sign_admission`) carrying **both
  proofs, the binding identity, and the resolved BMS fingerprint**, plus the
  Book-definition (or BMS-definition) fingerprint and a mandatory plain-words summary,
  each an identity field — so a signature can never attest a superseded template
  (DEC-0116, DEC-0158).

:func:`admit` composes the three in order, ending in the signature — the only path to
an :class:`AdmittedBinding`. The worked-example recompute is expressed against a
:class:`ProducerContract` **Protocol seam**: the linter never does the arithmetic, it
invokes the cited producer the composition root injects (DEC-0142) — a small reference
producer (:data:`LOSS_RUNWAY_PRODUCER`, :func:`sizing_producer`) wraps the already
governed ``qmf-core`` / ``qmf.risk`` arithmetic to demonstrate the seam, never a
second implementation.

Imports only ``qmf-core`` and sibling ``qmf.risk`` modules; nothing imports
``qmf.risk`` (default-deny, L30/DEC-0120). Ratified ``defined-unwired`` surface — no
live binding is authorized by this code (DEC-0146, DEC-0158).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Protocol, cast, runtime_checkable

from qmf.core import (
    AccountRole,
    Fingerprint,
    Instant,
    Money,
    Ok,
    Result,
    TypedRefusal,
    is_refusal,
)
from qmf.risk._common import clean_str, coerce_enum, invalid, policy, unavailable
from qmf.risk.admission_bar import AdmissionBar, check_no_paper_role_gates_live
from qmf.risk.control_rank import check_control_rank_uniqueness
from qmf.risk.dimensional import WorkedExample
from qmf.risk.grammar import NotYetRuled, VariableValue, value_unit_kind
from qmf.risk.r_faces import r_to_money
from qmf.risk.templates import BmsDefinition, BookDefinition

__all__ = [
    "ADMISSION_LAYERS",
    "FORBIDDEN_ADMISSION_GATES",
    "LOSS_RUNWAY_PRODUCER",
    "AdmissionLayer",
    "AdmissionPage",
    "AdmittedBinding",
    "CallableProducer",
    "Layer1Result",
    "Layer2Result",
    "OperatorSignature",
    "ProducerContract",
    "admit",
    "assemble_admission_page",
    "check_worked_examples",
    "recompute_worked_example",
    "reject_forbidden_admission_gate",
    "run_layer1_linters",
    "run_layer2_shakedown",
    "sign_admission",
    "sizing_producer",
]

# This module's own contract format version stamped into fp1 identity content; its
# meaning never mutates — an incompatible change mints the next version (L15).
_ADMISSION_FORMAT_VERSION = 1


class AdmissionLayer(StrEnum):
    """The three ordered admission layers — and no fourth (AD-32; DEC-0146).

    Exactly three, in order: Layer 1 machine linters at registration, Layer 2 a
    technical shakedown on a demo/paper binding, Layer 3 one operator signature. There
    is deliberately **no** trial-period, probation-window, or paper-performance layer —
    those redemption loops stay dead (see :data:`FORBIDDEN_ADMISSION_GATES`).
    """

    LAYER_1_LINTERS = "layer-1-linters"
    LAYER_2_SHAKEDOWN = "layer-2-technical-shakedown"
    LAYER_3_SIGNATURE = "layer-3-operator-signature"


# The layers in canonical order — exactly three, ending in the signature.
ADMISSION_LAYERS: Final[tuple[AdmissionLayer, ...]] = (
    AdmissionLayer.LAYER_1_LINTERS,
    AdmissionLayer.LAYER_2_SHAKEDOWN,
    AdmissionLayer.LAYER_3_SIGNATURE,
)

# The gates admission forbids by construction — no trial period, probation window, or
# paper-performance gate ever gates a live binding (AD-32; DEC-0146).
FORBIDDEN_ADMISSION_GATES: Final[frozenset[str]] = frozenset(
    {"trial-period", "probation-window", "paper-performance-gate"}
)


def reject_forbidden_admission_gate(gate: object) -> TypedRefusal:
    """Refuse any trial period, probation window, or paper-performance gate (AC1).

    Admission is exactly three layers ending in the operator's signature; a caller
    reaching for a redemption loop — a trial period, a probation window, or a
    paper-performance gate — gets a ``policy rejection`` naming it, never a silent
    fourth layer. A name outside the forbidden set is still refused: no gate beyond the
    three layers exists.
    """
    name = clean_str(gate) or "unnamed-gate"
    return policy(
        "admission",
        "admission is exactly three ordered layers ending in the operator's signature; no "
        "trial period, probation window, or paper-performance gate exists",
        gate=name,
        forbidden=sorted(FORBIDDEN_ADMISSION_GATES),
    )


@runtime_checkable
class ProducerContract(Protocol):
    """A cited governed producer contract that recomputes a worked example (AC5).

    The admission Layer-1 worked-example check **invokes the cited producer contract
    itself** — never a linter-local re-implementation of the governed formula. A
    producer takes the worked example's exact inputs and returns the recomputed exact
    value or a typed refusal. The concrete producer is injected at the composition root
    (the sizing ladder's runtime evaluation is the node's, DEC-0142); this module ships
    only the seam and thin reference adapters over already-governed arithmetic.
    """

    def recompute(self, inputs: Mapping[str, VariableValue]) -> Result[VariableValue]:
        """Recompute the formula's output from its exact inputs, value-or-refusal."""
        ...


@dataclass(frozen=True, slots=True)
class CallableProducer:
    """Adapt a governed callable to the :class:`ProducerContract` seam (AC5).

    Wraps a ``recompute`` callable — the single governed implementation of a formula —
    so the composition root can inject any governed arithmetic as a cited producer
    without the linter ever re-implementing it.
    """

    recompute_fn: Callable[[Mapping[str, VariableValue]], Result[VariableValue]]

    def recompute(self, inputs: Mapping[str, VariableValue]) -> Result[VariableValue]:
        """Invoke the wrapped governed callable."""
        return self.recompute_fn(inputs)


def recompute_worked_example(worked_example: object, producer: object) -> Result[VariableValue]:
    """Recompute one worked example by invoking its cited producer (AC5; DEC-0146).

    Invokes ``producer.recompute`` on the worked example's exact inputs and requires
    the recomputed value to equal the declared ``expected_output`` by canonical
    identity. The arithmetic is the **producer's**, never this linter's: a producer
    that disagrees makes the check fail (``invalid input``), proving the recompute is
    not a second local implementation. A producer that is not a
    :class:`ProducerContract` is ``invalid input``; a producer refusal propagates.
    """
    if not isinstance(worked_example, WorkedExample):
        return invalid(
            "worked_example", "the recompute reads a WorkedExample", given=repr(worked_example)
        )
    if not isinstance(producer, ProducerContract):
        return invalid(
            "producer",
            "the cited producer is a ProducerContract (it exposes recompute); the linter "
            "never does the arithmetic itself",
            given=repr(producer),
        )
    recomputed = producer.recompute(worked_example.inputs)
    if is_refusal(recomputed):
        return recomputed
    if recomputed.value.fp1_identity() != worked_example.expected_output.fp1_identity():
        return invalid(
            "worked_example",
            "the cited producer's recomputed output disagrees with the declared worked-example "
            "expected output",
            expected=worked_example.expected_output.fp1_identity(),
            recomputed=recomputed.value.fp1_identity(),
        )
    return recomputed


def check_worked_examples(worked_examples: object, producers: object) -> Result[None]:
    """Recompute every worked example via its cited producer (AC5; DEC-0146).

    ``worked_examples`` is a mapping ``formula_id -> WorkedExample`` (one entry per
    declared formula id); ``producers`` is a mapping ``formula_id -> ProducerContract``
    — the cited governed producers. Each worked example is recomputed by invoking its
    producer (:func:`recompute_worked_example`); a formula id with **no cited producer
    is an ``unavailable dependency`` refusal** — the linter never falls back to its own
    arithmetic. A recompute mismatch is ``invalid input``. Returns ``Ok(None)`` when
    every worked example recomputes.
    """
    examples = _coerce_worked_examples(worked_examples)
    if isinstance(examples, TypedRefusal):
        return examples
    producer_map = _coerce_producers(producers)
    if isinstance(producer_map, TypedRefusal):
        return producer_map
    for formula_id, example in examples.items():
        producer = producer_map.get(formula_id)
        if producer is None:
            return unavailable(
                "producers",
                "a worked example cites a producer that is not injected; the linter recomputes "
                "by invoking the cited producer contract, never by local arithmetic",
                formula_id=formula_id,
            )
        recomputed = recompute_worked_example(example, producer)
        if is_refusal(recomputed):
            return recomputed
    return Ok(None)


def _coerce_worked_examples(value: object) -> dict[str, WorkedExample] | TypedRefusal:
    """Resolve a ``formula_id -> WorkedExample`` mapping, or a refusal."""
    if not isinstance(value, Mapping):
        return invalid(
            "worked_examples",
            "worked examples are a formula_id -> WorkedExample mapping",
            given=repr(type(value).__name__),
        )
    mapping = cast("Mapping[object, object]", value)
    resolved: dict[str, WorkedExample] = {}
    for key, example in mapping.items():
        token = clean_str(key)
        if token is None:
            return invalid("worked_examples", "a formula id is a non-empty string", given=repr(key))
        if not isinstance(example, WorkedExample):
            return invalid(
                "worked_examples",
                "each entry is a WorkedExample",
                formula_id=token,
                given=repr(example),
            )
        resolved[token] = example
    return resolved


def _coerce_producers(value: object) -> dict[str, ProducerContract] | TypedRefusal:
    """Resolve a ``formula_id -> ProducerContract`` mapping, or a refusal."""
    if not isinstance(value, Mapping):
        return invalid(
            "producers",
            "cited producers are a formula_id -> ProducerContract mapping",
            given=repr(type(value).__name__),
        )
    mapping = cast("Mapping[object, object]", value)
    resolved: dict[str, ProducerContract] = {}
    for key, producer in mapping.items():
        token = clean_str(key)
        if token is None:
            return invalid("producers", "a formula id is a non-empty string", given=repr(key))
        if not isinstance(producer, ProducerContract):
            return invalid(
                "producers",
                "each cited producer is a ProducerContract (it exposes recompute)",
                formula_id=token,
                given=repr(producer),
            )
        resolved[token] = producer
    return resolved


# --- Layer 1 -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Layer1Result:
    """The proof that Layer-1 machine linters passed at registration (AD-32; DEC-0146).

    Carries the registered definition's ``fp1`` (so a later signed page can bind to the
    exact template linted, never a superseded one) and whether it is a BMS definition.
    """

    definition_fingerprint: Fingerprint
    is_bms: bool

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the Layer-1 proof."""
        return {
            "class": "admission-layer1-result",
            "definition_fingerprint": self.definition_fingerprint.value,
            "is_bms": self.is_bms,
            "format_version": _ADMISSION_FORMAT_VERSION,
        }


def run_layer1_linters(
    definition: object,
    admission_bar: object,
    control_rank_table: object,
    worked_examples: object,
    producers: object,
    *,
    gates_live_binding: bool = False,
) -> Result[Layer1Result]:
    """Run the Layer-1 machine linters at registration (AC1, AC4, AC5; DEC-0146).

    In order: completeness (the ``definition`` is a validated
    :class:`~qmf.risk.templates.BookDefinition` or
    :class:`~qmf.risk.templates.BmsDefinition`); **unit-kind coverage** on every
    declared variable (every ruled number an exact carrier whose unit-kind matches its
    declaration — no binary float); **worked-example recompute** by invoking the cited
    producers (:func:`check_worked_examples`); and **control-rank uniqueness**
    (:func:`~qmf.risk.control_rank.check_control_rank_uniqueness`). When
    ``gates_live_binding`` is set, the Layer-1 policy check that **no paper role gates
    live money** also runs (AC4). Returns a :class:`Layer1Result` on success, else the
    first refusal.
    """
    if isinstance(definition, BookDefinition):
        is_bms = False
    elif isinstance(definition, BmsDefinition):
        is_bms = True
    else:
        return invalid(
            "definition",
            "Layer 1 lints a validated Book or BMS definition; an unbuilt definition never "
            "reaches the linters",
            given=repr(definition),
        )
    if not isinstance(admission_bar, AdmissionBar):
        return invalid(
            "admission_bar", "Layer 1 reads a validated AdmissionBar", given=repr(admission_bar)
        )
    coverage = _check_unit_kind_coverage(definition.flat_variables())
    if isinstance(coverage, TypedRefusal):
        return coverage
    worked = check_worked_examples(worked_examples, producers)
    if is_refusal(worked):
        return worked
    ranks = check_control_rank_uniqueness(control_rank_table)
    if is_refusal(ranks):
        return ranks
    if gates_live_binding:
        paper = check_no_paper_role_gates_live(admission_bar, AccountRole.LIVE)
        if is_refusal(paper):
            return paper
    fingerprint = definition.fingerprint()
    if is_refusal(fingerprint):
        return fingerprint
    return Ok(Layer1Result(definition_fingerprint=fingerprint.value, is_bms=is_bms))


def _check_unit_kind_coverage(
    variables: Mapping[str, object],
) -> TypedRefusal | None:
    """Enforce unit-kind coverage on every declared variable (AC5; DEC-0154).

    Every declared variable carries a unit-kind, and every **ruled** value is an exact
    ``qmf-core`` carrier whose own unit-kind equals the declared one — a binary float
    or a unit-kind mismatch is ``invalid input``. A :class:`~qmf.risk.grammar.NotYetRuled`
    blank carries no number, so the declared unit-kind stands and the value is skipped.
    Returns ``None`` when every variable is covered.
    """
    for key, variable in variables.items():
        declared = getattr(variable, "unit_kind", None)
        value = getattr(variable, "value", None)
        if declared is None:
            return invalid(
                "variables", "a declared variable is missing its unit-kind", variable=key
            )
        if isinstance(value, NotYetRuled):
            continue
        resolved = value_unit_kind(value)
        if resolved is None:
            return invalid(
                "variables",
                "a declared variable's value is not an exact carrier (a binary float is banned "
                "off the money path); blankness is an explicit NotYetRuled marker",
                variable=key,
            )
        if resolved is not declared:
            return invalid(
                "variables",
                "a declared variable's value unit-kind disagrees with its declared unit-kind",
                variable=key,
                declared=declared.value,
                value_unit_kind=resolved.value,
            )
    return None


# --- Layer 2 -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Layer2Result:
    """The proof of the Layer-2 technical shakedown (AD-32; DEC-0146).

    Carries the ``binding_identity`` shaken down, the demo/paper ``shakedown_role`` it
    ran on (never live), and the two named prerequisites — a recorded live-path rung
    baseline on the declared ``(OS, CPU-class)`` tuple, and a present baseline artifact
    for every sensor the Book's doors read — so a bring-up deadlock surfaces here.
    """

    binding_identity: str
    shakedown_role: AccountRole
    live_path_rung_baseline_present: bool
    sensor_baselines_present: bool

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the Layer-2 proof."""
        return {
            "class": "admission-layer2-result",
            "binding_identity": self.binding_identity,
            "shakedown_role": self.shakedown_role.value,
            "live_path_rung_baseline_present": self.live_path_rung_baseline_present,
            "sensor_baselines_present": self.sensor_baselines_present,
            "format_version": _ADMISSION_FORMAT_VERSION,
        }


def run_layer2_shakedown(
    binding_identity: object,
    shakedown_role: object,
    live_path_rung_baseline_present: object,
    sensor_baselines_present: object,
) -> Result[Layer2Result]:
    """Run the Layer-2 technical shakedown on a demo/paper binding (AC1; DEC-0146).

    The shakedown proves the machinery works and proves nothing about edge, so it runs
    on a **demo or paper** binding — a ``live`` ``shakedown_role`` is a ``policy
    rejection`` (Layer 2 never runs live). Its two named prerequisites must be present —
    a recorded live-path rung baseline and a present sensor baseline artifact — else an
    ``unavailable dependency`` refusal surfaces the bring-up deadlock here, not at the
    first tick. Returns the :class:`Layer2Result` proof.
    """
    identity = clean_str(binding_identity)
    if identity is None:
        return invalid(
            "binding_identity",
            "the shakedown names the binding identity it ran on",
            given=repr(binding_identity),
        )
    role = coerce_enum(AccountRole, shakedown_role)
    if role is None:
        return invalid(
            "shakedown_role",
            "the shakedown declares the account role it ran on",
            given=repr(shakedown_role),
            allowed=[member.value for member in AccountRole],
        )
    if role is AccountRole.LIVE:
        return policy(
            "shakedown_role",
            "the Layer-2 technical shakedown runs on a demo/paper binding, never a live one; it "
            "proves the machinery works and proves nothing about edge",
        )
    if not isinstance(live_path_rung_baseline_present, bool):
        return invalid(
            "live_path_rung_baseline_present",
            "the live-path rung baseline prerequisite is a bool",
            given=repr(live_path_rung_baseline_present),
        )
    if not isinstance(sensor_baselines_present, bool):
        return invalid(
            "sensor_baselines_present",
            "the sensor-baseline prerequisite is a bool",
            given=repr(sensor_baselines_present),
        )
    if not live_path_rung_baseline_present:
        return unavailable(
            "live_path_rung_baseline_present",
            "the recorded live-path rung baseline on the declared (OS, CPU-class) tuple is a "
            "Layer-2 prerequisite; its absence surfaces the bring-up deadlock here",
        )
    if not sensor_baselines_present:
        return unavailable(
            "sensor_baselines_present",
            "a present baseline artifact for every sensor the Book's doors read is a Layer-2 "
            "prerequisite; its absence surfaces the bring-up deadlock here",
        )
    return Ok(
        Layer2Result(
            binding_identity=identity,
            shakedown_role=role,
            live_path_rung_baseline_present=True,
            sensor_baselines_present=True,
        )
    )


# --- Layer 3 -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AdmissionPage:
    """The one assembled Layer-3 page carrying both proofs (AC1; DEC-0146, DEC-0116).

    Carries the Layer-1 and Layer-2 proofs, the ``binding_identity``, the resolved
    ``bms_fingerprint``, the ``definition_fingerprint`` (Book or BMS — an identity
    field, so a signature can never attest a superseded template), and a mandatory
    ``plain_words_summary`` (also an identity field, the exact words the human reads).
    """

    layer1: Layer1Result
    layer2: Layer2Result
    binding_identity: str
    bms_fingerprint: Fingerprint
    definition_fingerprint: Fingerprint
    plain_words_summary: str

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the assembled page."""
        return {
            "class": "admission-page",
            "layer1": self.layer1.fp1_identity(),
            "layer2": self.layer2.fp1_identity(),
            "binding_identity": self.binding_identity,
            "bms_fingerprint": self.bms_fingerprint.value,
            "definition_fingerprint": self.definition_fingerprint.value,
            "plain_words_summary": self.plain_words_summary,
            "format_version": _ADMISSION_FORMAT_VERSION,
        }


def assemble_admission_page(
    layer1: object,
    layer2: object,
    binding_identity: object,
    bms_fingerprint: object,
    definition_fingerprint: object,
    plain_words_summary: object,
) -> Result[AdmissionPage]:
    """Assemble the one Layer-3 page carrying both proofs (AC1; DEC-0146, DEC-0158).

    Requires both layer proofs, a non-blank ``binding_identity`` matching the Layer-2
    proof, the resolved ``bms_fingerprint``, the ``definition_fingerprint`` matching the
    exact template Layer 1 linted (so a signature can never attest a superseded
    template — ``invalid input`` on mismatch), and a mandatory non-blank
    ``plain_words_summary``. Returns the :class:`AdmissionPage`; it is not yet admitted
    — Layer 3 is the *signature* (:func:`sign_admission`).
    """
    if not isinstance(layer1, Layer1Result):
        return invalid("layer1", "the page carries the Layer-1 proof", given=repr(layer1))
    if not isinstance(layer2, Layer2Result):
        return invalid("layer2", "the page carries the Layer-2 proof", given=repr(layer2))
    identity = clean_str(binding_identity)
    if identity is None:
        return invalid(
            "binding_identity", "the page names the binding identity", given=repr(binding_identity)
        )
    if identity != layer2.binding_identity:
        return invalid(
            "binding_identity",
            "the page's binding identity must equal the shaken-down binding",
            page=identity,
            shakedown=layer2.binding_identity,
        )
    if not isinstance(bms_fingerprint, Fingerprint):
        return invalid(
            "bms_fingerprint",
            "the page carries the resolved BMS fingerprint",
            given=repr(bms_fingerprint),
        )
    if not isinstance(definition_fingerprint, Fingerprint):
        return invalid(
            "definition_fingerprint",
            "the page carries the Book/BMS-definition fingerprint",
            given=repr(definition_fingerprint),
        )
    if definition_fingerprint.value != layer1.definition_fingerprint.value:
        return invalid(
            "definition_fingerprint",
            "the page's definition fingerprint must equal the exact template Layer 1 linted; a "
            "signature can never attest a superseded template",
            page=definition_fingerprint.value,
            linted=layer1.definition_fingerprint.value,
        )
    summary = clean_str(plain_words_summary)
    if summary is None:
        return invalid(
            "plain_words_summary",
            "the promotion card's plain-words summary is a mandatory identity field",
            given=repr(plain_words_summary),
        )
    return Ok(
        AdmissionPage(
            layer1=layer1,
            layer2=layer2,
            binding_identity=identity,
            bms_fingerprint=bms_fingerprint,
            definition_fingerprint=definition_fingerprint,
            plain_words_summary=summary,
        )
    )


@dataclass(frozen=True, slots=True)
class OperatorSignature:
    """The operator's Layer-3 signature — the human-only boundary (AC1; DEC-0116).

    Carries the ``signer_identity`` and the injected ``signed_at`` :class:`~qmf.core.Instant`
    (never a clock read below the composition root). Only a human signature authorizes
    a live binding; no proof stack substitutes for it.
    """

    signer_identity: str
    signed_at: Instant

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the signature."""
        return {
            "class": "operator-signature",
            "signer_identity": self.signer_identity,
            "signed_at": self.signed_at.fp1_identity(),
            "format_version": _ADMISSION_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class AdmittedBinding:
    """A fully admitted binding — the assembled page plus the operator signature.

    The only value this module produces that represents a completed admission; it is
    reached solely by signing an assembled page (Layer 3), which itself requires both
    prior proofs. Ratified ``defined-unwired``: constructing this authorizes nothing —
    live binding runs only through the factory pipeline (DEC-0146).
    """

    page: AdmissionPage
    signature: OperatorSignature

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the admitted binding."""
        return {
            "class": "admitted-binding",
            "page": self.page.fp1_identity(),
            "signature": self.signature.fp1_identity(),
            "format_version": _ADMISSION_FORMAT_VERSION,
        }


def sign_admission(
    page: object, signer_identity: object, signed_at: object
) -> Result[AdmittedBinding]:
    """Layer 3 — one operator signature on one assembled page (AC1; DEC-0116, DEC-0146).

    Only a human signature admits: a non-blank ``signer_identity`` and an injected
    ``signed_at`` :class:`~qmf.core.Instant` (never a clock read here). Returns the
    :class:`AdmittedBinding`; the signature attests the exact page — both proofs, the
    binding identity, the resolved BMS fingerprint, the template fingerprint, and the
    plain-words summary — so it can never attest a superseded template.
    """
    if not isinstance(page, AdmissionPage):
        return invalid("page", "Layer 3 signs an assembled AdmissionPage", given=repr(page))
    signer = clean_str(signer_identity)
    if signer is None:
        return invalid(
            "signer_identity",
            "only a human signature admits; the signer identity is a non-empty token",
            given=repr(signer_identity),
        )
    if not isinstance(signed_at, Instant):
        return invalid(
            "signed_at",
            "the signature is dated with an injected Instant (never a clock read below the "
            "composition root)",
            given=repr(signed_at),
        )
    return Ok(
        AdmittedBinding(
            page=page,
            signature=OperatorSignature(signer_identity=signer, signed_at=signed_at),
        )
    )


def admit(
    definition: object,
    admission_bar: object,
    control_rank_table: object,
    worked_examples: object,
    producers: object,
    *,
    binding_identity: object,
    shakedown_role: object,
    live_path_rung_baseline_present: object,
    sensor_baselines_present: object,
    bms_fingerprint: object,
    plain_words_summary: object,
    signer_identity: object,
    signed_at: object,
    gates_live_binding: bool = False,
) -> Result[AdmittedBinding]:
    """Admit a Book or BMS through the three ordered layers, ending in the signature.

    Runs Layer 1 (:func:`run_layer1_linters`), then Layer 2
    (:func:`run_layer2_shakedown`), then assembles the page
    (:func:`assemble_admission_page`) and signs it (:func:`sign_admission`) — **strictly
    in order**, short-circuiting on the first refusal. There is no trial period,
    probation window, or paper-performance gate anywhere in the sequence. Returns the
    :class:`AdmittedBinding`, the only path to a completed admission.
    """
    layer1 = run_layer1_linters(
        definition,
        admission_bar,
        control_rank_table,
        worked_examples,
        producers,
        gates_live_binding=gates_live_binding,
    )
    if is_refusal(layer1):
        return layer1
    layer2 = run_layer2_shakedown(
        binding_identity,
        shakedown_role,
        live_path_rung_baseline_present,
        sensor_baselines_present,
    )
    if is_refusal(layer2):
        return layer2
    page = assemble_admission_page(
        layer1.value,
        layer2.value,
        binding_identity,
        bms_fingerprint,
        layer1.value.definition_fingerprint,
        plain_words_summary,
    )
    if is_refusal(page):
        return page
    return sign_admission(page.value, signer_identity, signed_at)


# --- reference producers over already-governed arithmetic (AC5) ---------------
#
# These wrap the SINGLE governed implementation of a formula — never a second one — so
# the composition root has a concrete cited producer for the worked-example recompute,
# and the seam is demonstrably invoked. The sizing ladder's runtime evaluation against
# live book state stays the node's (DEC-0142); these recompute only fixed worked-example
# data through the existing qmf-core / qmf.risk arithmetic.


def _loss_runway(inputs: Mapping[str, VariableValue]) -> Result[VariableValue]:
    """Recompute ``loss_runway = book_capital - loss_floor`` via ``Money.subtract``.

    The subtraction is ``qmf-core``'s governed Money arithmetic — not a second
    implementation. Missing or non-:class:`~qmf.core.Money` inputs are ``invalid input``.
    """
    book_capital = inputs.get("book_capital")
    loss_floor = inputs.get("loss_floor")
    if not isinstance(book_capital, Money):
        return invalid(
            "book_capital", "loss_runway takes a Money book_capital", given=repr(book_capital)
        )
    if not isinstance(loss_floor, Money):
        return invalid("loss_floor", "loss_runway takes a Money loss_floor", given=repr(loss_floor))
    difference = book_capital.subtract(loss_floor)
    if is_refusal(difference):
        return difference
    computed: VariableValue = difference.value
    return Ok(computed)


# The cited producer for the ``FORM-loss-runway`` formula, over governed Money arithmetic.
LOSS_RUNWAY_PRODUCER: Final[CallableProducer] = CallableProducer(recompute_fn=_loss_runway)


def sizing_producer(money_scale: int) -> CallableProducer:
    """A cited producer for ``position_risk_amount`` over the governed R→Money crossing.

    Wraps :func:`qmf.risk.r_faces.r_to_money` — the single governed money-path crossing
    (``position_risk_amount = requested_r × r_unit_price`` at ``money_scale``) — so the
    worked-example recompute invokes the real producer, never a local re-implementation.
    """

    def _position_risk_amount(inputs: Mapping[str, VariableValue]) -> Result[VariableValue]:
        priced = r_to_money(
            inputs.get("requested_r"), inputs.get("r_unit_price"), scale=money_scale
        )
        if is_refusal(priced):
            return priced
        computed: VariableValue = priced.value
        return Ok(computed)

    return CallableProducer(recompute_fn=_position_risk_amount)
