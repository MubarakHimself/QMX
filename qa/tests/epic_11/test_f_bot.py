"""Epic 11 / Story 11.6 — CT-33 Bot definition identity + versioning (FR-047, CT-33).

F1 identity carve-out (the highest-damage guarantee); F2 parameter space law;
F3 family cardinality-one + confluence ordering; F4 permitted-intent subset;
F5 canonical assignment as a derived locus; F6 AD-30 versioning; F7 root-mints.
Header exclusion is observed through a real Registrar sink; F7 uses a recording
Registrar subclass owned by the test.
"""

from __future__ import annotations

import helpers as H

from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import UnitKind
from qmf.core.refusal import Result
from qmf.registry import KindRegistry, Registrar
from qml.declaration import (
    KIND_BOT_DEFINITION,
    BotDefinition,
    BotVersionGraph,
    install_bot_definition_kind,
    mint_bot_definition,
    promote_tuned_assignment,
    register_bot_definition,
)
from qml.footprint import mint_footprint
from qml.logic import mint_logic_identity


def _host_registrar() -> Registrar:
    registry = KindRegistry()
    H.unwrap(install_bot_definition_kind(registry), "install bot-definition kind")
    return Registrar(registry)


def _fp(payload_overrides: object = None, **kw: object) -> str:
    payload = H.bot_payload(**kw) if payload_overrides is None else payload_overrides
    bot = H.unwrap(mint_bot_definition(payload), "bot")
    return H.unwrap(bot.fingerprint_content(), "bot fp").value


# --- F1 identity carve-out ---------------------------------------------------


def test_f1_ad16_header_fields_are_excluded_from_identity() -> None:
    """F1 (11.6 AC1): registering the same content with different header facts gives one stable id.

    Two sandboxes differing only in (writer, sequence, created_at) derive an
    identical stable_id — the AD-16 header is carved out of fp1. Counter-case: if
    writer/created_at entered identity, the two stable_ids would differ.
    """
    # Two independent composition roots (sandboxes): each write is 'stored' with
    # its own writer, so both records carry their real, differing header facts.
    payload = H.bot_payload()
    a = H.unwrap(
        register_bot_definition(
            payload,
            registrar=_host_registrar(),
            writer=H.writer("node-a", KIND_BOT_DEFINITION),
            sequence=0,
            created_at=H.instant(H.CREATED_NS),
        ),
        "sandbox-a",
    )
    b = H.unwrap(
        register_bot_definition(
            payload,
            registrar=_host_registrar(),
            writer=H.writer("node-b", KIND_BOT_DEFINITION),
            sequence=3,
            created_at=H.instant(H.CREATED_NS + 5_000),
        ),
        "sandbox-b",
    )
    assert a.record.writer != b.record.writer
    assert a.record.sequence != b.record.sequence
    assert a.record.created_at != b.record.created_at
    assert a.record.stable_id == b.record.stable_id  # header carved out of identity
    # The fingerprintable content payload carries no header fields at all.
    payload_identity = H.unwrap(mint_bot_definition(payload), "content").identity_payload()
    for header in ("writer", "sequence", "stable_id", "created_at"):
        assert header not in payload_identity


def test_f1_each_semantic_group_enters_identity() -> None:
    """F1 (11.6 AC1): varying any of the six semantic groups changes fp1.

    Counter-case: a group whose change leaves fp1 unchanged is not in identity.
    """
    base = _fp()
    other_conf = H.a_confluence(tag="other-zone")
    other_footprint = H.unwrap(
        mint_footprint([H.stream()], [H.calendar()], [H.pinned("other-producer")]),
        "other footprint",
    )
    other_logic = mint_logic_identity("research-bot", "2.0.0", H.logic_source())
    variants = {
        "family": _fp(strategy_family_id="mean-revert"),
        "confluence": _fp(confluence_set=[other_conf]),
        "parameter_default": _fp(
            parameter_space=[
                {
                    "name": "lookback",
                    "type": "exact integer",
                    "bounds": {"min": 1, "max": 200},
                    "step": 1,
                    "default": 21,
                    "unit_kind": UnitKind.COUNT,
                    "ui": "ui-editable",
                }
            ]
        ),
        "footprint": _fp(footprint=other_footprint),
        "permitted_exit_intents": _fp(permitted_exit_intents=("close_full",)),
        "logic": _fp(logic_reference=H.unwrap(other_logic, "other logic")),
    }
    for group, fp in variants.items():
        assert fp != base, f"changing {group} did not change fp1 (group absent from identity)"


