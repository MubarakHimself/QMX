"""Command-fingerprint-to-venue-id binding before wire handoff (TN-6; CT-19).

V1 maps into the venue client-id field through a durable command-id-binding
record persisted **before** submission — ``(venue client id, command fp1,
account, session epoch)`` — because a short venue client id cannot be a total
injection over an fp1 digest space plus stream qualification. Unpersistable
identity blocks submission (DEC-0191, DEC-0224).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, cast

from qmf.core import Ok, RecordSink, RefusalCategory, Result, Retryability, TypedRefusal, is_refusal

from qmn.venue import BindingOutcome, Command, CommandIdBindingRegistry

__all__ = [
    "VENUE_CLIENT_ID_PREFIX",
    "CommandIdentityBinder",
    "mint_venue_client_id",
]


VENUE_CLIENT_ID_PREFIX: Final[str] = "qmn"


def mint_venue_client_id(*, ordering_ordinal: object, session_epoch: object) -> Result[str]:
    """Mint a short venue client id for the non-injective cTrader clientMsgId map."""
    if (
        not isinstance(ordering_ordinal, int)
        or isinstance(ordering_ordinal, bool)
        or ordering_ordinal < 0
    ):
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "ordering_ordinal",
                "reason": "venue client id derivation requires the command ordinal",
                "given": repr(ordering_ordinal),
            },
        )
    if not isinstance(session_epoch, str) or session_epoch.strip() == "":
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "session_epoch",
                "reason": "venue client id derivation requires the session epoch",
                "given": repr(session_epoch),
            },
        )
    # Keep well under cTrader's 100-character clientMsgId bound.
    epoch_token = session_epoch.strip().replace(" ", "")[-24:]
    return Ok(f"{VENUE_CLIENT_ID_PREFIX}-{ordering_ordinal}-{epoch_token}")


@dataclass
class CommandIdentityBinder:
    """Persist command-fingerprint-to-venue-id binding before wire handoff.

    Wraps :class:`CommandIdBindingRegistry`. When the CT-18 mapping is not
    injective-and-total (V1 cTrader path), binding must succeed before handoff;
    storage failure blocks submission.
    """

    registry: CommandIdBindingRegistry
    injective_total: bool = False

    @classmethod
    def try_create(
        cls,
        record_sink: object,
        *,
        injective_total: object = False,
    ) -> Result[CommandIdentityBinder]:
        if not isinstance(injective_total, bool):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "injective_total",
                    "reason": "CT-18 command_id_mapping.injective_total is a boolean",
                    "given": repr(injective_total),
                },
            )
        if not isinstance(record_sink, RecordSink):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "record_sink",
                    "reason": "command-id binding persists through an injected RecordSink",
                    "given": repr(record_sink),
                },
            )
        registry = CommandIdBindingRegistry.try_create(
            cast("RecordSink[object]", record_sink)
        )
        if is_refusal(registry):
            return registry
        return Ok(cls(registry=registry.value, injective_total=injective_total))

    def bind_before_wire_handoff(
        self,
        command: object,
        *,
        venue_client_id: object | None = None,
    ) -> Result[BindingOutcome]:
        """Persist the fp1↔venue-id binding before wire handoff.

        Unpersistable identity is surfaced and blocks submission. Ordinal-bearing
        venue client ids are minted when the caller does not supply one.
        """
        if not isinstance(command, Command):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "command",
                    "reason": "identity binding requires a typed CT-19 Command",
                    "given": type(command).__name__,
                },
            )
        client_id = venue_client_id
        if client_id is None:
            minted = mint_venue_client_id(
                ordering_ordinal=command.ordering_ordinal,
                session_epoch=command.session_epoch,
            )
            if is_refusal(minted):
                return minted
            client_id = minted.value
        if not isinstance(client_id, str) or client_id.strip() == "":
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "venue_client_id",
                    "reason": "command-fingerprint-to-venue-id binding needs a venue client id",
                    "given": repr(client_id),
                },
            )
        bound = self.registry.bind_before_submission(
            command,
            venue_client_id=client_id.strip(),
            injective_total=self.injective_total,
        )
        if is_refusal(bound):
            # Unpersistable identity blocks submission — never hand off.
            return bound
        return bound
