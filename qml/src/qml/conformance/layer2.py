"""Layer 2 execution-conformance verdict (QL-8).

QML owns the pure format-versioned surface. Hosts own only process spawning
and isolation and feed results back here, so a bot's conformance verdict is
host-independent by construction and no Book is present or needed (DEC-0178).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal

from qml._refuse import invalid, policy
from qml.conformance.contract import (
    CONFORMANCE_FORMAT_VERSION,
    LAYER2_CHECKS,
)
from qml.conformance.harness import (
    INTENT_KIND_ENTRY,
    construct_for_slice,
    drive_error_kind,
    drive_golden_slice,
    intent_trace_kinds,
    restore_round_trip,
    traces_equal,
)
from qml.conformance.scan import ScanFinding, ScanReport, scan_logic_source
from qml.conformance.slice import generate_golden_slice
from qml.declaration.bot import BotDefinition, mint_bot_definition
from qml.protocol.factory import resolve_assignment

__all__ = [
    "LAYER2_CHECKS",
    "Layer2Observations",
    "Layer2Verdict",
    "collect_layer2_observations",
    "evaluate_layer2",
    "run_layer2_suite",
]

_LAYER: Final[int] = 2
_SEED_NAME: Final[str] = "seed"


def _journal(refusal: TypedRefusal) -> TypedRefusal:
    extra: dict[str, object] = dict(refusal.context)
    extra["journal"] = True
    extra.setdefault("layer", _LAYER)
    return TypedRefusal(
        category=refusal.category,
        retryability=refusal.retryability,
        context=extra,
        after_condition_descriptor=refusal.after_condition_descriptor,
    )


def _fail(field: str, reason: str, **extra: object) -> TypedRefusal:
    return _journal(policy(field, reason, layer=_LAYER, journal=True, **extra))


@dataclass(frozen=True, slots=True)
class Layer2Observations:
    """Host-fed Layer-2 evidence. Host identity never enters the verdict."""

    loaded_in_isolation: bool
    book_present: bool
    scan: ScanReport
    golden_slice_fingerprint: Fingerprint
    declaration_fingerprint: Fingerprint
    first_run: tuple[tuple[dict[str, object], ...], ...]
    second_run: tuple[tuple[dict[str, object], ...], ...]
    emitted_kinds: tuple[str, ...]
    permitted_exit_intents: tuple[str, ...]
    state_bound_holds: bool
    restore_equivalent: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "qml-layer2-observations",
            "contract_format_version": CONFORMANCE_FORMAT_VERSION,
            "loaded_in_isolation": self.loaded_in_isolation,
            "book_present": self.book_present,
            "scan": self.scan.fp1_identity(),
            "golden_slice_fingerprint": self.golden_slice_fingerprint.value,
            "declaration_fingerprint": self.declaration_fingerprint.value,
            "first_run": [list(instant) for instant in self.first_run],
            "second_run": [list(instant) for instant in self.second_run],
            "emitted_kinds": list(self.emitted_kinds),
            "permitted_exit_intents": list(self.permitted_exit_intents),
            "state_bound_holds": self.state_bound_holds,
            "restore_equivalent": self.restore_equivalent,
        }

    @classmethod
    def try_from_mapping(cls, value: object) -> Result[Layer2Observations]:
        if isinstance(value, cls):
            return Ok(value)
        if not isinstance(value, Mapping):
            return invalid(
                "observations",
                "Layer 2 observations are a mapping hosts feed to the pure verdict function",
                given=type(value).__name__,
                layer=_LAYER,
            )
        mapping = cast("Mapping[str, object]", value)
        loaded = _as_bool(mapping.get("loaded_in_isolation"), "loaded_in_isolation")
        if is_refusal(loaded):
            return loaded
        book = _as_bool(mapping.get("book_present", False), "book_present")
        if is_refusal(book):
            return book
        scan = _as_scan(mapping.get("scan", mapping.get("scan_findings", ())))
        if is_refusal(scan):
            return scan
        slice_fp = _as_fingerprint(
            mapping.get("golden_slice_fingerprint"), "golden_slice_fingerprint"
        )
        if is_refusal(slice_fp):
            return slice_fp
        decl_fp = _as_fingerprint(mapping.get("declaration_fingerprint"), "declaration_fingerprint")
        if is_refusal(decl_fp):
            return decl_fp
        first = _as_trace(mapping.get("first_run"), "first_run")
        if is_refusal(first):
            return first
        second = _as_trace(mapping.get("second_run"), "second_run")
        if is_refusal(second):
            return second
        if "emitted_kinds" in mapping:
            kinds = _as_kind_tuple(mapping.get("emitted_kinds"), "emitted_kinds")
            if is_refusal(kinds):
                return kinds
            emitted = kinds.value
        else:
            first_kinds = intent_trace_kinds(first.value)
            if is_refusal(first_kinds):
                return first_kinds
            second_kinds = intent_trace_kinds(second.value)
            if is_refusal(second_kinds):
                return second_kinds
            emitted = first_kinds.value + second_kinds.value
        permitted = _as_kind_tuple(
            mapping.get("permitted_exit_intents", ()), "permitted_exit_intents"
        )
        if is_refusal(permitted):
            return permitted
        bound = _as_bool(mapping.get("state_bound_holds"), "state_bound_holds")
        if is_refusal(bound):
            return bound
        restore = _as_bool(mapping.get("restore_equivalent"), "restore_equivalent")
        if is_refusal(restore):
            return restore
        return Ok(
            cls(
                loaded_in_isolation=loaded.value,
                book_present=book.value,
                scan=scan.value,
                golden_slice_fingerprint=slice_fp.value,
                declaration_fingerprint=decl_fp.value,
                first_run=first.value,
                second_run=second.value,
                emitted_kinds=emitted,
                permitted_exit_intents=permitted.value,
                state_bound_holds=bound.value,
                restore_equivalent=restore.value,
            )
        )


@dataclass(frozen=True, slots=True)
class Layer2Verdict:
    """Proof that the logic passed every Layer-2 check (DEC-0178).

    Host identity is not a field: two hosts feeding equal observations mint
    one verdict fingerprint.
    """

    declaration_fingerprint: Fingerprint
    golden_slice_fingerprint: Fingerprint
    checks: tuple[str, ...] = LAYER2_CHECKS

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity of the Layer-2 proof. Package SemVer never enters."""
        return {
            "class": "qml-layer2-verdict",
            "contract_format_version": CONFORMANCE_FORMAT_VERSION,
            "declaration_fingerprint": self.declaration_fingerprint.value,
            "golden_slice_fingerprint": self.golden_slice_fingerprint.value,
            "checks": list(self.checks),
        }

    def fingerprint_content(self) -> Result[Fingerprint]:
        return fingerprint(self)


