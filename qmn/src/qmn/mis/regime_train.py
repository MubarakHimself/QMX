"""Story 30.4 — operator-run offline training script for ``regime_classifier_v1``.

One bounded, reproducible offline script the operator launches on their own
machine. Records command/config, code fp1, dependency lock, machine/OS/CPU/
memory, RNG algorithm and seed, exact data/split windows, start/end time,
resource use, trial/hyperparameter records, and deterministic output locations.
Checkpoints support resume; partial outputs cannot register as a model; one
terminal training record reports completed/aborted/refused with cause. No
broker/node credential, trading-VPS, cloud, or live-network path
(FR-079; NFR-03; DEC-0262; GAP-0051). Evaluation and registry publication are
Stories 30.5 / 30.6 — this module never mutates the sealed holdout for
acceptance and never grants money-path authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Final, cast

from qmb.orchestrator.paths import (
    MAX_JSONL_BYTES,
    append_bytes_no_follow,
    read_contained_bytes,
    read_contained_text,
    write_bytes_exclusive_no_follow,
)
from qmf.core import Fingerprint, Ok, Result, TypedRefusal, fingerprint, is_refusal
from qmf.data import SegmentRole

from qmn.mis._refuse import clean_token, invalid, policy, unavailable
from qmn.mis.regime_corpus import BAR_INTERVAL_M5_NS, CleanedCorpus, CleanedCorpusRow
from qmn.mis.regime_design import (
    CHOSEN_MODEL_FAMILY,
    DECLARED_TRADING_SESSIONS,
    REGIME_CLASS_VOCABULARY,
    ExecutableRegimeContract,
    HyperparameterBounds,
    RegimeClassifierDesign,
    accepted_regime_classifier_design,
    assert_design_unchanged,
    executable_regime_contract,
)
from qmn.mis.regime_labels import EXCLUSION_CLASS, LabeledCorpus, LabeledRow

__all__ = [
    "DEFAULT_TRAINING_SEED",
    "REGIME_TRAIN_ARTIFACT_ID",
    "REGIME_TRAIN_FORMAT_VERSION",
    "REGIME_TRAIN_SURFACE",
    "RNG_ALGORITHM",
    "TRAINING_BACKEND_DETERMINISTIC",
    "TRAINING_BACKEND_LIGHTGBM",
    "TRAINING_LOCATION",
    "DependencyLockRecord",
    "MachineEnvironment",
    "PreparedTrainingMatrix",
    "TrainingArtifact",
    "TrainingCheckpoint",
    "TrainingConfig",
    "TrainingRecord",
    "TrainingTerminalStatus",
    "TrialHyperparameters",
    "TrialRecord",
    "assert_registerable_training_artifact",
    "build_labeled_feature_rows",
    "build_training_config",
    "build_training_matrix",
    "capture_machine_environment",
    "main",
    "refuse_broker_or_node_credential",
    "refuse_live_network_training",
    "refuse_partial_model_registration",
    "refuse_reproducibility_mismatch",
    "refuse_vps_or_cloud_training",
    "resolve_dependency_lock",
    "resume_offline_training",
    "run_offline_training",
]

REGIME_TRAIN_SURFACE: Final[str] = "qmn.mis.regime_train"
REGIME_TRAIN_ARTIFACT_ID: Final[str] = "regime_classifier_v1_training_run"
REGIME_TRAIN_FORMAT_VERSION: Final[int] = 1
TRAINING_LOCATION: Final[str] = "operator-machine-offline-script"
RNG_ALGORITHM: Final[str] = "python-random-Random"
DEFAULT_TRAINING_SEED: Final[int] = 30_04_2026
TRAINING_BACKEND_DETERMINISTIC: Final[str] = "deterministic-surrogate"
TRAINING_BACKEND_LIGHTGBM: Final[str] = "lightgbm"
_SPLIT_ROLE_HOLDOUT: Final[str] = SegmentRole.SEALED_TEST.value
_MODEL_FILENAME: Final[str] = "model.txt"
_RECORD_FILENAME: Final[str] = "training_record.json"
_CHECKPOINT_FILENAME: Final[str] = "checkpoint.json"
_CONFIG_FILENAME: Final[str] = "training_config.json"
_TRIALS_FILENAME: Final[str] = "trials.jsonl"

_TrainRow = tuple[str, tuple[float, ...], str]
FitFn = Callable[
    [Sequence[_TrainRow], Mapping[str, object], int],
    tuple[str, int, int],
]


class TrainingTerminalStatus(StrEnum):
    """Closed vocabulary for the one terminal training record."""

    COMPLETED = "completed"
    ABORTED = "aborted"
    REFUSED = "refused"


@dataclass(frozen=True, slots=True)
class MachineEnvironment:
    """Host facts recorded for an offline operator-machine run."""

    os_name: str
    os_release: str
    os_version: str
    machine: str
    processor: str
    python_version: str
    cpu_count: int | None
    memory_total_bytes: int | None
    hostname_redacted: str

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-training-machine-environment",
            "os_name": self.os_name,
            "os_release": self.os_release,
            "os_version": self.os_version,
            "machine": self.machine,
            "processor": self.processor,
            "python_version": self.python_version,
            "cpu_count": self.cpu_count,
            "memory_total_bytes": self.memory_total_bytes,
            "hostname_redacted": self.hostname_redacted,
        }


@dataclass(frozen=True, slots=True)
class DependencyLockRecord:
    """Dependency lock identity cited by the training record."""

    lock_path: str
    lock_fp: str
    present: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-training-dependency-lock",
            "lock_path": self.lock_path,
            "lock_fp": self.lock_fp,
            "present": self.present,
        }


@dataclass(frozen=True, slots=True)
class TrialHyperparameters:
    """One trial drawn inside the Story 30.1 hyperparameter bounds."""

    trial_index: int
    num_leaves: int
    learning_rate_num: int
    learning_rate_den: int
    min_data_in_leaf: int
    feature_fraction_num: int
    feature_fraction_den: int
    early_stopping_rounds: int

    def as_mapping(self) -> dict[str, object]:
        return {
            "trial_index": self.trial_index,
            "num_leaves": self.num_leaves,
            "learning_rate": [self.learning_rate_num, self.learning_rate_den],
            "min_data_in_leaf": self.min_data_in_leaf,
            "feature_fraction": [
                self.feature_fraction_num,
                self.feature_fraction_den,
            ],
            "early_stopping_rounds": self.early_stopping_rounds,
        }

    def fp1_identity(self) -> dict[str, object]:
        body: dict[str, object] = {"class": "regime-training-trial-hyperparameters"}
        body.update(self.as_mapping())
        return body


@dataclass(frozen=True, slots=True)
class TrialRecord:
    """One completed or aborted trial inside the offline search."""

    trial_index: int
    hyperparameters: TrialHyperparameters
    validation_score_ppb: int
    status: str
    model_bytes_fp: str | None
    elapsed_ms: int

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-training-trial-record",
            "trial_index": self.trial_index,
            "hyperparameters": self.hyperparameters.fp1_identity(),
            "validation_score_ppb": self.validation_score_ppb,
            "status": self.status,
            "model_bytes_fp": self.model_bytes_fp,
            "elapsed_ms": self.elapsed_ms,
        }


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    """Fingerprinted offline training command/config (no credentials)."""

    design_fp: Fingerprint
    contract_fp: Fingerprint
    labeled_fp: Fingerprint
    cleaned_fp: Fingerprint
    splits_fp: Fingerprint
    data_window_start_ns: int
    data_window_end_ns: int
    train_end_ns: int
    validation_end_ns: int
    holdout_end_ns: int
    sessions: tuple[str, ...]
    rng_algorithm: str
    seed: int
    backend: str
    max_trials: int
    output_dir: str
    command: tuple[str, ...]
    allow_live_network: bool
    allow_vps_or_cloud: bool
    allow_broker_or_node_credential: bool
    grants_money_path_authority: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-training-config",
            "design_fp": self.design_fp.value,
            "contract_fp": self.contract_fp.value,
            "labeled_fp": self.labeled_fp.value,
            "cleaned_fp": self.cleaned_fp.value,
            "splits_fp": self.splits_fp.value,
            "data_window_start_ns": self.data_window_start_ns,
            "data_window_end_ns": self.data_window_end_ns,
            "train_end_ns": self.train_end_ns,
            "validation_end_ns": self.validation_end_ns,
            "holdout_end_ns": self.holdout_end_ns,
            "sessions": list(self.sessions),
            "rng_algorithm": self.rng_algorithm,
            "seed": self.seed,
            "backend": self.backend,
            "max_trials": self.max_trials,
            "output_dir": self.output_dir,
            "command": list(self.command),
            "allow_live_network": self.allow_live_network,
            "allow_vps_or_cloud": self.allow_vps_or_cloud,
            "allow_broker_or_node_credential": self.allow_broker_or_node_credential,
            "grants_money_path_authority": self.grants_money_path_authority,
            "training_location": TRAINING_LOCATION,
            "format_version": REGIME_TRAIN_FORMAT_VERSION,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())


@dataclass(frozen=True, slots=True)
class PreparedTrainingMatrix:
    """Causal feature/label matrix for train and validation only (holdout sealed)."""

    feature_ids: tuple[str, ...]
    class_vocabulary: tuple[str, ...]
    train_rows: tuple[tuple[str, tuple[float, ...], str], ...]
    validation_rows: tuple[tuple[str, tuple[float, ...], str], ...]
    excluded_count: int
    sealed_holdout_count: int
    sealed_holdout_unused: bool
    peer_features_supplied: bool

    def fp1_identity(self) -> dict[str, object]:
        # Float feature payloads are content-digested — fp1 forbids bare floats.
        return {
            "class": "regime-prepared-training-matrix",
            "feature_ids": list(self.feature_ids),
            "class_vocabulary": list(self.class_vocabulary),
            "train_row_count": len(self.train_rows),
            "validation_row_count": len(self.validation_rows),
            "train_row_ids": [row[0] for row in self.train_rows],
            "validation_row_ids": [row[0] for row in self.validation_rows],
            "train_labels": [row[2] for row in self.train_rows],
            "validation_labels": [row[2] for row in self.validation_rows],
            "feature_payload_fp": _matrix_payload_fp(self.train_rows, self.validation_rows),
            "excluded_count": self.excluded_count,
            "sealed_holdout_count": self.sealed_holdout_count,
            "sealed_holdout_unused": self.sealed_holdout_unused,
            "peer_features_supplied": self.peer_features_supplied,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())


@dataclass(frozen=True, slots=True)
class TrainingCheckpoint:
    """Resumable search state. Never registerable as a model on its own."""

    config_fp: Fingerprint
    code_fp: Fingerprint
    matrix_fp: Fingerprint
    completed_trials: tuple[TrialRecord, ...]
    next_trial_index: int
    best_trial_index: int | None
    best_validation_score_ppb: int | None
    registerable: bool
    output_dir: str

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-training-checkpoint",
            "config_fp": self.config_fp.value,
            "code_fp": self.code_fp.value,
            "matrix_fp": self.matrix_fp.value,
            "completed_trials": [row.fp1_identity() for row in self.completed_trials],
            "next_trial_index": self.next_trial_index,
            "best_trial_index": self.best_trial_index,
            "best_validation_score_ppb": self.best_validation_score_ppb,
            "registerable": self.registerable,
            "output_dir": self.output_dir,
            "format_version": REGIME_TRAIN_FORMAT_VERSION,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())


@dataclass(frozen=True, slots=True)
class TrainingRecord:
    """One terminal training record: completed, aborted, or refused."""

    artifact_id: str
    status: TrainingTerminalStatus
    cause: str
    config_fp: Fingerprint
    code_fp: Fingerprint
    dependency_lock: DependencyLockRecord
    machine: MachineEnvironment
    rng_algorithm: str
    seed: int
    data_window_start_ns: int
    data_window_end_ns: int
    train_end_ns: int
    validation_end_ns: int
    holdout_end_ns: int
    start_time_utc: str
    end_time_utc: str
    elapsed_ms: int
    peak_rss_bytes: int | None
    trials: tuple[TrialRecord, ...]
    best_trial_index: int | None
    output_locations: Mapping[str, str]
    model_path: str | None
    model_fp: str | None
    registerable: bool
    grants_money_path_authority: bool
    grants_governed_binding: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-training-record",
            "artifact_id": self.artifact_id,
            "status": self.status.value,
            "cause": self.cause,
            "config_fp": self.config_fp.value,
            "code_fp": self.code_fp.value,
            "dependency_lock": self.dependency_lock.fp1_identity(),
            "machine": self.machine.fp1_identity(),
            "rng_algorithm": self.rng_algorithm,
            "seed": self.seed,
            "data_window_start_ns": self.data_window_start_ns,
            "data_window_end_ns": self.data_window_end_ns,
            "train_end_ns": self.train_end_ns,
            "validation_end_ns": self.validation_end_ns,
            "holdout_end_ns": self.holdout_end_ns,
            "start_time_utc": self.start_time_utc,
            "end_time_utc": self.end_time_utc,
            "elapsed_ms": self.elapsed_ms,
            "peak_rss_bytes": self.peak_rss_bytes,
            "trials": [row.fp1_identity() for row in self.trials],
            "best_trial_index": self.best_trial_index,
            "output_locations": dict(sorted(self.output_locations.items())),
            "model_path": self.model_path,
            "model_fp": self.model_fp,
            "registerable": self.registerable,
            "grants_money_path_authority": self.grants_money_path_authority,
            "grants_governed_binding": self.grants_governed_binding,
            "training_location": TRAINING_LOCATION,
            "format_version": REGIME_TRAIN_FORMAT_VERSION,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())

    def as_jsonable(self) -> dict[str, object]:
        return self.fp1_identity()


@dataclass(frozen=True, slots=True)
class TrainingArtifact:
    """Completed offline training candidate. Registration is Story 30.6."""

    artifact_id: str
    record: TrainingRecord
    model_text: str
    model_fp: Fingerprint
    config_fp: Fingerprint
    code_fp: Fingerprint
    matrix_fp: Fingerprint
    design_fp: Fingerprint
    registerable: bool
    grants_money_path_authority: bool
    grants_governed_binding: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-training-artifact",
            "artifact_id": self.artifact_id,
            "record": self.record.fp1_identity(),
            "model_fp": self.model_fp.value,
            "config_fp": self.config_fp.value,
            "code_fp": self.code_fp.value,
            "matrix_fp": self.matrix_fp.value,
            "design_fp": self.design_fp.value,
            "registerable": self.registerable,
            "grants_money_path_authority": self.grants_money_path_authority,
            "grants_governed_binding": self.grants_governed_binding,
            "format_version": REGIME_TRAIN_FORMAT_VERSION,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())


@dataclass(frozen=True, slots=True)
class _TrainingSession:
    """Clock, config, and output root for one offline training invocation."""

    config: TrainingConfig
    config_fp: Fingerprint
    code_fp: Fingerprint
    lock: DependencyLockRecord
    machine: MachineEnvironment
    start_utc: str
    start_mono_ns: int
    clock_ns: Callable[[], int]
    out_root: Path


@dataclass(frozen=True, slots=True)
class _SearchSnapshot:
    """Mutable search fields captured between resume, trials, and finish."""

    completed: tuple[TrialRecord, ...]
    best_index: int | None
    best_score: int | None
    best_model_text: str | None
    start_trial: int


@dataclass(frozen=True, slots=True)
class _TrialFitOutcome:
    """One trial fit: completed model text, or an abort cause with no model."""

    trial: TrialRecord
    model_text: str | None
    abort_cause: str | None


def refuse_vps_or_cloud_training(*, location: object) -> TypedRefusal:
    """Training runs only on the operator machine offline script (DEC-0262)."""
    return policy(
        "location",
        "regime_classifier_v1 training is an operator-machine offline script; "
        "no trading-VPS or cloud training path",
        failure_id="mis.regime_train.vps_or_cloud",
        given=repr(location),
    )


def refuse_broker_or_node_credential(*, claim: object) -> TypedRefusal:
    """Offline training never opens broker or node credentials (FR-079)."""
    return policy(
        "credential",
        "offline training runs from prepared data with no broker/node credential "
        "or trading-VPS access",
        failure_id="mis.regime_train.broker_or_node_credential",
        given=repr(claim),
    )


def refuse_live_network_training(*, claim: object) -> TypedRefusal:
    """No live network path during the offline training transaction."""
    return policy(
        "network",
        "offline training uses prepared local data only; live network is refused",
        failure_id="mis.regime_train.live_network",
        given=repr(claim),
    )


def refuse_partial_model_registration(*, status: object) -> TypedRefusal:
    """Partial/aborted/refused outputs cannot register as a model (NFR-03)."""
    return policy(
        "registerable",
        "partial outputs cannot register as a model; only a completed terminal "
        "training record may later enter Story 30.6 registration",
        failure_id="mis.regime_train.partial_register",
        given=repr(status),
    )


def refuse_reproducibility_mismatch(
    *,
    expected_fp: object,
    observed_fp: object,
) -> TypedRefusal:
    """Identical inputs must reproduce or return an explicit refusal (NFR-03)."""
    return policy(
        "reproducibility",
        "rerun under identical inputs must reproduce the governed training "
        "artifact or return an explicit reproducibility refusal",
        failure_id="mis.regime_train.reproducibility_mismatch",
        expected=repr(expected_fp),
        observed=repr(observed_fp),
    )


def capture_machine_environment() -> MachineEnvironment:
    """Capture OS/CPU/memory facts without opening network or credentials."""
    memory_total = _probe_memory_total_bytes()
    host = platform.node() or "unknown"
    redacted = f"host-{hashlib.sha256(host.encode('utf-8')).hexdigest()[:12]}"
    return MachineEnvironment(
        os_name=platform.system(),
        os_release=platform.release(),
        os_version=platform.version(),
        machine=platform.machine(),
        processor=platform.processor() or "unknown",
        python_version=platform.python_version(),
        cpu_count=os.cpu_count(),
        memory_total_bytes=memory_total,
        hostname_redacted=redacted,
    )


def resolve_dependency_lock(*, lock_path: object | None = None) -> Result[DependencyLockRecord]:
    """Fingerprint the workspace uv.lock (or an explicit lock path) when present."""
    path = _resolve_lock_path(lock_path)
    if path is None:
        return Ok(
            DependencyLockRecord(
                lock_path="uv.lock",
                lock_fp="absent",
                present=False,
            )
        )
    try:
        loaded = read_contained_bytes(
            path,
            contain_within=_worktree_root(),
            max_bytes=MAX_JSONL_BYTES,
            field="dependency_lock",
        )
    except OSError as exc:
        return unavailable_lock(path, exc)
    if is_refusal(loaded):
        return unavailable_lock(
            path,
            OSError(str(loaded.context.get("reason", "unreadable"))),
        )
    payload = loaded.value
    digest = hashlib.sha256(payload).hexdigest()
    return Ok(
        DependencyLockRecord(
            lock_path=_posix_rel(path),
            lock_fp=f"fp1:sha256:{digest}",
            present=True,
        )
    )


def unavailable_lock(path: Path, exc: OSError) -> TypedRefusal:
    """Typed refusal when the declared lock cannot be read."""
    return unavailable(
        "dependency_lock",
        "dependency lock path is not readable for training provenance",
        path=str(path),
        errno=getattr(exc, "errno", None),
        failure_id="mis.regime_train.dependency_lock",
    )


def build_training_config(
    *,
    labeled: object,
    cleaned: object,
    output_dir: object,
    seed: object = DEFAULT_TRAINING_SEED,
    backend: object = TRAINING_BACKEND_DETERMINISTIC,
    max_trials: object | None = None,
    command: object | None = None,
    design: RegimeClassifierDesign | None = None,
    contract: ExecutableRegimeContract | None = None,
    allow_live_network: object = False,
    allow_vps_or_cloud: object = False,
    allow_broker_or_node_credential: object = False,
) -> Result[TrainingConfig]:
    """Mint the fingerprinted offline training config from Story 30.1–30.3 inputs."""
    blocked = _refuse_training_allowances(
        allow_live_network=allow_live_network,
        allow_vps_or_cloud=allow_vps_or_cloud,
        allow_broker_or_node_credential=allow_broker_or_node_credential,
    )
    if is_refusal(blocked):
        return blocked
    inputs = _require_training_inputs(
        labeled=labeled,
        cleaned=cleaned,
        output_dir=output_dir,
        seed=seed,
        backend=backend,
    )
    if is_refusal(inputs):
        return inputs
    return _assemble_training_config(
        inputs.value, design=design, contract=contract, max_trials=max_trials, command=command
    )


def build_labeled_feature_rows(
    cleaned: object,
    labeled: object,
    *,
    roles: frozenset[str] | set[str],
    peer_features: Mapping[str, Mapping[str, float]] | None = None,
    design: RegimeClassifierDesign | None = None,
    contract: ExecutableRegimeContract | None = None,
) -> Result[
    tuple[
        tuple[str, ...],
        tuple[str, ...],
        dict[str, tuple[tuple[str, tuple[float, ...], str, str], ...]],
        int,
    ]
]:
    """Causal feature rows for the requested split roles (shared by train/eval).

    Each row is ``(row_id, features, class_label, session)``. Callers that must
    keep the sealed holdout unused (Story 30.4) omit ``sealed-test`` from
    ``roles``; Story 30.5 evaluation includes it read-only.
    """
    inputs = _feature_row_inputs(
        cleaned=cleaned,
        labeled=labeled,
        roles=roles,
        peer_features=peer_features,
        design=design,
        contract=contract,
    )
    if is_refusal(inputs):
        return inputs
    cleaned_corpus, labeled_corpus, role_set, feature_ids, peer_ids, peer_map, peer_supplied = (
        inputs.value
    )
    collected = _collect_labeled_feature_rows(
        cleaned_corpus,
        labeled_corpus,
        role_set=role_set,
        feature_ids=feature_ids,
        peer_ids=peer_ids,
        peer_map=peer_map,
        peer_supplied=peer_supplied,
    )
    if is_refusal(collected):
        return collected
    frozen, excluded = collected.value
    return Ok((feature_ids, REGIME_CLASS_VOCABULARY, frozen, excluded))


def build_training_matrix(
    cleaned: object,
    labeled: object,
    *,
    peer_features: Mapping[str, Mapping[str, float]] | None = None,
    design: RegimeClassifierDesign | None = None,
    contract: ExecutableRegimeContract | None = None,
    inspect_sealed_holdout: object = False,
) -> Result[PreparedTrainingMatrix]:
    """Build train/validation feature rows; sealed holdout stays unused."""
    peeked = _refuse_sealed_holdout_peek(inspect_sealed_holdout)
    if is_refusal(peeked):
        return peeked
    built = build_labeled_feature_rows(
        cleaned,
        labeled,
        roles={SegmentRole.TRAIN.value, SegmentRole.VALIDATION.value},
        peer_features=peer_features,
        design=design,
        contract=contract,
    )
    if is_refusal(built):
        return built
    if not isinstance(labeled, LabeledCorpus):
        return invalid("labeled", "training matrix takes a LabeledCorpus")
    return _prepared_training_matrix(
        labeled, built.value, peer_features_supplied=peer_features is not None
    )


def run_offline_training(
    *,
    labeled: object,
    cleaned: object,
    output_dir: object,
    seed: object = DEFAULT_TRAINING_SEED,
    backend: object = TRAINING_BACKEND_DETERMINISTIC,
    max_trials: object | None = None,
    command: object | None = None,
    peer_features: Mapping[str, Mapping[str, float]] | None = None,
    design: RegimeClassifierDesign | None = None,
    contract: ExecutableRegimeContract | None = None,
    lock_path: object | None = None,
    resume: object = False,
    abort_after_trials: object | None = None,
    fit_fn: FitFn | None = None,
    allow_live_network: object = False,
    allow_vps_or_cloud: object = False,
    allow_broker_or_node_credential: object = False,
    clock_ns: Callable[[], int] | None = None,
) -> Result[TrainingArtifact | TrainingRecord]:
    """Run or resume the bounded offline training script."""
    return _run_offline_training_body(
        labeled,
        cleaned,
        output_dir,
        seed,
        backend,
        max_trials,
        command,
        peer_features,
        design,
        contract,
        lock_path,
        resume,
        abort_after_trials,
        fit_fn,
        allow_live_network,
        allow_vps_or_cloud,
        allow_broker_or_node_credential,
        clock_ns,
    )


def _run_offline_training_body(
    labeled: object,
    cleaned: object,
    output_dir: object,
    seed: object,
    backend: object,
    max_trials: object | None,
    command: object | None,
    peer_features: Mapping[str, Mapping[str, float]] | None,
    design: RegimeClassifierDesign | None,
    contract: ExecutableRegimeContract | None,
    lock_path: object | None,
    resume: object,
    abort_after_trials: object | None,
    fit_fn: FitFn | None,
    allow_live_network: object,
    allow_vps_or_cloud: object,
    allow_broker_or_node_credential: object,
    clock_ns: Callable[[], int] | None,
) -> Result[TrainingArtifact | TrainingRecord]:
    session = _open_training_session(
        labeled=labeled,
        cleaned=cleaned,
        output_dir=output_dir,
        seed=seed,
        backend=backend,
        max_trials=max_trials,
        command=command,
        design=design,
        contract=contract,
        lock_path=lock_path,
        allow_live_network=allow_live_network,
        allow_vps_or_cloud=allow_vps_or_cloud,
        allow_broker_or_node_credential=allow_broker_or_node_credential,
        clock_ns=clock_ns,
    )
    if is_refusal(session):
        return session
    return _execute_offline_training(
        session.value,
        labeled=labeled,
        cleaned=cleaned,
        peer_features=peer_features,
        design=design,
        contract=contract,
        resume=resume,
        abort_after_trials=abort_after_trials,
        fit_fn=fit_fn,
    )


def resume_offline_training(**kwargs: object) -> Result[TrainingArtifact | TrainingRecord]:
    """Resume an interrupted offline training run from its checkpoint."""
    kwargs = dict(kwargs)
    kwargs["resume"] = True
    return run_offline_training(**kwargs)  # type: ignore[arg-type]


def assert_registerable_training_artifact(
    artifact: object,
) -> Result[None]:
    """Only a completed terminal record/artifact may later register (Story 30.6)."""
    if isinstance(artifact, TrainingArtifact):
        return _assert_completed_registerable(
            registerable=artifact.registerable,
            status=artifact.record.status,
            grants_money_path_authority=artifact.grants_money_path_authority,
            grants_governed_binding=artifact.grants_governed_binding,
            status_token=artifact.record.status.value,
        )
    if isinstance(artifact, TrainingRecord):
        return _assert_completed_registerable(
            registerable=artifact.registerable,
            status=artifact.status,
            grants_money_path_authority=artifact.grants_money_path_authority,
            grants_governed_binding=artifact.grants_governed_binding,
            status_token=artifact.status.value,
        )
    if isinstance(artifact, TrainingCheckpoint):
        return refuse_partial_model_registration(status="checkpoint")
    return invalid(
        "artifact",
        "registerability check takes a TrainingArtifact or TrainingRecord",
        given=type(artifact).__name__,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Operator entry: ``python -m qmn.mis.regime_train`` (never a node CLI)."""
    args = _train_cli_parser().parse_args(list(argv) if argv is not None else None)
    if args.labeled_json is None or args.cleaned_json is None:
        sys.stderr.write(
            "operator-prepared --labeled-json and --cleaned-json are required; "
            "this script never fetches providers or opens credentials\n"
        )
        return 2
    return _refuse_cli_loader(args, argv)


