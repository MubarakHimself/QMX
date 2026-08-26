"""Story 19.5 — pure downstream reads: render, interpret, reproduce."""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TypeVar, cast

import qmb.results.render as render_mod
from qmb.config import ResolvedRunConfig
from qmb.doors import api
from qmb.results import (
    AGENTS_PARSE_HTML,
    CONCURRENCY_IS_SCHEDULING_ONLY,
    CT32_ARTIFACT_NAME,
    DOWNSTREAM_FORBIDDEN_ACTS,
    DOWNSTREAM_PUBLISH_ONLY,
    HTML_REPORT_NAME,
    HTML_TEMPLATE,
    INTERPRETATION_SOURCE,
    MARKDOWN_REPORT_NAME,
    MARKDOWN_TEMPLATE,
    RENDER_ADDS_COMPUTATION,
    RENDER_MODE,
    RESULTS_DIR_NAME,
    SHARED_MUTABLE_RENDER_STATE,
    assemble_run_performance_result,
    compare_runs,
    downstream_read_identity,
    explain_run,
    flag_refusal_heavy,
    load_stored_ct32,
    looks_like_rendering,
    refuse_downstream_act,
    render_html,
    render_markdown,
    render_report,
    result_identity,
    stored_ct32_fingerprint,
    write_run_renders,
)
from qmb.runloop import (
    STREAM_SET_KEY,
    SilentSliceHandler,
    SliceObservation,
    run,
    verify_stored_reproduction,
)
from qmf.core.chrono import Instant
from qmf.core.fingerprint import World, fingerprint
from qmf.core.identity import AccountRole
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.risk.performance import PerformanceResult, PublishAct

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_CONCURRENT_RUNS = 14


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _obs(stream_id: str, ns: int = _NS, *, closed: bool = True) -> SliceObservation:
    return _ok(SliceObservation.try_create(stream_id, _instant(ns), closed))


def _config(
    *,
    streams: tuple[str, ...] = ("eurusd",),
    account_role: object = AccountRole.DEMO,
    **keys: object,
) -> ResolvedRunConfig:
    stamp = _ok(
        fingerprint(
            {
                "n": "downstream-reads-cfg",
                "streams": list(streams),
                "role": repr(account_role),
                "keys": sorted(keys),
            }
        )
    )
    payload: dict[str, object] = {STREAM_SET_KEY: streams, "account_role": account_role}
    payload.update(keys)
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys=payload,
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
        binding_fp1=stamp,
    )


def _slices(streams: tuple[str, ...] = ("eurusd",)) -> tuple[tuple[SliceObservation, ...], ...]:
    first = tuple(_obs(stream_id, _NS) for stream_id in streams)
    second = tuple(_obs(stream_id, _NS + 1) for stream_id in streams)
    return (first, second)


def _run(*, config: ResolvedRunConfig | None = None) -> object:
    bound = config if config is not None else _config()
    return _ok(run(slices=_slices(), config=bound, handler=SilentSliceHandler()))


def _stored(tmp_path: Path, *, config: ResolvedRunConfig | None = None) -> dict[str, object]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    outcome = _run(config=config)
    _ok(assemble_run_performance_result(outcome, output_dir=tmp_path))
    return _ok(load_stored_ct32(tmp_path))


def _digits(text: str) -> set[str]:
    return set(re.findall(r"-?\d+", text))


def test_renderers_are_token_substitution_and_add_no_number(tmp_path: Path) -> None:
    body = _stored(tmp_path)
    html_page = _ok(render_html(body))
    markdown = _ok(render_markdown(body))
    report = _ok(render_report(tmp_path))
    assert html_page == report.html
    assert markdown == report.markdown
    assert RENDER_MODE == "token-substitution"
    assert RENDER_ADDS_COMPUTATION is False
    assert result_identity()["html_payload"] is False
    artifact_digits = _digits(json.dumps(body))
    assert _digits(html_page) <= artifact_digits | _digits(HTML_TEMPLATE)
    assert _digits(markdown) <= artifact_digits | _digits(MARKDOWN_TEMPLATE)
    assert "assemble_v1_measure_set" not in vars(render_mod)
    assert "assemble_v1_chart_set" not in vars(render_mod)


