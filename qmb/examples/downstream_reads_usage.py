"""Reference usage — pure downstream reads of a stored CT-32 (Story 19.5).

Executable::

    python qmb/examples/downstream_reads_usage.py

Shows the things R-RPT-21/22/24 / R-RPT-2/9 / B-10 pin down:

1. HTML and markdown are token substitution of the stored CT-32 artifact.
2. The headline shows world and account-binding role verbatim and unmissably.
3. Interpretation skills read CT-32 and refuse HTML.
4. Re-executing a stored run id reproduces the stored fingerprint, or refuses.
5. Concurrent writes use isolated output directories; no shared render state.
6. Rendering, interpretation, and reproduction are publish-only.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TypeVar

from qmb.config import ResolvedRunConfig
from qmb.results import (
    AGENTS_PARSE_HTML,
    DOWNSTREAM_PUBLISH_ONLY,
    RENDER_ADDS_COMPUTATION,
    SHARED_MUTABLE_RENDER_STATE,
    assemble_run_performance_result,
    compare_runs,
    explain_run,
    flag_refusal_heavy,
    refuse_downstream_act,
    render_html,
    render_markdown,
    render_report,
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
from qmf.core.refusal import Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int = _NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _obs(stream_id: str, ns: int = _NS) -> SliceObservation:
    return _unwrap(SliceObservation.try_create(stream_id, _instant(ns), True), "observation")


def _config() -> ResolvedRunConfig:
    stamp = _unwrap(fingerprint({"n": "downstream-reads-example"}), "stamp")
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={STREAM_SET_KEY: ("eurusd",), "account_role": AccountRole.DEMO},
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
        binding_fp1=stamp,
    )


def main() -> None:
    assert qmb.render_html is render_html
    assert qmb.explain_run is explain_run
    assert qmb.verify_stored_reproduction is verify_stored_reproduction
    assert RENDER_ADDS_COMPUTATION is False
    assert AGENTS_PARSE_HTML is False
    assert SHARED_MUTABLE_RENDER_STATE is False
    assert DOWNSTREAM_PUBLISH_ONLY is True
    config = _config()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        outcome = _unwrap(
            run(
                slices=((_obs("eurusd"),),),
                config=config,
                handler=SilentSliceHandler(),
            ),
            "run",
        )
        _unwrap(assemble_run_performance_result(outcome, output_dir=root), "assemble")
        report = _unwrap(render_report(root), "render")
        assert "world=replay" in report.html
        assert "account-binding-role=demo" in report.html
        assert report.html.index("qmb-headline-unmissable") < report.html.index("<main>")
        markdown = _unwrap(render_markdown(root), "markdown")
        assert markdown.startswith("# world=replay · account-binding-role=demo")
        explained = _unwrap(explain_run(root), "explain")
        assert explained.source == "ct-32"
        assert explained.parsed_html is False
        html_refused = explain_run(report.html)
        assert is_refusal(html_refused)
        compared = _unwrap(compare_runs(root, root), "compare")
        assert compared.same_world is True
        quiet = _unwrap(flag_refusal_heavy(root), "flag")
        assert quiet.refusal_bearing is False
        reproduced = _unwrap(
            verify_stored_reproduction(
                run_id=config.fingerprint,
                config=config,
                output_dir=root,
                slices=((_obs("eurusd"),),),
                handler=SilentSliceHandler(),
            ),
            "verify",
        )
        assert reproduced.account_binding_role is AccountRole.DEMO
        sibling = root / "sibling"
        sibling.mkdir()
        _unwrap(assemble_run_performance_result(outcome, output_dir=sibling), "sibling-assemble")
        first = _unwrap(write_run_renders(root), "write-a")
        second = _unwrap(write_run_renders(sibling), "write-b")
        assert first.html.parent != second.html.parent
        for act in ("size", "promote", "bench", "bind", "change_mode"):
            refused = refuse_downstream_act(act)
            assert is_refusal(refused)
        print("HTML/markdown are token substitution of the stored CT-32; no new number")
        print("headline shows world and account-binding role verbatim and unmissably")
        print("interpretation skills read CT-32 and never parse HTML")
        print("re-execute stored run id reproduces the CT-32 fingerprint or typed refusal")
        print("concurrent runs write isolated output directories; no shared render state")
        print("rendering, interpretation, and reproduction are publish-only")
        print("pure downstream reads ok")


if __name__ == "__main__":
    main()