def _train_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qmn.mis.regime_train",
        description=(
            "Offline operator-machine regime_classifier_v1 training script. "
            "No VPS/cloud, no broker/node credentials, no money-path authority."
        ),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=DEFAULT_TRAINING_SEED)
    parser.add_argument(
        "--backend",
        choices=(TRAINING_BACKEND_DETERMINISTIC, TRAINING_BACKEND_LIGHTGBM),
        default=TRAINING_BACKEND_DETERMINISTIC,
    )
    parser.add_argument("--max-trials", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--labeled-json",
        type=Path,
        help="Path to a prepared labeled-corpus JSON envelope (operator-prepared).",
    )
    parser.add_argument(
        "--cleaned-json",
        type=Path,
        help="Path to a prepared cleaned-corpus JSON envelope (operator-prepared).",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Write config/provenance scaffolding only; do not fit trials.",
    )
    return parser


def _refuse_cli_loader(args: argparse.Namespace, argv: Sequence[str] | None) -> int:
    sys.stderr.write(
        "JSON envelope loading for operator-prepared corpora is staged through "
        "run_offline_training with in-memory Story 30.2/30.3 artifacts; pass "
        "objects from Python rather than relying on an undeclared on-disk schema "
        "in Story 30.4. Refusing rather than inventing a loader.\n"
    )
    refusal = policy(
        "cli_loader",
        "Story 30.4 ships the offline training script API; operator JSON envelope "
        "loading stays explicit via Python objects from Stories 30.2/30.3 rather "
        "than an invented on-disk schema",
        failure_id="mis.regime_train.cli_loader",
        labeled_json=str(args.labeled_json),
        cleaned_json=str(args.cleaned_json),
        plan_only=bool(args.plan_only),
        resume=bool(args.resume),
        seed=args.seed,
        backend=args.backend,
        output_dir=str(args.output_dir),
    )
    envelope = {
        "status": TrainingTerminalStatus.REFUSED.value,
        "cause": refusal.context.get("reason"),
        "failure_id": refusal.context.get("failure_id"),
        "training_location": TRAINING_LOCATION,
        "command": list(sys.argv if argv is None else argv),
    }
    prepared = _ensure_contained_dir(args.output_dir, contain_within=args.output_dir)
    if not is_refusal(prepared):
        _write_json(
            args.output_dir / _RECORD_FILENAME,
            envelope,
            contain_within=args.output_dir,
        )
    return 1