# --- F2 parameter space law --------------------------------------------------


def test_f2_variable_missing_unit_kind_is_invalid_input() -> None:
    """F2 (11.6 AC2): a declared variable missing its AD-40 unit-kind is invalid input.

    Counter-case: a unit-kind-less variable minting.
    """
    refused = mint_bot_definition(
        H.bot_payload(
            parameter_space=[
                {
                    "name": "lookback",
                    "type": "exact integer",
                    "bounds": {"min": 1, "max": 10},
                    "step": 1,
                    "default": 2,
                    "ui": "ui-editable",
                }
            ]
        )
    )
    assert H.category_of(refused) == "invalid input"


def test_f2_variable_missing_default_is_invalid_input() -> None:
    """F2: every declared parameter carries a mandatory default; an omission is invalid input."""
    refused = mint_bot_definition(
        H.bot_payload(
            parameter_space=[
                {
                    "name": "lookback",
                    "type": "exact integer",
                    "bounds": {"min": 1, "max": 10},
                    "step": 1,
                    "unit_kind": UnitKind.COUNT,
                    "ui": "ui-editable",
                }
            ]
        )
    )
    assert H.category_of(refused) == "invalid input"


def test_f2_all_four_parameter_types_validate() -> None:
    """F2: each B-8 type — exact integer, exact rational, categorical, boolean — is admissible."""
    specs = [
        {
            "name": "lookback",
            "type": "exact integer",
            "bounds": {"min": 1, "max": 200},
            "step": 1,
            "default": 20,
            "unit_kind": UnitKind.COUNT,
            "ui": "ui-editable",
        },
        {
            "name": "ratio",
            "type": "exact rational",
            "bounds": {"min": H.exact(1, 2, UnitKind.DIMENSIONLESS_RATIO), "max": H.exact(2, 1, UnitKind.DIMENSIONLESS_RATIO)},
            "step": H.exact(1, 2, UnitKind.DIMENSIONLESS_RATIO),
            "default": H.exact(1, 1, UnitKind.DIMENSIONLESS_RATIO),
            "unit_kind": UnitKind.DIMENSIONLESS_RATIO,
            "ui": "ui-editable",
        },
        {
            "name": "mode",
            "type": "categorical",
            "options": ["fast", "slow"],
            "default": "fast",
            "unit_kind": UnitKind.DIMENSIONLESS_RATIO,
            "ui": "ui-editable",
        },
        {
            "name": "enabled",
            "type": "boolean",
            "default": True,
            "unit_kind": UnitKind.DIMENSIONLESS_RATIO,
            "ui": "ui-editable",
        },
    ]
    bot = H.unwrap(mint_bot_definition(H.bot_payload(parameter_space=specs)), "four-type bot")
    assert len(bot.parameter_space) == 4


# --- F3 family cardinality-one + confluence ordering ------------------------


def test_f3_family_cardinality_must_be_exactly_one() -> None:
    """F3 (11.6 AC3): zero or more-than-one strategy-family id is invalid input (AD-17).

    Counter-case: two family ids being accepted.
    """
    zero = mint_bot_definition(H.bot_payload(strategy_family_id=[]))
    assert H.category_of(zero) == "invalid input"
    two = mint_bot_definition(H.bot_payload(strategy_family_id=["trend-follow", "mean-revert"]))
    assert H.category_of(two) == "invalid input"


