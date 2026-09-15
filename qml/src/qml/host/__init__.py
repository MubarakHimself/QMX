"""QML/host composition root — CT-06 envelope mint (AD-25 root-mints).

QML authors fingerprintable CT-33/CT-34 content and logic-source bytes. This
module is the composition root that holds the ``WriterId`` and stamps the dated
CT-06 envelope. QMB runs the resulting candidates; it does not author them.

Declaration helpers stay unwired for Bot-kind install/register (OR-06). The
host path is the first authoring write path for generation.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, cast

from qmf.core.chrono import Instant, WriterId
from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.registry import (
    FieldSetKind,
    KindRegistry,
    Registrar,
    RegistrationReceipt,
)

from qml._refuse import invalid, policy
from qml.conformance.registration import ConformanceTicket
from qml.declaration.bot import (
    KIND_BOT_DEFINITION,
    BotDefinition,
    bot_definition_kind_contract,
    mint_bot_definition,
)
from qml.declaration.confluence import (
    KIND_CONFLUENCE,
    Confluence,
    install_confluence_kind,
    register_confluence,
)
from qml.generation import AuthoredStructure

__all__ = [
    "HOST_MINTS_CT06_ENVELOPE",
    "QMB_AUTHORS_CANDIDATES",
    "HostMintedCandidate",
    "install_bot_definition_kind",
    "install_bot_domain_kinds",
    "mint_ct06_envelope",
    "mint_generation_envelope",
    "register_bot_definition",
]

HOST_MINTS_CT06_ENVELOPE: Final[bool] = True
QMB_AUTHORS_CANDIDATES: Final[bool] = False


def install_bot_definition_kind(registry: object) -> Result[FieldSetKind]:
    """Register the CT-33 kind on a host :class:`KindRegistry`."""
    if not isinstance(registry, KindRegistry):
        return invalid(
            "registry",
            "the Bot definition kind installs on a CT-06 KindRegistry at the "
            "QML/host composition root",
            given=type(registry).__name__,
        )
    contract = bot_definition_kind_contract()
    if is_refusal(contract):
        return contract
    installed = registry.register(contract.value)
    if is_refusal(installed):
        return installed
    return Ok(contract.value)


def install_bot_domain_kinds(registry: object) -> Result[KindRegistry]:
    """Install confluence and bot-definition kinds for a generation host mint."""
    if not isinstance(registry, KindRegistry):
        return invalid(
            "registry",
            "bot-domain kinds install on a CT-06 KindRegistry",
            given=type(registry).__name__,
        )
    confluence = install_confluence_kind(registry)
    if is_refusal(confluence):
        return confluence
    bot = install_bot_definition_kind(registry)
    if is_refusal(bot):
        return bot
    return Ok(registry)


def register_bot_definition(
    declaration: object,
    *,
    registrar: object,
    writer: object,
    sequence: object,
    created_at: object,
    ticket: object,
    at_birth_parent_refs: object = (),
) -> Result[RegistrationReceipt]:
    """Stamp fingerprintable CT-33 content onto a host CT-06 :class:`Registrar`.

    The Bot kind mints only when both conformance layers passed (QL-8). The host
    supplies writer, sequence, and created-at (AD-25). Declaration helpers do
    not ship this wiring (OR-06).
    """
    if not isinstance(registrar, Registrar):
        return invalid(
            "registrar",
            "a host composition root stamps the dated CT-06 record through a Registrar",
            given=type(registrar).__name__,
        )
    if not isinstance(ticket, ConformanceTicket) or not (
        ticket.layer1_passed and ticket.layer2_passed
    ):
        return policy(
            "ticket",
            "the Bot kind mints only for artifacts passing both conformance layers; "
            "the QML/host composition root does not stamp a CT-06 bot-definition "
            "envelope without a ticket",
            given=repr(type(ticket).__name__),
        )
    if isinstance(declaration, BotDefinition):
        content = declaration
    else:
        parsed = mint_bot_definition(declaration)
        if is_refusal(parsed):
            return parsed
        content = parsed.value
    parents: object = at_birth_parent_refs
    if parents in ((), None) and content.at_birth_parent_refs:
        parents = content.at_birth_parent_refs
    return registrar.register(
        kind=KIND_BOT_DEFINITION,
        body=content.body(),
        writer=writer,
        sequence=sequence,
        created_at=created_at,
        at_birth_parent_refs=parents,
    )


def mint_ct06_envelope(
    *,
    kind: object,
    body: object,
    registrar: object,
    writer: object,
    sequence: object,
    created_at: object,
    ticket: object = None,
    at_birth_parent_refs: object = (),
) -> Result[RegistrationReceipt]:
    """Mint one dated CT-06 envelope at the QML/host composition root."""
    if not isinstance(registrar, Registrar):
        return invalid(
            "registrar",
            "a host composition root stamps the dated CT-06 record through a Registrar",
            given=type(registrar).__name__,
        )
    token: str | None
    if isinstance(kind, str):
        token = kind
    else:
        raw = getattr(kind, "value", None)
        token = raw if isinstance(raw, str) else None
    if token is None:
        return invalid(
            "kind",
            "a CT-06 envelope names a bot-domain kind",
            given=repr(kind),
        )
    if token == KIND_BOT_DEFINITION:
        return register_bot_definition(
            body,
            registrar=registrar,
            writer=writer,
            sequence=sequence,
            created_at=created_at,
            ticket=ticket,
            at_birth_parent_refs=at_birth_parent_refs,
        )
    if token == KIND_CONFLUENCE:
        if isinstance(body, Confluence):
            legs: object = body.legs
            order = body.ordering.value if body.order_significant else None
        elif isinstance(body, Mapping):
            mapping = cast("Mapping[str, object]", body)
            legs = mapping.get("legs")
            if legs is None:
                legs = mapping
            order = mapping.get("order_significance")
        else:
            legs = body
            order = None
        if not isinstance(writer, WriterId):
            return invalid(
                "writer",
                "the host supplies a WriterId for the confluence stream",
                given=type(writer).__name__,
            )
        return register_confluence(
            legs,
            registrar=registrar,
            writer=writer,
            sequence=sequence,
            created_at=created_at,
            order_significance=order,
            at_birth_parent_refs=at_birth_parent_refs,
        )
    return invalid(
        "kind",
        "the QML/host composition root mints CT-06 envelopes for bot-definition "
        "and confluence; other kinds are not this write path",
        given=token,
    )


@dataclass(frozen=True, slots=True)
class HostMintedCandidate:
    """CT-06-stamped generation candidate. QMB runs it; QMB does not author it."""

    confluence: RegistrationReceipt | None
    bot: RegistrationReceipt | None
    logic_fp1: Fingerprint | None
    qmb_authors: bool = QMB_AUTHORS_CANDIDATES
    host_mints_envelope: bool = HOST_MINTS_CT06_ENVELOPE

    def bot_fp1(self) -> Fingerprint | None:
        """The minted Bot definition stable id, when a CT-33 envelope was stamped."""
        if self.bot is None:
            return None
        return self.bot.record.stable_id


def mint_generation_envelope(
    authored: object,
    *,
    registrar: object,
    created_at: object,
    ticket: object = None,
    bot_writer: object = None,
    confluence_writer: object = None,
    sequence: object = 0,
) -> Result[HostMintedCandidate]:
    """Stamp CT-06 envelopes for QML-authored generation content (FR-W38).

    QMB is not on this write path.
    """
    if not isinstance(authored, AuthoredStructure):
        return invalid(
            "authored",
            "the host mints CT-06 envelopes for qml.generation AuthoredStructure",
            given=type(authored).__name__,
        )
    if not isinstance(registrar, Registrar):
        return invalid(
            "registrar",
            "a host composition root stamps the dated CT-06 record through a Registrar",
            given=type(registrar).__name__,
        )
    stamped_at: Instant
    if isinstance(created_at, Instant):
        stamped_at = created_at
    else:
        parsed_at = Instant.try_create(created_at)
        if is_refusal(parsed_at):
            return invalid(
                "created_at",
                "the host supplies the CT-06 created-at Instant",
                given=repr(created_at),
            )
        stamped_at = parsed_at.value
    confluence_receipt: RegistrationReceipt | None = None
    bot_receipt: RegistrationReceipt | None = None
    if authored.confluence is not None:
        if confluence_writer is None:
            return invalid(
                "confluence_writer",
                "the host supplies a WriterId for the confluence kind stream",
            )
        stamped = register_confluence(
            authored.confluence.legs,
            registrar=registrar,
            writer=confluence_writer,
            sequence=sequence,
            created_at=stamped_at,
            order_significance=(
                authored.confluence.ordering.value
                if authored.confluence.order_significant
                else None
            ),
        )
        if is_refusal(stamped):
            return stamped
        confluence_receipt = stamped.value
    if authored.bot is not None:
        if bot_writer is None:
            return invalid(
                "bot_writer",
                "the host supplies a WriterId for the bot-definition kind stream",
            )
        stamped_bot = register_bot_definition(
            authored.bot,
            registrar=registrar,
            writer=bot_writer,
            sequence=sequence,
            created_at=stamped_at,
            ticket=ticket,
        )
        if is_refusal(stamped_bot):
            return stamped_bot
        bot_receipt = stamped_bot.value
    logic_fp: Fingerprint | None = None
    if authored.logic is not None:
        logic_fp = authored.logic.source_manifest
    if confluence_receipt is None and bot_receipt is None and logic_fp is None:
        return invalid(
            "authored",
            "generation stamps a CT-06 envelope for new CT-33/CT-34 content "
            "and/or records logic-source bytes; an empty authoring is refused",
        )
    return Ok(
        HostMintedCandidate(
            confluence=confluence_receipt,
            bot=bot_receipt,
            logic_fp1=logic_fp,
        )
    )
