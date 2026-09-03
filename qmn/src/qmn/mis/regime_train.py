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
from qmn.mis.regime_labels import EXCLUSION_CLASS, LabeledCorpus

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
        payload = path.read_bytes()
    except OSError as exc:
        return unavailable_lock(path, exc)
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

    resolved = _resolve_contract(design=design, contract=contract)
    if is_refusal(resolved):
        return resolved
    design_artifact, resolved_contract = resolved.value
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

    cmd: tuple[str, ...]
    if command is None:
        cmd = ("python", "-m", "qmn.mis.regime_train", "--output-dir", out)
    elif isinstance(command, Sequence) and not isinstance(command, (str, bytes)):
        tokens = tuple(str(item) for item in cast("Sequence[object]", command))
        if not tokens:
            return invalid("command", "command is a non-empty argv sequence")
        cmd = tokens
    else:
        return invalid("command", "command is an argv sequence", given=type(command).__name__)

    sessions = tuple(sorted({row.session for row in cleaned.rows}))
    if set(sessions) != set(DECLARED_TRADING_SESSIONS):
        return policy(
            "sessions",
            "training data must cover asia, london, and new_york exactly",
            given=list(sessions),
            required=list(DECLARED_TRADING_SESSIONS),
            failure_id="mis.regime_train.session_coverage",
        )

    return Ok(
        TrainingConfig(
            design_fp=resolved_contract.design_fp,
            contract_fp=contract_fp.value,
            labeled_fp=labeled_fp.value,
            cleaned_fp=cleaned_fp.value,
            splits_fp=labeled.splits_fp,
            data_window_start_ns=start_ns,
            data_window_end_ns=end_ns,
            train_end_ns=train_end,
            validation_end_ns=validation_end,
            holdout_end_ns=holdout_end,
            sessions=tuple(DECLARED_TRADING_SESSIONS),
            rng_algorithm=RNG_ALGORITHM,
            seed=seed,
            backend=backend_token,
            max_trials=trial_cap,
            output_dir=out,
            command=cmd,
            allow_live_network=False,
            allow_vps_or_cloud=False,
            allow_broker_or_node_credential=False,
            grants_money_path_authority=False,
        )
    )


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
    if not isinstance(cleaned, CleanedCorpus):
        return invalid(
            "cleaned",
            "training matrix takes a CleanedCorpus",
            given=type(cleaned).__name__,
        )
    if not isinstance(labeled, LabeledCorpus):
        return invalid(
            "labeled",
            "training matrix takes a LabeledCorpus",
            given=type(labeled).__name__,
        )
    resolved = _resolve_contract(design=design, contract=contract)
    if is_refusal(resolved):
        return resolved
    _design_artifact, resolved_contract = resolved.value
    feature_ids = resolved_contract.feature_contract.feature_ids
    peer_ids = set(resolved_contract.feature_contract.peer_mis_inputs)
    peer_map = peer_features or {}
    peer_supplied = peer_features is not None

    by_id = {row.row_id: row for row in cleaned.rows}
    by_instrument = _group_cleaned(cleaned.rows)
    index_by_id: dict[str, tuple[str, int]] = {}
    for instrument, rows in by_instrument.items():
        for index, row in enumerate(rows):
            index_by_id[row.row_id] = (instrument, index)

    train_rows: list[tuple[str, tuple[float, ...], str]] = []
    validation_rows: list[tuple[str, tuple[float, ...], str]] = []
    excluded = 0
    sealed = 0
    for labeled_row in labeled.rows:
        if labeled_row.class_label == EXCLUSION_CLASS:
            excluded += 1
            continue
        if labeled_row.class_label not in REGIME_CLASS_VOCABULARY:
            return policy(
                "class_label",
                "training labels must stay inside the closed regime vocabulary",
                given=labeled_row.class_label,
            )
        if labeled_row.split_role == _SPLIT_ROLE_HOLDOUT:
            sealed += 1
            continue
        cleaned_row = by_id.get(labeled_row.row_id)
        if cleaned_row is None:
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
        instrument, index = located
        series = by_instrument[instrument]
        peer = peer_map.get(labeled_row.row_id, {})
        features = _feature_vector(
            series,
            index,
            feature_ids=feature_ids,
            peer_ids=peer_ids,
            peer_values=peer,
            peer_supplied=peer_supplied,
        )
        if is_refusal(features):
            return features
        item = (labeled_row.row_id, features.value, labeled_row.class_label)
        if labeled_row.split_role == SegmentRole.TRAIN.value:
            train_rows.append(item)
        elif labeled_row.split_role == SegmentRole.VALIDATION.value:
            validation_rows.append(item)
        else:
            return policy(
                "split_role",
                "training matrix admits only train/validation/sealed-test roles",
                given=labeled_row.split_role,
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
    return Ok(
        PreparedTrainingMatrix(
            feature_ids=feature_ids,
            class_vocabulary=REGIME_CLASS_VOCABULARY,
            train_rows=tuple(train_rows),
            validation_rows=tuple(validation_rows),
            excluded_count=excluded,
            sealed_holdout_count=sealed,
            sealed_holdout_unused=True,
            peer_features_supplied=peer_supplied,
        )
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
    """Run or resume the bounded offline training script.

    Returns a ``TrainingArtifact`` on ``completed``, otherwise the terminal
    ``TrainingRecord`` (``aborted`` / ``refused``). Never executes a multi-hour
    cloud/VPS job; the deterministic surrogate backend finishes in-process for
    tests and dry operator rehearsals. LightGBM is optional and imported lazily.
    Duration comes from an injected nanosecond clock reader — never the host
    clock below the composition root.
    """
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

    code_fp = _training_code_fp()
    if is_refusal(code_fp):
        return code_fp
    config_fp = config.value.fingerprint()
    if is_refusal(config_fp):
        return config_fp

    out_root = Path(config.value.output_dir)
    try:
        out_root.mkdir(parents=True, exist_ok=True)
        _write_json(out_root / _CONFIG_FILENAME, config.value.fp1_identity())
    except OSError as exc:
        return policy(
            "output_dir",
            "training output directory is not writable",
            path=str(out_root),
            errno=getattr(exc, "errno", None),
            failure_id="mis.regime_train.output_dir",
        )

    matrix = build_training_matrix(
        cleaned,
        labeled,
        peer_features=peer_features,
        design=design,
        contract=contract,
    )
    if is_refusal(matrix):
        record = _terminal_record(
            status=TrainingTerminalStatus.REFUSED,
            cause=str(matrix.context.get("reason", "matrix refused")),
            config=config.value,
            config_fp=config_fp.value,
            code_fp=code_fp.value,
            lock=lock.value,
            machine=machine,
            start_utc=start_utc,
            start_mono_ns=start_mono_ns,
            clock_ns=mono,
            trials=(),
            best_trial_index=None,
            model_path=None,
            model_fp=None,
            registerable=False,
        )
        _persist_record(out_root, record)
        return Ok(record)

    matrix_fp = matrix.value.fingerprint()
    if is_refusal(matrix_fp):
        return matrix_fp

    completed: list[TrialRecord] = []
    best_index: int | None = None
    best_score: int | None = None
    best_model_text: str | None = None
    start_trial = 0

    if resume is True:
        loaded = _load_checkpoint(out_root)
        if is_refusal(loaded):
            record = _terminal_record(
                status=TrainingTerminalStatus.REFUSED,
                cause=str(loaded.context.get("reason", "checkpoint refused")),
                config=config.value,
                config_fp=config_fp.value,
                code_fp=code_fp.value,
                lock=lock.value,
                machine=machine,
                start_utc=start_utc,
                start_mono_ns=start_mono_ns,
                clock_ns=mono,
                trials=(),
                best_trial_index=None,
                model_path=None,
                model_fp=None,
                registerable=False,
            )
            _persist_record(out_root, record)
            return Ok(record)
        if loaded.value is not None:
            checkpoint = loaded.value
            if checkpoint.config_fp.value != config_fp.value.value:
                return refuse_reproducibility_mismatch(
                    expected_fp=checkpoint.config_fp.value,
                    observed_fp=config_fp.value.value,
                )
            if checkpoint.registerable:
                return refuse_partial_model_registration(status="checkpoint-registerable")
            completed = list(checkpoint.completed_trials)
            start_trial = checkpoint.next_trial_index
            best_index = checkpoint.best_trial_index
            best_score = checkpoint.best_validation_score_ppb
            if best_index is not None:
                prior = out_root / "trials" / f"trial_{best_index:04d}" / _MODEL_FILENAME
                if prior.is_file():
                    best_model_text = prior.read_text(encoding="utf-8")
    elif resume not in (False, None):
        return invalid("resume", "resume is a bool", given=repr(resume))

    if (
        abort_after_trials is not None
        and (
            not isinstance(abort_after_trials, int)
            or isinstance(abort_after_trials, bool)
            or abort_after_trials < 0
        )
    ):
        return invalid(
            "abort_after_trials",
            "abort_after_trials is a non-negative int when set",
            given=repr(abort_after_trials),
        )

    if fit_fn is not None:
        fitter: Result[FitFn] = Ok(fit_fn)
    else:
        fitter = _select_fitter(config.value.backend)
    if is_refusal(fitter):
        record = _terminal_record(
            status=TrainingTerminalStatus.REFUSED,
            cause=str(fitter.context.get("reason", "fitter refused")),
            config=config.value,
            config_fp=config_fp.value,
            code_fp=code_fp.value,
            lock=lock.value,
            machine=machine,
            start_utc=start_utc,
            start_mono_ns=start_mono_ns,
            clock_ns=mono,
            trials=tuple(completed),
            best_trial_index=best_index,
            model_path=None,
            model_fp=None,
            registerable=False,
        )
        _persist_record(out_root, record)
        return Ok(record)

    # Declared reproducible search RNG (NFR-03) — not a cryptographic source.
    rng = random.Random(config.value.seed)  # noqa: S311
    bounds = _bounds_from_config(config.value, design=design, contract=contract)
    # Advance RNG to the resume point so later draws match a fresh run.
    for trial_index in range(start_trial):
        _draw_hyperparameters(rng, trial_index=trial_index, bounds=bounds)

    trials_path = out_root / _TRIALS_FILENAME
    if start_trial == 0 and trials_path.exists():
        trials_path.unlink()

    aborted = False
    abort_cause = "operator-abort-after-trials"
    train_payload = tuple(
        (row[0], row[1], row[2]) for row in matrix.value.train_rows
    )
    valid_payload = tuple(
        (row[0], row[1], row[2]) for row in matrix.value.validation_rows
    )
    for trial_index in range(start_trial, config.value.max_trials):
        if abort_after_trials is not None and len(completed) >= abort_after_trials:
            aborted = True
            break
        params = _draw_hyperparameters(rng, trial_index=trial_index, bounds=bounds)
        trial_started_ns = mono()
        try:
            model_text, score_ppb, _train_score = fitter.value(
                train_payload,
                {
                    "validation_rows": valid_payload,
                    "feature_ids": list(matrix.value.feature_ids),
                    "class_vocabulary": list(matrix.value.class_vocabulary),
                    "hyperparameters": params.as_mapping(),
                    "seed": config.value.seed,
                    "backend": config.value.backend,
                },
                config.value.seed + trial_index,
            )
        except Exception as exc:
            aborted = True
            abort_cause = f"trial-fit-failed:{type(exc).__name__}"
            elapsed_ms = _elapsed_ms(trial_started_ns, mono)
            completed.append(
                TrialRecord(
                    trial_index=trial_index,
                    hyperparameters=params,
                    validation_score_ppb=0,
                    status="aborted",
                    model_bytes_fp=None,
                    elapsed_ms=elapsed_ms,
                )
            )
            break

        model_digest = hashlib.sha256(model_text.encode("utf-8")).hexdigest()
        model_fp_value = f"fp1:sha256:{model_digest}"
        elapsed_ms = _elapsed_ms(trial_started_ns, mono)
        trial = TrialRecord(
            trial_index=trial_index,
            hyperparameters=params,
            validation_score_ppb=score_ppb,
            status="completed",
            model_bytes_fp=model_fp_value,
            elapsed_ms=elapsed_ms,
        )
        completed.append(trial)
        trial_dir = out_root / "trials" / f"trial_{trial_index:04d}"
        trial_dir.mkdir(parents=True, exist_ok=True)
        (trial_dir / _MODEL_FILENAME).write_text(model_text, encoding="utf-8")
        _append_jsonl(trials_path, trial.fp1_identity())
        if best_score is None or score_ppb > best_score:
            best_score = score_ppb
            best_index = trial_index
            best_model_text = model_text

        checkpoint = TrainingCheckpoint(
            config_fp=config_fp.value,
            code_fp=code_fp.value,
            matrix_fp=matrix_fp.value,
            completed_trials=tuple(completed),
            next_trial_index=trial_index + 1,
            best_trial_index=best_index,
            best_validation_score_ppb=best_score,
            registerable=False,
            output_dir=config.value.output_dir,
        )
        _write_json(out_root / _CHECKPOINT_FILENAME, checkpoint.fp1_identity())
        if checkpoint.registerable:
            return refuse_partial_model_registration(status="checkpoint")

    if aborted:
        record = _terminal_record(
            status=TrainingTerminalStatus.ABORTED,
            cause=abort_cause,
            config=config.value,
            config_fp=config_fp.value,
            code_fp=code_fp.value,
            lock=lock.value,
            machine=machine,
            start_utc=start_utc,
            start_mono_ns=start_mono_ns,
            clock_ns=mono,
            trials=tuple(completed),
            best_trial_index=best_index,
            model_path=None,
            model_fp=None,
            registerable=False,
        )
        _persist_record(out_root, record)
        assert_register = assert_registerable_training_artifact(record)
        if not is_refusal(assert_register):
            return refuse_partial_model_registration(status=record.status.value)
        return Ok(record)

    if best_model_text is None or best_index is None:
        record = _terminal_record(
            status=TrainingTerminalStatus.REFUSED,
            cause="no-completed-trial",
            config=config.value,
            config_fp=config_fp.value,
            code_fp=code_fp.value,
            lock=lock.value,
            machine=machine,
            start_utc=start_utc,
            start_mono_ns=start_mono_ns,
            clock_ns=mono,
            trials=tuple(completed),
            best_trial_index=None,
            model_path=None,
            model_fp=None,
            registerable=False,
        )
        _persist_record(out_root, record)
        return Ok(record)

    model_path = out_root / _MODEL_FILENAME
    model_path.write_text(best_model_text, encoding="utf-8")
    model_digest = hashlib.sha256(best_model_text.encode("utf-8")).hexdigest()
    model_fp = f"fp1:sha256:{model_digest}"
    record = _terminal_record(
        status=TrainingTerminalStatus.COMPLETED,
        cause="search-complete",
        config=config.value,
        config_fp=config_fp.value,
        code_fp=code_fp.value,
        lock=lock.value,
        machine=machine,
        start_utc=start_utc,
        start_mono_ns=start_mono_ns,
        clock_ns=mono,
        trials=tuple(completed),
        best_trial_index=best_index,
        model_path=_posix_rel(model_path),
        model_fp=model_fp,
        registerable=True,
    )
    _persist_record(out_root, record)
    # Drop the checkpoint after a completed terminal record so resume cannot
    # revive a finished search as a partial registerable model.
    checkpoint_path = out_root / _CHECKPOINT_FILENAME
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    model_fp_obj = Fingerprint.try_create(model_fp)
    if is_refusal(model_fp_obj):
        return model_fp_obj
    artifact = TrainingArtifact(
        artifact_id=REGIME_TRAIN_ARTIFACT_ID,
        record=record,
        model_text=best_model_text,
        model_fp=model_fp_obj.value,
        config_fp=config_fp.value,
        code_fp=code_fp.value,
        matrix_fp=matrix_fp.value,
        design_fp=config.value.design_fp,
        registerable=True,
        grants_money_path_authority=False,
        grants_governed_binding=False,
    )
    return Ok(artifact)


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
        if (
            artifact.registerable
            and artifact.record.status is TrainingTerminalStatus.COMPLETED
            and artifact.grants_money_path_authority is False
            and artifact.grants_governed_binding is False
        ):
            return Ok(None)
        return refuse_partial_model_registration(status=artifact.record.status.value)
    if isinstance(artifact, TrainingRecord):
        if (
            artifact.registerable
            and artifact.status is TrainingTerminalStatus.COMPLETED
            and artifact.grants_money_path_authority is False
            and artifact.grants_governed_binding is False
        ):
            return Ok(None)
        return refuse_partial_model_registration(status=artifact.status.value)
    if isinstance(artifact, TrainingCheckpoint):
        return refuse_partial_model_registration(status="checkpoint")
    return invalid(
        "artifact",
        "registerability check takes a TrainingArtifact or TrainingRecord",
        given=type(artifact).__name__,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Operator entry: ``python -m qmn.mis.regime_train`` (never a node CLI)."""
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
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.labeled_json is None or args.cleaned_json is None:
        print(
            "operator-prepared --labeled-json and --cleaned-json are required; "
            "this script never fetches providers or opens credentials",
            file=sys.stderr,
        )
        return 2

    # The CLI loads operator-prepared JSON envelopes produced by Stories 30.2/30.3
    # tooling outside this module. In-library callers should use run_offline_training
    # with live LabeledCorpus / CleanedCorpus objects instead.
    print(
        "JSON envelope loading for operator-prepared corpora is staged through "
        "run_offline_training with in-memory Story 30.2/30.3 artifacts; pass "
        "objects from Python rather than relying on an undeclared on-disk schema "
        "in Story 30.4. Refusing rather than inventing a loader.",
        file=sys.stderr,
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
    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        _write_json(args.output_dir / _RECORD_FILENAME, envelope)
    except OSError:
        pass
    return 1


# --- internals -----------------------------------------------------------------


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
        if row.split_role == SegmentRole.TRAIN.value:
            train_end = row.event_time_ns + BAR_INTERVAL_M5_NS if train_end is None else max(
                train_end, row.event_time_ns + BAR_INTERVAL_M5_NS
            )
        elif row.split_role == SegmentRole.VALIDATION.value:
            validation_end = (
                row.event_time_ns + BAR_INTERVAL_M5_NS
                if validation_end is None
                else max(validation_end, row.event_time_ns + BAR_INTERVAL_M5_NS)
            )
        elif row.split_role == _SPLIT_ROLE_HOLDOUT:
            holdout_end = (
                row.event_time_ns + BAR_INTERVAL_M5_NS
                if holdout_end is None
                else max(holdout_end, row.event_time_ns + BAR_INTERVAL_M5_NS)
            )
    # Prefer edges from the labeled corpus provenance when roles are present.
    # Fall back to ordered unique event times if a role is empty (refused later).
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
        if feature_id in peer_ids or feature_id in {
            "spread_state_elevated",
            "spread_state_extreme",
            "liquidity_stress",
            "sqs_hard_block",
            "gap_event",
            "feed_state_degraded",
        }:
            key = feature_id
            if feature_id.startswith("spread_state_"):
                key = "spread_state"
            elif feature_id == "sqs_hard_block":
                key = "sqs"
            elif feature_id == "feed_state_degraded":
                key = "feed_state"
            if peer_supplied and key in peer_values:
                values.append(float(peer_values[key]))
            elif peer_supplied and feature_id in peer_values:
                values.append(float(peer_values[feature_id]))
            else:
                values.append(0.0)
            continue
        computed = _bar_feature(series, index, feature_id)
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


def _bar_feature(
    series: Sequence[CleanedCorpusRow],
    index: int,
    feature_id: str,
) -> Result[float]:
    row = series[index]
    if feature_id == "session_asia":
        return Ok(1.0 if row.session == "asia" else 0.0)
    if feature_id == "session_london":
        return Ok(1.0 if row.session == "london" else 0.0)
    if feature_id == "session_new_york":
        return Ok(1.0 if row.session == "new_york" else 0.0)
    if feature_id == "hour_of_session":
        # Deterministic hour proxy from event time (ns -> hour-of-day UTC).
        hour = (row.event_time_ns // 3_600_000_000_000) % 24
        return Ok(float(hour))
    if feature_id in {"realized_range_pct_20", "realized_range_pct_60"}:
        window = 20 if feature_id.endswith("_20") else 60
        return Ok(_realized_range_pct(series, index, window))
    if feature_id in {"return_z_20", "return_z_60"}:
        window = 20 if feature_id.endswith("_20") else 60
        return Ok(_return_z(series, index, window))
    if feature_id == "atr_ratio_20_60":
        short = _mean_range(series, index, 20)
        long = _mean_range(series, index, 60)
        if long == 0.0:
            return Ok(0.0)
        return Ok(short / long)
    return policy(
        "feature_id",
        "unknown feature id in the ruled feature contract",
        feature_id=feature_id,
    )


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
            import lightgbm  # noqa: F401, PLC0415  # pyright: ignore[reportMissingImports]

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
    hyper_obj = context.get("hyperparameters", {})
    hyper: Mapping[str, object] = (
        cast("Mapping[str, object]", hyper_obj) if isinstance(hyper_obj, Mapping) else {}
    )
    feature_ids_obj = context.get("feature_ids", [])
    if isinstance(feature_ids_obj, Sequence) and not isinstance(
        feature_ids_obj, (str, bytes)
    ):
        feature_ids = [str(item) for item in cast("Sequence[object]", feature_ids_obj)]
    else:
        feature_ids = []
    vocab_obj = context.get("class_vocabulary", list(REGIME_CLASS_VOCABULARY))
    if isinstance(vocab_obj, Sequence) and not isinstance(vocab_obj, (str, bytes)):
        vocabulary = [str(item) for item in cast("Sequence[object]", vocab_obj)]
    else:
        vocabulary = list(REGIME_CLASS_VOCABULARY)
    validation_obj = context.get("validation_rows")
    validation_rows: tuple[_TrainRow, ...]
    if isinstance(validation_obj, Sequence) and not isinstance(
        validation_obj, (str, bytes)
    ):
        validation_rows = tuple(
            cast("_TrainRow", row)
            for row in cast("Sequence[object]", validation_obj)
            if isinstance(row, tuple) and len(cast("tuple[object, ...]", row)) >= 3
        )
    else:
        validation_rows = ()
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
    model_text = "\n".join(lines) + "\n"
    score = _surrogate_validation_score(
        train_rows,
        validation_rows,
        seed=seed,
        hyper=hyper,
    )
    return model_text, score, score


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

    lgb_api: Any = lgb
    hyper_obj = context.get("hyperparameters", {})
    if not isinstance(hyper_obj, Mapping):
        raise TypeError("hyperparameters mapping required")
    hyper = cast("Mapping[str, object]", hyper_obj)
    vocab_obj = context.get("class_vocabulary", list(REGIME_CLASS_VOCABULARY))
    if isinstance(vocab_obj, Sequence) and not isinstance(vocab_obj, (str, bytes)):
        vocabulary = [str(item) for item in cast("Sequence[object]", vocab_obj)]
    else:
        vocabulary = list(REGIME_CLASS_VOCABULARY)
    label_to_index = {name: index for index, name in enumerate(vocabulary)}
    x_train = [list(row[1]) for row in train_rows]
    y_train = [label_to_index[row[2]] for row in train_rows]
    validation_obj = context.get("validation_rows")
    x_valid: list[list[float]] = []
    y_valid: list[int] = []
    if isinstance(validation_obj, Sequence) and not isinstance(
        validation_obj, (str, bytes)
    ):
        for row_obj in cast("Sequence[object]", validation_obj):
            if not isinstance(row_obj, tuple):
                continue
            row = cast("tuple[object, ...]", row_obj)
            if len(row) < 3:
                continue
            features = row[1]
            if not isinstance(features, (tuple, list)):
                continue
            x_valid.append(
                [
                    _coerce_float(value)
                    for value in cast("Sequence[object]", features)
                ]
            )
            y_valid.append(label_to_index[str(row[2])])
    train_set = lgb_api.Dataset(x_train, label=y_train, free_raw_data=False)
    valid_set = (
        lgb_api.Dataset(x_valid, label=y_valid, reference=train_set, free_raw_data=False)
        if x_valid
        else None
    )
    lr_obj = hyper.get("learning_rate", [1, 100])
    if isinstance(lr_obj, list):
        lr = cast("list[object]", lr_obj)
        if len(lr) == 2:
            learning_rate = _coerce_float(lr[0]) / _coerce_float(lr[1])
        else:
            learning_rate = 0.05
    else:
        learning_rate = 0.05
    ff_obj = hyper.get("feature_fraction", [1, 1])
    if isinstance(ff_obj, list):
        ff = cast("list[object]", ff_obj)
        if len(ff) == 2:
            feature_fraction = _coerce_float(ff[0]) / _coerce_float(ff[1])
        else:
            feature_fraction = 1.0
    else:
        feature_fraction = 1.0
    params = {
        "objective": "multiclass",
        "num_class": len(vocabulary),
        "num_leaves": _coerce_int(hyper.get("num_leaves", 31)),
        "learning_rate": learning_rate,
        "min_data_in_leaf": _coerce_int(hyper.get("min_data_in_leaf", 20)),
        "feature_fraction": feature_fraction,
        "verbosity": -1,
        "seed": seed,
        "deterministic": True,
        "force_row_wise": True,
    }
    callbacks: list[Any] = []
    early = hyper.get("early_stopping_rounds")
    if valid_set is not None and isinstance(early, int) and early > 0:
        callbacks.append(lgb_api.early_stopping(early, verbose=False))
    booster = lgb_api.train(
        params,
        train_set,
        num_boost_round=200,
        valid_sets=[valid_set] if valid_set is not None else None,
        callbacks=callbacks or None,
    )
    model_text = str(booster.model_to_string())
    if valid_set is None or not x_valid:
        score = 0
    else:
        preds = cast("Sequence[Sequence[float]]", booster.predict(x_valid))
        correct = 0
        for index, row in enumerate(preds):
            predicted = max(range(len(row)), key=lambda i, current=row: current[i])
            if predicted == y_valid[index]:
                correct += 1
        score = (correct * 1_000_000_000) // max(1, len(y_valid))
    return model_text, score, score


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


def _resolve_lock_path(lock_path: object | None) -> Path | None:
    if lock_path is not None:
        token = clean_token(lock_path)
        if token is None:
            return None
        path = Path(token)
        return path if path.is_file() else None
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "uv.lock"
        if candidate.is_file():
            return candidate
    return None


def _posix_rel(path: Path) -> str:
    try:
        return path.resolve().as_posix()
    except OSError:
        return path.as_posix()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _append_jsonl(path: Path, payload: Mapping[str, object]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), sort_keys=True) + "\n")


def _persist_record(out_root: Path, record: TrainingRecord) -> None:
    _write_json(out_root / _RECORD_FILENAME, record.as_jsonable())


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
    path = out_root / _CHECKPOINT_FILENAME
    if not path.is_file():
        return Ok(None)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
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
    payload = cast("dict[str, object]", raw)
    if payload.get("registerable") is True:
        return refuse_partial_model_registration(status="checkpoint-file")
    config_fp = Fingerprint.try_create(payload.get("config_fp"))
    code_fp = Fingerprint.try_create(payload.get("code_fp"))
    matrix_fp = Fingerprint.try_create(payload.get("matrix_fp"))
    if is_refusal(config_fp) or is_refusal(code_fp) or is_refusal(matrix_fp):
        return policy(
            "checkpoint",
            "checkpoint fingerprints must be fp1 values",
            failure_id="mis.regime_train.checkpoint",
        )
    trials_raw = payload.get("completed_trials", [])
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
    next_index = payload.get("next_trial_index")
    if not isinstance(next_index, int) or isinstance(next_index, bool):
        return policy(
            "checkpoint",
            "next_trial_index must be an int",
            failure_id="mis.regime_train.checkpoint",
        )
    best_trial_obj = payload.get("best_trial_index")
    best_trial_index = (
        best_trial_obj
        if isinstance(best_trial_obj, int) or best_trial_obj is None
        else None
    )
    if isinstance(best_trial_index, bool):
        best_trial_index = None
    best_score_obj = payload.get("best_validation_score_ppb")
    best_validation_score_ppb = (
        best_score_obj
        if isinstance(best_score_obj, int) or best_score_obj is None
        else None
    )
    if isinstance(best_validation_score_ppb, bool):
        best_validation_score_ppb = None
    return Ok(
        TrainingCheckpoint(
            config_fp=config_fp.value,
            code_fp=code_fp.value,
            matrix_fp=matrix_fp.value,
            completed_trials=tuple(trials),
            next_trial_index=next_index,
            best_trial_index=best_trial_index,
            best_validation_score_ppb=best_validation_score_ppb,
            registerable=False,
            output_dir=str(payload.get("output_dir", out_root.as_posix())),
        )
    )


def _trial_from_jsonable(raw: object) -> Result[TrialRecord]:
    if not isinstance(raw, dict):
        return policy(
            "trial",
            "trial record must be an object",
            failure_id="mis.regime_train.checkpoint",
        )
    payload = cast("dict[str, object]", raw)
    hyper_obj = payload.get("hyperparameters")
    if not isinstance(hyper_obj, dict):
        return policy(
            "trial",
            "trial hyperparameters must be an object",
            failure_id="mis.regime_train.checkpoint",
        )
    hyper_raw = cast("dict[str, object]", hyper_obj)
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
        hyper = TrialHyperparameters(
            trial_index=_coerce_int(hyper_raw["trial_index"]),
            num_leaves=_coerce_int(hyper_raw["num_leaves"]),
            learning_rate_num=_coerce_int(lr[0]),
            learning_rate_den=_coerce_int(lr[1]),
            min_data_in_leaf=_coerce_int(hyper_raw["min_data_in_leaf"]),
            feature_fraction_num=_coerce_int(ff[0]),
            feature_fraction_den=_coerce_int(ff[1]),
            early_stopping_rounds=_coerce_int(hyper_raw["early_stopping_rounds"]),
        )
        model_fp_obj = payload.get("model_bytes_fp")
        model_bytes_fp = (
            model_fp_obj
            if model_fp_obj is None or isinstance(model_fp_obj, str)
            else None
        )
        trial = TrialRecord(
            trial_index=_coerce_int(payload["trial_index"]),
            hyperparameters=hyper,
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
    locations = {
        "output_dir": config.output_dir,
        "config": f"{config.output_dir}/{_CONFIG_FILENAME}",
        "record": f"{config.output_dir}/{_RECORD_FILENAME}",
        "trials": f"{config.output_dir}/{_TRIALS_FILENAME}",
    }
    if model_path is not None:
        locations["model"] = model_path
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


if __name__ == "__main__":
    raise SystemExit(main())