def test_f3_confluence_set_is_one_or_more_ordered_by_child_fingerprint() -> None:
    """F3: the confluence set is one-or-more, canonically ordered by child fp ascending.

    Counter-case: a zero-member set admitted, or the canonical order not ascending.
    """
    empty = mint_bot_definition(H.bot_payload(confluence_set=[]))
    assert H.category_of(empty) == "invalid input"
    c1 = H.a_confluence(tag="alpha")
    c2 = H.a_confluence(tag="omega")
    bot = H.unwrap(mint_bot_definition(H.bot_payload(confluence_set=[c1, c2])), "bot")
    order = [cite.fingerprint.value for cite in bot.canonical_confluence_set()]
    assert order == sorted(order)


# --- F4 permitted-intent subset ---------------------------------------------


def test_f4_permitted_intents_are_a_subset_possibly_empty_entry_never_listed() -> None:
    """F4 (11.6 AC4): permitted exit intents are a subset of the CT-23 exit vocabulary.

    An empty set is legal (entry-only); 'entry' is never declared; an out-of-vocab
    kind refuses. Counter-case: 'entry' being admitted into the declared set.
    """
    entry_only = H.unwrap(mint_bot_definition(H.bot_payload(permitted_exit_intents=())), "entry only")
    assert entry_only.permitted_exit_intents == ()
    full = H.unwrap(mint_bot_definition(H.bot_payload(permitted_exit_intents=["close_full"])), "cf")
    assert "close_full" in full.permitted_exit_intents
    listed_entry = mint_bot_definition(H.bot_payload(permitted_exit_intents=["entry"]))
    assert H.category_of(listed_entry) == "invalid input"
    out_of_vocab = mint_bot_definition(H.bot_payload(permitted_exit_intents=["close_partial"]))
    assert H.category_of(out_of_vocab) == "invalid input"


def test_f4_no_sizing_venue_or_exit_logic_field() -> None:
    """F4: the declaration carries no sizing, venue command, or exit-logic field.

    Counter-case: an exit_logic / requested_r / venue_command field being admitted.
    """
    for forbidden in ("exit_logic", "requested_r", "venue_command", "sizing"):
        refused = mint_bot_definition({**H.bot_payload(), forbidden: "x"})
        assert H.category_of(refused) == "invalid input", f"{forbidden} admitted"


# --- F5 canonical assignment is a derived locus -----------------------------


def test_f5_canonical_assignment_is_the_default_projection_not_a_stored_field() -> None:
    """F5 (11.6 AC2): the canonical assignment is the defaults projection, derived twice equal.

    Counter-case: canonical_assignment differing from the declared defaults, or a
    separately declared canonical_assignment field being admitted.
    """
    bot = H.unwrap(mint_bot_definition(H.bot_payload()), "bot")
    assert dict(bot.canonical_assignment()) == {"lookback": 20}
    assert dict(bot.canonical_assignment()) == dict(bot.canonical_assignment())
    assert "canonical_assignment" not in bot.body()
    stuffed = mint_bot_definition({**H.bot_payload(), "canonical_assignment": {"lookback": 20}})
    assert H.category_of(stuffed) == "invalid input"


# --- F6 AD-30 versioning -----------------------------------------------------


def test_f6_versioning_branches_from_graph_multiple_heads_and_dated_current() -> None:
    """F6 (11.6 AC5): branches-from graph allows multiple heads; current is a separate dated pointer.

    A changed default mints a new Bot; re-adding a version is refused (immutable).
    Counter-case: a single-head-only graph, or a re-add succeeding.
    """
    root = H.unwrap(mint_bot_definition(H.bot_payload()), "root")
    tuned = H.unwrap(promote_tuned_assignment(root, {"lookback": 14}), "tuned")
    sibling = H.unwrap(promote_tuned_assignment(root, {"lookback": 30}), "sibling")
    root_fp = H.unwrap(root.fingerprint_content(), "root fp")
    tuned_fp = H.unwrap(tuned.fingerprint_content(), "tuned fp")
    sibling_fp = H.unwrap(sibling.fingerprint_content(), "sibling fp")
    assert tuned_fp != root_fp and sibling_fp != root_fp and tuned_fp != sibling_fp

    graph = BotVersionGraph()
    H.unwrap(graph.append_version(root_fp), "append root")
    H.unwrap(graph.append_version(tuned_fp, branches_from=root_fp), "append tuned")
    H.unwrap(graph.append_version(sibling_fp, branches_from=root_fp), "append sibling")
    assert set(graph.heads()) == {tuned_fp, sibling_fp}  # multiple heads legal
    assert graph.is_readable(root_fp)  # every version readable forever

    H.unwrap(graph.set_current(tuned_fp, H.instant()), "current-1")
    assert graph.current() == tuned_fp
    H.unwrap(graph.set_current(sibling_fp, H.instant(H.CREATED_NS + 1_000)), "current-2")
    assert graph.current() == sibling_fp
    assert len(graph.pointer_history()) == 2  # a separate dated pointer record each time

    readd = graph.append_version(root_fp)
    assert H.category_of(readd) == "invalid input"  # a version is immutable