def evaluate_layer2(observations: object) -> Result[Layer2Verdict]:
    """Pure Layer-2 verdict. Hosts feed observations; QML never spawns a process.

    Differing golden-slice intents or a non-permitted intent kind is a Layer-2
    conformance failure (FM-5). The verdict is identical for equal observations
    regardless of which host recorded them. A Book must not be present.
    """
    parsed = Layer2Observations.try_from_mapping(observations)
    if is_refusal(parsed):
        return _journal(parsed) if parsed.context.get("layer") != _LAYER else parsed
    obs = parsed.value
    if obs.scan.findings:
        first = obs.scan.findings[0]
        return _fail(
            "static_ast_import_scan",
            "the static AST/import scan detected a denied capability "
            "(clock/I-O/network/undeclared randomness); this is a Layer-2 "
            "conformance failure",
            capability=first.capability,
            path=first.path,
            lineno=first.lineno,
            detail=first.detail,
            findings=tuple(item.fp1_identity() for item in obs.scan.findings),
        )
    if not obs.loaded_in_isolation:
        return _fail(
            "logic_loads_in_isolation",
            "the logic artifact must load in isolation with no Book present",
        )
    if obs.book_present:
        return _fail(
            "no_book_present",
            "Layer 2 runs with no Book present or needed; the bot's output under "
            "test is intents with advisory proposals",
        )
    disallowed = _disallowed_kinds(obs.emitted_kinds, obs.permitted_exit_intents)
    if disallowed:
        return _fail(
            "permitted_intent_kinds",
            "only permitted intent kinds may be emitted; a non-permitted kind is "
            "a Layer-2 conformance failure",
            given=disallowed[0],
            permitted=("entry", *obs.permitted_exit_intents),
        )
    if not traces_equal(obs.first_run, obs.second_run):
        return _fail(
            "golden_slice_determinism",
            "a golden slice run twice must yield identical intents; differing "
            "intents are a Layer-2 conformance failure",
        )
    if not obs.state_bound_holds:
        return _fail(
            "state_bound_restore_equivalent",
            "the declared state bound must hold; bot state is bounded and "
            "declared, never unbounded — a Layer-2 conformance concern",
        )
    if not obs.restore_equivalent:
        return _fail(
            "state_bound_restore_equivalent",
            "a snapshot/restore round-trip must be equivalent (AD-22 restore-"
            "equivalence); a mismatch is a Layer-2 conformance failure",
        )
    return Ok(
        Layer2Verdict(
            declaration_fingerprint=obs.declaration_fingerprint,
            golden_slice_fingerprint=obs.golden_slice_fingerprint,
            checks=LAYER2_CHECKS,
        )
    )