# --- internals -----------------------------------------------------------------


def _refuse_training_allowances(
    *,
    allow_live_network: object,
    allow_vps_or_cloud: object,
    allow_broker_or_node_credential: object,
) -> Result[None]:
    if allow_live_network is True:
        return refuse_live_network_training(claim="allow_live_network=True")
    if allow_live_network not in (False, None):
        return invalid(
            "allow_live_network",
            "allow_live_network is False for offline training",
            given=repr(allow_live_network),
        )
    if allow_vps_or_cloud is True:
        return refuse_vps_or_cloud_training(location="vps-or-cloud")
    if allow_vps_or_cloud not in (False, None):
        return invalid(
            "allow_vps_or_cloud",
            "allow_vps_or_cloud is False for offline training",
            given=repr(allow_vps_or_cloud),
        )
    if allow_broker_or_node_credential is True:
        return refuse_broker_or_node_credential(claim="allow_broker_or_node_credential=True")
    if allow_broker_or_node_credential not in (False, None):
        return invalid(
            "allow_broker_or_node_credential",
            "allow_broker_or_node_credential is False for offline training",
            given=repr(allow_broker_or_node_credential),
        )
    return Ok(None)


def _require_training_inputs(
    *,
    labeled: object,
    cleaned: object,
    output_dir: object,
    seed: object,
    backend: object,
) -> Result[tuple[LabeledCorpus, CleanedCorpus, str, int, str]]:
    if not isinstance(labeled, LabeledCorpus):
        return invalid(
            "labeled",
            "offline training takes a LabeledCorpus from Story 30.3",
            given=type(labeled).__name__,
        )
    if not isinstance(cleaned, CleanedCorpus):
        return invalid(
            "cleaned",
            "offline training takes the CleanedCorpus cited by the labeled corpus",
            given=type(cleaned).__name__,
        )
    out = clean_token(output_dir)
    if out is None:
        return invalid("output_dir", "output_dir is a non-blank path string")
    if not isinstance(seed, int) or isinstance(seed, bool):
        return invalid("seed", "training seed is a declared int", given=repr(seed))
    backend_token = clean_token(backend)
    if backend_token not in {
        TRAINING_BACKEND_DETERMINISTIC,
        TRAINING_BACKEND_LIGHTGBM,
    }:
        return invalid(
            "backend",
            "backend is deterministic-surrogate or lightgbm",
            given=repr(backend),
        )
    return Ok((labeled, cleaned, out, seed, backend_token))


def _assemble_training_config(
    inputs: tuple[LabeledCorpus, CleanedCorpus, str, int, str],
    *,
    design: RegimeClassifierDesign | None,
    contract: ExecutableRegimeContract | None,
    max_trials: object | None,
    command: object | None,
) -> Result[TrainingConfig]:
    labeled_corpus, cleaned_corpus, out, seed_i, backend_token = inputs
    cited = _cite_training_design(
        labeled=labeled_corpus,
        cleaned=cleaned_corpus,
        design=design,
        contract=contract,
    )
    if is_refusal(cited):
        return cited
    _design_artifact, resolved_contract, labeled_fp, cleaned_fp, contract_fp = cited.value
    windows = _training_windows_and_trials(
        labeled=labeled_corpus,
        cleaned=cleaned_corpus,
        resolved_contract=resolved_contract,
        max_trials=max_trials,
    )
    if is_refusal(windows):
        return windows
    start_ns, end_ns, train_end, validation_end, holdout_end, trial_cap = windows.value
    command_sessions = _training_command_and_sessions(
        cleaned=cleaned_corpus, output_dir=out, command=command
    )
    if is_refusal(command_sessions):
        return command_sessions
    cmd, sessions = command_sessions.value
    return Ok(
        _mint_training_config(
            resolved_contract=resolved_contract,
            labeled_corpus=labeled_corpus,
            labeled_fp=labeled_fp,
            cleaned_fp=cleaned_fp,
            contract_fp=contract_fp,
            windows=(start_ns, end_ns, train_end, validation_end, holdout_end),
            sessions=sessions,
            seed=seed_i,
            backend=backend_token,
            max_trials=trial_cap,
            output_dir=out,
            command=cmd,
        )
    )


def _cite_training_design(
    *,
    labeled: LabeledCorpus,
    cleaned: CleanedCorpus,
    design: RegimeClassifierDesign | None,
    contract: ExecutableRegimeContract | None,
) -> Result[
    tuple[
        RegimeClassifierDesign,
        ExecutableRegimeContract,
        Fingerprint,
        Fingerprint,
        Fingerprint,
    ]
]:
    resolved = _resolve_contract(design=design, contract=contract)
    if is_refusal(resolved):
        return resolved
    design_artifact, resolved_contract = resolved.value
    aligned = _assert_training_design_aligned(
        labeled=labeled,
        cleaned=cleaned,
        design_artifact=design_artifact,
        resolved_contract=resolved_contract,
    )
    if is_refusal(aligned):
        return aligned
    fps = _training_input_fingerprints(
        labeled=labeled, cleaned=cleaned, resolved_contract=resolved_contract
    )
    if is_refusal(fps):
        return fps
    labeled_fp, cleaned_fp, contract_fp = fps.value
    return Ok((design_artifact, resolved_contract, labeled_fp, cleaned_fp, contract_fp))


def _assert_training_design_aligned(
    *,
    labeled: LabeledCorpus,
    cleaned: CleanedCorpus,
    design_artifact: RegimeClassifierDesign,
    resolved_contract: ExecutableRegimeContract,
) -> Result[None]:
    if labeled.design_fp.value != resolved_contract.design_fp.value:
        return policy(
            "design_fp",
            "labeled corpus must cite the accepted Story 30.1 design fingerprint",
            labeled=labeled.design_fp.value,
            design=resolved_contract.design_fp.value,
        )
    if cleaned.design_fp.value != resolved_contract.design_fp.value:
        return policy(
            "design_fp",
            "cleaned corpus must cite the accepted Story 30.1 design fingerprint",
            cleaned=cleaned.design_fp.value,
            design=resolved_contract.design_fp.value,
        )
    unchanged = assert_design_unchanged(labeled.design_fp, design=design_artifact)
    if is_refusal(unchanged):
        return unchanged
    if resolved_contract.chosen_family != CHOSEN_MODEL_FAMILY:
        return policy(
            "chosen_family",
            "offline training implements only lightgbm-multiclass",
            given=resolved_contract.chosen_family,
        )
    if resolved_contract.training_location != TRAINING_LOCATION:
        return refuse_vps_or_cloud_training(location=resolved_contract.training_location)
    return Ok(None)


def _training_input_fingerprints(
    *,
    labeled: LabeledCorpus,
    cleaned: CleanedCorpus,
    resolved_contract: ExecutableRegimeContract,
) -> Result[tuple[Fingerprint, Fingerprint, Fingerprint]]:
    labeled_fp = labeled.fingerprint()
    if is_refusal(labeled_fp):
        return labeled_fp
    cleaned_fp = cleaned.fingerprint()
    if is_refusal(cleaned_fp):
        return cleaned_fp
    if labeled.cleaned_fp.value != cleaned_fp.value.value:
        return policy(
            "cleaned_fp",
            "cleaned corpus fingerprint must match the labeled corpus citation",
            labeled=labeled.cleaned_fp.value,
            cleaned=cleaned_fp.value.value,
        )
    contract_fp = resolved_contract.fingerprint()
    if is_refusal(contract_fp):
        return contract_fp
    return Ok((labeled_fp.value, cleaned_fp.value, contract_fp.value))


def _training_windows_and_trials(
    *,
    labeled: LabeledCorpus,
    cleaned: CleanedCorpus,
    resolved_contract: ExecutableRegimeContract,
    max_trials: object | None,
) -> Result[tuple[int, int, int, int, int, int]]:
    windows = _data_windows(cleaned.rows)
    if is_refusal(windows):
        return windows
    start_ns, end_ns = windows.value
    boundaries = _split_boundaries_from_labeled(labeled)
    if is_refusal(boundaries):
        return boundaries
    train_end, validation_end, holdout_end = boundaries.value
    bounds = resolved_contract.hyperparameter_bounds
    trial_cap = bounds.max_trials if max_trials is None else max_trials
    if not isinstance(trial_cap, int) or isinstance(trial_cap, bool) or trial_cap < 1:
        return invalid("max_trials", "max_trials is a positive int", given=repr(max_trials))
    if trial_cap > bounds.max_trials:
        return policy(
            "max_trials",
            "max_trials cannot exceed the Story 30.1 hyperparameter bound",
            given=trial_cap,
            bound=bounds.max_trials,
        )
    return Ok((start_ns, end_ns, train_end, validation_end, holdout_end, trial_cap))


def _training_command_and_sessions(
    *,
    cleaned: CleanedCorpus,
    output_dir: str,
    command: object | None,
) -> Result[tuple[tuple[str, ...], tuple[str, ...]]]:
    cmd = _training_command_argv(output_dir=output_dir, command=command)
    if is_refusal(cmd):
        return cmd
    sessions = tuple(sorted({row.session for row in cleaned.rows}))
    if set(sessions) != set(DECLARED_TRADING_SESSIONS):
        return policy(
            "sessions",
            "training data must cover asia, london, and new_york exactly",
            given=list(sessions),
            required=list(DECLARED_TRADING_SESSIONS),
            failure_id="mis.regime_train.session_coverage",
        )
    return Ok((cmd.value, tuple(DECLARED_TRADING_SESSIONS)))


def _training_command_argv(
    *,
    output_dir: str,
    command: object | None,
) -> Result[tuple[str, ...]]:
    if command is None:
        return Ok(("python", "-m", "qmn.mis.regime_train", "--output-dir", output_dir))
    if isinstance(command, Sequence) and not isinstance(command, (str, bytes)):
        tokens = tuple(str(item) for item in cast("Sequence[object]", command))
        if not tokens:
            return invalid("command", "command is a non-empty argv sequence")
        return Ok(tokens)
    return invalid("command", "command is an argv sequence", given=type(command).__name__)


