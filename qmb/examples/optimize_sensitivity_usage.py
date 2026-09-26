"""Reference usage — anti-overfit parameter-sensitivity report (Story 21.6).

Executable::

    python qmb/examples/optimize_sensitivity_usage.py

Shows the things B-8 / OPT-22 / Story 21.6 pin down:

1. A completed Study emits a parameter-sensitivity report as a pure read-time fold
   over its role=trial ledger lines: an objective distribution summary (mean, std,
   min, max, median) over every completed trial, plus per-parameter objective slices.
2. The slices are chart series as data — every point cites the exact parameter value
   and the exact objective magnitude, and no image is ever the canonical payload.
3. The favourable-side trials cluster into good regions, each described as data. A
   winner sitting alone in an unstable neighbourhood is flagged isolated-spike,
   distinct from a winner inside a stable cluster.
4. The report describes structure and neighbourhood stability only: it emits no
   SR*/search-quality pass/fail verdict and invents no threshold — the favourable
   divider is the data's own median, and the threshold sitting stays deferred.
5. P&L inputs stay exact-integer; a float exists only inside the std statistic under
   a fixed rounding contract, and the stored value is a label-derived scaled rational.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar, cast

from qmb.doors import api
from qmf.core.exact import Money
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

T = TypeVar("T")

_BAR = fingerprint({"class": "book-bar", "id": "bar-1"})


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _fp(*parts: object) -> Fingerprint:
    return _unwrap(fingerprint({"parts": list(parts)}), "fp")


def _net_profit(minor: int) -> dict[str, object]:
    money = Money(value=minor, currency="USD", scale=2)
    return _unwrap(api.emit_measure("net_profit", money), "np").fp1_identity()


def _trial(run: str, minor: int) -> api.LedgerLine:
    return api.LedgerLine(
        run_id=_fp("run", run),
        role="trial",
        world=World.REPLAY,
        result_label={"class": "result-label", "run": run},
        book_bar_fp1=_unwrap(_BAR, "bar"),
        measures=(_net_profit(minor),),
        ct32_fingerprint=_fp("ct32", run),
    )


def main() -> None:
    # A dense good region around (fast in 10..12, slow in 20..22) plus a handful of
    # poor trials, and one lucky isolated spike far away with the highest objective.
    lines: list[api.LedgerLine] = []
    parameters: dict[str, dict[str, object]] = {}
    dense = (
        ("d0", 130, 10, 20),
        ("d1", 132, 11, 20),
        ("d2", 134, 10, 21),
        ("d3", 136, 11, 21),
        ("d4", 138, 12, 22),
    )
    poor = (("p0", 10, 50, 90), ("p1", 12, 51, 91), ("p2", 14, 52, 92))
    for run, minor, fast, slow in (*dense, *poor):
        lines.append(_trial(run, minor))
        parameters[_fp("run", run).value] = {"fast": fast, "slow": slow}
    lines.append(_trial("spike", 200))
    parameters[_fp("run", "spike").value] = {"fast": 500, "slow": 900}

    report = _unwrap(
        api.build_sensitivity_report(
            lines,
            parameters=parameters,
            objective="net_profit",
            world=World.REPLAY,
            direction="max",
        ),
        "sensitivity report",
    )

    distribution = report.distribution
    assert distribution is not None
    print(
        "objective distribution summary over all completed role=trial lines: "
        f"count={distribution.count} mean={distribution.mean} min={distribution.minimum} "
        f"max={distribution.maximum} median={distribution.median}"
    )

    slice_names = [item.parameter for item in report.parameter_slices]
    print(
        "per-parameter objective slices as chart series (data, never an image): "
        f"{slice_names} canonical_payload={report.canonical_payload} "
        f"emits_image_payload={report.emits_image_payload}"
    )

    print(
        "good regions cluster the favourable-side trials, each described as data: "
        f"cluster_count={report.cluster_count}"
    )

    stability = report.winner_stability
    print(
        "the objective-best winner is flagged isolated-spike when its good-region "
        f"cluster is a singleton: stability={stability.stability} "
        f"cluster_size={stability.cluster_size} good_neighbours={stability.good_neighbour_count}"
    )

    # The same trials with the best objective moved inside the dense cluster: a
    # stable-cluster winner, distinct from the isolated spike above.
    stable_lines: list[api.LedgerLine] = []
    stable_params: dict[str, dict[str, object]] = {}
    stable_dense = (
        ("d0", 130, 10, 20),
        ("d1", 500, 11, 20),
        ("d2", 134, 10, 21),
        ("d3", 136, 11, 21),
        ("d4", 138, 12, 22),
    )
    for run, minor, fast, slow in (*stable_dense, *poor):
        stable_lines.append(_trial(run, minor))
        stable_params[_fp("run", run).value] = {"fast": fast, "slow": slow}
    stable = _unwrap(
        api.build_sensitivity_report(
            stable_lines,
            parameters=stable_params,
            objective="net_profit",
            world=World.REPLAY,
            direction="max",
        ),
        "stable report",
    )
    print(
        "a winner inside a stable cluster is flagged distinctly: "
        f"stability={stable.winner_stability.stability} "
        f"cluster_size={stable.winner_stability.cluster_size}"
    )

    print(
        "the report describes structure and neighbourhood stability only: "
        f"makes_search_quality_verdict={report.makes_search_quality_verdict} "
        f"invents_threshold={report.invents_threshold} "
        f"deferred_to={report.verdict_deferred_to}"
    )
    verdict = api.refuse_search_quality_verdict("SR*")
    assert is_refusal(verdict) and verdict.category is RefusalCategory.POLICY_REJECTION
    print("an SR*/search-quality pass/fail verdict is refused: the threshold sitting is deferred")

    std_slot = distribution.fp1_identity()["std"]
    assert isinstance(std_slot, dict)
    print(
        "P&L inputs stay exact-integer; the std statistic re-enters through the named "
        f"rounding boundary as a scaled rational: std={std_slot['num']}/{std_slot['den']} "
        f"rounding={std_slot['rounding']} scale={std_slot['scale']}"
    )
    assert not _has_float(report.fp1_identity())
    print("no raw binary float ever appears in the report identity")

    first = _unwrap(report.fingerprint(), "fingerprint")
    second = _unwrap(
        _unwrap(
            api.build_sensitivity_report(
                lines,
                parameters=parameters,
                objective="net_profit",
                world=World.REPLAY,
                direction="max",
            ),
            "reproduced report",
        ).fingerprint(),
        "fingerprint",
    )
    assert first.value == second.value
    print("recomputing the report over the same trials reproduces its fingerprint (NFR-03)")

    print("parameter-sensitivity report ok")


def _has_float(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, float):
        return True
    if isinstance(value, dict):
        return any(_has_float(item) for item in cast("dict[object, object]", value).values())
    if isinstance(value, (list, tuple)):
        return any(_has_float(item) for item in cast("Sequence[object]", value))
    return False


if __name__ == "__main__":
    main()
