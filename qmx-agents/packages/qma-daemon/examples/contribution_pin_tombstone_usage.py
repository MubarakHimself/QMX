"""Reference usage — pin tuple, invoke revalidation, disable tombstone (Story 53.3)."""

from __future__ import annotations

from qma.core.plugins import PluginContext
from qma.daemon.plugins import ContributionPinService, DaemonPluginContext, PluginLoader
from qma.wire import (
    CONTRIBUTION_PIN_IS_GRANT,
    CONTRIBUTION_PIN_WIRED_AT_INSPECT_SHA,
    ContributionHit,
)
from qmf.core import is_ok, is_refusal


def _activate(ctx: PluginContext) -> None:
    assert isinstance(ctx, DaemonPluginContext)
    ctx.register_tool("inspect", {"name": "inspect"})


def main() -> None:
    assert CONTRIBUTION_PIN_WIRED_AT_INSPECT_SHA is False
    assert CONTRIBUTION_PIN_IS_GRANT is False
    loader = PluginLoader()
    enabled = loader.enable(
        {
            "id": "research-corpus",
            "version": "0.1.0",
            "qma_api": ">=0.1.0,<1.0.0",
            "desk": "research",
            "entrypoint": "research_corpus.activate",
            "contributions": [{"point": "tool", "local_id": "inspect"}],
            "contributes": [{"point": "tool", "local_id": "inspect"}],
        },
        activator=_activate,
    )
    assert is_ok(enabled)
    pins = ContributionPinService(loader)
    row = next(item for item in loader.published_contributions() if item.qualified_id)
    hit = ContributionHit.try_create(
        plugin_id=row.plugin_id,
        point=row.point,
        qualified_id=row.qualified_id,
        package_id=row.package_id,
        package_version=row.package_version,
        availability_revision=row.availability_revision,
        availability=row.availability,
    )
    assert is_ok(hit)
    pinned = pins.pin(hit.value)
    assert is_ok(pinned)
    live = pins.invoke(pinned.value)
    assert is_ok(live)
    assert live.value.is_grant is False
    print("pin stored (qualified_id, package_version, availability_revision); not a grant")

    gone = pins.disable("research-corpus")
    assert is_ok(gone)
    later = pins.invoke(pinned.value)
    assert is_refusal(later)
    assert later.context["availability"] == "unavailable"
    print("disable → unavailable; never another package_version")


if __name__ == "__main__":
    main()
