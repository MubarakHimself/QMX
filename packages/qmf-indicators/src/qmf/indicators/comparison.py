"""CT-16 — the arithmetic-upgrade comparison suite and the format-version mint
(COMP-QMF-INDICATORS; Story 7.6, FM-4).

A dependency upgrade that changes a configured indicator's output for **identical
canonical inputs** must never be silently accepted, and must never trigger a
protocol-wide version bump. The comparison suite catches the change **before the upgrade
lands** — by comparing the output the current pinned reference produces (the *before*
result) against the output the candidate reference produces (the *after* result) over the
same configuration and the same canonical inputs — and, on any difference, mints the
**per-configured-indicator** contract format version with recorded **before/after
evidence** (DEC-0127, DEC-0030).

:func:`compare_reference_outputs` is that suite. It compares the two results channel by
channel under the same per-configuration integer-ULP comparator the equality law uses
(default 0), and returns a :class:`ComparisonReport`:

* **Unchanged** — every channel equal within tolerance: the upgrade may land with no mint
  (identical output is not a change).
* **Changed** — any channel differs: the report **always** carries a
  :class:`ContractFormatMint` (never a silent accept, FM-4). The mint records the previous
  and the next per-configured-indicator format version (``previous + 1``, never a jump and
  never the protocol version), the changed channels, and the ``fp1`` fingerprint of every
  channel's output on both sides — the recorded before/after evidence. The CT-16 protocol
  format version is reported unchanged: an arithmetic upgrade mints per configured
  indicator, never a protocol-wide bump.

Default-deny holds: this module imports **only** ``qmf.core`` and this package's own
modules. Public value types are frozen dataclasses and every operation succeeds or RETURNS
a CT-04 typed refusal (DEC-0101, DEC-0109, DEC-0120).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from qmf.core import Ok, RefusalCategory, Result, Retryability, TypedRefusal, is_refusal
from qmf.indicators.batch import BatchResult
from qmf.indicators.configured_indicator import CONTRACT_FORMAT_VERSION, ConfiguredIndicator
from qmf.indicators.series import IndicatorSeries
from qmf.indicators.streaming import ModeEqualityComparator, series_equal_within_ulps

__all__ = [
    "ComparisonReport",
    "ContractFormatMint",
    "OutputChangeVerdict",
    "compare_reference_outputs",
]


class OutputChangeVerdict(StrEnum):
    """Whether a candidate reference changed a configuration's output (CT-16 FM-4; DEC-0127).

    ``unchanged`` — every output channel is equal within the declared tolerance; the
    upgrade may land with no mint. ``changed`` — at least one channel differs; the change
    is never silently accepted and mints the per-configured-indicator contract format
    version.
    """

    UNCHANGED = "unchanged"
    CHANGED = "changed"


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a comparison operation returns (CT-04)."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT, retryability=Retryability.NO, context=context
    )


@dataclass(frozen=True, slots=True)
class ContractFormatMint:
    """The per-configured-indicator format-version mint an output change triggers (FM-4).

    ``formula_id`` and ``previous_format_version`` identify the configured indicator whose
    arithmetic changed; ``minted_format_version`` is ``previous + 1`` — the next
    per-configured-indicator format version, never a jump and never the protocol version.
    ``changed_channels`` names the output channels that differed, and ``before_evidence`` /
    ``after_evidence`` map every output channel to its output series' ``fp1`` fingerprint on
    the current-reference and candidate-reference sides — the recorded before/after
    evidence (DEC-0127, DEC-0030).
    """

    formula_id: str
    previous_format_version: int
    minted_format_version: int
    changed_channels: tuple[str, ...]
    before_evidence: Mapping[str, str]
    after_evidence: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class ComparisonReport:
    """The result of comparing a candidate reference's output to the current one (FM-4).

    ``verdict`` is unchanged or changed; ``per_channel_equal`` records, per declared output
    channel, whether the two sides are equal within tolerance; ``mint`` is the
    :class:`ContractFormatMint` when (and only when) the verdict is changed — a changed
    verdict is **never** a silent accept; and ``protocol_format_version`` is the CT-16
    contract format version, reported **unchanged** because an arithmetic upgrade mints per
    configured indicator, never a protocol-wide bump (DEC-0127, DEC-0103).
    """

    verdict: OutputChangeVerdict
    per_channel_equal: Mapping[str, bool]
    mint: ContractFormatMint | None
    protocol_format_version: int


def compare_reference_outputs(
    configuration: object,
    before: object,
    after: object,
    comparator: object = None,
) -> Result[ComparisonReport]:
    """Compare a candidate reference's output to the current one, minting on a change (FM-4).

    ``before`` is the result the current pinned reference produced and ``after`` the result
    the candidate reference produced, both over the **same configuration** and the **same
    canonical inputs**. The two must agree on the configuration's producer identity and on
    the input fingerprints — that is what "identical canonical inputs" means; a mismatch is
    an ``invalid input`` refusal, because a comparison over different inputs proves nothing
    about the upgrade. Each declared output channel is compared under the per-configuration
    integer-ULP ``comparator`` (default 0, exact equality).

    Returns a :class:`ComparisonReport`. When nothing changed, the verdict is unchanged and
    ``mint`` is ``None`` — the upgrade may land with no mint. When any channel changed, the
    verdict is changed and ``mint`` is **always** present (never a silent accept): it
    records ``previous + 1`` as the next per-configured-indicator format version, the
    changed channels, and every channel's before/after ``fp1`` evidence — while the CT-16
    protocol format version stays unchanged (never a protocol-wide bump).
    """
    if not isinstance(configuration, ConfiguredIndicator):
        return _invalid(
            "configuration", "a ConfiguredIndicator is required", given=repr(configuration)
        )
    if not isinstance(before, BatchResult) or not isinstance(after, BatchResult):
        return _invalid(
            "results",
            "the comparison takes the before and after BatchResults (current vs candidate "
            "reference over identical canonical inputs)",
        )
    resolved_comparator = comparator if comparator is not None else ModeEqualityComparator()
    if not isinstance(resolved_comparator, ModeEqualityComparator):
        return _invalid(
            "comparator",
            "a ModeEqualityComparator is required (or omit it for exact equality)",
            given=repr(comparator),
        )
    inputs_guard = _guard_identical_inputs(before, after)
    if inputs_guard is not None:
        return inputs_guard
    channels = tuple(channel.name for channel in configuration.output_schema)
    per_channel = _compare_channels(channels, before, after, resolved_comparator.ulps)
    if isinstance(per_channel, TypedRefusal):
        return per_channel
    changed = tuple(name for name in channels if not per_channel[name])
    if not changed:
        return Ok(
            ComparisonReport(
                verdict=OutputChangeVerdict.UNCHANGED,
                per_channel_equal=MappingProxyType(dict(per_channel)),
                mint=None,
                protocol_format_version=CONTRACT_FORMAT_VERSION,
            )
        )
    evidence = _channel_evidence(channels, before, after)
    if isinstance(evidence, TypedRefusal):  # pragma: no cover - series fingerprints are canonical
        return evidence
    before_evidence, after_evidence = evidence
    mint = ContractFormatMint(
        formula_id=configuration.formula_id,
        previous_format_version=configuration.contract_format_version,
        minted_format_version=configuration.contract_format_version + 1,
        changed_channels=changed,
        before_evidence=MappingProxyType(before_evidence),
        after_evidence=MappingProxyType(after_evidence),
    )
    return Ok(
        ComparisonReport(
            verdict=OutputChangeVerdict.CHANGED,
            per_channel_equal=MappingProxyType(dict(per_channel)),
            mint=mint,
            protocol_format_version=CONTRACT_FORMAT_VERSION,
        )
    )


def _guard_identical_inputs(before: BatchResult, after: BatchResult) -> TypedRefusal | None:
    """Refuse unless the two results share the configuration identity and canonical inputs.

    The FM-4 premise is "identical canonical inputs": the two results must name the same
    producer contract identity (the same configuration) and the same input fingerprints. A
    comparison over different inputs proves nothing about the upgrade, so it is refused.
    """
    if before.label.producer_contract_identity != after.label.producer_contract_identity:
        return _invalid(
            "results",
            "the before and after results name different producer identities; the "
            "comparison is over one configuration",
            before=before.label.producer_contract_identity.value,
            after=after.label.producer_contract_identity.value,
        )
    if before.label.input_fingerprints != after.label.input_fingerprints:
        return _invalid(
            "results",
            "the before and after results were computed over different canonical inputs; "
            "FM-4 compares identical canonical inputs",
        )
    return None


def _compare_channels(
    channels: tuple[str, ...],
    before: BatchResult,
    after: BatchResult,
    ulps: int,
) -> dict[str, bool] | TypedRefusal:
    """Compare each declared channel's before/after series under the integer-ULP tolerance."""
    per_channel: dict[str, bool] = {}
    for name in channels:
        before_series = before.outputs.get(name)
        after_series = after.outputs.get(name)
        if not isinstance(before_series, IndicatorSeries) or not isinstance(
            after_series, IndicatorSeries
        ):
            return _invalid(
                "results",
                "both results must carry an output series for every declared channel",
                channel=name,
            )
        equal = series_equal_within_ulps(before_series, after_series, ulps)
        if is_refusal(equal):  # pragma: no cover - both operands are IndicatorSeries
            return equal
        per_channel[name] = equal.value
    return per_channel


def _channel_evidence(
    channels: tuple[str, ...], before: BatchResult, after: BatchResult
) -> tuple[dict[str, str], dict[str, str]] | TypedRefusal:
    """The per-channel before/after ``fp1`` evidence for every declared channel."""
    before_evidence: dict[str, str] = {}
    after_evidence: dict[str, str] = {}
    for name in channels:
        before_fp = before.outputs[name].fingerprint()
        if is_refusal(before_fp):  # pragma: no cover - series content is canonical
            return before_fp
        after_fp = after.outputs[name].fingerprint()
        if is_refusal(after_fp):  # pragma: no cover - series content is canonical
            return after_fp
        before_evidence[name] = before_fp.value.value
        after_evidence[name] = after_fp.value.value
    return before_evidence, after_evidence
