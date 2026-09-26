"""CT-25 — read-time entity-journal projections (logbooks), owned by COMP-QMF-DATA.

The Book journal, the BMS journal, and the per-bot journal — the operator's logbook —
are **declared read-time projections** over the AD-21 writer-scoped journal streams
Story 3.5 records, selected by **entity identity**. An entity holds no ``WriterId`` and
mints no stream of its own; per-entity, per-binding, and combined views are all extracted
on demand from the one recorded set of writer-scoped streams (AC1; DEC-0145). This module
is **read-only**: it never writes, and nothing here becomes an additional journal writer.

Four things this module pins down.

**Entity journals are projections, never writers (AC1; DEC-0145, DEC-0158).** A projection
is a selection over the recorded :class:`~qmf.data.journal.JournalEvent` streams keyed by
an :class:`EntitySelector` — a Book instance, a BMS instance, a Bot definition + seat, or a
full binding. :func:`entity_journal` (and the :func:`book_journal` / :func:`bms_journal` /
:func:`bot_logbook` conveniences) resolves the one recorded set of streams into a
:class:`Logbook`; the same recorded set yields many views, and no view is a stream.

**Two event classes, split because the neutral venue port cannot carry Book identity and
must not learn it (AC2; DEC-0145, DEC-0143, DEC-0173).** :func:`event_class_of` maps each
of the seven types to a :class:`EventClass`. **Risk-authored** events (decision, risk
transition, control action, promotion) carry the Book-definition fingerprint, the binding
identity ``(BookInstanceId, BmsInstanceId, VenueId, AccountId, world)``, and — where one
bot is concerned — the CT-33 Bot definition ``fp1`` plus its AD-41 seat binding, as
identity fields modelled generically on ``qmf-core`` nouns (no risk/QML type is imported —
they arrive in later epics). **Venue-authored** events (order, fill, data quality) carry
**only** the command record's content fingerprint; threading Book identity into the neutral
venue payload is a refusal (:func:`guard_neutral_venue_payload`). A Book projection that
must include orders and fills joins venue-authored events through the pinned versioned
command-fingerprint join (:class:`CommandIndex`), never by learning Book identity.

**Paper and live are separated by construction (AC3; FM-11, DEC-0145, DEC-0158).** A
projection resolves inside one **role-scoped namespace** (:func:`role_namespace`): the live
evidence namespace admits only ``role = live`` rows; demo, paper-validation, and
paper-benched rows resolve in their own role-scoped namespaces. Aggregating across account
roles **without** an explicitly-declared cross-role read is a ``policy rejection`` refusal
(FM-11). Only the two declared exceptions span roles — the AD-35 decay-cohort read
(:func:`decay_cohort_read`, DEC-0149) and the multi-role entity projection
(``cross_role=MULTI_ROLE_ENTITY``) — each carrying ``role`` on every projected row. There
is no write exception ever; this module never writes.

**The legacy five Records streams survive as projection names only (AC4; DEC-0145).**
``veto_ledger``, ``trade_journal``, ``book_journal``, ``ksa_audit_log``, and
``correlation_ledger`` are :class:`RecordsStreamName` projection names mapped onto the seven
journal event types by the **one** versioned :data:`RECORDS_STREAM_MAPPING` table — no
second event catalog is minted (:func:`records_stream`). ``veto_ledger`` selects on the
decision event's declared ``outcome = refused-by-door`` field, never on key presence.

Stdlib + qmf-core + the qmf-data journal vocabulary; frozen, immutable values throughout.

Identity readers, selectors, the projection engine, and the Records mapping live in
sibling modules; this module re-exports the public names so existing import paths keep
working.
"""

from __future__ import annotations

from qmf.data.logbooks_identity import (
    BindingIdentity,
    BotSeat,
    guard_neutral_venue_payload,
    read_binding,
    read_bot_seat,
    read_command_fingerprint,
    read_role,
)
from qmf.data.logbooks_project import (
    Logbook,
    ProjectedRow,
    bms_journal,
    book_journal,
    bot_logbook,
    decay_cohort_read,
    entity_journal,
)
from qmf.data.logbooks_records import (
    RECORDS_STREAM_MAPPING,
    RecordsStreamName,
    RecordsStreamRule,
    records_stream,
)
from qmf.data.logbooks_select import (
    CommandAttribution,
    CommandIndex,
    EntityKind,
    EntitySelector,
)
from qmf.data.logbooks_types import (
    ACCOUNT_ID_KEY,
    BMS_INSTANCE_ID_KEY,
    BOOK_DEFINITION_FP_KEY,
    BOOK_IDENTITY_FIELDS,
    BOOK_INSTANCE_ID_KEY,
    BOT_DEFINITION_FP_KEY,
    COMMAND_FINGERPRINT_KEY,
    CT25_CONTRACT_FORMAT_VERSION,
    ROLE_KEY,
    SEAT_BINDING_KEY,
    VENUE_ID_KEY,
    CrossRoleRead,
    EventClass,
    event_class_of,
    role_namespace,
)

__all__ = [
    "ACCOUNT_ID_KEY",
    "BMS_INSTANCE_ID_KEY",
    "BOOK_DEFINITION_FP_KEY",
    "BOOK_IDENTITY_FIELDS",
    "BOOK_INSTANCE_ID_KEY",
    "BOT_DEFINITION_FP_KEY",
    "COMMAND_FINGERPRINT_KEY",
    "CT25_CONTRACT_FORMAT_VERSION",
    "RECORDS_STREAM_MAPPING",
    "ROLE_KEY",
    "SEAT_BINDING_KEY",
    "VENUE_ID_KEY",
    "BindingIdentity",
    "BotSeat",
    "CommandAttribution",
    "CommandIndex",
    "CrossRoleRead",
    "EntityKind",
    "EntitySelector",
    "EventClass",
    "Logbook",
    "ProjectedRow",
    "RecordsStreamName",
    "RecordsStreamRule",
    "bms_journal",
    "book_journal",
    "bot_logbook",
    "decay_cohort_read",
    "entity_journal",
    "event_class_of",
    "guard_neutral_venue_payload",
    "read_binding",
    "read_bot_seat",
    "read_command_fingerprint",
    "read_role",
    "records_stream",
    "role_namespace",
]