def test_headline_shows_world_and_role_verbatim_and_unmissably(tmp_path: Path) -> None:
    paper = _stored(tmp_path, config=_config(account_role=AccountRole.PAPER_VALIDATION))
    html_page = _ok(render_html(paper))
    markdown = _ok(render_markdown(paper))
    world = cast("dict[str, object]", paper["result_label"])["world"]
    role = paper["account_binding_role"]
    assert world == World.REPLAY.value
    assert role == AccountRole.PAPER_VALIDATION.value
    assert html_page.index("qmb-headline-unmissable") < html_page.index("<main>")
    assert f'data-world="{world}"' in html_page
    assert f'data-account-binding-role="{role}"' in html_page
    assert f"world={world}" in html_page
    assert f"account-binding-role={role}" in html_page
    assert markdown.startswith(f"# world={world} · account-binding-role={role}")
    live_copy = dict(paper)
    live_label = dict(cast("dict[str, object]", paper["result_label"]))
    live_label["world"] = World.LIVE.value
    live_copy["result_label"] = live_label
    live_copy["account_binding_role"] = AccountRole.LIVE.value
    live_html = _ok(render_html(live_copy))
    assert "world=live" in live_html
    assert "account-binding-role=live" in live_html
    assert "world=replay" not in live_html


def test_interpretation_reads_ct32_never_html(tmp_path: Path) -> None:
    body = _stored(tmp_path)
    html_page = _ok(render_html(body))
    explained = _ok(explain_run(body))
    assert explained.source == INTERPRETATION_SOURCE
    assert explained.parsed_html is False
    assert AGENTS_PARSE_HTML is False
    assert explained.world == World.REPLAY.value
    assert explained.account_binding_role == AccountRole.DEMO.value
    refused_html = explain_run(html_page)
    assert is_refusal(refused_html)
    assert refused_html.category is RefusalCategory.POLICY_REJECTION
    assert refused_html.context["field"] == "artifact"
    refused_md = compare_runs(_ok(render_markdown(body)), body)
    assert is_refusal(refused_md)
    assert looks_like_rendering(html_page) is True
    assert looks_like_rendering(body) is False


def test_compare_runs_and_refusal_heavy_copy_stored_fields(tmp_path: Path) -> None:
    left = _stored(tmp_path / "left")
    right_dir = tmp_path / "right"
    right_dir.mkdir()
    right = _stored(right_dir)
    same = _ok(compare_runs(left, right))
    assert same.same_world is True
    assert same.same_account_binding_role is True
    assert same.differing == ()
    assert same.publish_only is True
    mutated = dict(right)
    mutated["account_binding_role"] = AccountRole.LIVE.value
    label = dict(cast("dict[str, object]", right["result_label"]))
    label["world"] = World.LIVE.value
    mutated["result_label"] = label
    diff = _ok(compare_runs(left, mutated))
    assert diff.same_world is False
    assert diff.same_account_binding_role is False
    paths = {row.path for row in diff.differing}
    assert "result_label.world" in paths
    assert "account_binding_role" in paths
    quiet = _ok(flag_refusal_heavy(left))
    assert quiet.refusal_bearing is False
    assert quiet.suppression_rows == ()
    assert quiet.veto_rows == ()
    heavy = dict(left)
    vetoes = list(cast("list[object]", left["veto_accounting"]))
    first = dict(cast("dict[str, object]", vetoes[0]))
    first["count"] = 1
    vetoes[0] = first
    heavy["veto_accounting"] = vetoes
    flagged = _ok(flag_refusal_heavy(heavy))
    assert flagged.refusal_bearing is True
    assert flagged.veto_rows[0] == first
    assert flagged.source == "ct-32"


def test_stored_reproduction_matches_or_typed_refusal(tmp_path: Path) -> None:
    config = _config()
    outcome = _run(config=config)
    _ok(assemble_run_performance_result(outcome, output_dir=tmp_path))
    stored_fp = _ok(stored_ct32_fingerprint(tmp_path))
    reproduced = _ok(
        verify_stored_reproduction(
            run_id=config.fingerprint,
            config=config,
            output_dir=tmp_path,
            slices=_slices(),
            handler=SilentSliceHandler(),
        )
    )
    assert isinstance(reproduced, PerformanceResult)
    assert _ok(reproduced.fingerprint()) == stored_fp
    path = tmp_path / RESULTS_DIR_NAME / CT32_ARTIFACT_NAME
    tampered = json.loads(path.read_text(encoding="utf-8"))
    tampered["account_binding_role"] = AccountRole.LIVE.value
    path.write_text(json.dumps(tampered), encoding="utf-8")
    mismatch = verify_stored_reproduction(
        run_id=config.fingerprint,
        config=config,
        output_dir=tmp_path,
        slices=_slices(),
        handler=SilentSliceHandler(),
    )
    assert is_refusal(mismatch)
    assert mismatch.category is RefusalCategory.POLICY_REJECTION
    assert mismatch.context["field"] == "ct32_fingerprint"