def collect_layer2_observations(
    *,
    declaration: object,
    factory: object,
    source_tree: object,
    assignment: object = None,
    state_scope: object,
    state_bound: object,
) -> Result[Layer2Observations]:
    """In-process Layer-2 observations. Spawns no process; hosts may isolate this.

    Hosts that spawn a process run this collector in the child and feed the
    returned observations to :func:`evaluate_layer2` in the parent, so the
    verdict stays QML-owned. No Book is injected. Capability starvation is
    the injected read-surfaces-only path.
    """
    bot = _admit_declaration(declaration)
    if is_refusal(bot):
        return _journal(bot)
    definition = bot.value
    decl_fp = definition.fingerprint_content()
    if is_refusal(decl_fp):
        return _journal(decl_fp)
    resolved = _assignment_of(definition, assignment)
    if is_refusal(resolved):
        return _journal(resolved)
    scan = scan_logic_source(source_tree, declared_seed=_has_declared_seed(definition))
    if is_refusal(scan):
        return _journal(scan)
    slice_ = generate_golden_slice(definition.footprint)
    if is_refusal(slice_):
        return _journal(slice_)
    slice_fp = slice_.value.fingerprint_content()
    if is_refusal(slice_fp):
        return _journal(slice_fp)
    if scan.value.findings:
        return Ok(
            _observations(
                loaded_in_isolation=True,
                book_present=False,
                scan=scan.value,
                golden_slice_fingerprint=slice_fp.value,
                declaration_fingerprint=decl_fp.value,
                first_run=(),
                second_run=(),
                emitted_kinds=(),
                permitted_exit_intents=definition.permitted_exit_intents,
                state_bound_holds=True,
                restore_equivalent=True,
            )
        )
    first_bot = construct_for_slice(
        factory,
        declaration=definition,
        assignment=resolved.value,
        slice_=slice_.value,
        state_scope=state_scope,
        state_bound=state_bound,
    )
    if is_refusal(first_bot):
        return Ok(
            _observations(
                loaded_in_isolation=False,
                book_present=False,
                scan=scan.value,
                golden_slice_fingerprint=slice_fp.value,
                declaration_fingerprint=decl_fp.value,
                first_run=(),
                second_run=(),
                emitted_kinds=(),
                permitted_exit_intents=definition.permitted_exit_intents,
                state_bound_holds=False,
                restore_equivalent=False,
            )
        )
    first_run = drive_golden_slice(first_bot.value, slice_.value)
    if is_refusal(first_run):
        return _drive_refusal_observations(
            first_run,
            scan=scan.value,
            slice_fp=slice_fp.value,
            decl_fp=decl_fp.value,
            permitted=definition.permitted_exit_intents,
        )
    second_bot = construct_for_slice(
        factory,
        declaration=definition,
        assignment=resolved.value,
        slice_=slice_.value,
        state_scope=state_scope,
        state_bound=state_bound,
    )
    if is_refusal(second_bot):
        return Ok(
            _observations(
                loaded_in_isolation=False,
                book_present=False,
                scan=scan.value,
                golden_slice_fingerprint=slice_fp.value,
                declaration_fingerprint=decl_fp.value,
                first_run=first_run.value,
                second_run=(),
                emitted_kinds=(),
                permitted_exit_intents=definition.permitted_exit_intents,
                state_bound_holds=False,
                restore_equivalent=False,
            )
        )
    second_run = drive_golden_slice(second_bot.value, slice_.value)
    if is_refusal(second_run):
        return _drive_refusal_observations(
            second_run,
            scan=scan.value,
            slice_fp=slice_fp.value,
            decl_fp=decl_fp.value,
            permitted=definition.permitted_exit_intents,
            first_run=first_run.value,
        )
    kinds = intent_trace_kinds(first_run.value)
    if is_refusal(kinds):
        return _journal(kinds)
    bound_and_restore = restore_round_trip(
        factory,
        declaration=definition,
        assignment=resolved.value,
        slice_=slice_.value,
        state_scope=state_scope,
        state_bound=state_bound,
    )
    state_bound_holds = True
    restore_equivalent = True
    if is_refusal(bound_and_restore):
        field = bound_and_restore.context.get("field")
        if field == "state_bound":
            state_bound_holds = False
            restore_equivalent = False
        else:
            restore_equivalent = False
            if field in {"state_scope", "payload"}:
                state_bound_holds = field != "payload"
    else:
        restore_equivalent = bound_and_restore.value
    return Ok(
        _observations(
            loaded_in_isolation=True,
            book_present=False,
            scan=scan.value,
            golden_slice_fingerprint=slice_fp.value,
            declaration_fingerprint=decl_fp.value,
            first_run=first_run.value,
            second_run=second_run.value,
            emitted_kinds=kinds.value,
            permitted_exit_intents=definition.permitted_exit_intents,
            state_bound_holds=state_bound_holds,
            restore_equivalent=restore_equivalent,
        )
    )