def _mint_training_config(
    *,
    resolved_contract: ExecutableRegimeContract,
    labeled_corpus: LabeledCorpus,
    labeled_fp: Fingerprint,
    cleaned_fp: Fingerprint,
    contract_fp: Fingerprint,
    windows: tuple[int, int, int, int, int],
    sessions: tuple[str, ...],
    seed: int,
    backend: str,
    max_trials: int,
    output_dir: str,
    command: tuple[str, ...],
) -> TrainingConfig:
    start_ns, end_ns, train_end, validation_end, holdout_end = windows
    return TrainingConfig(
        design_fp=resolved_contract.design_fp,
        contract_fp=contract_fp,
        labeled_fp=labeled_fp,
        cleaned_fp=cleaned_fp,
        splits_fp=labeled_corpus.splits_fp,
        data_window_start_ns=start_ns,
        data_window_end_ns=end_ns,
        train_end_ns=train_end,
        validation_end_ns=validation_end,
        holdout_end_ns=holdout_end,
        sessions=sessions,
        rng_algorithm=RNG_ALGORITHM,
        seed=seed,
        backend=backend,
        max_trials=max_trials,
        output_dir=output_dir,
        command=command,
        allow_live_network=False,
        allow_vps_or_cloud=False,
        allow_broker_or_node_credential=False,
        grants_money_path_authority=False,
    )


def _refuse_sealed_holdout_peek(inspect_sealed_holdout: object) -> Result[None]:
    if inspect_sealed_holdout is True:
        return policy(
            "inspect_sealed_holdout",
            "training must not inspect sealed holdout outcomes; evaluation is Story 30.5",
            failure_id="mis.regime_train.sealed_holdout_peek",
        )
    if inspect_sealed_holdout not in (False, None):
        return invalid(
            "inspect_sealed_holdout",
            "inspect_sealed_holdout is False for offline training",
            given=repr(inspect_sealed_holdout),
        )
    return Ok(None)


def _prepared_training_matrix(
    labeled: LabeledCorpus,
    built: tuple[
        tuple[str, ...],
        tuple[str, ...],
        dict[str, tuple[tuple[str, tuple[float, ...], str, str], ...]],
        int,
    ],
    *,
    peer_features_supplied: bool,
) -> Result[PreparedTrainingMatrix]:
    feature_ids, vocabulary, buckets, excluded = built
    train_rows = tuple(
        (row_id, features, label)
        for row_id, features, label, _session in buckets.get(SegmentRole.TRAIN.value, ())
    )
    validation_rows = tuple(
        (row_id, features, label)
        for row_id, features, label, _session in buckets.get(SegmentRole.VALIDATION.value, ())
    )
    if not train_rows:
        return policy(
            "train_rows",
            "offline training requires at least one non-excluded train row",
            failure_id="mis.regime_train.insufficient_train_rows",
        )
    if not validation_rows:
        return policy(
            "validation_rows",
            "offline training requires at least one non-excluded validation row",
            failure_id="mis.regime_train.insufficient_validation_rows",
        )
    sealed = sum(1 for row in labeled.rows if row.split_role == _SPLIT_ROLE_HOLDOUT)
    return Ok(
        PreparedTrainingMatrix(
            feature_ids=feature_ids,
            class_vocabulary=vocabulary,
            train_rows=train_rows,
            validation_rows=validation_rows,
            excluded_count=excluded,
            sealed_holdout_count=sealed,
            sealed_holdout_unused=True,
            peer_features_supplied=peer_features_supplied,
        )
    )


def _assert_completed_registerable(
    *,
    registerable: bool,
    status: TrainingTerminalStatus,
    grants_money_path_authority: bool,
    grants_governed_binding: bool,
    status_token: str,
) -> Result[None]:
    if (
        registerable
        and status is TrainingTerminalStatus.COMPLETED
        and grants_money_path_authority is False
        and grants_governed_binding is False
    ):
        return Ok(None)
    return refuse_partial_model_registration(status=status_token)


def _open_training_session(
    *,
    labeled: object,
    cleaned: object,
    output_dir: object,
    seed: object,
    backend: object,
    max_trials: object | None,
    command: object | None,
    design: RegimeClassifierDesign | None,
    contract: ExecutableRegimeContract | None,
    lock_path: object | None,
    allow_live_network: object,
    allow_vps_or_cloud: object,
    allow_broker_or_node_credential: object,
    clock_ns: Callable[[], int] | None,
) -> Result[_TrainingSession]:
    mono = _resolve_clock_ns(clock_ns)
    start_mono_ns = mono()
    start_utc = _utc_now()
    machine = capture_machine_environment()
    lock = resolve_dependency_lock(lock_path=lock_path)
    if is_refusal(lock):
        return lock
    config = build_training_config(
        labeled=labeled,
        cleaned=cleaned,
        output_dir=output_dir,
        seed=seed,
        backend=backend,
        max_trials=max_trials,
        command=command,
        design=design,
        contract=contract,
        allow_live_network=allow_live_network,
        allow_vps_or_cloud=allow_vps_or_cloud,
        allow_broker_or_node_credential=allow_broker_or_node_credential,
    )
    if is_refusal(config):
        return config
    return _session_from_config(config.value, lock.value, machine, start_utc, start_mono_ns, mono)


def _session_from_config(
    config: TrainingConfig,
    lock: DependencyLockRecord,
    machine: MachineEnvironment,
    start_utc: str,
    start_mono_ns: int,
    clock_ns: Callable[[], int],
) -> Result[_TrainingSession]:
    code_fp = _training_code_fp()
    if is_refusal(code_fp):
        return code_fp
    config_fp = config.fingerprint()
    if is_refusal(config_fp):
        return config_fp
    out_root = Path(config.output_dir)
    prepared = _ensure_contained_dir(out_root, contain_within=out_root)
    if is_refusal(prepared):
        return prepared
    written = _write_json(
        out_root / _CONFIG_FILENAME,
        config.fp1_identity(),
        contain_within=out_root,
    )
    if is_refusal(written):
        return written
    return Ok(
        _TrainingSession(
            config=config,
            config_fp=config_fp.value,
            code_fp=code_fp.value,
            lock=lock,
            machine=machine,
            start_utc=start_utc,
            start_mono_ns=start_mono_ns,
            clock_ns=clock_ns,
            out_root=out_root,
        )
    )


def _execute_offline_training(
    session: _TrainingSession,
    *,
    labeled: object,
    cleaned: object,
    peer_features: Mapping[str, Mapping[str, float]] | None,
    design: RegimeClassifierDesign | None,
    contract: ExecutableRegimeContract | None,
    resume: object,
    abort_after_trials: object | None,
    fit_fn: FitFn | None,
) -> Result[TrainingArtifact | TrainingRecord]:
    prepared = _prepare_training_matrix(
        session,
        labeled=labeled,
        cleaned=cleaned,
        peer_features=peer_features,
        design=design,
        contract=contract,
    )
    if is_refusal(prepared):
        return prepared
    if isinstance(prepared.value, TrainingRecord):
        return Ok(prepared.value)
    matrix, matrix_fp = prepared.value
    ready = _training_search_ready(session, resume=resume, fit_fn=fit_fn)
    if is_refusal(ready):
        return ready
    if isinstance(ready.value, TrainingRecord):
        return Ok(ready.value)
    search, fitter = ready.value
    abort_ok = _validate_abort_after_trials(abort_after_trials)
    if is_refusal(abort_ok):
        return abort_ok
    ran = _run_trial_search(
        session,
        matrix,
        matrix_fp,
        search,
        fitter,
        design=design,
        contract=contract,
        abort_after_trials=abort_after_trials,
    )
    if is_refusal(ran):
        return ran
    snapshot, aborted, abort_cause = ran.value
    return _finish_training_run(session, matrix_fp, snapshot, aborted, abort_cause)


def _prepare_training_matrix(
    session: _TrainingSession,
    *,
    labeled: object,
    cleaned: object,
    peer_features: Mapping[str, Mapping[str, float]] | None,
    design: RegimeClassifierDesign | None,
    contract: ExecutableRegimeContract | None,
) -> Result[tuple[PreparedTrainingMatrix, Fingerprint] | TrainingRecord]:
    matrix = build_training_matrix(
        cleaned,
        labeled,
        peer_features=peer_features,
        design=design,
        contract=contract,
    )
    if is_refusal(matrix):
        persisted = _persist_status(
            session,
            status=TrainingTerminalStatus.REFUSED,
            cause=str(matrix.context.get("reason", "matrix refused")),
        )
        if is_refusal(persisted):
            return persisted
        return Ok(persisted.value)
    matrix_fp = matrix.value.fingerprint()
    if is_refusal(matrix_fp):
        return matrix_fp
    return Ok((matrix.value, matrix_fp.value))


def _training_search_ready(
    session: _TrainingSession,
    *,
    resume: object,
    fit_fn: FitFn | None,
) -> Result[tuple[_SearchSnapshot, FitFn] | TrainingRecord]:
    search = _resume_search_state(session, resume=resume)
    if is_refusal(search):
        return search
    if isinstance(search.value, TrainingRecord):
        return Ok(search.value)
    fitter = _resolve_training_fitter(session, search.value, fit_fn)
    if is_refusal(fitter):
        return fitter
    if isinstance(fitter.value, TrainingRecord):
        return Ok(fitter.value)
    return Ok((search.value, fitter.value))


def _persist_status(
    session: _TrainingSession,
    *,
    status: TrainingTerminalStatus,
    cause: str,
    trials: tuple[TrialRecord, ...] = (),
    best_trial_index: int | None = None,
    model_path: str | None = None,
    model_fp: str | None = None,
    registerable: bool = False,
) -> Result[TrainingRecord]:
    record = _terminal_record(
        status=status,
        cause=cause,
        config=session.config,
        config_fp=session.config_fp,
        code_fp=session.code_fp,
        lock=session.lock,
        machine=session.machine,
        start_utc=session.start_utc,
        start_mono_ns=session.start_mono_ns,
        clock_ns=session.clock_ns,
        trials=trials,
        best_trial_index=best_trial_index,
        model_path=model_path,
        model_fp=model_fp,
        registerable=registerable,
    )
    persisted = _persist_record(session.out_root, record)
    if is_refusal(persisted):
        return persisted
    return Ok(record)


def _empty_search() -> _SearchSnapshot:
    return _SearchSnapshot(
        completed=(),
        best_index=None,
        best_score=None,
        best_model_text=None,
        start_trial=0,
    )


def _resume_search_state(
    session: _TrainingSession,
    *,
    resume: object,
) -> Result[_SearchSnapshot | TrainingRecord]:
    if resume is True:
        return _resume_from_checkpoint(session)
    if resume not in (False, None):
        return invalid("resume", "resume is a bool", given=repr(resume))
    return Ok(_empty_search())


def _resume_from_checkpoint(
    session: _TrainingSession,
) -> Result[_SearchSnapshot | TrainingRecord]:
    loaded = _load_checkpoint(session.out_root)
    if is_refusal(loaded):
        persisted = _persist_status(
            session,
            status=TrainingTerminalStatus.REFUSED,
            cause=str(loaded.context.get("reason", "checkpoint refused")),
        )
        if is_refusal(persisted):
            return persisted
        return Ok(persisted.value)
    if loaded.value is None:
        return Ok(_empty_search())
    applied = _apply_checkpoint(session, loaded.value)
    if is_refusal(applied):
        return applied
    return Ok(applied.value)


def _apply_checkpoint(
    session: _TrainingSession,
    checkpoint: TrainingCheckpoint,
) -> Result[_SearchSnapshot]:
    if checkpoint.config_fp.value != session.config_fp.value:
        return refuse_reproducibility_mismatch(
            expected_fp=checkpoint.config_fp.value,
            observed_fp=session.config_fp.value,
        )
    if checkpoint.registerable:
        return refuse_partial_model_registration(status="checkpoint-registerable")
    best_model_text: str | None = None
    if checkpoint.best_trial_index is not None:
        loaded = _load_prior_best_model(session.out_root, checkpoint.best_trial_index)
        if is_refusal(loaded):
            return loaded
        best_model_text = loaded.value
    return Ok(
        _SearchSnapshot(
            completed=tuple(checkpoint.completed_trials),
            best_index=checkpoint.best_trial_index,
            best_score=checkpoint.best_validation_score_ppb,
            best_model_text=best_model_text,
            start_trial=checkpoint.next_trial_index,
        )
    )


def _load_prior_best_model(out_root: Path, best_index: int) -> Result[str | None]:
    prior = out_root / "trials" / f"trial_{best_index:04d}" / _MODEL_FILENAME
    if not (prior.is_symlink() or prior.is_file()):
        return Ok(None)
    prior_text = read_contained_text(
        prior,
        contain_within=out_root,
        max_bytes=MAX_JSONL_BYTES,
        field="output_dir",
    )
    if is_refusal(prior_text):
        return _output_dir_refusal(prior, given=prior_text.context.get("reason"))
    return Ok(prior_text.value)


def _validate_abort_after_trials(abort_after_trials: object | None) -> Result[None]:
    if abort_after_trials is not None and (
        not isinstance(abort_after_trials, int)
        or isinstance(abort_after_trials, bool)
        or abort_after_trials < 0
    ):
        return invalid(
            "abort_after_trials",
            "abort_after_trials is a non-negative int when set",
            given=repr(abort_after_trials),
        )
    return Ok(None)


def _resolve_training_fitter(
    session: _TrainingSession,
    search: _SearchSnapshot,
    fit_fn: FitFn | None,
) -> Result[FitFn | TrainingRecord]:
    fitter: Result[FitFn] = (
        Ok(fit_fn) if fit_fn is not None else _select_fitter(session.config.backend)
    )
    if is_refusal(fitter):
        persisted = _persist_status(
            session,
            status=TrainingTerminalStatus.REFUSED,
            cause=str(fitter.context.get("reason", "fitter refused")),
            trials=search.completed,
            best_trial_index=search.best_index,
        )
        if is_refusal(persisted):
            return persisted
        return Ok(persisted.value)
    return Ok(fitter.value)


