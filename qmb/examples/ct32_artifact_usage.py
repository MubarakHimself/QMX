"""Reference usage — canonical CT-32 result artifact (Story 19.1).

Executable::

    python qmb/examples/ct32_artifact_usage.py

Shows the things B-10 / B-13 / AR-59 pin down:

1. A completed pure ``run()`` return assembles into exactly one CT-32 file.
2. The container carries the full AD-12 label plus the AR-59 stamps.
3. ``fp1`` is label-derived via qmf-core only — no float bytes, no second report JSON.
4. A multi-role span is a policy rejection and writes nothing.
5. ``world`` is copied from data-derived provenance; V1 fills stay optimistic-tainted.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TypeVar

from qmb.config import ResolvedRunConfig
from qmb.execution import COMPOSITION_VERSION, TAINT_OPTIMISTIC, stamp_fidelity
from qmb.results import (
    CT32_ARTIFACT_RELATIVE_PATH,
    DATA_FINGERPRINT_KEY,
    FIDELITY_KEY,
    REGISTRY_AS_OF_KEY,
    RESULT_CONTRACT,
    RESULTS_DIR_NAME,
    RNG_PROVENANCE_KEY,
    SPLIT_FINGERPRINT_KEY,
    assemble_run_performance_result,
    result_identity,
)
from qmb.runloop import STREAM_SET_KEY, SilentSliceHandler, SliceObservation, run
from qmf.core.chrono import Instant
from qmf.core.fingerprint import World, canonical_bytes, fingerprint
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


def _config(**keys: object) -> ResolvedRunConfig:
    stamp = _unwrap(fingerprint({"n": "ct32-artifact-example", "keys": sorted(keys)}), "stamp")
    payload: dict[str, object] = {STREAM_SET_KEY: ("eurusd", "gbpusd")}
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


def assemble_one_canonical_artifact(output_dir: Path) -> str:
    """Write exactly one CT-32 container and return its ``fp1``."""
    registry_as_of = _instant(_NS + 3)
    data_fp = _unwrap(fingerprint({"class": "data-window", "n": "example"}), "data")
    split_fp = _unwrap(fingerprint({"class": "split-manifest", "n": "example"}), "split")
    fidelity = _unwrap(
        stamp_fidelity("fill.declared-path", composition_version=COMPOSITION_VERSION),
        "fidelity",
    )
    config = _config(
        registry_as_of=registry_as_of,
        data_fingerprint=data_fp,
        split_fingerprint=split_fp,
        fidelity=fidelity,
        rng_provenance={
            "family": "qmx-pcg64",
            "algorithm_version": "v1",
            "base_seed": 1,
        },
    )
    outcome = _unwrap(
        run(
            slices=((_obs("eurusd"), _obs("gbpusd")),),
            config=config,
            handler=SilentSliceHandler(),
        ),
        "run",
    )
    artifact = outcome.performance_result
    assert artifact is not None
    label = artifact.result_label
    assert label.world is World.REPLAY
    assert label.world is config.world
    assert artifact.account_binding_role is AccountRole.DEMO
    assert config.fingerprint in label.input_fingerprints
    assert data_fp in label.input_fingerprints
    assert split_fp in label.input_fingerprints
    assert fidelity.taint == TAINT_OPTIMISTIC
    assert result_identity()["claims_edge"] is False
    stamped = _unwrap(
        assemble_run_performance_result(outcome, output_dir=output_dir),
        "assemble",
    )
    path = output_dir / CT32_ARTIFACT_RELATIVE_PATH
    assert path.is_file()
    assert list((output_dir / RESULTS_DIR_NAME).iterdir()) == [path]
    assert not (output_dir / "report.json").exists()
    raw = path.read_bytes()
    assert raw == _unwrap(canonical_bytes(artifact.fp1_identity()), "canonical")
    assert stamped == _unwrap(fingerprint(artifact.fp1_identity()), "fp1")
    return stamped.value


def multi_role_writes_nothing(output_dir: Path) -> None:
    """A result spanning account roles is a policy rejection; no artifact."""
    config = _config(account_role=(AccountRole.DEMO, AccountRole.LIVE))
    refused = run(
        slices=((_obs("eurusd"), _obs("gbpusd")),),
        config=config,
        handler=SilentSliceHandler(),
    )
    assert is_refusal(refused)
    assembled = assemble_run_performance_result(refused, output_dir=output_dir)
    assert is_refusal(assembled)
    assert not (output_dir / RESULTS_DIR_NAME).exists()
    assert not (output_dir / "report.json").exists()


def main() -> None:
    assert qmb.RESULT_CONTRACT == RESULT_CONTRACT
    assert qmb.assemble_run_performance_result is assemble_run_performance_result
    assert REGISTRY_AS_OF_KEY == "registry_as_of"
    assert DATA_FINGERPRINT_KEY == "data_fingerprint"
    assert SPLIT_FINGERPRINT_KEY == "split_fingerprint"
    assert FIDELITY_KEY == "fidelity"
    assert RNG_PROVENANCE_KEY == "rng_provenance"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        written = assemble_one_canonical_artifact(root)
        assert written.startswith("fp1:sha256:")
        print("exactly one CT-32 container written; fp1 label-derived via qmf-core")
        print("AD-12 label plus registry_as_of, data/split, fidelity, RNG stamps")
        print("world=replay from data-derived provenance; optimistic taint; no edge claim")
        empty = root / "empty"
        empty.mkdir()
        multi_role_writes_nothing(empty)
        print("multi-role span is policy rejection; writes nothing")
        print("no second report JSON")
        print("canonical CT-32 artifact ok")


if __name__ == "__main__":
    main()
