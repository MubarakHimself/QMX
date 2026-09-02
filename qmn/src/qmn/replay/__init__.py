"""Replay import surface (TN-21 / Story 27.7).

A recorded day is replayed as a credential-free decision diff: a process
outside the node, ``world = replay``, disjoint WriterIds, the replay
VenueClientPort, and the named one-way sealed-archive import port. Signal
snapshots are reused, not recomputed. GAP-0056 stays deferred — no fill
simulation and no command submit. The diff is diagnostic evidence only.
"""

from __future__ import annotations

from typing import Final

from qmn.replay.port import (
    FILL_SIMULATION_IN_REPLAY,
    GAP_0056_DEFERRED,
    RECORDED_DAY_KIND,
    REPLAY_IMPORT_PORT,
    REPLAY_IMPORT_SURFACE,
    RecordedDay,
    RecordedSignalSnapshot,
    ReplayImportPort,
    decode_recorded_day,
    encode_recorded_day,
    refuse_cross_world_write,
    refuse_fill_simulation,
    refuse_sqs_recompute,
)
from qmn.replay.session import (
    NODE_PROCESS_ENV,
    REPLAY_PROCESS_ENV,
    REPLAY_WRITER_ROLE_PREFIX,
    ReplayComposition,
    ReplayDiffReport,
    ReplayJobSpec,
    ReplaySliceHandler,
    ReplayWorldSink,
    allocate_replay_writer,
    assert_outside_node_process,
    attach_replay_to_loop,
    diff_recorded_day,
    refuse_admission_gate,
    refuse_command_submit,
    refuse_credential_bind,
    refuse_in_node_process,
    refuse_live_sink,
    refuse_live_venue_client,
    refuse_network,
    refuse_restore_into_live,
    refuse_secret_resolution,
    run_recorded_day,
    writers_are_disjoint,
)
from qmn.replay.spawn import (
    REPLAY_MODULE,
    ReplaySpawnReceipt,
    spawn_replay_job,
    spec_from_jsonable,
    spec_to_jsonable,
)

__all__ = [
    "FILL_SIMULATION_IN_REPLAY",
    "GAP_0056_DEFERRED",
    "NODE_PROCESS_ENV",
    "RECORDED_DAY_KIND",
    "REPLAY_IMPORT_PORT",
    "REPLAY_IMPORT_SURFACE",
    "REPLAY_MODULE",
    "REPLAY_PROCESS_ENV",
    "REPLAY_SURFACE",
    "REPLAY_WRITER_ROLE_PREFIX",
    "RecordedDay",
    "RecordedSignalSnapshot",
    "ReplayComposition",
    "ReplayDiffReport",
    "ReplayImportPort",
    "ReplayJobSpec",
    "ReplaySliceHandler",
    "ReplaySpawnReceipt",
    "ReplayWorldSink",
    "allocate_replay_writer",
    "assert_outside_node_process",
    "attach_replay_to_loop",
    "decode_recorded_day",
    "diff_recorded_day",
    "encode_recorded_day",
    "refuse_admission_gate",
    "refuse_command_submit",
    "refuse_credential_bind",
    "refuse_cross_world_write",
    "refuse_fill_simulation",
    "refuse_in_node_process",
    "refuse_live_sink",
    "refuse_live_venue_client",
    "refuse_network",
    "refuse_restore_into_live",
    "refuse_secret_resolution",
    "refuse_sqs_recompute",
    "run_recorded_day",
    "spawn_replay_job",
    "spec_from_jsonable",
    "spec_to_jsonable",
    "writers_are_disjoint",
]

REPLAY_SURFACE: Final[str] = "qmn.replay"