def test_concurrent_renders_use_isolated_dirs_and_no_shared_state(tmp_path: Path) -> None:
    assert SHARED_MUTABLE_RENDER_STATE is False
    assert CONCURRENCY_IS_SCHEDULING_ONLY is True
    for name, value in vars(render_mod).items():
        if name.startswith("__"):
            continue
        assert not isinstance(value, (dict, list, set)), name

    def _one(index: int) -> str:
        root = tmp_path / f"run-{index}"
        root.mkdir()
        stamp_config = _config()
        payload = dict(stamp_config.keys)
        payload["marker"] = f"run-{index}"
        bound = ResolvedRunConfig(
            format_version=stamp_config.format_version,
            book_fp1=stamp_config.book_fp1,
            bms_fp1=stamp_config.bms_fp1,
            bot_fp1=stamp_config.bot_fp1,
            book_fragment_fp1=stamp_config.book_fragment_fp1,
            bms_fragment_fp1=stamp_config.bms_fragment_fp1,
            keys=payload,
            clock=stamp_config.clock,
            data_provenance=stamp_config.data_provenance,
            world=stamp_config.world,
            fingerprint=_ok(fingerprint({"n": "downstream-iso", "i": index})),
            binding_fp1=stamp_config.binding_fp1,
        )
        outcome = _ok(run(slices=_slices(), config=bound, handler=SilentSliceHandler()))
        _ok(assemble_run_performance_result(outcome, output_dir=root))
        paths = _ok(write_run_renders(root))
        html_text = paths.html.read_text(encoding="utf-8")
        md_text = paths.markdown.read_text(encoding="utf-8")
        assert paths.html.parent == root / RESULTS_DIR_NAME
        assert paths.html.name == HTML_REPORT_NAME
        assert paths.markdown.name == MARKDOWN_REPORT_NAME
        assert (root / RESULTS_DIR_NAME / CT32_ARTIFACT_NAME).is_file()
        assert bound.fingerprint.value in html_text
        assert bound.fingerprint.value in md_text
        assert f"world={World.REPLAY.value}" in html_text
        return bound.fingerprint.value

    with ThreadPoolExecutor(max_workers=_CONCURRENT_RUNS) as pool:
        marks = list(pool.map(_one, range(_CONCURRENT_RUNS)))
    assert len(set(marks)) == _CONCURRENT_RUNS
    for index, mark in enumerate(marks):
        html_text = (tmp_path / f"run-{index}" / RESULTS_DIR_NAME / HTML_REPORT_NAME).read_text(
            encoding="utf-8"
        )
        assert mark in html_text
        for other in marks:
            if other != mark:
                assert other not in html_text
        explained = _ok(explain_run(tmp_path / f"run-{index}"))
        assert explained.parsed_html is False
        assert explained.publish_only is True


def test_downstream_reads_are_publish_only() -> None:
    assert DOWNSTREAM_PUBLISH_ONLY is True
    identity = downstream_read_identity()
    assert identity["publish_only"] is True
    assert identity["agents_parse_html"] is False
    assert identity["render_adds_computation"] is False
    assert identity["shared_mutable_render_state"] is False
    assert identity["interpretation_source"] == "ct-32"
    for act in (*DOWNSTREAM_FORBIDDEN_ACTS, *PublishAct):
        refused = refuse_downstream_act(act)
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
        assert refused.context["field"] == "act"
    assert is_refusal(refuse_downstream_act("bind"))
    unknown = refuse_downstream_act("explode")
    assert is_refusal(unknown)
    assert unknown.category is RefusalCategory.INVALID_INPUT


def test_missing_headline_or_rendering_input_is_typed_refusal() -> None:
    assert is_refusal(render_html("<html>world=replay</html>"))
    assert is_refusal(load_stored_ct32("not-a-path-that-exists"))
    missing = render_html(
        {
            "class": "performance-result",
            "account_binding_role": "demo",
            "result_label": {"class": "result-label"},
            "population": {},
            "period": {},
            "measure_set": [],
            "suppression_accounting": [],
            "veto_accounting": [],
        }
    )
    assert is_refusal(missing)
    assert missing.context["field"] == "world"


def test_door_exports_the_downstream_read_surface() -> None:
    assert api.render_html is qmb.render_html
    assert api.render_markdown is qmb.render_markdown
    assert api.render_report is qmb.render_report
    assert api.write_run_renders is qmb.write_run_renders
    assert api.explain_run is qmb.explain_run
    assert api.compare_runs is qmb.compare_runs
    assert api.flag_refusal_heavy is qmb.flag_refusal_heavy
    assert api.verify_stored_reproduction is qmb.verify_stored_reproduction
    assert api.load_stored_ct32 is qmb.load_stored_ct32
    assert api.refuse_downstream_act is qmb.refuse_downstream_act
    assert api.downstream_read_identity is qmb.downstream_read_identity
    assert api.AGENTS_PARSE_HTML is False
    assert api.SHARED_MUTABLE_RENDER_STATE is False
    assert api.INTERPRETATION_SOURCE == "ct-32"
