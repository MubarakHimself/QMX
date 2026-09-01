"""Operator-signed CT-24 Book-mode PAPER transitions (TN-9; Story 26.5).

A paper flip is a dated binding-epoch change — never a new Book and never a Bot
twin. The transition appends to the CT-24 stream, freezes a paper epoch, points
at exactly one paired demo target (role ``demo``, ``world = live``), and leaves
current mode as a read-time fold over the stream (DEC-0149, DEC-0194, DEC-0261).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from qmf.core import Fingerprint, Instant, Money, Ok, Result, fingerprint, is_refusal
from qmf.risk.binding import BookInstanceId
from qmf.risk.paper import (
    BindingTransitionRecord,
    BindingTransitionStream,
    BookMode,
    PaperEpochLog,
    PaperEpochRecord,
    PaperTargetLog,
    PaperTargetRecord,
    TriggerDisposition,
    TriggerKind,
)

from qmn.paper._refuse import clean_token, invalid, policy
from qmn.paper.routing import (
    NODE_PAPER_WORLD,
    PairedDemoBinding,
    require_demo_paper_target,
)

__all__ = [
    "OPERATOR_PAPER_FLIP_TRIGGER",
    "PaperFlipPackage",
    "fold_book_mode",
    "mint_operator_paper_flip",
]

OPERATOR_PAPER_FLIP_TRIGGER: Final[str] = "operator-paper-flip"


@dataclass(frozen=True, slots=True)
class PaperFlipPackage:
    """Everything minted by one operator-signed LIVE→PAPER transition.

    Carries the CT-24 transition, the frozen paper epoch, the active paper-target
    record, the paired-demo binding descriptor, and the new binding epoch. Twin
    flags stay false — the flip never mints a Bot or Book twin.
    """

    transition: BindingTransitionRecord
    transition_fingerprint: Fingerprint
    paper_epoch: PaperEpochRecord
    paper_epoch_fingerprint: Fingerprint
    paper_target_record: PaperTargetRecord
    paper_target_fingerprint: Fingerprint
    paired: PairedDemoBinding
    binding_epoch: Fingerprint
    world: str = NODE_PAPER_WORLD.value
    bot_twin_minted: bool = False
    book_twin_minted: bool = False

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "binding_epoch": self.binding_epoch.value,
                "bot_twin_minted": self.bot_twin_minted,
                "book_twin_minted": self.book_twin_minted,
                "paper_epoch_fingerprint": self.paper_epoch_fingerprint.value,
                "paper_target_fingerprint": self.paper_target_fingerprint.value,
                "transition_fingerprint": self.transition_fingerprint.value,
                "world": self.world,
            }
        )


def fold_book_mode(
    stream: object,
    book_instance_id: object,
    *,
    as_of: object = None,
) -> Result[BookMode]:
    """Read current Book mode as the CT-24 fold — never a stored field."""
    if not isinstance(stream, BindingTransitionStream):
        return invalid(
            "stream",
            "Book mode folds over a BindingTransitionStream",
            given=repr(stream),
        )
    fold = stream.current_mode(book_instance_id, as_of=as_of)
    return Ok(fold.mode)


def mint_operator_paper_flip(
    *,
    book_instance_id: object,
    live_binding_epoch: object,
    transition_instant: object,
    operator_signature: object,
    starting_balance: object,
    paired: object,
    transition_stream: object,
    paper_target_log: object,
    paper_epoch_log: object,
    mint_bot_twin: object = False,
    mint_book_twin: object = False,
) -> Result[PaperFlipPackage]:
    """Mint an operator-signed CT-24 LIVE→PAPER flip for one Book (SCN-0006).

    Appends the transition, freezes the paper epoch, and records the single
    active paper-routing target. Refuses any request to mint a Bot or Book twin.
    """
    if mint_bot_twin is not False:
        return policy(
            "mint_bot_twin",
            "a paper flip never mints a Bot twin; DEC-0069 stays dead and "
            "DEC-0261 grants no per-bot paper lane on the node",
            given=repr(mint_bot_twin),
        )
    if mint_book_twin is not False:
        return policy(
            "mint_book_twin",
            "a paper flip is a dated binding-epoch change, never a new Book",
            given=repr(mint_book_twin),
        )
    if not isinstance(book_instance_id, BookInstanceId):
        return invalid(
            "book_instance_id",
            "a paper flip names the Book instance it applies to — never a new Book",
            given=repr(book_instance_id),
        )
    if not isinstance(live_binding_epoch, Fingerprint):
        return invalid(
            "live_binding_epoch",
            "a paper flip cites the live binding epoch it supersedes",
            given=repr(live_binding_epoch),
        )
    if not isinstance(transition_instant, Instant):
        return invalid(
            "transition_instant",
            "a paper flip is dated with an injected Instant",
            given=repr(transition_instant),
        )
    signature = clean_token(operator_signature)
    if signature is None:
        return invalid(
            "operator_signature",
            "an operator-signed CT-24 paper flip carries a non-empty signature",
            given=repr(operator_signature),
        )
    if not isinstance(starting_balance, Money):
        return invalid(
            "starting_balance",
            "the paper starting balance is exact Money frozen at flip",
            given=repr(starting_balance),
        )
    if not isinstance(paired, PairedDemoBinding):
        return invalid(
            "paired",
            "a paper flip routes through a PairedDemoBinding",
            given=repr(paired),
        )
    if paired.live_binding_epoch != live_binding_epoch:
        return invalid(
            "paired",
            "the paired demo binding must cite the same live binding epoch",
            paired_epoch=paired.live_binding_epoch.value,
            live_binding_epoch=live_binding_epoch.value,
        )
    demo = require_demo_paper_target(paired.paper_target)
    if is_refusal(demo):
        return demo
    if not isinstance(transition_stream, BindingTransitionStream):
        return invalid(
            "transition_stream",
            "the CT-24 stream is a BindingTransitionStream",
            given=repr(transition_stream),
        )
    if not isinstance(paper_target_log, PaperTargetLog):
        return invalid(
            "paper_target_log",
            "the paper-target log is a PaperTargetLog",
            given=repr(paper_target_log),
        )
    if not isinstance(paper_epoch_log, PaperEpochLog):
        return invalid(
            "paper_epoch_log",
            "the paper-epoch log is a PaperEpochLog",
            given=repr(paper_epoch_log),
        )

    trigger_result = TriggerKind.try_create(
        OPERATOR_PAPER_FLIP_TRIGGER,
        TriggerDisposition.ROUTES_TO_PAPER,
    )
    if is_refusal(trigger_result):
        return trigger_result

    epoch_result = PaperEpochRecord.try_create(
        book_instance_id,
        live_binding_epoch,
        starting_balance,
        signature,
        transition_instant,
    )
    if is_refusal(epoch_result):
        return epoch_result
    epoch_fp = paper_epoch_log.mint(epoch_result.value)
    if is_refusal(epoch_fp):
        return epoch_fp

    target_record = PaperTargetRecord.try_create(
        live_binding_epoch,
        demo.value,
        transition_instant,
    )
    if is_refusal(target_record):
        return target_record
    target_fp = paper_target_log.mint(target_record.value)
    if is_refusal(target_fp):
        return target_fp

    binding_epoch = fingerprint(
        {
            "class": "paper-binding-epoch",
            "live_binding_epoch": live_binding_epoch.value,
            "paper_epoch": epoch_fp.value.value,
            "paper_target": target_fp.value.value,
            "transition_instant": transition_instant.fp1_identity(),
            "world": NODE_PAPER_WORLD.value,
        }
    )
    if is_refusal(binding_epoch):
        return binding_epoch

    transition = BindingTransitionRecord.try_create(
        book_instance_id,
        binding_epoch.value,
        BookMode.PAPER,
        transition_instant,
        trigger_result.value,
        paper_target_ref=demo.value,
        paper_epoch_ref=epoch_fp.value,
        operator_signature=signature,
    )
    if is_refusal(transition):
        return transition
    transition_fp = transition_stream.mint(transition.value)
    if is_refusal(transition_fp):
        return transition_fp

    return Ok(
        PaperFlipPackage(
            transition=transition.value,
            transition_fingerprint=transition_fp.value,
            paper_epoch=epoch_result.value,
            paper_epoch_fingerprint=epoch_fp.value,
            paper_target_record=target_record.value,
            paper_target_fingerprint=target_fp.value,
            paired=paired,
            binding_epoch=binding_epoch.value,
            world=NODE_PAPER_WORLD.value,
            bot_twin_minted=False,
            book_twin_minted=False,
        )
    )