def run_layer2_suite(
    *,
    declaration: object,
    factory: object,
    source_tree: object,
    assignment: object = None,
    state_scope: object,
    state_bound: object,
) -> Result[Layer2Verdict]:
    """In-process Layer-2 suite. Spawns no process; feeds the pure verdict.

    Asserts: logic loads in isolation; a golden slice run twice yields identical
    intents; only permitted intent kinds are emitted; the declared state bound
    holds with a snapshot/restore round-trip equivalent. No Book is injected.
    """
    observed = collect_layer2_observations(
        declaration=declaration,
        factory=factory,
        source_tree=source_tree,
        assignment=assignment,
        state_scope=state_scope,
        state_bound=state_bound,
    )
    if is_refusal(observed):
        return observed
    return evaluate_layer2(observed.value)


def _drive_refusal_observations(
    refusal: TypedRefusal,
    *,
    scan: ScanReport,
    slice_fp: Fingerprint,
    decl_fp: Fingerprint,
    permitted: tuple[str, ...],
    first_run: tuple[tuple[dict[str, object], ...], ...] = (),
) -> Result[Layer2Observations]:
    check = drive_error_kind(refusal)
    given = refusal.context.get("given")
    emitted: tuple[str, ...] = ()
    if check == "permitted_intent_kinds" and isinstance(given, str):
        emitted = (given,)
    if check == "permitted_intent_kinds":
        if not emitted:
            return _fail(
                "permitted_intent_kinds",
                "only permitted intent kinds may be emitted; a non-permitted kind is "
                "a Layer-2 conformance failure",
                given=repr(given),
                permitted=("entry", *permitted),
            )
        return Ok(
            _observations(
                loaded_in_isolation=True,
                book_present=False,
                scan=scan,
                golden_slice_fingerprint=slice_fp,
                declaration_fingerprint=decl_fp,
                first_run=first_run,
                second_run=(),
                emitted_kinds=emitted,
                permitted_exit_intents=permitted,
                state_bound_holds=True,
                restore_equivalent=True,
            )
        )
    return _fail(
        check,
        "a golden slice run that cannot emit intents is a Layer-2 conformance failure",
        cause=dict(refusal.context),
    )


def _observations(
    *,
    loaded_in_isolation: bool,
    book_present: bool,
    scan: ScanReport,
    golden_slice_fingerprint: Fingerprint,
    declaration_fingerprint: Fingerprint,
    first_run: tuple[tuple[dict[str, object], ...], ...],
    second_run: tuple[tuple[dict[str, object], ...], ...],
    emitted_kinds: tuple[str, ...],
    permitted_exit_intents: tuple[str, ...],
    state_bound_holds: bool,
    restore_equivalent: bool,
) -> Layer2Observations:
    return Layer2Observations(
        loaded_in_isolation=loaded_in_isolation,
        book_present=book_present,
        scan=scan,
        golden_slice_fingerprint=golden_slice_fingerprint,
        declaration_fingerprint=declaration_fingerprint,
        first_run=first_run,
        second_run=second_run,
        emitted_kinds=emitted_kinds,
        permitted_exit_intents=permitted_exit_intents,
        state_bound_holds=state_bound_holds,
        restore_equivalent=restore_equivalent,
    )


def _admit_declaration(declaration: object) -> Result[BotDefinition]:
    if isinstance(declaration, BotDefinition):
        return Ok(declaration)
    return mint_bot_definition(declaration)


def _assignment_of(bot: BotDefinition, assignment: object) -> Result[Mapping[str, object]]:
    if assignment is None:
        assignment = bot.canonical_assignment()
    return resolve_assignment(bot, assignment)


def _has_declared_seed(bot: BotDefinition) -> bool:
    for spec in bot.parameter_space:
        name = spec.name
        if name == _SEED_NAME or name.endswith("_seed"):
            return True
    return False


def _disallowed_kinds(emitted: Sequence[str], permitted_exits: Sequence[str]) -> tuple[str, ...]:
    allowed = {INTENT_KIND_ENTRY, *permitted_exits}
    return tuple(kind for kind in emitted if kind not in allowed)


