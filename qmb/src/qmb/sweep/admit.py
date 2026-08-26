"""One registry as-of resolved at batch admission, frozen for every combination.

A sweep is admitted as a batch: admission resolves exactly ONE registry as-of
through the single library-owned registry-read port, freezes it for the whole
batch, and stamps that one as-of — a (``registry_as_of`` instant + set
fingerprint) — into the sweep label and into every combination's run label
(B-15; AR-55; SC-11; spec R10). There is no door-side or second cache: the one
port is frozen and every trial reads the same as-of.

The bot/Book/BMS context is declared once for the whole sweep, so admission
resolves it once — the bot to its ``fp1`` and the Book/BMS to materialized
config fragments — and every combination shares those identical fingerprints.
Two combinations citing the same Book therefore resolve the identical Book
``fp1``; a fresher registry state arriving mid-batch never changes an in-flight
or not-yet-started combination, because the frozen port does not consult a
fresher as-of set (SC-11; B-15). Compiling a combination's resolved run-config
cites every Book/BMS/bot fragment by explicit fingerprint against the frozen
as-of set, never by ``name@latest`` (B-3; B-13).

A context reference that a fresher as-of set shows superseded at admission time
is an AD-11 stale-evidence refusal at the port's configured
``qmb_stale_evidence_severity`` — returned, never raised, and with no invented
default — rather than a silent bind of either the stale or the fresher version
(AD-11; AR-55; FM-7). The frozen as-of is stamped into each combination's
resolved run-config as the ``registry_as_of`` field, so it appears verbatim in
every combination's CT-32 label set (B-13; AR-59).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, cast

from qmf.core.chrono import Instant, WriterId
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal

from qmb._refuse import invalid
from qmb.config import (
    ConfigFragment,
    ResolvedRunConfig,
    compile_run_config,
    materialize_bms_fragment,
    materialize_book_fragment,
)
from qmb.registryread import RegistryReadPort
from qmb.sweep.axes import SweepDeclaration, SweepRunSpec, expand_sweep

__all__ = [
    "ADMISSION_FREEZES_AS_OF",
    "ADMISSION_HAS_SECOND_CACHE",
    "ADMISSION_SINGLE_AS_OF",
    "REGISTRY_AS_OF_KEY",
    "SWEEP_LABEL_CLASS",
    "SWEEP_LABEL_FORMAT_VERSION",
    "SWEEP_RUN_LABEL_CLASS",
    "AdmittedSweep",
    "SweepLabel",
    "admit_sweep",
    "sweep_admission_identity",
]

# The frozen as-of is stamped under this run-config key so it lands verbatim in
# the CT-32 label set; it MUST match the results container's registry_as_of
# field (AR-59). ``test_sweep_admit`` asserts the two constants agree.
REGISTRY_AS_OF_KEY: Final[str] = "registry_as_of"

SWEEP_LABEL_CLASS: Final[str] = "qmb-sweep-label"
SWEEP_RUN_LABEL_CLASS: Final[str] = "qmb-sweep-run-label"
SWEEP_LABEL_FORMAT_VERSION: Final[int] = 1

# Admission resolves exactly one as-of and freezes it; the one port is the only
# cache there is (B-15; SC-11; DEC-0165).
ADMISSION_SINGLE_AS_OF: Final[bool] = True
ADMISSION_FREEZES_AS_OF: Final[bool] = True
ADMISSION_HAS_SECOND_CACHE: Final[bool] = False

_BOT_LAYER_KEY: Final[str] = "bot"


def sweep_admission_identity() -> dict[str, object]:
    """Identity-bearing batch-admission fields. Package SemVer is omitted."""
    return {
        "admission_freezes_as_of": ADMISSION_FREEZES_AS_OF,
        "admission_has_second_cache": ADMISSION_HAS_SECOND_CACHE,
        "admission_single_as_of": ADMISSION_SINGLE_AS_OF,
        "registry_as_of_key": REGISTRY_AS_OF_KEY,
        "sweep_label_class": SWEEP_LABEL_CLASS,
        "sweep_label_format_version": SWEEP_LABEL_FORMAT_VERSION,
        "sweep_run_label_class": SWEEP_RUN_LABEL_CLASS,
    }


def _registry_as_of_stamp(
    registry_as_of: Instant, set_fingerprint: Fingerprint
) -> dict[str, object]:
    """The frozen as-of as JSON-native (instant nanoseconds + set fingerprint).

    Shaped so the CT-32 result container reads it back verbatim as the
    ``registry_as_of`` field of every combination's label set (B-13, AR-59).
    """
    return {
        "value_ns": registry_as_of.value_ns,
        "fingerprint": set_fingerprint.value,
    }


@dataclass(frozen=True, slots=True)
class SweepLabel:
    """The one label the whole batch shares: the frozen registry as-of plus context.

    ``sweep_id`` is the sweep declaration's ``fp1``. ``registry_as_of`` and
    ``set_fingerprint`` ARE the one frozen as-of resolved at admission; every
    combination's run label carries the identical pair. ``bot_fp1`` /
    ``book_fp1`` / ``bms_fp1`` are the context resolved once to explicit
    fingerprints so no two combinations resolve different versions (B-15, SC-11).
    """

    sweep_id: Fingerprint
    registry_as_of: Instant
    set_fingerprint: Fingerprint
    bot_fp1: Fingerprint
    book_fp1: Fingerprint
    bms_fp1: Fingerprint

    def registry_as_of_stamp(self) -> dict[str, object]:
        """The frozen as-of stamp (instant nanoseconds + set fingerprint)."""
        return _registry_as_of_stamp(self.registry_as_of, self.set_fingerprint)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical sweep-label identity. Package SemVer is omitted."""
        return {
            "bms_fp1": self.bms_fp1.value,
            "book_fp1": self.book_fp1.value,
            "bot_fp1": self.bot_fp1.value,
            "class": SWEEP_LABEL_CLASS,
            "format_version": SWEEP_LABEL_FORMAT_VERSION,
            "registry_as_of": self.registry_as_of.fp1_identity(),
            "set_fingerprint": self.set_fingerprint.value,
            "sweep_id": self.sweep_id.value,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """The sweep label's ``fp1``, computed only by the qmf-core seam."""
        return fingerprint(self.fp1_identity())


@dataclass(frozen=True, slots=True)
class AdmittedSweep:
    """A sweep admitted as a batch over one frozen registry as-of (B-15, SC-11).

    ``port`` is the single library-owned registry-read port, frozen at
    admission: after admission it resolves by explicit fingerprint only, and a
    fresher as-of set arriving on the hub never reaches an in-flight or
    not-yet-started combination. ``book_fragment`` and ``bms_fragment`` are the
    context resolved once — shared identically by every combination — and
    ``combos`` are the expanded run specs.
    """

    declaration: SweepDeclaration
    port: RegistryReadPort
    label: SweepLabel
    book_fragment: ConfigFragment
    bms_fragment: ConfigFragment
    combos: tuple[SweepRunSpec, ...]

    @property
    def registry_as_of(self) -> Instant:
        """The one frozen as-of instant every combination shares."""
        return self.label.registry_as_of

    @property
    def set_fingerprint(self) -> Fingerprint:
        """The one frozen as-of set fingerprint every combination shares."""
        return self.label.set_fingerprint

    @property
    def run_count(self) -> int:
        """The batch size — the number of admitted combinations (spec R9)."""
        return len(self.combos)

    def registry_as_of_stamp(self) -> dict[str, object]:
        """The frozen as-of stamp that lands in every combo's CT-32 label set."""
        return self.label.registry_as_of_stamp()

    def run_label(self, combo: object) -> Result[dict[str, object]]:
        """The per-combination run label, carrying the frozen registry as-of (spec R10).

        A run label stamps the one frozen as-of onto this combination's identity
        (bot/Book/BMS by ``fp1`` plus the instrument, ``BarSpec``, and parameter
        content). Every combination's run label carries the identical
        ``registry_as_of`` pair the sweep label carries (B-15).
        """
        resolved = self._require_member(combo)
        if is_refusal(resolved):
            return resolved
        member = resolved.value
        label: dict[str, object] = {
            "bms_fp1": self.label.bms_fp1.value,
            "book_fp1": self.label.book_fp1.value,
            "bot_fp1": self.label.bot_fp1.value,
            "class": SWEEP_RUN_LABEL_CLASS,
            "combination": member.fp1_identity(),
            "format_version": SWEEP_LABEL_FORMAT_VERSION,
            "registry_as_of": self.registry_as_of_stamp(),
            "sweep_id": self.label.sweep_id.value,
        }
        return Ok(label)

    def compile_combo(
        self,
        combo: object,
        *,
        invocation_flags: object = None,
        workspace_defaults: object = None,
        condition_presets: object = (),
    ) -> Result[ResolvedRunConfig]:
        """Compile one combination's resolved run-config against the frozen as-of.

        The bot is cited by its resolved ``fp1`` and the Book/BMS ride as the
        fragments materialized once at admission, so compilation resolves every
        fragment by explicit fingerprint against the frozen as-of set, never by
        ``name@latest`` (B-3; B-13; B-15). The frozen ``registry_as_of`` is
        stamped into the resolved run-config so it appears verbatim in this
        combination's CT-32 label set (AR-59). ``registry_as_of`` is
        admission-owned: a caller may not declare it on an invocation flag or a
        workspace default.
        """
        resolved = self._require_member(combo)
        if is_refusal(resolved):
            return resolved
        member = resolved.value
        guarded = _refuse_caller_registry_as_of(invocation_flags, "invocation_flags")
        if guarded is not None:
            return guarded
        guarded = _refuse_caller_registry_as_of(workspace_defaults, "workspace_defaults")
        if guarded is not None:
            return guarded
        run_spec = dict(member.run_spec_layer())
        # Cite the bot by the one fingerprint resolved at admission; a frozen
        # port refuses an alias, so the run spec never carries name@latest.
        run_spec[_BOT_LAYER_KEY] = self.label.bot_fp1
        run_spec[REGISTRY_AS_OF_KEY] = self.registry_as_of_stamp()
        return compile_run_config(
            self.port,
            book_fragment=self.book_fragment,
            bms_fragment=self.bms_fragment,
            run_spec=run_spec,
            invocation_flags=invocation_flags,
            workspace_defaults=workspace_defaults,
            condition_presets=condition_presets,
        )

    def compile_all(
        self,
        *,
        invocation_flags: object = None,
        workspace_defaults: object = None,
        condition_presets: object = (),
    ) -> Result[tuple[ResolvedRunConfig, ...]]:
        """Compile every combination under one set of batch-level run settings.

        Each combination is one isolated resolved run-config; the batch merges
        nothing (DEC-0169). A single combination's compile refusal is returned
        as the batch's refusal here — per-combo isolation under the orchestrator
        is Story 20.3.
        """
        configs: list[ResolvedRunConfig] = []
        for member in self.combos:
            compiled = self.compile_combo(
                member,
                invocation_flags=invocation_flags,
                workspace_defaults=workspace_defaults,
                condition_presets=condition_presets,
            )
            if is_refusal(compiled):
                return compiled
            configs.append(compiled.value)
        return Ok(tuple(configs))

    def _require_member(self, combo: object) -> Result[SweepRunSpec]:
        """A combination that belongs to this admitted batch, cited by identity."""
        if not isinstance(combo, SweepRunSpec):
            return invalid(
                "combo",
                "a run label / combo compile names a SweepRunSpec of this batch",
                given=repr(type(combo).__name__),
            )
        identity = combo.fp1_identity()
        for member in self.combos:
            if member.fp1_identity() == identity:
                return Ok(member)
        return invalid(
            "combo",
            "this SweepRunSpec is not a combination of this admitted sweep",
            given=repr(identity),
        )


def admit_sweep(
    declaration: object,
    port: object,
    writer: object,
) -> Result[AdmittedSweep]:
    """Admit a sweep as a batch over exactly one frozen registry as-of (B-15, SC-11).

    Admission resolves the bot/Book/BMS context ONCE through the single
    library-owned registry-read port — the bot to its ``fp1`` and the Book/BMS
    to materialized config fragments — then freezes the port's as-of for the
    whole batch and stamps it into the sweep label. A context reference that a
    fresher as-of set shows superseded at admission time is an AD-11
    stale-evidence refusal at the port's configured severity, returned never
    raised (AD-11; AR-55; FM-7). Pass the live (unfrozen) port so admission can
    detect stale evidence before it freezes.
    """
    parsed = _as_declaration(declaration)
    if is_refusal(parsed):
        return parsed
    spec = parsed.value
    if not isinstance(port, RegistryReadPort):
        return invalid(
            "port",
            "a sweep admits its batch through the one library-owned registry-read port",
            given=repr(type(port).__name__),
        )
    if not isinstance(writer, WriterId):
        return invalid(
            "writer",
            "batch admission stamps a WriterId on each materialized fragment's "
            "CT-07 occurrence-of edge",
            given=repr(type(writer).__name__),
        )
    # Resolve the context against the LIVE port so a superseded reference is an
    # AD-11 stale-evidence refusal here, before the as-of is frozen.
    bot = port.resolve(spec.bot)
    if is_refusal(bot):
        return bot
    book_fragment = materialize_book_fragment(port, spec.book, writer)
    if is_refusal(book_fragment):
        return book_fragment
    bms_fragment = materialize_bms_fragment(port, spec.bms, writer)
    if is_refusal(bms_fragment):
        return bms_fragment
    combos = expand_sweep(spec)
    if is_refusal(combos):
        return combos
    sweep_id = spec.fingerprint()
    if is_refusal(sweep_id):
        return sweep_id
    # Freeze the one as-of for every combination. admit_batch flips the frozen
    # flag only, so the bound as-of — and its (instant + set fingerprint) — is
    # the one just used to resolve the context.
    frozen = port.admit_batch()
    label = SweepLabel(
        sweep_id=sweep_id.value,
        registry_as_of=frozen.bound.registry_as_of,
        set_fingerprint=frozen.bound.fingerprint,
        bot_fp1=bot.value.fingerprint,
        book_fp1=book_fragment.value.source_fp1,
        bms_fp1=bms_fragment.value.source_fp1,
    )
    return Ok(
        AdmittedSweep(
            declaration=spec,
            port=frozen,
            label=label,
            book_fragment=book_fragment.value,
            bms_fragment=bms_fragment.value,
            combos=combos.value,
        )
    )


def _as_declaration(value: object) -> Result[SweepDeclaration]:
    """Accept a :class:`SweepDeclaration` or coerce the raw axis mapping."""
    if isinstance(value, SweepDeclaration):
        return Ok(value)
    if not isinstance(value, Mapping):
        return invalid(
            "declaration",
            "a sweep is a SweepDeclaration or a mapping naming bot/book/bms plus "
            "the axes instruments, timeframes, and parameters",
            given=repr(type(value).__name__),
        )
    body = cast("Mapping[str, object]", value)
    return SweepDeclaration.try_create(
        bot=body.get("bot"),
        book=body.get("book"),
        bms=body.get("bms"),
        instruments=body.get("instruments"),
        timeframes=body.get("timeframes"),
        parameters=body.get("parameters"),
    )


def _refuse_caller_registry_as_of(layer: object, field: str) -> TypedRefusal | None:
    """Refuse a caller-declared ``registry_as_of``; admission owns the frozen as-of."""
    if isinstance(layer, Mapping) and REGISTRY_AS_OF_KEY in cast("Mapping[str, object]", layer):
        return invalid(
            field,
            "registry_as_of is stamped by batch admission from the one frozen "
            "as-of; it is never caller-declared (B-15, AR-59)",
            key=REGISTRY_AS_OF_KEY,
        )
    return None
