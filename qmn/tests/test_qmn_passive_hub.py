"""Story 27.4 — passive hub write-only inbox, sandbox refusal, promotion pull."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar

from qmf.core import Fingerprint, Result, WriterId, fingerprint_bytes, is_ok, is_refusal
from qmn.promotion import (
    HUB_INBOX_NAME,
    HUB_PUBLISHED_NAME,
    INBOUND_CROSSINGS,
    SANDBOX_PROVENANCE,
    HubFragment,
    PassiveHubTree,
    accept_inbox_fragment,
    publish_inbox_fragment,
    pull_from_published,
    refuse_evidence_sync_into_inbox,
    refuse_inbound_crossing,
    refuse_inbox_promotion_read,
    refuse_published_direct_write,
    refuse_sandbox_provenance,
)

T = TypeVar("T")

_SRC = Path(__file__).resolve().parents[1] / "src" / "qmn"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _writer() -> WriterId:
    return _ok(WriterId.try_create("vps-fra-01", "sandbox-push", "bot-as-of", "boot-27-4"))


def _fragment(
    *,
    key: str = "bot",
    payload: bytes = b"live-as-of-bot",
    provenance: str = "live",
    writer: WriterId | None = None,
    fp1: Fingerprint | None = None,
) -> Result[HubFragment]:
    return HubFragment.try_create(
        artifact_key=key,
        fp1=fp1 if fp1 is not None else fingerprint_bytes(payload),
        provenance=provenance,
        writer=writer if writer is not None else _writer(),
        payload=payload,
    )


def test_inbound_crossings_are_sandbox_push_and_promotion_pull() -> None:
    assert frozenset({"sandbox-push", "promotion-pull"}) == INBOUND_CROSSINGS
    assert HUB_INBOX_NAME == "hub-inbox"
    assert HUB_PUBLISHED_NAME == "hub-published"
    assert is_ok(refuse_inbound_crossing(crossing="sandbox-push"))
    assert is_ok(refuse_inbound_crossing(crossing="promotion-pull"))
    extra = _refusal(refuse_inbound_crossing(crossing="evidence-sync"))
    assert extra.context["failure_id"] == "hub.inbound_crossing"


def test_sandbox_can_write_inbox_but_cannot_publish_or_pull(tmp_path: Path) -> None:
    tree = PassiveHubTree(tmp_path)
    writer = _writer()
    payload = b"sandbox-bot-as-of"
    sandbox = _ok(_fragment(payload=payload, provenance=SANDBOX_PROVENANCE, writer=writer))
    accepted = _ok(accept_inbox_fragment(tree, sandbox))
    assert accepted.write_only is True
    assert accepted.provenance == SANDBOX_PROVENANCE
    published = _refusal(publish_inbox_fragment(tree, writer=writer, artifact_key="bot"))
    assert published.context["field"] == "provenance"
    assert published.context["crossing"] == "publish"
    live = _ok(_fragment(key="book", payload=b"live-book", writer=writer))
    _ok(accept_inbox_fragment(tree, live))
    _ok(publish_inbox_fragment(tree, writer=writer, artifact_key="book"))
    pulled = _refusal(
        pull_from_published(
            tree,
            artifact_keys=("bot", "book"),
            attested_fp1=fingerprint_bytes(payload),
            template_fp1=fingerprint_bytes(b"live-book"),
        )
    )
    # sandbox never reached published; bot is absent there.
    assert pulled.context["field"] in {"artifact_key", "provenance"}


def test_hub_publish_moves_live_fragment_and_pull_reads_published_only(
    tmp_path: Path,
) -> None:
    tree = PassiveHubTree(tmp_path)
    writer = _writer()
    bot_bytes = b"live-bot-as-of"
    book_bytes = b"live-book-as-of"
    bot_fp = fingerprint_bytes(bot_bytes)
    book_fp = fingerprint_bytes(book_bytes)
    _ok(accept_inbox_fragment(tree, _ok(_fragment(payload=bot_bytes, writer=writer))))
    _ok(accept_inbox_fragment(tree, _ok(_fragment(key="book", payload=book_bytes, writer=writer))))
    moved = _ok(publish_inbox_fragment(tree, writer=writer, artifact_key="bot"))
    assert moved.artifact.fp1 == bot_fp
    _ok(publish_inbox_fragment(tree, writer=writer, artifact_key="book"))
    pulled = _ok(
        pull_from_published(
            tree,
            artifact_keys=("bot", "book"),
            attested_fp1=bot_fp,
            template_fp1=book_fp,
        )
    )
    assert {item.artifact_key for item in pulled} == {"bot", "book"}
    inbox_read = _refusal(tree.read_inbox_for_promotion(writer=writer, artifact_key="bot"))
    assert inbox_read.context["failure_id"] == "hub.inbox.read"
    direct = _refusal(tree.write_published(_ok(_fragment(payload=bot_bytes))))
    assert direct.context["failure_id"] == "hub.published.write"
    sync = _refusal(tree.sync_into_inbox(b"hot-prefix"))
    assert sync.context["failure_id"] == "hub.inbound_crossing"


def test_writer_scope_and_fp1_mismatch_are_refused() -> None:
    missing_writer = _refusal(
        HubFragment.try_create(
            artifact_key="bot",
            fp1=fingerprint_bytes(b"x"),
            provenance="live",
            writer="not-a-writer",
            payload=b"x",
        )
    )
    assert missing_writer.context["failure_id"] == "hub.writer_scope"
    mismatched = _refusal(
        HubFragment.try_create(
            artifact_key="bot",
            fp1=fingerprint_bytes(b"expected"),
            provenance="live",
            writer=_writer(),
            payload=b"other-bytes",
        )
    )
    assert mismatched.context["field"] == "fp1"


def test_closed_refusals_name_the_two_areas() -> None:
    inbox = _refusal(refuse_inbox_promotion_read(source=HUB_INBOX_NAME))
    assert inbox.context["failure_id"] == "hub.inbox.read"
    published = _refusal(refuse_published_direct_write(target=HUB_PUBLISHED_NAME))
    assert published.context["failure_id"] == "hub.published.write"
    sync = _refusal(refuse_evidence_sync_into_inbox(target=HUB_INBOX_NAME))
    assert sync.context["failure_id"] == "hub.sync_into_inbox"
    assert is_ok(refuse_sandbox_provenance("live", crossing="publish"))


def test_hub_tree_does_not_import_off_host_backup_infra() -> None:
    path = _SRC / "promotion" / "passive_hub.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    banned = ("rclone", "boto3", "b2sdk", "qmn.data.sealed_archive")
    assert not any(name.split(".", 1)[0] in banned or name in banned for name in imported)