def _prepare_search_rng(
    session: _TrainingSession,
    search: _SearchSnapshot,
    *,
    design: RegimeClassifierDesign | None,
    contract: ExecutableRegimeContract | None,
) -> Result[tuple[random.Random, HyperparameterBounds]]:
    rng = random.Random(session.config.seed)  # noqa: S311
    bounds = _bounds_from_config(session.config, design=design, contract=contract)
    for trial_index in range(search.start_trial):
        _draw_hyperparameters(rng, trial_index=trial_index, bounds=bounds)
    trials_path = session.out_root / _TRIALS_FILENAME
    if search.start_trial == 0 and (trials_path.exists() or trials_path.is_symlink()):
        unlinked = _unlink_contained_regular(
            trials_path, contain_within=session.out_root, missing_ok=False
        )
        if is_refusal(unlinked):
            return unlinked
    return Ok((rng, bounds))


def _run_trial_search(
    session: _TrainingSession,
    matrix: PreparedTrainingMatrix,
    matrix_fp: Fingerprint,
    search: _SearchSnapshot,
    fitter: FitFn,
    *,
    design: RegimeClassifierDesign | None,
    contract: ExecutableRegimeContract | None,
    abort_after_trials: object | None,
) -> Result[tuple[_SearchSnapshot, bool, str]]:
    prepared_rng = _prepare_search_rng(session, search, design=design, contract=contract)
    if is_refusal(prepared_rng):
        return prepared_rng
    rng, bounds = prepared_rng.value
    state: list[TrialRecord] = list(search.completed)
    best_index = search.best_index
    best_score = search.best_score
    best_model_text = search.best_model_text
    aborted = False
    abort_cause = "operator-abort-after-trials"
    for trial_index in range(search.start_trial, session.config.max_trials):
        stepped = _step_one_trial(
            session,
            matrix,
            matrix_fp,
            fitter=fitter,
            rng=rng,
            bounds=bounds,
            trial_index=trial_index,
            abort_after_trials=abort_after_trials,
            completed=state,
            best_index=best_index,
            best_score=best_score,
            best_model_text=best_model_text,
        )
        if is_refusal(stepped):
            return stepped
        state, best_index, best_score, best_model_text, aborted, abort_cause, stop = stepped.value
        if stop:
            break
    snapshot = _SearchSnapshot(
        completed=tuple(state),
        best_index=best_index,
        best_score=best_score,
        best_model_text=best_model_text,
        start_trial=session.config.max_trials,
    )
    return Ok((snapshot, aborted, abort_cause))


def _step_one_trial(
    session: _TrainingSession,
    matrix: PreparedTrainingMatrix,
    matrix_fp: Fingerprint,
    *,
    fitter: FitFn,
    rng: random.Random,
    bounds: HyperparameterBounds,
    trial_index: int,
    abort_after_trials: object | None,
    completed: list[TrialRecord],
    best_index: int | None,
    best_score: int | None,
    best_model_text: str | None,
) -> Result[tuple[list[TrialRecord], int | None, int | None, str | None, bool, str, bool]]:
    if (
        isinstance(abort_after_trials, int)
        and not isinstance(abort_after_trials, bool)
        and len(completed) >= abort_after_trials
    ):
        return Ok(
            _stopped_search(
                completed, best_index, best_score, best_model_text, "operator-abort-after-trials"
            )
        )
    params = _draw_hyperparameters(rng, trial_index=trial_index, bounds=bounds)
    outcome = _fit_one_trial(
        fitter=fitter,
        matrix=matrix,
        config=session.config,
        params=params,
        trial_index=trial_index,
        clock_ns=session.clock_ns,
    )
    if outcome.abort_cause is not None:
        completed.append(outcome.trial)
        return Ok(
            _stopped_search(completed, best_index, best_score, best_model_text, outcome.abort_cause)
        )
    committed = _commit_completed_trial(
        session,
        matrix_fp,
        trial=outcome.trial,
        model_text=outcome.model_text or "",
        completed=completed,
        best_index=best_index,
        best_score=best_score,
        best_model_text=best_model_text,
    )
    if is_refusal(committed):
        return committed
    return Ok(_continued_search(committed.value))


def _stopped_search(
    completed: list[TrialRecord],
    best_index: int | None,
    best_score: int | None,
    best_model_text: str | None,
    abort_cause: str,
) -> tuple[list[TrialRecord], int | None, int | None, str | None, bool, str, bool]:
    return (completed, best_index, best_score, best_model_text, True, abort_cause, True)


def _continued_search(
    committed: tuple[list[TrialRecord], int | None, int | None, str | None],
) -> tuple[list[TrialRecord], int | None, int | None, str | None, bool, str, bool]:
    state, best_index, best_score, best_model_text = committed
    return (
        state,
        best_index,
        best_score,
        best_model_text,
        False,
        "operator-abort-after-trials",
        False,
    )


def _fit_one_trial(
    *,
    fitter: FitFn,
    matrix: PreparedTrainingMatrix,
    config: TrainingConfig,
    params: TrialHyperparameters,
    trial_index: int,
    clock_ns: Callable[[], int],
) -> _TrialFitOutcome:
    trial_started_ns = clock_ns()
    train_payload = tuple((row[0], row[1], row[2]) for row in matrix.train_rows)
    valid_payload = tuple((row[0], row[1], row[2]) for row in matrix.validation_rows)
    try:
        model_text, score_ppb, _train_score = fitter(
            train_payload,
            {
                "validation_rows": valid_payload,
                "feature_ids": list(matrix.feature_ids),
                "class_vocabulary": list(matrix.class_vocabulary),
                "hyperparameters": params.as_mapping(),
                "seed": config.seed,
                "backend": config.backend,
            },
            config.seed + trial_index,
        )
    except Exception as exc:
        elapsed_ms = _elapsed_ms(trial_started_ns, clock_ns)
        trial = TrialRecord(
            trial_index=trial_index,
            hyperparameters=params,
            validation_score_ppb=0,
            status="aborted",
            model_bytes_fp=None,
            elapsed_ms=elapsed_ms,
        )
        return _TrialFitOutcome(
            trial=trial,
            model_text=None,
            abort_cause=f"trial-fit-failed:{type(exc).__name__}",
        )
    return _completed_trial_outcome(
        trial_index=trial_index,
        params=params,
        model_text=model_text,
        score_ppb=score_ppb,
        elapsed_ms=_elapsed_ms(trial_started_ns, clock_ns),
    )


def _completed_trial_outcome(
    *,
    trial_index: int,
    params: TrialHyperparameters,
    model_text: str,
    score_ppb: int,
    elapsed_ms: int,
) -> _TrialFitOutcome:
    model_digest = hashlib.sha256(model_text.encode("utf-8")).hexdigest()
    trial = TrialRecord(
        trial_index=trial_index,
        hyperparameters=params,
        validation_score_ppb=score_ppb,
        status="completed",
        model_bytes_fp=f"fp1:sha256:{model_digest}",
        elapsed_ms=elapsed_ms,
    )
    return _TrialFitOutcome(trial=trial, model_text=model_text, abort_cause=None)


def _commit_completed_trial(
    session: _TrainingSession,
    matrix_fp: Fingerprint,
    *,
    trial: TrialRecord,
    model_text: str,
    completed: list[TrialRecord],
    best_index: int | None,
    best_score: int | None,
    best_model_text: str | None,
) -> Result[tuple[list[TrialRecord], int | None, int | None, str | None]]:
    completed.append(trial)
    written = _write_trial_outputs(session, trial, model_text)
    if is_refusal(written):
        return written
    if best_score is None or trial.validation_score_ppb > best_score:
        best_score = trial.validation_score_ppb
        best_index = trial.trial_index
        best_model_text = model_text
    checkpointed = _write_search_checkpoint(
        session,
        matrix_fp,
        completed=completed,
        next_trial_index=trial.trial_index + 1,
        best_index=best_index,
        best_score=best_score,
    )
    if is_refusal(checkpointed):
        return checkpointed
    return Ok((completed, best_index, best_score, best_model_text))


def _write_trial_outputs(
    session: _TrainingSession,
    trial: TrialRecord,
    model_text: str,
) -> Result[None]:
    trial_dir = session.out_root / "trials" / f"trial_{trial.trial_index:04d}"
    prepared_trial = _ensure_contained_dir(trial_dir, contain_within=session.out_root)
    if is_refusal(prepared_trial):
        return prepared_trial
    written_model = _write_contained_bytes(
        trial_dir / _MODEL_FILENAME,
        model_text.encode("utf-8"),
        contain_within=session.out_root,
    )
    if is_refusal(written_model):
        return written_model
    return _append_jsonl(
        session.out_root / _TRIALS_FILENAME,
        trial.fp1_identity(),
        contain_within=session.out_root,
    )


def _write_search_checkpoint(
    session: _TrainingSession,
    matrix_fp: Fingerprint,
    *,
    completed: Sequence[TrialRecord],
    next_trial_index: int,
    best_index: int | None,
    best_score: int | None,
) -> Result[None]:
    checkpoint = TrainingCheckpoint(
        config_fp=session.config_fp,
        code_fp=session.code_fp,
        matrix_fp=matrix_fp,
        completed_trials=tuple(completed),
        next_trial_index=next_trial_index,
        best_trial_index=best_index,
        best_validation_score_ppb=best_score,
        registerable=False,
        output_dir=session.config.output_dir,
    )
    written_checkpoint = _write_json(
        session.out_root / _CHECKPOINT_FILENAME,
        checkpoint.fp1_identity(),
        contain_within=session.out_root,
    )
    if is_refusal(written_checkpoint):
        return written_checkpoint
    if checkpoint.registerable:
        return refuse_partial_model_registration(status="checkpoint")
    return Ok(None)


def _finish_training_run(
    session: _TrainingSession,
    matrix_fp: Fingerprint,
    snapshot: _SearchSnapshot,
    aborted: bool,
    abort_cause: str,
) -> Result[TrainingArtifact | TrainingRecord]:
    if aborted:
        aborted_record = _finish_aborted_training(session, snapshot, abort_cause)
        if is_refusal(aborted_record):
            return aborted_record
        return Ok(aborted_record.value)
    if snapshot.best_model_text is None or snapshot.best_index is None:
        persisted = _persist_status(
            session,
            status=TrainingTerminalStatus.REFUSED,
            cause="no-completed-trial",
            trials=snapshot.completed,
        )
        if is_refusal(persisted):
            return persisted
        return Ok(persisted.value)
    completed = _finish_completed_training(session, matrix_fp, snapshot)
    if is_refusal(completed):
        return completed
    return Ok(completed.value)


def _finish_aborted_training(
    session: _TrainingSession,
    snapshot: _SearchSnapshot,
    abort_cause: str,
) -> Result[TrainingRecord]:
    persisted = _persist_status(
        session,
        status=TrainingTerminalStatus.ABORTED,
        cause=abort_cause,
        trials=snapshot.completed,
        best_trial_index=snapshot.best_index,
    )
    if is_refusal(persisted):
        return persisted
    record = persisted.value
    assert_register = assert_registerable_training_artifact(record)
    if not is_refusal(assert_register):
        return refuse_partial_model_registration(status=record.status.value)
    return Ok(record)


def _finish_completed_training(
    session: _TrainingSession,
    matrix_fp: Fingerprint,
    snapshot: _SearchSnapshot,
) -> Result[TrainingArtifact]:
    best_model_text = snapshot.best_model_text
    best_index = snapshot.best_index
    if best_model_text is None or best_index is None:
        return invalid("best_trial", "completed search is missing a best trial")
    model_path = session.out_root / _MODEL_FILENAME
    written_best = _write_contained_bytes(
        model_path, best_model_text.encode("utf-8"), contain_within=session.out_root
    )
    if is_refusal(written_best):
        return written_best
    model_digest = hashlib.sha256(best_model_text.encode("utf-8")).hexdigest()
    model_fp = f"fp1:sha256:{model_digest}"
    persisted = _persist_status(
        session,
        status=TrainingTerminalStatus.COMPLETED,
        cause="search-complete",
        trials=snapshot.completed,
        best_trial_index=best_index,
        model_path=_posix_rel(model_path),
        model_fp=model_fp,
        registerable=True,
    )
    if is_refusal(persisted):
        return persisted
    dropped = _drop_completed_checkpoint(session)
    if is_refusal(dropped):
        return dropped
    return _training_artifact(session, persisted.value, best_model_text, model_fp, matrix_fp)


def _drop_completed_checkpoint(session: _TrainingSession) -> Result[None]:
    checkpoint_path = session.out_root / _CHECKPOINT_FILENAME
    if checkpoint_path.exists() or checkpoint_path.is_symlink():
        return _unlink_contained_regular(
            checkpoint_path, contain_within=session.out_root, missing_ok=False
        )
    return Ok(None)


def _training_artifact(
    session: _TrainingSession,
    record: TrainingRecord,
    model_text: str,
    model_fp: str,
    matrix_fp: Fingerprint,
) -> Result[TrainingArtifact]:
    model_fp_obj = Fingerprint.try_create(model_fp)
    if is_refusal(model_fp_obj):
        return model_fp_obj
    return Ok(
        TrainingArtifact(
            artifact_id=REGIME_TRAIN_ARTIFACT_ID,
            record=record,
            model_text=model_text,
            model_fp=model_fp_obj.value,
            config_fp=session.config_fp,
            code_fp=session.code_fp,
            matrix_fp=matrix_fp,
            design_fp=session.config.design_fp,
            registerable=True,
            grants_money_path_authority=False,
            grants_governed_binding=False,
        )
    )


