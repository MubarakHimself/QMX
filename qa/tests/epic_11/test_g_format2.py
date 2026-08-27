"""Epic 11 / Story 11.7 — CT-22/CT-23 format-version-2 mint DELTA (SC-05, R-009).

The format-2 shapes are qmf-risk-owned (COMP-QMF-RISK) with QML-authored
semantics; only the format-2 delta + migration/back-compat is Story 11.7's, so
only that is tested (the base CT-22/CT-23 door behaviour is Epic 10 and is not
re-asserted). Reached through public qmf.risk surfaces:

* G4 (R-009): a format-1 reader confronting a format-2 artifact refuses
  ``unsupported capability`` (``parse_inbound_intent`` version negotiation).
* G1a: the ``exit_policy`` catch-all default entry lands ONLY through the
  format-2 mint (a format-1 exit_policy cannot carry it).
* G3a: pre-mint format-1 artifacts stay readable forever.
* G5: a not-yet-ruled footprint requirement passes registration but blocks a
  live binding.

G1's "adds exactly three things and nothing more", the CT-23
``advisory_stop_proposal`` field-carrying (G2), and the full CT-23 intent
back-compat (G3 intent-level) are recorded UNPROVEN in RESULTS.md — see the
scope-honesty note there.
"""

from __future__ import annotations

import helpers as H

from qmf.core import AccountRole, UnitKind
from qmf.risk.door import (
    CT23_ACTIVE_FORMAT_VERSION,
    CT23_FORMAT_VERSION_1,
    ExitLogicRef,
    parse_inbound_intent,
)
from qmf.risk.exit_policy import ExitPolicy, ExitPolicyResolution, resolve_exit_policy_entry
from qmf.risk.footprint_requirements import (
    FootprintRequirement,
    FootprintRequirements,
    check_footprint_requirements_live_binding,
)
from qmf.risk.grammar import NotYetRuled


# --- G4 (R-009) version negotiation -----------------------------------------


def test_g4_format1_reader_refuses_a_format2_ct23_artifact() -> None:
    """G4 (11.7 AC4, R-009): a format-1 reader confronting a format-2 artifact refuses.

    The refusal is ``unsupported capability``, never a best-effort read. The version
    check short-circuits before the entry is built. Counter-case: a best-effort read
    (Ok) or a non-unsupported category on the newer-than-reader mismatch.
    """
    refused = parse_inbound_intent(
        {"contract_format_version": CT23_ACTIVE_FORMAT_VERSION, "intent_family": "entry", "entry": None},
        ct23_format_version=CT23_FORMAT_VERSION_1,
    )
    assert H.category_of(refused) == "unsupported capability"


def test_g4_unknown_ct23_version_is_unsupported_capability() -> None:
    """G4: an unknown CT-23 contract format version is unsupported capability, never best-effort."""
    refused = parse_inbound_intent(
        {"contract_format_version": 99, "intent_family": "entry", "entry": None},
        ct23_format_version=CT23_ACTIVE_FORMAT_VERSION,
    )
    assert H.category_of(refused) == "unsupported capability"


# --- G1a exit_policy catch-all is format-2-only surface ---------------------


def test_g1a_exit_policy_catch_all_lands_only_through_the_format2_mint() -> None:
    """G1 (11.7 AC1): the exit_policy catch-all default entry is net-new format-2 surface.

    A format-1 exit_policy cannot carry it; a format-2 one can and it resolves for a
    family with no explicit entry. Counter-case: a format-1 exit_policy accepting the
    catch-all (a silent field addition an old parser would admit).
    """
    ref = H.unwrap(ExitLogicRef.try_create("catch-all-mode"), "catch-all ref")
    family_ref = H.unwrap(ExitLogicRef.try_create("explicit-mode"), "family ref")

    format1_with_catch_all = ExitPolicy.try_create(
        {"trend-follow": family_ref},
        ("close_full",),
        catch_all_default_entry=ref,
        contract_format_version=1,
    )
    assert H.category_of(format1_with_catch_all) == "invalid input"

    format2 = H.unwrap(
        ExitPolicy.try_create(
            {"trend-follow": family_ref},
            ("close_full",),
            catch_all_default_entry=ref,
            contract_format_version=2,
        ),
        "format-2 exit policy",
    )
    # A family with no explicit entry resolves to the format-2 catch-all.
    resolved = H.unwrap(resolve_exit_policy_entry(format2, "unlisted-family"), "catch-all resolve")
    assert resolved.entry == ref
    assert resolved.resolution is not ExitPolicyResolution.EXPLICIT_FAMILY


def test_g4_unknown_exit_policy_version_is_unsupported_capability() -> None:
    """G4: an unknown exit_policy contract format version is unsupported capability."""
    ref = H.unwrap(ExitLogicRef.try_create("mode"), "ref")
    refused = ExitPolicy.try_create({"f": ref}, (), contract_format_version=3)
    assert H.category_of(refused) == "unsupported capability"


# --- G3a pre-mint format-1 artifacts stay readable --------------------------


def test_g3a_format1_exit_policy_stays_readable_forever() -> None:
    """G3 (11.7 AC3, AD-5): a pre-mint format-1 exit_policy stays readable at format 1.

    Counter-case: a format-1 exit_policy (no format-2 field) being refused after the
    format-2 mint.
    """
    ref = H.unwrap(ExitLogicRef.try_create("mode"), "ref")
    readable = H.unwrap(
        ExitPolicy.try_create({"trend-follow": ref}, ("close_full",), contract_format_version=1),
        "format-1 exit policy",
    )
    assert readable.contract_format_version == 1
    resolved = H.unwrap(resolve_exit_policy_entry(readable, "trend-follow"), "resolve")
    assert resolved.resolution is ExitPolicyResolution.EXPLICIT_FAMILY


# --- G5 not-yet-ruled passes registration, blocks live binding --------------


def _blank_requirements() -> FootprintRequirements:
    req = H.unwrap(
        FootprintRequirement.try_create(
            field_kind="stream_set",
            field_identity="primary",
            unit=UnitKind.COUNT,
            comparison="at-least",
            threshold=H.unwrap(NotYetRuled.try_create("GAP-0048"), "not-yet-ruled"),
            display_ordinal=0,
        ),
        "footprint requirement",
    )
    return H.unwrap(FootprintRequirements.try_create([req], contract_format_version=2), "reqs")


def test_g5_not_yet_ruled_requirement_passes_registration() -> None:
    """G5 (11.7 AC5): a not-yet-ruled requirement still registers (interfaces-only, SC-07).

    Counter-case: a blank (GAP-0048/0049) requirement failing to construct at all.
    """
    reqs = _blank_requirements()
    assert reqs.is_blank is True
    # It registers/binds non-live freely (a paper-validation account role).
    non_live = check_footprint_requirements_live_binding(reqs, AccountRole.PAPER_VALIDATION)
    from qmf.core.refusal import is_ok

    assert is_ok(non_live)


def test_g5_not_yet_ruled_requirement_blocks_live_binding() -> None:
    """G5 (11.7 AC5): a not-yet-ruled requirement blocks a live binding (policy rejection).

    Counter-case: a blank requirement admitting a live binding (blank must block live money).
    """
    reqs = _blank_requirements()
    refused = check_footprint_requirements_live_binding(reqs, AccountRole.LIVE)
    assert H.category_of(refused) == "policy rejection"
