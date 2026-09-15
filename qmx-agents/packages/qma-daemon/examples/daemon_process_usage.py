"""L27 reference usage: compose the asyncio daemon process (FR-W09)."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from qma.core.plugins.packs import DESK_PLUGIN_PACK_IDS
from qma.core.ports.qmb import ANALYSIS_BACKTEST_PLUGIN_ID
from qma.daemon.backtest.service import BacktestingService
from qma.daemon.process import (
    COMP_EXP_MINTED,
    HTTP_EXPERIMENT_SERVICE_MINTED,
    QMB_JSONL_MERGED_INTO_SQLITE,
    SIXTH_APPLICATION_MINTED,
    DaemonProcess,
)
from qma.wire.schemas import SCHEMA_FILES
from qma.wire.vocabulary import WIRE_VOCABULARY_OWNER
from qmf.core import is_ok, is_refusal


def main() -> None:
    assert COMP_EXP_MINTED is False
    assert HTTP_EXPERIMENT_SERVICE_MINTED is False
    assert SIXTH_APPLICATION_MINTED is False
    assert QMB_JSONL_MERGED_INTO_SQLITE is False

    async def _run(root: Path) -> None:
        composed = DaemonProcess.compose(
            root,
            machine="example-host",
            boot_epoch_id="boot-example-36-1",
            bind_port=0,
        )
        assert is_ok(composed), composed
        process = composed.value
        try:
            bound = await process.bind()
            assert is_ok(bound), bound
            assert bound.value.loopback is True
            assert process.sqlite_connection_count() == 1
            assert tuple(process.roster.loader.loaded_ids()) == DESK_PLUGIN_PACK_IDS
            assert isinstance(process.backtesting, BacktestingService)
            assert process.backtesting.plugin_id == ANALYSIS_BACKTEST_PLUGIN_ID
            assert process.wire_schema_owner == WIRE_VOCABULARY_OWNER
            assert dict(process.wire_schema_files) == dict(SCHEMA_FILES)
            assert is_refusal(process.start_http_experiment_service())
            assert is_refusal(process.merge_qmb_jsonl())
            assert is_refusal(process.import_qmb_package())
            second = DaemonProcess.compose(
                root / "other",
                machine="example-host",
                boot_epoch_id="boot-example-36-1-b",
            )
            assert is_refusal(second)
        finally:
            await process.aclose()

    with tempfile.TemporaryDirectory() as raw:
        asyncio.run(_run(Path(raw)))


if __name__ == "__main__":
    main()