def _as_bool(value: object, field: str) -> Result[bool]:
    if isinstance(value, bool):
        return Ok(value)
    return invalid(
        field,
        "a Layer-2 observation flag is a bool",
        given=repr(value),
        layer=_LAYER,
    )


def _as_fingerprint(value: object, field: str) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    parsed = Fingerprint.try_create(value)
    if is_refusal(parsed):
        return invalid(
            field,
            "a Layer-2 observation fingerprint is fp1:sha256:<hex>",
            given=repr(value),
            layer=_LAYER,
        )
    return parsed


def _as_scan(value: object) -> Result[ScanReport]:
    if isinstance(value, ScanReport):
        return Ok(value)
    if value is None:
        return Ok(ScanReport(findings=()))
    if isinstance(value, Mapping):
        mapping = cast("Mapping[str, object]", value)
        raw = mapping.get("findings", ())
        items = _as_findings(raw)
        if is_refusal(items):
            return items
        return Ok(ScanReport(findings=items.value))
    return _as_findings_report(value)


def _as_findings_report(value: object) -> Result[ScanReport]:
    items = _as_findings(value)
    if is_refusal(items):
        return items
    return Ok(ScanReport(findings=items.value))


def _as_findings(value: object) -> Result[tuple[ScanFinding, ...]]:
    if isinstance(value, ScanFinding):
        return Ok((value,))
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "scan_findings",
            "scan findings are a sequence of capability/path/lineno/detail records",
            given=type(value).__name__,
            layer=_LAYER,
        )
    found: list[ScanFinding] = []
    for item in cast("Sequence[object]", value):
        if isinstance(item, ScanFinding):
            found.append(item)
            continue
        if not isinstance(item, Mapping):
            return invalid(
                "scan_findings",
                "each scan finding is a mapping of capability, path, lineno, detail",
                given=type(item).__name__,
                layer=_LAYER,
            )
        mapping = cast("Mapping[str, object]", item)
        capability = mapping.get("capability")
        path = mapping.get("path")
        lineno = mapping.get("lineno")
        detail = mapping.get("detail")
        if not isinstance(capability, str) or not isinstance(path, str):
            return invalid(
                "scan_findings",
                "a scan finding names a denial-set capability and a source path",
                layer=_LAYER,
            )
        if isinstance(lineno, bool) or not isinstance(lineno, int):
            return invalid(
                "scan_findings",
                "a scan finding lineno is an integer",
                given=repr(lineno),
                layer=_LAYER,
            )
        if not isinstance(detail, str):
            return invalid(
                "scan_findings",
                "a scan finding detail is a string",
                layer=_LAYER,
            )
        found.append(ScanFinding(capability=capability, path=path, lineno=lineno, detail=detail))
    return Ok(tuple(found))


def _as_trace(value: object, field: str) -> Result[tuple[tuple[dict[str, object], ...], ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            field,
            "a golden-slice run is a sequence of per-instant intent-identity tuples",
            given=type(value).__name__,
            layer=_LAYER,
        )
    steps: list[tuple[dict[str, object], ...]] = []
    for instant in cast("Sequence[object]", value):
        if isinstance(instant, Mapping):
            steps.append((dict(cast("Mapping[str, object]", instant)),))
            continue
        if isinstance(instant, (str, bytes)) or not isinstance(instant, Sequence):
            return invalid(
                field,
                "each golden-slice instant is a sequence of intent identity mappings",
                given=type(instant).__name__,
                layer=_LAYER,
            )
        identities: list[dict[str, object]] = []
        for item in cast("Sequence[object]", instant):
            if not isinstance(item, Mapping):
                return invalid(
                    field,
                    "an intent identity is a mapping",
                    given=type(item).__name__,
                    layer=_LAYER,
                )
            identities.append(dict(cast("Mapping[str, object]", item)))
        steps.append(tuple(identities))
    return Ok(tuple(steps))


def _as_kind_tuple(value: object, field: str) -> Result[tuple[str, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, str):
        return Ok((value,))
    if not isinstance(value, Sequence) or isinstance(value, bytes):
        return invalid(
            field,
            "intent kinds are a sequence of tokens",
            given=type(value).__name__,
            layer=_LAYER,
        )
    names: list[str] = []
    for item in cast("Sequence[object]", value):
        if not isinstance(item, str) or item.strip() == "":
            return invalid(
                field,
                "an intent kind is a non-empty token",
                given=repr(item),
                layer=_LAYER,
            )
        names.append(item)
    return Ok(tuple(names))
