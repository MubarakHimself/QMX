"""Reference usage — atomic roster, export-scan oracle, unsupported_door (58.5)."""

from __future__ import annotations

from pathlib import Path

from qma.core.refusals import UnsupportedDoor
from qma.daemon import PackLifecycleFixture, claim_gap_0098_closed
from qma.daemon.plugins import (
    COMPOSITION_MODES,
    EXPORTS_SECRETS_AUTHORIZES_EXPORT,
    GAP_0098_STATUS,
    MISSING_DEP_WARN_AND_CONTINUE,
    PACK_LIFECYCLE_WIRED_AT_INSPECT_SHA,
    SESSION_GRANTED_IS_PACK_STATE,
)
from qmf.core import is_ok, is_refusal

_AT = "2026-09-20T16:00:00Z"


def _manifest(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "id": "research-corpus",
        "version": "0.1.0",
        "qma_api": ">=0.1.0,<1.0.0",
        "desk": "research",
        "entrypoint": "research_corpus.activate",
        "dependencies": [],
        "contributions": [{"point": "tool", "local_id": "inspect"}],
        "contributes": [{"point": "tool", "local_id": "inspect"}],
        "permissions": [],
        "migrations": [],
        "exports_secrets": False,
    }
    body.update(overrides)
    return body


def main(root: Path) -> None:
    assert PACK_LIFECYCLE_WIRED_AT_INSPECT_SHA is False
    assert EXPORTS_SECRETS_AUTHORIZES_EXPORT is False
    assert MISSING_DEP_WARN_AND_CONTINUE is False
    assert SESSION_GRANTED_IS_PACK_STATE is False
    assert GAP_0098_STATUS == "open"
    assert is_refusal(claim_gap_0098_closed())
    assert len(COMPOSITION_MODES) == 4

    fixture = PackLifecycleFixture(root=root)
    files = {
        "manifest.json": '{"id":"research-corpus","token":"cred:research-corpus:models"}',
        "notes.md": "liquidity notes",
    }
    assert is_ok(fixture.download(_manifest(), files=files, transitioned_at=_AT))
    assert is_ok(fixture.install("research-corpus", transitioned_at=_AT))
    assert is_ok(fixture.validate("research-corpus", transitioned_at=_AT))
    enabled = fixture.enable("research-corpus", transitioned_at=_AT)
    assert is_ok(enabled)
    assert enabled.value.to_state == "enabled"
    assert fixture.roster.live_path.is_file()

    pin = fixture.pin("research-corpus")
    assert is_ok(pin)
    live = fixture.invoke_pin(pin.value)
    assert is_ok(live)
    assert live.value.is_grant is False

    exported = fixture.export("research-corpus")
    assert is_ok(exported)
    assert exported.value.report.result == "fail-closed-pass"
    assert is_refusal(fixture.export("research-corpus", trust_manifest=True))

    missing = fixture.download(
        _manifest(
            id="research-notes",
            entrypoint="research_notes.activate",
            dependencies=["analysis-backtest"],
            contributes=[{"point": "tool", "local_id": "cite"}],
            contributions=[{"point": "tool", "local_id": "cite"}],
        ),
        transitioned_at=_AT,
    )
    assert is_ok(missing)
    assert is_ok(fixture.install("research-notes", transitioned_at=_AT))
    assert is_ok(fixture.validate("research-notes", transitioned_at=_AT))
    refused = fixture.enable("research-notes", transitioned_at=_AT)
    assert is_refusal(refused)
    assert refused.context["warn_and_continue"] is False
    corpus = fixture.pack("research-corpus")
    assert corpus is not None
    assert corpus.state == "enabled"

    door = fixture.invoke_door(op_id="qma.procedure.start", version=1, adapter="qmb-cli")
    assert is_refusal(door)
    assert UnsupportedDoor.matches(door)
    assert is_refusal(fixture.mint_operator_cli("qma"))
    parity = fixture.supported_door_parity(op_id="qma.procedure.start", version=1)
    assert is_ok(parity)

    disabled = fixture.disable("research-corpus", transitioned_at=_AT)
    assert is_ok(disabled)
    later = fixture.invoke_pin(pin.value)
    assert is_refusal(later)
    assert later.context["availability"] in {"unavailable", "tombstone"}
    print("atomic roster published; scanner is the oracle; unsupported_door stays typed")
    print("GAP-0098 stays open")


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        main(Path(tmp))
