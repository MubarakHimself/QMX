"""L3 acceptance — Story 19.5: pure downstream reads.

Requirements R24-R27, R29. Rendering is token substitution of the artifact and is
byte-stable; the headline shows world + role verbatim; interpretation reads the
CT-32 artifact and never a rendering; reproduction reproduces the fingerprint or
returns a typed refusal; every downstream read is publish-only.
"""

from __future__ import annotations

import pytest

from conftest import config, mint_args, ok

from qmf.core.fingerprint import World, canonical_bytes, fingerprint
from qmf.core.identity import AccountRole
from qmf.core.refusal import RefusalCategory, is_ok, is_refusal
from qmf.risk.performance import PerformanceResult, PublishAct
from qmb.results.ct32 import mint_run_performance_result, require_reproduced_fingerprint
from qmb.results.interpret import (
    DOWNSTREAM_FORBIDDEN_ACTS,
    compare_runs,
    explain_run,
    flag_refusal_heavy,
    refuse_downstream_act,
)
from qmb.results.render import (
    HTML_TEMPLATE,
    render_html,
    render_markdown,
    render_report,
    substitute_tokens,
)


def _mint(**overrides) -> PerformanceResult:
    args = mint_args(config())
    args.update(overrides)
    return ok(mint_run_performance_result(**args))


def _mint_role(role: AccountRole) -> PerformanceResult:
    return ok(mint_run_performance_result(**mint_args(config(account_role=role))))


# --- A20: render is a pure, byte-stable function of the artifact [R24] P0 -----


def test_a20_render_is_byte_stable_and_reads_the_same_from_object_or_bytes() -> None:
    artifact = _mint()
    first = ok(render_report(artifact))
    second = ok(render_report(artifact))
    assert first.html == second.html
    assert first.markdown == second.markdown

    # the SAME artifact via its stored canonical bytes renders identically —
    # rendering derives nothing the stored artifact does not already carry.
    raw = ok(canonical_bytes(artifact.fp1_identity()))
    from_bytes = ok(render_report(raw))
    assert from_bytes.html == first.html
    assert from_bytes.markdown == first.markdown


def test_a20_renderer_cannot_invent_a_value() -> None:
    # A template token with no stored field is a refusal, never a fabricated value.
    refused = substitute_tokens("x={{$NOT_A_STORED_FIELD}}", {"WORLD": "replay"})
    assert is_refusal(refused)
    assert refused.context["field"] == "tokens"


# --- A21: headline shows world + role verbatim, unmissably [R25] P0 ----------


def test_a21_headline_shows_world_and_role_verbatim() -> None:
    artifact = _mint()  # world=replay, role=demo
    html = ok(render_html(artifact))
    md = ok(render_markdown(artifact))
    assert "world=replay" in html
    assert "account-binding-role=demo" in html
    assert md.splitlines()[0].startswith("# world=replay")
    assert "account-binding-role=demo" in md.splitlines()[0]


def test_a21_a_different_role_changes_the_headline_verbatim() -> None:
    # Falsifiability: the headline tracks the stored role, not a constant.
    paper = _mint_role(AccountRole.PAPER_VALIDATION)
    html = ok(render_html(paper))
    assert f"account-binding-role={AccountRole.PAPER_VALIDATION.value}" in html
    assert "account-binding-role=demo" not in html


# --- A22: interpretation reads CT-32, never a rendering [R26] P1 -------------


def test_a22_interpretation_reads_the_artifact_not_a_rendering() -> None:
    artifact = _mint()
    explained = ok(explain_run(artifact))
    assert explained.world == World.REPLAY.value
    assert explained.account_binding_role == AccountRole.DEMO.value
    assert len(explained.measure_set) == len(artifact.measure_set)

    # given the rendered HTML, the skill has no path to the numbers — it refuses.
    html = ok(render_html(artifact))
    refused = explain_run(html)
    assert is_refusal(refused)
    assert refused.context["field"] == "artifact"


def test_a22_compare_and_flag_also_consume_the_artifact() -> None:
    artifact = _mint()
    compared = ok(compare_runs(artifact, artifact))
    assert compared.same_world is True
    assert compared.same_account_binding_role is True
    flagged = ok(flag_refusal_heavy(artifact))
    # a quiet run's tallies are all zero => not refusal-bearing
    assert flagged.refusal_bearing is False
    # comparing an artifact against its rendering is refused
    assert is_refusal(compare_runs(artifact, ok(render_html(artifact))))


# --- A23: reproduction reproduces exactly, or returns a typed refusal [R27] P0


def test_a23_identical_inputs_reproduce_the_fingerprint() -> None:
    cfg = config()
    first = ok(mint_run_performance_result(**mint_args(cfg)))
    second = ok(mint_run_performance_result(**mint_args(cfg)))
    fp1 = ok(first.fingerprint())
    fp2 = ok(second.fingerprint())
    assert fp1 == fp2
    assert ok(require_reproduced_fingerprint(fp1, fp2)) == fp1


def test_a23_a_mismatch_is_a_typed_refusal_never_silently_tolerated() -> None:
    cfg = config()
    fp = ok(ok(mint_run_performance_result(**mint_args(cfg))).fingerprint())
    # a run whose stream order differs mints a different fingerprint
    other = ok(ok(mint_run_performance_result(
        **mint_args(config(streams=("gbpusd",)), stream_order=("gbpusd",))
    )).fingerprint())
    assert fp != other
    refused = require_reproduced_fingerprint(fp, other, run_id=cfg.fingerprint)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "ct32_fingerprint"


# --- A24: every downstream read is publish-only [R29] P0 ---------------------


def test_a24_refuse_downstream_act_refuses_every_act_with_no_allow_arm() -> None:
    acts = set(DOWNSTREAM_FORBIDDEN_ACTS) | {m.value for m in PublishAct}
    for act in acts:
        result = refuse_downstream_act(act)
        assert is_refusal(result), act
        assert result.category is RefusalCategory.POLICY_REJECTION, act
    # an unknown act is invalid input, NEVER silently allowed (no Ok arm exists)
    unknown = refuse_downstream_act("read")
    assert is_refusal(unknown)
    assert unknown.category is RefusalCategory.INVALID_INPUT


def test_a24_publish_act_enum_covers_size_promote_bench_and_mode() -> None:
    # the forbidden-act vocabulary spans the acts a measurement producer may never
    # take — sizing, promotion, benching, and mode change among them.
    covered = {m.value for m in PublishAct}
    assert {"size", "promote", "bench", "change_mode"}.issubset(covered)
    for act in ("size", "promote", "bench", "change_mode", "bind"):
        assert is_refusal(refuse_downstream_act(act)), act


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
