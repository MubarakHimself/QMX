"""Book-level paper routing to one paired demo target (TN-9; Story 26.5).

The node collapses AD-9 paper roles: V1 paper routing uses role ``demo`` and
``world = live`` only. ``paper-validation`` and ``paper-benched`` are deliberately
unused so Book-mode PAPER evidence and benched-seat evidence share one
role-scoped namespace and are told apart by the routing reason on the
execution-target record (DEC-0194, DEC-0251). Routing never mints a Bot or Book
twin (DEC-0069 stays dead; DEC-0261).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from qmf.core import AccountRole, Fingerprint, Ok, Result, VenueId, World, is_refusal
from qmf.risk.binding import PairingRecord
from qmf.risk.paper import ExecutionResolution, ExecutionTarget, resolve_execution_target

from qmn.paper._refuse import clean_token, invalid, policy

__all__ = [
    "NODE_PAPER_ACCOUNT_ROLE",
    "NODE_PAPER_WORLD",
    "PairedDemoBinding",
    "build_paired_demo_target",
    "require_demo_paper_target",
    "resolve_book_execution_target",
]

# V1 node collapse: paper routing shares the demo role namespace (DEC-0194).
NODE_PAPER_ACCOUNT_ROLE: Final[AccountRole] = AccountRole.DEMO
NODE_PAPER_WORLD: Final[World] = World.LIVE


@dataclass(frozen=True, slots=True)
class PairedDemoBinding:
    """The single active paper-routing target for one live binding (TN-9).

    Carries the paired demo ``ExecutionTarget`` (role ``demo``), the typed BMS
    pairing record, and the binding's constant ``world = live``. No Bot or Book
    twin is present — the flip is a dated binding-epoch change only.
    """

    live_binding_epoch: Fingerprint
    paper_target: ExecutionTarget
    pairing: PairingRecord
    world: World = World.LIVE
    bot_twin_minted: bool = False
    book_twin_minted: bool = False

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "bot_twin_minted": self.bot_twin_minted,
                "book_twin_minted": self.book_twin_minted,
                "live_binding_epoch": self.live_binding_epoch.value,
                "pairing": self.pairing.fp1_identity(),
                "paper_target": self.paper_target.fp1_identity(),
                "world": self.world.value,
            }
        )


def require_demo_paper_target(target: object) -> Result[ExecutionTarget]:
    """Refuse any paper target that is not role ``demo`` (DEC-0194).

    ``paper-validation`` and ``paper-benched`` are not used on the node in V1.
    """
    if not isinstance(target, ExecutionTarget):
        return invalid(
            "paper_target",
            "paper routing reads an ExecutionTarget",
            given=repr(target),
        )
    if target.role is AccountRole.LIVE:
        return invalid(
            "paper_target",
            "the paper-routing target is a paired demo account, never the live account",
            given=target.role.value,
        )
    if target.role is not NODE_PAPER_ACCOUNT_ROLE:
        return policy(
            "paper_target",
            "V1 node paper routing uses role demo only; paper-validation and "
            "paper-benched are deliberately unused and told apart by routing "
            "reason, never by namespace",
            given=target.role.value,
            required=NODE_PAPER_ACCOUNT_ROLE.value,
        )
    return Ok(target)


def build_paired_demo_target(
    *,
    venue_id: object,
    account_id: object,
    live_bms_instance_id: object,
    paired_bms_instance_id: object,
    live_binding_epoch: object,
) -> Result[PairedDemoBinding]:
    """Build the single paired-demo paper target with its own BMS pairing.

    The target carries role ``demo`` and the binding keeps ``world = live``. No
    Bot twin and no Book twin are minted (DEC-0149, DEC-0261).
    """
    if not isinstance(venue_id, VenueId):
        return invalid(
            "venue_id",
            "a paired demo target names a VenueId",
            given=repr(venue_id),
        )
    account = clean_token(account_id)
    if account is None:
        return invalid(
            "account_id",
            "a paired demo target names a non-empty demo account id",
            given=repr(account_id),
        )
    if not isinstance(live_binding_epoch, Fingerprint):
        return invalid(
            "live_binding_epoch",
            "paper routing is scoped to the live binding epoch fingerprint",
            given=repr(live_binding_epoch),
        )
    target_result = ExecutionTarget.try_create(NODE_PAPER_ACCOUNT_ROLE, venue_id, account)
    if is_refusal(target_result):
        return target_result
    pairing_result = PairingRecord.try_create(
        live_bms_instance_id,
        paired_bms_instance_id,
        account,
    )
    if is_refusal(pairing_result):
        return pairing_result
    return Ok(
        PairedDemoBinding(
            live_binding_epoch=live_binding_epoch,
            paper_target=target_result.value,
            pairing=pairing_result.value,
            world=NODE_PAPER_WORLD,
            bot_twin_minted=False,
            book_twin_minted=False,
        )
    )


def resolve_book_execution_target(
    *,
    book_mode: object,
    seat_state: object,
    active_controls: object,
    live_target: object,
    paper_target: object,
    blocked_act: object = "entry",
) -> Result[ExecutionResolution]:
    """Resolve one per-intent execution target under node V1 paper rules.

    Wraps :func:`qmf.risk.paper.resolve_execution_target` after enforcing the
    demo-role paper target. Capital/authority controls and Book-mode PAPER /
    benched seats route to the paired target; market-risk ``blocks-paper``
    controls block live and paper alike (AD-35; DEC-0149).
    """
    demo = require_demo_paper_target(paper_target)
    if is_refusal(demo):
        return demo
    return resolve_execution_target(
        book_mode=book_mode,
        seat_state=seat_state,
        active_controls=active_controls,
        live_target=live_target,
        paper_target=demo.value,
        blocked_act=blocked_act,
    )