def _resolve_contract(
    *,
    design: RegimeClassifierDesign | None,
    contract: ExecutableRegimeContract | None,
) -> Result[tuple[RegimeClassifierDesign, ExecutableRegimeContract]]:
    artifact = design if design is not None else accepted_regime_classifier_design()
    if contract is None:
        built = executable_regime_contract(artifact)
        if is_refusal(built):
            return built
        return Ok((artifact, built.value))
    current = artifact.fingerprint()
    if is_refusal(current):
        return current
    if contract.design_fp.value != current.value.value:
        return policy(
            "contract",
            "executable contract must cite the supplied design fingerprint",
            contract=contract.design_fp.value,
            design=current.value.value,
        )
    return Ok((artifact, contract))


def _data_windows(
    rows: Sequence[CleanedCorpusRow],
) -> Result[tuple[int, int]]:
    if not rows:
        return invalid("cleaned", "cleaned corpus has no rows")
    start = min(row.event_time_ns for row in rows)
    end = max(row.event_time_ns for row in rows) + BAR_INTERVAL_M5_NS
    return Ok((start, end))


def _split_boundaries_from_labeled(
    labeled: LabeledCorpus,
) -> Result[tuple[int, int, int]]:
    train_end: int | None = None
    validation_end: int | None = None
    holdout_end: int | None = None
    for row in labeled.rows:
        end_ns = row.event_time_ns + BAR_INTERVAL_M5_NS
        if row.split_role == SegmentRole.TRAIN.value:
            train_end = end_ns if train_end is None else max(train_end, end_ns)
        elif row.split_role == SegmentRole.VALIDATION.value:
            validation_end = end_ns if validation_end is None else max(validation_end, end_ns)
        elif row.split_role == _SPLIT_ROLE_HOLDOUT:
            holdout_end = end_ns if holdout_end is None else max(holdout_end, end_ns)
    return _require_split_window(train_end, validation_end, holdout_end)


def _require_split_window(
    train_end: int | None,
    validation_end: int | None,
    holdout_end: int | None,
) -> Result[tuple[int, int, int]]:
    if train_end is None or validation_end is None or holdout_end is None:
        return policy(
            "splits",
            "labeled corpus must expose train, validation, and sealed-test rows",
            train_end=train_end,
            validation_end=validation_end,
            holdout_end=holdout_end,
        )
    if not (train_end <= validation_end <= holdout_end):
        return policy(
            "splits",
            "train/validation/holdout windows must be non-decreasing",
            train_end=train_end,
            validation_end=validation_end,
            holdout_end=holdout_end,
        )
    return Ok((train_end, validation_end, holdout_end))


def _feature_row_inputs(
    *,
    cleaned: object,
    labeled: object,
    roles: frozenset[str] | set[str],
    peer_features: Mapping[str, Mapping[str, float]] | None,
    design: RegimeClassifierDesign | None,
    contract: ExecutableRegimeContract | None,
) -> Result[
    tuple[
        CleanedCorpus,
        LabeledCorpus,
        frozenset[str],
        tuple[str, ...],
        set[str],
        Mapping[str, Mapping[str, float]],
        bool,
    ]
]:
    if not isinstance(cleaned, CleanedCorpus):
        return invalid(
            "cleaned",
            "feature rows take a CleanedCorpus",
            given=type(cleaned).__name__,
        )
    if not isinstance(labeled, LabeledCorpus):
        return invalid(
            "labeled",
            "feature rows take a LabeledCorpus",
            given=type(labeled).__name__,
        )
    role_set = _feature_role_set(roles)
    if is_refusal(role_set):
        return role_set
    resolved = _resolve_contract(design=design, contract=contract)
    if is_refusal(resolved):
        return resolved
    _design_artifact, resolved_contract = resolved.value
    return Ok(
        (
            cleaned,
            labeled,
            role_set.value,
            resolved_contract.feature_contract.feature_ids,
            set(resolved_contract.feature_contract.peer_mis_inputs),
            peer_features or {},
            peer_features is not None,
        )
    )


def _feature_role_set(roles: frozenset[str] | set[str]) -> Result[frozenset[str]]:
    role_set = frozenset(roles)
    allowed = {
        SegmentRole.TRAIN.value,
        SegmentRole.VALIDATION.value,
        _SPLIT_ROLE_HOLDOUT,
    }
    if not role_set or not role_set.issubset(allowed):
        return invalid(
            "roles",
            "roles is a non-empty subset of train/validation/sealed-test",
            given=sorted(role_set),
        )
    return Ok(role_set)


def _locate_labeled_row(
    labeled_row: LabeledRow,
    *,
    by_id: Mapping[str, CleanedCorpusRow],
    index_by_id: Mapping[str, tuple[str, int]],
) -> Result[tuple[str, int]]:
    if labeled_row.row_id not in by_id:
        return policy(
            "row_id",
            "labeled row must cite a cleaned corpus row",
            row_id=labeled_row.row_id,
        )
    located = index_by_id.get(labeled_row.row_id)
    if located is None:
        return policy(
            "row_id",
            "labeled row missing from instrument index",
            row_id=labeled_row.row_id,
        )
    return Ok(located)


def _cleaned_row_index(
    cleaned: CleanedCorpus,
) -> tuple[
    dict[str, CleanedCorpusRow],
    dict[str, list[CleanedCorpusRow]],
    dict[str, tuple[str, int]],
]:
    by_id = {row.row_id: row for row in cleaned.rows}
    by_instrument = _group_cleaned(cleaned.rows)
    index_by_id: dict[str, tuple[str, int]] = {}
    for instrument, rows in by_instrument.items():
        for index, row in enumerate(rows):
            index_by_id[row.row_id] = (instrument, index)
    return by_id, by_instrument, index_by_id


def _collect_labeled_feature_rows(
    cleaned: CleanedCorpus,
    labeled: LabeledCorpus,
    *,
    role_set: frozenset[str],
    feature_ids: Sequence[str],
    peer_ids: set[str],
    peer_map: Mapping[str, Mapping[str, float]],
    peer_supplied: bool,
) -> Result[tuple[dict[str, tuple[tuple[str, tuple[float, ...], str, str], ...]], int]]:
    by_id, by_instrument, index_by_id = _cleaned_row_index(cleaned)
    buckets: dict[str, list[tuple[str, tuple[float, ...], str, str]]] = {
        role: [] for role in role_set
    }
    excluded = 0
    for labeled_row in labeled.rows:
        appended = _append_labeled_feature_row(
            labeled_row,
            role_set=role_set,
            by_id=by_id,
            by_instrument=by_instrument,
            index_by_id=index_by_id,
            feature_ids=feature_ids,
            peer_ids=peer_ids,
            peer_map=peer_map,
            peer_supplied=peer_supplied,
        )
        if is_refusal(appended):
            return appended
        if appended.value is None:
            if labeled_row.class_label == EXCLUSION_CLASS:
                excluded += 1
            continue
        buckets[labeled_row.split_role].append(appended.value)
    return Ok(({role: tuple(rows) for role, rows in buckets.items()}, excluded))


def _append_labeled_feature_row(
    labeled_row: LabeledRow,
    *,
    role_set: frozenset[str],
    by_id: Mapping[str, CleanedCorpusRow],
    by_instrument: Mapping[str, Sequence[CleanedCorpusRow]],
    index_by_id: Mapping[str, tuple[str, int]],
    feature_ids: Sequence[str],
    peer_ids: set[str],
    peer_map: Mapping[str, Mapping[str, float]],
    peer_supplied: bool,
) -> Result[tuple[str, tuple[float, ...], str, str] | None]:
    if labeled_row.class_label == EXCLUSION_CLASS:
        return Ok(None)
    if labeled_row.class_label not in REGIME_CLASS_VOCABULARY:
        return policy(
            "class_label",
            "labels must stay inside the closed regime vocabulary",
            given=labeled_row.class_label,
        )
    if labeled_row.split_role not in role_set:
        return Ok(None)
    located = _locate_labeled_row(labeled_row, by_id=by_id, index_by_id=index_by_id)
    if is_refusal(located):
        return located
    instrument, index = located.value
    features = _feature_vector(
        by_instrument[instrument],
        index,
        feature_ids=feature_ids,
        peer_ids=peer_ids,
        peer_values=peer_map.get(labeled_row.row_id, {}),
        peer_supplied=peer_supplied,
    )
    if is_refusal(features):
        return features
    return Ok(
        (
            labeled_row.row_id,
            features.value,
            labeled_row.class_label,
            labeled_row.session,
        )
    )


def _group_cleaned(
    rows: Sequence[CleanedCorpusRow],
) -> dict[str, list[CleanedCorpusRow]]:
    grouped: dict[str, list[CleanedCorpusRow]] = {}
    for row in rows:
        grouped.setdefault(row.instrument, []).append(row)
    for instrument_rows in grouped.values():
        instrument_rows.sort(key=lambda item: item.event_time_ns)
    return grouped


def _feature_vector(
    series: Sequence[CleanedCorpusRow],
    index: int,
    *,
    feature_ids: Sequence[str],
    peer_ids: set[str],
    peer_values: Mapping[str, float],
    peer_supplied: bool,
) -> Result[tuple[float, ...]]:
    row = series[index]
    values: list[float] = []
    for feature_id in feature_ids:
        computed = _one_feature_value(
            series,
            index,
            feature_id,
            peer_ids=peer_ids,
            peer_values=peer_values,
            peer_supplied=peer_supplied,
        )
        if is_refusal(computed):
            return computed
        values.append(computed.value)
    if row.knowledge_time_ns < row.event_time_ns:
        return policy(
            "knowledge_time_ns",
            "feature rows refuse future knowledge relative to event time",
            row_id=row.row_id,
        )
    return Ok(tuple(values))


def _one_feature_value(
    series: Sequence[CleanedCorpusRow],
    index: int,
    feature_id: str,
    *,
    peer_ids: set[str],
    peer_values: Mapping[str, float],
    peer_supplied: bool,
) -> Result[float]:
    if feature_id in peer_ids or feature_id in {
        "spread_state_elevated",
        "spread_state_extreme",
        "liquidity_stress",
        "sqs_hard_block",
        "gap_event",
        "feed_state_degraded",
    }:
        return Ok(_peer_or_state_feature(feature_id, peer_values, peer_supplied))
    return _bar_feature(series, index, feature_id)


def _peer_or_state_feature(
    feature_id: str,
    peer_values: Mapping[str, float],
    peer_supplied: bool,
) -> float:
    key = feature_id
    if feature_id.startswith("spread_state_"):
        key = "spread_state"
    elif feature_id == "sqs_hard_block":
        key = "sqs"
    elif feature_id == "feed_state_degraded":
        key = "feed_state"
    if peer_supplied and key in peer_values:
        return float(peer_values[key])
    if peer_supplied and feature_id in peer_values:
        return float(peer_values[feature_id])
    return 0.0


def _bar_feature(
    series: Sequence[CleanedCorpusRow],
    index: int,
    feature_id: str,
) -> Result[float]:
    session = _session_bar_feature(series[index], feature_id)
    if session is not None:
        return Ok(session)
    if feature_id in {"realized_range_pct_20", "realized_range_pct_60"}:
        window = 20 if feature_id.endswith("_20") else 60
        return Ok(_realized_range_pct(series, index, window))
    if feature_id in {"return_z_20", "return_z_60"}:
        window = 20 if feature_id.endswith("_20") else 60
        return Ok(_return_z(series, index, window))
    if feature_id == "atr_ratio_20_60":
        short = _mean_range(series, index, 20)
        long = _mean_range(series, index, 60)
        return Ok(0.0 if long == 0.0 else short / long)
    return policy(
        "feature_id",
        "unknown feature id in the ruled feature contract",
        feature_id=feature_id,
    )