def test_f6_occurrence_facts_never_mint_a_new_bot() -> None:
    """F6: re-binding, seat assignment, and paper flips are not identity fields.

    Counter-case: a 'seat' or 'paper' occurrence field being admitted into the Bot.
    """
    for occurrence in ("seat", "paper", "rebinding"):
        refused = mint_bot_definition({**H.bot_payload(), occurrence: "x"})
        assert H.category_of(refused) == "invalid input", f"{occurrence} admitted into Bot identity"


# --- F7 root-mints (AD-25) ---------------------------------------------------


class _RecordingRegistrar(Registrar):
    """A composition-root sink (IS-a Registrar) that records every register call."""

    def __init__(self, kinds: KindRegistry) -> None:
        super().__init__(kinds)
        self.calls: list[dict[str, object]] = []

    def register(self, **kwargs: object) -> Result[object]:  # type: ignore[override]
        self.calls.append(dict(kwargs))
        return super().register(**kwargs)


def test_f7_qml_returns_content_only_host_root_stamps_occurrence_facts() -> None:
    """F7 (11.6 AC6): qml returns fingerprintable content only; the host root mints the record.

    mint_bot_definition returns a BotDefinition, never a stamped record; the host
    supplies writer/sequence/created_at, observed reaching an injected recording
    sink. Counter-case: mint returning a record, or register not forwarding the
    host writer.
    """
    minted = H.unwrap(mint_bot_definition(H.bot_payload()), "content")
    assert isinstance(minted, BotDefinition)
    assert "writer" not in minted.identity_payload()

    registry = KindRegistry()
    H.unwrap(install_bot_definition_kind(registry), "install kind")
    sink = _RecordingRegistrar(registry)
    host_writer = H.writer("node-root", KIND_BOT_DEFINITION)
    receipt = H.unwrap(
        register_bot_definition(
            H.bot_payload(),
            registrar=sink,
            writer=host_writer,
            sequence=7,
            created_at=H.instant(),
        ),
        "root mint",
    )
    # The host's occurrence facts reached the sink unchanged; qml invented none.
    assert len(sink.calls) == 1
    call = sink.calls[0]
    assert call["writer"] == host_writer
    assert call["sequence"] == 7
    assert call["kind"] == KIND_BOT_DEFINITION
    # The writer unit is (machine, authoring role, kind).
    assert receipt.record.writer.machine == "node-root"
    assert receipt.record.writer.role == "authoring"
    assert receipt.record.writer.stream == KIND_BOT_DEFINITION


def test_f7_register_refusal_is_seen_through_the_sink() -> None:
    """F7: the composition root sees every RecordSink refusal.

    A bad writer reaches the sink and comes back as a typed refusal, not an
    exception. Counter-case: the refusal being swallowed or raised across the seam.
    """
    registry = KindRegistry()
    H.unwrap(install_bot_definition_kind(registry), "install kind")
    sink = _RecordingRegistrar(registry)
    refused = register_bot_definition(
        H.bot_payload(),
        registrar=sink,
        writer="not-a-writer-id",
        sequence=0,
        created_at=H.instant(),
    )
    assert H.category_of(refused) == "invalid input"
