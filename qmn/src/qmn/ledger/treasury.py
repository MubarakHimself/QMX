"""Operator-signed treasury boundary acts (TN-25; Story 26.4).

Accounting rollover, sweep, refund, re-seed, and paper reset mint append-only
boundary events. A boundary act never touches positions and never re-bases a
frozen R. Missed rollover is reconstructed as a correction. Paper P&L never
becomes treasury cash (DEC-0149, DEC-0158, DEC-0210).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Fingerprint, Instant, Money, Ok, Result, TypedRefusal, fingerprint, is_refusal
from qmf.risk.paper import reject_paper_pnl_to_treasury
from qmf.risk.r_faces import RFaces

from qmn.ledger._refuse import clean_token, invalid, policy
from qmn.ledger.binding_ledger import BindingVirtualLedger

__all__ = [
    "TREASURY_BOUNDARY_KINDS",
    "TreasuryBoundaryAct",
    "TreasuryBoundaryActKind",
    "TreasuryBoundaryJournal",
    "apply_treasury_boundary",
    "journal_missed_rollover_correction",
    "mint_treasury_boundary_act",
    "refuse_boundary_rebase_of_r",
    "refuse_paper_pnl_to_treasury",
]


class TreasuryBoundaryActKind(StrEnum):
    """Node treasury boundary acts including accounting rollover (TN-25).

    The four AD-16 reserved kinds plus ``accounting_rollover``. Rollover is
    journaled as a risk-transition boundary; missed rollover reconstructs as a
    correction of the same kind.
    """

    SWEEP = "sweep"
    REFUND = "refund"
    RE_SEED = "re_seed"
    PAPER_EPOCH_RESET = "paper_epoch_reset"
    ACCOUNTING_ROLLOVER = "accounting_rollover"


TREASURY_BOUNDARY_KINDS: Final[tuple[TreasuryBoundaryActKind, ...]] = tuple(
    TreasuryBoundaryActKind
)


@dataclass(frozen=True, slots=True)
class TreasuryBoundaryAct:
    """One operator-signed append-only treasury boundary event."""

    act_fingerprint: Fingerprint
    kind: TreasuryBoundaryActKind
    binding_epoch: Fingerprint
    cash_delta: Money
    operator_signature: str
    dated_at: Instant
    is_correction: bool = False
    corrects: Fingerprint | None = None
    touches_positions: bool = False
    rebases_frozen_r: bool = False

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "act_fingerprint": self.act_fingerprint.value,
            "binding_epoch": self.binding_epoch.value,
            "cash_delta": self.cash_delta.fp1_identity(),
            "dated_at": self.dated_at.fp1_identity(),
            "is_correction": self.is_correction,
            "kind": self.kind.value,
            "operator_signature": self.operator_signature,
            "rebases_frozen_r": self.rebases_frozen_r,
            "touches_positions": self.touches_positions,
        }
        if self.corrects is not None:
            body["corrects"] = self.corrects.value
        return MappingProxyType(body)


@dataclass
class TreasuryBoundaryJournal:
    """Append-only journal of treasury boundary acts for one binding."""

    binding_epoch: Fingerprint
    _acts: list[TreasuryBoundaryAct] = field(default_factory=list[TreasuryBoundaryAct])

    @property
    def acts(self) -> tuple[TreasuryBoundaryAct, ...]:
        return tuple(self._acts)

    def append(self, act: TreasuryBoundaryAct) -> Result[TreasuryBoundaryAct]:
        if act.binding_epoch != self.binding_epoch:
            return invalid(
                "binding_epoch",
                "treasury boundary act must match the journal binding epoch",
            )
        if act.touches_positions or act.rebases_frozen_r:
            return policy(
                "boundary",
                "a treasury boundary act never touches positions and never "
                "re-bases a frozen R",
            )
        self._acts.append(act)
        return Ok(act)


def refuse_paper_pnl_to_treasury(amount: object) -> TypedRefusal:
    """Paper P&L never becomes treasury cash (DEC-0149)."""
    return reject_paper_pnl_to_treasury(amount)


def refuse_boundary_rebase_of_r(
    *,
    faces_before: object,
    faces_after: object,
) -> Result[None]:
    """A boundary act must leave frozen R faces unchanged."""
    if not isinstance(faces_before, RFaces) or not isinstance(faces_after, RFaces):
        return invalid(
            "faces",
            "frozen R faces are RFaces values",
            before=repr(faces_before),
            after=repr(faces_after),
        )
    if faces_before.fp1_identity() != faces_after.fp1_identity():
        return policy(
            "frozen_r",
            "a treasury boundary act never re-bases a frozen R; the only V1 "
            "re-base is the partial-entry fill re-base of original_risk_amount",
        )
    return Ok(None)


def mint_treasury_boundary_act(
    *,
    kind: object,
    binding_epoch: object,
    cash_delta: object,
    operator_signature: object,
    dated_at: object,
    is_correction: object = False,
    corrects: object = None,
) -> Result[TreasuryBoundaryAct]:
    """Mint an operator-signed treasury boundary act (TN-25)."""
    if isinstance(kind, TreasuryBoundaryActKind):
        resolved_kind = kind
    elif isinstance(kind, str):
        try:
            resolved_kind = TreasuryBoundaryActKind(kind)
        except ValueError:
            return invalid(
                "kind",
                "treasury boundary kind is sweep|refund|re_seed|paper_epoch_reset|"
                "accounting_rollover",
                given=repr(kind),
                allowed=[m.value for m in TreasuryBoundaryActKind],
            )
    else:
        return invalid(
            "kind",
            "treasury boundary kind is sweep|refund|re_seed|paper_epoch_reset|"
            "accounting_rollover",
            given=repr(kind),
        )
    if not isinstance(binding_epoch, Fingerprint):
        return invalid(
            "binding_epoch",
            "boundary act is scoped to the CT-28 binding epoch",
            given=repr(binding_epoch),
        )
    if isinstance(cash_delta, float):
        return invalid(
            "cash_delta",
            "no float on the money path; boundary cash is Money",
            given=repr(cash_delta),
        )
    if not isinstance(cash_delta, Money):
        return invalid("cash_delta", "boundary cash is Money", given=repr(cash_delta))
    sig = clean_token(operator_signature)
    if sig is None:
        return invalid(
            "operator_signature",
            "a treasury boundary act requires an operator signature",
            given=repr(operator_signature),
        )
    if not isinstance(dated_at, Instant):
        return invalid("dated_at", "boundary act carries an Instant", given=repr(dated_at))
    if not isinstance(is_correction, bool):
        return invalid("is_correction", "correction flag is a bool", given=repr(is_correction))
    corrects_fp: Fingerprint | None
    if corrects is None:
        corrects_fp = None
    elif isinstance(corrects, Fingerprint):
        corrects_fp = corrects
    else:
        return invalid(
            "corrects",
            "a correction cites the prior act fingerprint",
            given=repr(corrects),
        )
    if is_correction and corrects_fp is None:
        return invalid(
            "corrects",
            "a missed-rollover correction cites the act it corrects",
        )

    content = {
        "binding_epoch": binding_epoch.value,
        "cash_delta": cash_delta.fp1_identity(),
        "class": "treasury-boundary-act",
        "dated_at": dated_at.fp1_identity(),
        "is_correction": is_correction,
        "kind": resolved_kind.value,
        "operator_signature": sig,
    }
    if corrects_fp is not None:
        content["corrects"] = corrects_fp.value
    fp = fingerprint(content)
    if is_refusal(fp):
        return fp
    return Ok(
        TreasuryBoundaryAct(
            act_fingerprint=fp.value,
            kind=resolved_kind,
            binding_epoch=binding_epoch,
            cash_delta=cash_delta,
            operator_signature=sig,
            dated_at=dated_at,
            is_correction=is_correction,
            corrects=corrects_fp,
            touches_positions=False,
            rebases_frozen_r=False,
        )
    )


def apply_treasury_boundary(
    *,
    ledger: object,
    journal: object,
    act: object,
    open_faces: object = (),
) -> Result[TreasuryBoundaryAct]:
    """Journal a boundary act and apply cash — never touch positions or R."""
    if not isinstance(ledger, BindingVirtualLedger):
        return invalid("ledger", "boundary applies to a BindingVirtualLedger", given=repr(ledger))
    if not isinstance(journal, TreasuryBoundaryJournal):
        return invalid(
            "journal",
            "boundary journals through TreasuryBoundaryJournal",
            given=repr(journal),
        )
    if not isinstance(act, TreasuryBoundaryAct):
        return invalid("act", "apply takes a TreasuryBoundaryAct", given=repr(act))
    if act.touches_positions or act.rebases_frozen_r:
        return policy(
            "boundary",
            "a treasury boundary act never touches positions and never re-bases a frozen R",
        )
    if isinstance(open_faces, Sequence) and not isinstance(open_faces, (str, bytes)):
        for item in cast("Sequence[object]", open_faces):
            check = refuse_boundary_rebase_of_r(faces_before=item, faces_after=item)
            if is_refusal(check):
                return check
    elif open_faces not in ((), None):
        return invalid(
            "open_faces",
            "open_faces is a sequence of RFaces snapshots",
            given=repr(open_faces),
        )

    positions_before = dict(ledger.position_snapshots())
    appended = journal.append(act)
    if is_refusal(appended):
        return appended
    row = ledger.append_boundary(
        cash_delta=act.cash_delta,
        recorded_at=act.dated_at,
        note=act.kind.value,
    )
    if is_refusal(row):
        return row
    positions_after = dict(ledger.position_snapshots())
    if positions_before != positions_after:
        return policy(
            "positions",
            "a treasury boundary act never touches positions and never re-bases a frozen R",
        )
    return Ok(act)


def journal_missed_rollover_correction(
    *,
    journal: object,
    ledger: object,
    missed_act: object,
    operator_signature: object,
    dated_at: object,
) -> Result[TreasuryBoundaryAct]:
    """Reconstruct a missed rollover as an append-only correction (TN-10/25)."""
    if not isinstance(missed_act, TreasuryBoundaryAct):
        return invalid(
            "missed_act",
            "missed rollover reconstruction cites the intended boundary act",
            given=repr(missed_act),
        )
    if missed_act.kind is not TreasuryBoundaryActKind.ACCOUNTING_ROLLOVER:
        return invalid(
            "missed_act",
            "missed-rollover correction reconstructs an accounting_rollover act",
            given=missed_act.kind.value,
        )
    correction = mint_treasury_boundary_act(
        kind=TreasuryBoundaryActKind.ACCOUNTING_ROLLOVER,
        binding_epoch=missed_act.binding_epoch,
        cash_delta=missed_act.cash_delta,
        operator_signature=operator_signature,
        dated_at=dated_at,
        is_correction=True,
        corrects=missed_act.act_fingerprint,
    )
    if is_refusal(correction):
        return correction
    return apply_treasury_boundary(ledger=ledger, journal=journal, act=correction.value)