def _session_bar_feature(row: CleanedCorpusRow, feature_id: str) -> float | None:
    if feature_id == "session_asia":
        return 1.0 if row.session == "asia" else 0.0
    if feature_id == "session_london":
        return 1.0 if row.session == "london" else 0.0
    if feature_id == "session_new_york":
        return 1.0 if row.session == "new_york" else 0.0
    if feature_id == "hour_of_session":
        hour = (row.event_time_ns // 3_600_000_000_000) % 24
        return float(hour)
    return None


def _realized_range_pct(
    series: Sequence[CleanedCorpusRow],
    index: int,
    window: int,
) -> float:
    start = max(0, index - window + 1)
    total = 0.0
    count = 0
    for item in series[start : index + 1]:
        if item.close_scaled == 0:
            continue
        span = item.high_scaled - item.low_scaled
        total += span / item.close_scaled
        count += 1
    return total / count if count else 0.0


def _return_z(
    series: Sequence[CleanedCorpusRow],
    index: int,
    window: int,
) -> float:
    start = max(1, index - window + 1)
    returns: list[float] = []
    for cursor in range(start, index + 1):
        prev = series[cursor - 1].close_scaled
        cur = series[cursor].close_scaled
        if prev == 0:
            continue
        returns.append((cur - prev) / prev)
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    var = sum((value - mean) ** 2 for value in returns) / (len(returns) - 1)
    if var <= 0.0:
        return 0.0
    return (returns[-1] - mean) / (var**0.5)


def _mean_range(
    series: Sequence[CleanedCorpusRow],
    index: int,
    window: int,
) -> float:
    start = max(0, index - window + 1)
    chunk = series[start : index + 1]
    if not chunk:
        return 0.0
    return sum(item.high_scaled - item.low_scaled for item in chunk) / len(chunk)


def _bounds_from_config(
    config: TrainingConfig,
    *,
    design: RegimeClassifierDesign | None,
    contract: ExecutableRegimeContract | None,
) -> HyperparameterBounds:
    _ = config
    resolved = _resolve_contract(design=design, contract=contract)
    if is_refusal(resolved):
        return accepted_regime_classifier_design().hyperparameter_bounds
    return resolved.value[1].hyperparameter_bounds


def _draw_hyperparameters(
    rng: random.Random,
    *,
    trial_index: int,
    bounds: HyperparameterBounds,
) -> TrialHyperparameters:
    num_leaves = rng.randint(bounds.num_leaves_min, bounds.num_leaves_max)
    min_data = rng.randint(bounds.min_data_in_leaf_min, bounds.min_data_in_leaf_max)
    # Learning-rate and feature-fraction are exact rationals inside the bounds.
    lr_choices = (
        (bounds.learning_rate_num_min, bounds.learning_rate_den_min),
        (bounds.learning_rate_num_max, bounds.learning_rate_den_max),
        (1, 50),
        (1, 20),
    )
    ff_choices = (
        (bounds.feature_fraction_num_min, bounds.feature_fraction_den_min),
        (bounds.feature_fraction_num_max, bounds.feature_fraction_den_max),
        (8, 10),
        (9, 10),
    )
    lr_num, lr_den = lr_choices[rng.randrange(len(lr_choices))]
    ff_num, ff_den = ff_choices[rng.randrange(len(ff_choices))]
    return TrialHyperparameters(
        trial_index=trial_index,
        num_leaves=num_leaves,
        learning_rate_num=lr_num,
        learning_rate_den=lr_den,
        min_data_in_leaf=min_data,
        feature_fraction_num=ff_num,
        feature_fraction_den=ff_den,
        early_stopping_rounds=bounds.early_stopping_rounds,
    )


def _select_fitter(backend: str) -> Result[FitFn]:
    if backend == TRAINING_BACKEND_DETERMINISTIC:
        return Ok(_deterministic_surrogate_fit)
    if backend == TRAINING_BACKEND_LIGHTGBM:
        try:
            import lightgbm  # noqa: PLC0415  # pyright: ignore[reportMissingImports]

            _ = lightgbm
        except ImportError:
            return policy(
                "backend",
                "lightgbm backend requested but lightgbm is not installed on this "
                "operator machine; install locally or use deterministic-surrogate "
                "for rehearsal",
                failure_id="mis.regime_train.lightgbm_missing",
            )
        return Ok(_lightgbm_fit)
    return invalid("backend", "unknown training backend", given=backend)


def _deterministic_surrogate_fit(
    train_rows: Sequence[_TrainRow],
    context: Mapping[str, object],
    seed: int,
) -> tuple[str, int, int]:
    """Fast, seed-stable surrogate that writes lightgbm-text-shaped bytes.

    Used for operator rehearsals and tests. Never opens network or credentials.
    Validation score is a deterministic fold over validation_rows when present.
    """
    hyper, feature_ids, vocabulary, validation_rows = _surrogate_context(context)
    payload = {
        "class": "qmx-deterministic-surrogate-lightgbm-text",
        "seed": seed,
        "hyperparameters": dict(hyper),
        "feature_ids": feature_ids,
        "class_vocabulary": vocabulary,
        "train_row_ids": [row[0] for row in train_rows],
        "train_labels": [row[2] for row in train_rows],
        "train_features": [list(row[1]) for row in train_rows],
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    lines = [
        "qmx_deterministic_surrogate_lightgbm_text_v1",
        f"seed={seed}",
        f"digest={digest}",
        f"num_leaves={hyper.get('num_leaves')}",
        f"classes={','.join(vocabulary)}",
        f"features={','.join(feature_ids)}",
        f"train_rows={len(train_rows)}",
    ]
    score = _surrogate_validation_score(train_rows, validation_rows, seed=seed, hyper=hyper)
    return "\n".join(lines) + "\n", score, score


def _surrogate_context(
    context: Mapping[str, object],
) -> tuple[Mapping[str, object], list[str], list[str], tuple[_TrainRow, ...]]:
    hyper_obj = context.get("hyperparameters", {})
    hyper: Mapping[str, object] = (
        cast("Mapping[str, object]", hyper_obj) if isinstance(hyper_obj, Mapping) else {}
    )
    return (
        hyper,
        _string_sequence(context.get("feature_ids", [])),
        _class_vocabulary_from_context(context),
        _train_rows_from_context(context.get("validation_rows")),
    )


def _class_vocabulary_from_context(context: Mapping[str, object]) -> list[str]:
    vocab_obj = context.get("class_vocabulary", list(REGIME_CLASS_VOCABULARY))
    if isinstance(vocab_obj, Sequence) and not isinstance(vocab_obj, (str, bytes)):
        return [str(item) for item in cast("Sequence[object]", vocab_obj)]
    return list(REGIME_CLASS_VOCABULARY)


def _string_sequence(value: object) -> list[str]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [str(item) for item in cast("Sequence[object]", value)]
    return []


def _train_rows_from_context(value: object) -> tuple[_TrainRow, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(
            cast("_TrainRow", row)
            for row in cast("Sequence[object]", value)
            if isinstance(row, tuple) and len(cast("tuple[object, ...]", row)) >= 3
        )
    return ()


def _surrogate_validation_score(
    train_rows: Sequence[_TrainRow],
    validation_rows: Sequence[_TrainRow],
    *,
    seed: int,
    hyper: Mapping[str, object],
) -> int:
    """Deterministic ppb score in ``[0, 1_000_000_000]`` for trial ranking."""
    if not validation_rows:
        material = f"{seed}:{len(train_rows)}:{sorted(hyper.items())}"
        digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % 1_000_000_000
    # Majority label from train; reward validation agreement plus hyper hash.
    counts: dict[str, int] = {}
    for row in train_rows:
        counts[row[2]] = counts.get(row[2], 0) + 1
    majority = max(counts.items(), key=lambda item: (item[1], item[0]))[0] if counts else ""
    agree = 0
    total = 0
    for row in validation_rows:
        total += 1
        if row[2] == majority:
            agree += 1
    base = (agree * 1_000_000_000 // total) if total else 0
    twist = int(hashlib.sha256(f"{seed}:{hyper}".encode()).hexdigest()[:4], 16)
    return min(1_000_000_000, base + twist)


def _lightgbm_fit(
    train_rows: Sequence[_TrainRow],
    context: Mapping[str, object],
    seed: int,
) -> tuple[str, int, int]:
    """Lazy LightGBM fit for a real operator-machine run (hours-scale data)."""
    import lightgbm as lgb  # noqa: PLC0415  # pyright: ignore[reportMissingImports]

    hyper_obj = context.get("hyperparameters", {})
    if not isinstance(hyper_obj, Mapping):
        raise TypeError("hyperparameters mapping required")
    hyper = cast("Mapping[str, object]", hyper_obj)
    vocabulary = _class_vocabulary_from_context(context)
    label_to_index = {name: index for index, name in enumerate(vocabulary)}
    x_train = [list(row[1]) for row in train_rows]
    y_train = [label_to_index[row[2]] for row in train_rows]
    x_valid, y_valid = _lightgbm_validation_xy(context.get("validation_rows"), label_to_index)
    booster = _lightgbm_train(lgb, hyper, seed, vocabulary, x_train, y_train, x_valid, y_valid)
    score = _lightgbm_accuracy_ppb(booster, x_valid, y_valid)
    return str(booster.model_to_string()), score, score


def _lightgbm_validation_xy(
    validation_obj: object,
    label_to_index: Mapping[str, int],
) -> tuple[list[list[float]], list[int]]:
    x_valid: list[list[float]] = []
    y_valid: list[int] = []
    if not isinstance(validation_obj, Sequence) or isinstance(validation_obj, (str, bytes)):
        return x_valid, y_valid
    for row_obj in cast("Sequence[object]", validation_obj):
        if not isinstance(row_obj, tuple):
            continue
        row = cast("tuple[object, ...]", row_obj)
        if len(row) < 3:
            continue
        features = row[1]
        if not isinstance(features, (tuple, list)):
            continue
        x_valid.append([_coerce_float(value) for value in cast("Sequence[object]", features)])
        y_valid.append(label_to_index[str(row[2])])
    return x_valid, y_valid


def _lightgbm_train(
    lgb_api: Any,
    hyper: Mapping[str, object],
    seed: int,
    vocabulary: Sequence[str],
    x_train: Sequence[Sequence[float]],
    y_train: Sequence[int],
    x_valid: Sequence[Sequence[float]],
    y_valid: Sequence[int],
) -> Any:
    train_set = lgb_api.Dataset(x_train, label=y_train, free_raw_data=False)
    valid_set = (
        lgb_api.Dataset(x_valid, label=y_valid, reference=train_set, free_raw_data=False)
        if x_valid
        else None
    )
    params = {
        "objective": "multiclass",
        "num_class": len(vocabulary),
        "num_leaves": _coerce_int(hyper.get("num_leaves", 31)),
        "learning_rate": _rational_or_default(hyper.get("learning_rate", [1, 100]), 0.05),
        "min_data_in_leaf": _coerce_int(hyper.get("min_data_in_leaf", 20)),
        "feature_fraction": _rational_or_default(hyper.get("feature_fraction", [1, 1]), 1.0),
        "verbosity": -1,
        "seed": seed,
        "deterministic": True,
        "force_row_wise": True,
    }
    callbacks: list[Any] = []
    early = hyper.get("early_stopping_rounds")
    if valid_set is not None and isinstance(early, int) and early > 0:
        callbacks.append(lgb_api.early_stopping(early, verbose=False))
    return lgb_api.train(
        params,
        train_set,
        num_boost_round=200,
        valid_sets=[valid_set] if valid_set is not None else None,
        callbacks=callbacks or None,
    )


def _rational_or_default(value: object, default: float) -> float:
    if not isinstance(value, list):
        return default
    pair = cast("list[object]", value)
    if len(pair) != 2:
        return default
    return _coerce_float(pair[0]) / _coerce_float(pair[1])


def _lightgbm_accuracy_ppb(
    booster: Any,
    x_valid: Sequence[Sequence[float]],
    y_valid: Sequence[int],
) -> int:
    if not x_valid:
        return 0
    preds = cast("Sequence[Sequence[float]]", booster.predict(x_valid))
    correct = 0
    for index, row in enumerate(preds):
        predicted = max(range(len(row)), key=lambda i, current=row: current[i])
        if predicted == y_valid[index]:
            correct += 1
    return (correct * 1_000_000_000) // max(1, len(y_valid))


def _matrix_payload_fp(
    train_rows: Sequence[tuple[str, tuple[float, ...], str]],
    validation_rows: Sequence[tuple[str, tuple[float, ...], str]],
) -> str:
    """SHA-256 over quantized feature payloads (fp1-safe; no bare floats)."""
    parts: list[str] = []
    for role, rows in (("train", train_rows), ("validation", validation_rows)):
        for row_id, features, label in rows:
            quantized = ",".join(f"{value:.12g}" for value in features)
            parts.append(f"{role}:{row_id}:{label}:{quantized}")
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return f"fp1:sha256:{digest}"


def _training_code_fp() -> Result[Fingerprint]:
    return fingerprint(
        {
            "class": "regime-training-code",
            "surface": REGIME_TRAIN_SURFACE,
            "artifact_id": REGIME_TRAIN_ARTIFACT_ID,
            "format_version": REGIME_TRAIN_FORMAT_VERSION,
            "rng_algorithm": RNG_ALGORITHM,
            "chosen_family": CHOSEN_MODEL_FAMILY,
            "training_location": TRAINING_LOCATION,
        }
    )


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _probe_memory_total_bytes() -> int | None:
    if sys.platform == "win32":
        try:
            import ctypes  # noqa: PLC0415

            class _MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = _MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return int(stat.ullTotalPhys)
        except (AttributeError, OSError, ValueError):
            return None
        return None
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return int(pages * page_size)
    except (AttributeError, OSError, ValueError):
        return None


def _probe_peak_rss_bytes() -> int | None:
    """Best-effort process RSS; None when the host cannot report it."""
    if sys.platform == "win32":
        try:
            import ctypes  # noqa: PLC0415
            from ctypes import wintypes  # noqa: PLC0415

            class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = _PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(_PROCESS_MEMORY_COUNTERS)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            if ctypes.windll.psapi.GetProcessMemoryInfo(
                handle, ctypes.byref(counters), counters.cb
            ):
                return int(counters.PeakWorkingSetSize)
        except (AttributeError, OSError, ValueError):
            return None
        return None
    try:
        import resource as resource_mod  # noqa: PLC0415

        usage = resource_mod.getrusage(resource_mod.RUSAGE_SELF).ru_maxrss
        # Linux reports KiB; macOS reports bytes.
        if sys.platform == "darwin":
            return int(usage)
        return int(usage) * 1024
    except (AttributeError, OSError, ValueError, ImportError):
        return None


def _worktree_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "uv.lock").is_file() or (parent / "uv.lock").is_symlink():
            return parent
    return here.parents[4]


def _resolve_lock_path(lock_path: object | None) -> Path | None:
    if lock_path is not None:
        token = clean_token(lock_path)
        if token is None:
            return None
        path = Path(token)
        return path if path.is_symlink() or path.is_file() else None
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "uv.lock"
        if candidate.is_symlink() or candidate.is_file():
            return candidate
    return None


def _posix_rel(path: Path) -> str:
    try:
        return path.resolve().as_posix()
    except OSError:
        return path.as_posix()


def _output_dir_refusal(
    path: Path,
    *,
    given: object | None = None,
    errno: object | None = None,
) -> TypedRefusal:
    extra: dict[str, object] = {
        "path": str(path),
        "failure_id": "mis.regime_train.output_dir",
    }
    if given is not None:
        extra["given"] = given
    if errno is not None:
        extra["errno"] = errno
    return policy(
        "output_dir",
        "training output directory is not writable",
        **extra,
    )


def _map_output_dir(result: Result[None], path: Path) -> Result[None]:
    if not is_refusal(result):
        return result
    return _output_dir_refusal(path, given=result.context.get("reason"))


def _contained_pair(path: Path, contain_within: Path) -> Result[tuple[Path, Path]]:
    try:
        resolved = Path(os.path.realpath(path))
        root_real = Path(os.path.realpath(contain_within))
    except OSError as exc:
        return _output_dir_refusal(
            path, given=type(exc).__name__, errno=getattr(exc, "errno", None)
        )
    if path.is_symlink() or not resolved.is_relative_to(root_real):
        return _output_dir_refusal(path, given="symlink-or-escape")
    return Ok((resolved, root_real))


def _ensure_contained_dir(path: Path, *, contain_within: Path) -> Result[None]:
    contained = _contained_pair(path, contain_within)
    if is_refusal(contained):
        return contained
    try:
        path.mkdir(  # skylos: ignore[SKY-D215] contained, no-follow
            parents=True,
            exist_ok=True,
        )
    except OSError as exc:
        return _output_dir_refusal(
            path, given=type(exc).__name__, errno=getattr(exc, "errno", None)
        )
    return Ok(None)


def _unlink_contained_regular(
    path: Path,
    *,
    contain_within: Path,
    missing_ok: bool = False,
) -> Result[None]:
    contained = _contained_pair(path, contain_within)
    if is_refusal(contained):
        return contained
    if not path.exists() and not path.is_symlink():
        if missing_ok:
            return Ok(None)
        return _output_dir_refusal(path, given="missing")
    if path.is_symlink() or not path.is_file():
        return _output_dir_refusal(path, given="symlink-or-non-regular")
    try:
        os.unlink(path)  # skylos: ignore[SKY-D215] contained, no-follow
    except OSError as exc:
        return _output_dir_refusal(
            path, given=type(exc).__name__, errno=getattr(exc, "errno", None)
        )
    return Ok(None)


def _write_contained_bytes(
    path: Path,
    data: bytes,
    *,
    contain_within: Path,
) -> Result[None]:
    unlinked = _unlink_contained_regular(path, contain_within=contain_within, missing_ok=True)
    if is_refusal(unlinked):
        return unlinked
    written = write_bytes_exclusive_no_follow(
        path, data, contain_within=contain_within, field="output_dir"
    )
    return _map_output_dir(written, path)


def _write_json(
    path: Path,
    payload: Mapping[str, object],
    *,
    contain_within: Path,
) -> Result[None]:
    data = (json.dumps(dict(payload), indent=2, sort_keys=True) + "\n").encode("utf-8")
    return _write_contained_bytes(path, data, contain_within=contain_within)


def _append_jsonl(
    path: Path,
    payload: Mapping[str, object],
    *,
    contain_within: Path,
) -> Result[None]:
    data = (json.dumps(dict(payload), sort_keys=True) + "\n").encode("utf-8")
    appended = append_bytes_no_follow(path, data, contain_within=contain_within, field="output_dir")
    return _map_output_dir(appended, path)


def _persist_record(out_root: Path, record: TrainingRecord) -> Result[None]:
    return _write_json(
        out_root / _RECORD_FILENAME,
        record.as_jsonable(),
        contain_within=out_root,
    )


def _resolve_clock_ns(clock_ns: object) -> Callable[[], int]:
    """Bind an injected nanosecond clock reader; default is a no-op clock."""
    if callable(clock_ns):
        return cast("Callable[[], int]", clock_ns)
    return lambda: 0


def _elapsed_ms(started_ns: int, clock_ns: Callable[[], int]) -> int:
    return max(0, (clock_ns() - started_ns) // 1_000_000)


def _coerce_int(value: object) -> int:
    if isinstance(value, bool):
        raise TypeError("bool is not an int")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value)
    raise TypeError(type(value).__name__)


def _coerce_float(value: object) -> float:
    if isinstance(value, bool):
        raise TypeError("bool is not a float")
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        return float(value)
    raise TypeError(type(value).__name__)


def _load_checkpoint(out_root: Path) -> Result[TrainingCheckpoint | None]:
    payload = _read_checkpoint_payload(out_root)
    if is_refusal(payload):
        return payload
    if payload.value is None:
        return Ok(None)
    checkpoint = _checkpoint_from_payload(payload.value, out_root)
    if is_refusal(checkpoint):
        return checkpoint
    return Ok(checkpoint.value)


def _read_checkpoint_payload(out_root: Path) -> Result[dict[str, object] | None]:
    path = out_root / _CHECKPOINT_FILENAME
    if path.is_symlink():
        return _output_dir_refusal(path, given="symlink")
    if not path.is_file():
        return Ok(None)
    loaded = read_contained_text(
        path,
        contain_within=out_root,
        max_bytes=MAX_JSONL_BYTES,
        field="output_dir",
    )
    if is_refusal(loaded):
        return _output_dir_refusal(path, given=loaded.context.get("reason"))
    try:
        raw = json.loads(loaded.value)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return policy(
            "checkpoint",
            "checkpoint is not readable JSON",
            path=str(path),
            failure_id="mis.regime_train.checkpoint",
        )
    if not isinstance(raw, dict):
        return policy(
            "checkpoint",
            "checkpoint payload must be an object",
            failure_id="mis.regime_train.checkpoint",
        )
    return Ok(cast("dict[str, object]", raw))


def _checkpoint_from_payload(
    payload: Mapping[str, object],
    out_root: Path,
) -> Result[TrainingCheckpoint]:
    if payload.get("registerable") is True:
        return refuse_partial_model_registration(status="checkpoint-file")
    fps = _checkpoint_fingerprints(payload)
    if is_refusal(fps):
        return fps
    config_fp, code_fp, matrix_fp = fps.value
    trials = _checkpoint_trials(payload.get("completed_trials", []))
    if is_refusal(trials):
        return trials
    next_index = payload.get("next_trial_index")
    if not isinstance(next_index, int) or isinstance(next_index, bool):
        return policy(
            "checkpoint",
            "next_trial_index must be an int",
            failure_id="mis.regime_train.checkpoint",
        )
    return Ok(
        TrainingCheckpoint(
            config_fp=config_fp,
            code_fp=code_fp,
            matrix_fp=matrix_fp,
            completed_trials=tuple(trials.value),
            next_trial_index=next_index,
            best_trial_index=_optional_int(payload.get("best_trial_index")),
            best_validation_score_ppb=_optional_int(payload.get("best_validation_score_ppb")),
            registerable=False,
            output_dir=str(payload.get("output_dir", out_root.as_posix())),
        )
    )


def _checkpoint_fingerprints(
    payload: Mapping[str, object],
) -> Result[tuple[Fingerprint, Fingerprint, Fingerprint]]:
    config_fp = Fingerprint.try_create(payload.get("config_fp"))
    if is_refusal(config_fp):
        return _checkpoint_fp_refusal()
    code_fp = Fingerprint.try_create(payload.get("code_fp"))
    if is_refusal(code_fp):
        return _checkpoint_fp_refusal()
    matrix_fp = Fingerprint.try_create(payload.get("matrix_fp"))
    if is_refusal(matrix_fp):
        return _checkpoint_fp_refusal()
    return Ok((config_fp.value, code_fp.value, matrix_fp.value))


def _checkpoint_fp_refusal() -> TypedRefusal:
    return policy(
        "checkpoint",
        "checkpoint fingerprints must be fp1 values",
        failure_id="mis.regime_train.checkpoint",
    )


def _checkpoint_trials(trials_raw: object) -> Result[list[TrialRecord]]:
    if not isinstance(trials_raw, list):
        return policy(
            "checkpoint",
            "completed_trials must be a list",
            failure_id="mis.regime_train.checkpoint",
        )
    trials: list[TrialRecord] = []
    for item in cast("list[object]", trials_raw):
        parsed = _trial_from_jsonable(item)
        if is_refusal(parsed):
            return parsed
        trials.append(parsed.value)
    return Ok(trials)


def _optional_int(value: object) -> int | None:
    resolved = value if isinstance(value, int) or value is None else None
    if isinstance(resolved, bool):
        return None
    return resolved


def _trial_from_jsonable(raw: object) -> Result[TrialRecord]:
    if not isinstance(raw, dict):
        return policy(
            "trial",
            "trial record must be an object",
            failure_id="mis.regime_train.checkpoint",
        )
    payload = cast("dict[str, object]", raw)
    hyper = _hyper_from_jsonable(payload.get("hyperparameters"))
    if is_refusal(hyper):
        return hyper
    try:
        model_fp_obj = payload.get("model_bytes_fp")
        model_bytes_fp = (
            model_fp_obj if model_fp_obj is None or isinstance(model_fp_obj, str) else None
        )
        trial = TrialRecord(
            trial_index=_coerce_int(payload["trial_index"]),
            hyperparameters=hyper.value,
            validation_score_ppb=_coerce_int(payload["validation_score_ppb"]),
            status=str(payload["status"]),
            model_bytes_fp=model_bytes_fp,
            elapsed_ms=_coerce_int(payload["elapsed_ms"]),
        )
    except (KeyError, TypeError, ValueError):
        return policy(
            "trial",
            "trial record fields are malformed",
            failure_id="mis.regime_train.checkpoint",
        )
    return Ok(trial)


def _hyper_from_jsonable(raw: object) -> Result[TrialHyperparameters]:
    if not isinstance(raw, dict):
        return policy(
            "trial",
            "trial hyperparameters must be an object",
            failure_id="mis.regime_train.checkpoint",
        )
    hyper_raw = cast("dict[str, object]", raw)
    lr_obj = hyper_raw.get("learning_rate", [1, 100])
    ff_obj = hyper_raw.get("feature_fraction", [1, 1])
    if not isinstance(lr_obj, list) or not isinstance(ff_obj, list):
        return policy(
            "trial",
            "trial rational hyperparameters must be [num, den] pairs",
            failure_id="mis.regime_train.checkpoint",
        )
    lr = cast("list[object]", lr_obj)
    ff = cast("list[object]", ff_obj)
    if len(lr) != 2 or len(ff) != 2:
        return policy(
            "trial",
            "trial rational hyperparameters must be [num, den] pairs",
            failure_id="mis.regime_train.checkpoint",
        )
    try:
        return Ok(
            TrialHyperparameters(
                trial_index=_coerce_int(hyper_raw["trial_index"]),
                num_leaves=_coerce_int(hyper_raw["num_leaves"]),
                learning_rate_num=_coerce_int(lr[0]),
                learning_rate_den=_coerce_int(lr[1]),
                min_data_in_leaf=_coerce_int(hyper_raw["min_data_in_leaf"]),
                feature_fraction_num=_coerce_int(ff[0]),
                feature_fraction_den=_coerce_int(ff[1]),
                early_stopping_rounds=_coerce_int(hyper_raw["early_stopping_rounds"]),
            )
        )
    except (KeyError, TypeError, ValueError):
        return policy(
            "trial",
            "trial record fields are malformed",
            failure_id="mis.regime_train.checkpoint",
        )


def _terminal_record(
    *,
    status: TrainingTerminalStatus,
    cause: str,
    config: TrainingConfig,
    config_fp: Fingerprint,
    code_fp: Fingerprint,
    lock: DependencyLockRecord,
    machine: MachineEnvironment,
    start_utc: str,
    start_mono_ns: int,
    clock_ns: Callable[[], int],
    trials: tuple[TrialRecord, ...],
    best_trial_index: int | None,
    model_path: str | None,
    model_fp: str | None,
    registerable: bool,
) -> TrainingRecord:
    end_utc = _utc_now()
    elapsed_ms = _elapsed_ms(start_mono_ns, clock_ns)
    locations = _record_output_locations(config.output_dir, model_path)
    return TrainingRecord(
        artifact_id=REGIME_TRAIN_ARTIFACT_ID,
        status=status,
        cause=cause,
        config_fp=config_fp,
        code_fp=code_fp,
        dependency_lock=lock,
        machine=machine,
        rng_algorithm=config.rng_algorithm,
        seed=config.seed,
        data_window_start_ns=config.data_window_start_ns,
        data_window_end_ns=config.data_window_end_ns,
        train_end_ns=config.train_end_ns,
        validation_end_ns=config.validation_end_ns,
        holdout_end_ns=config.holdout_end_ns,
        start_time_utc=start_utc,
        end_time_utc=end_utc,
        elapsed_ms=elapsed_ms,
        peak_rss_bytes=_probe_peak_rss_bytes(),
        trials=trials,
        best_trial_index=best_trial_index,
        output_locations=locations,
        model_path=model_path,
        model_fp=model_fp,
        registerable=registerable and status is TrainingTerminalStatus.COMPLETED,
        grants_money_path_authority=False,
        grants_governed_binding=False,
    )


def _record_output_locations(output_dir: str, model_path: str | None) -> dict[str, str]:
    locations = {
        "output_dir": output_dir,
        "config": f"{output_dir}/{_CONFIG_FILENAME}",
        "record": f"{output_dir}/{_RECORD_FILENAME}",
        "trials": f"{output_dir}/{_TRIALS_FILENAME}",
    }
    if model_path is not None:
        locations["model"] = model_path
    return locations


if __name__ == "__main__":
    raise SystemExit(main())
