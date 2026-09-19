"""Story 53.3 / SCN-0018 — pin revalidation, disable tombstone, in-flight leases."""

from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
from pathlib import Path

from qma.core.plugins import PluginContext
from qma.core.ports.qmb import qmb_opens_daemon_sqlite
from qma.daemon.discovery import (
    FEDERATED_SEARCH_OCCUPANCY,
    FederatedDiscoveryService,
)
from qma.daemon.hooks.registry import HookRegistry
from qma.daemon.journal.stores import CLOSED_STORE_NAMES, DEFINITION_STORE_MEMBERS
from qma.daemon.knowledge import (
    KnowledgeService,
    KnowledgeSourceRegistry,
    PlainFileLibrarySource,
)
from qma.daemon.plugins import (
    PIN_LEASE_STORE,
    ContributionPinService,
    DaemonPluginContext,
    PluginLoader,
)
from qma.wire import (
    CONTRIBUTION_PIN_IS_GRANT,
    CONTRIBUTION_PIN_SIXTH_STORE_MINTED,
    CONTRIBUTION_PIN_WIRED_AT_INSPECT_SHA,
    ContributionHit,
)
from qmf.core import Ok, Result, is_ok, is_refusal
from qmf.core.refusal import RefusalCategory

_PINS_SRC = Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon" / "plugins" / "pins.py"
_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "contribution_pin_tombstone_usage.py"


def _corpus(tmp_path: Path) -> Path:
    root = tmp_path / "strats"
    root.mkdir()
    (root / "notes.md").write_text("liquidity sweep near London open\n", encoding="utf-8")
    return root


def _knowledge(tmp_path: Path) -> KnowledgeService:
    registry = KnowledgeSourceRegistry()
    source = PlainFileLibrarySource(root_path=_corpus(tmp_path), source_id="strats")
    bound = registry.bind("strats", source, plugin_id="research-strats")
    assert is_ok(bound)
    return KnowledgeService(registry, hooks=HookRegistry())


class _FakeArtifactPort:
    def search(
        self,
        *,
        kind: str | None = None,
        fp1: str | None = None,
        query: str | None = None,
    ) -> Result[Sequence[Mapping[str, object]]]:
        _ = (kind, fp1, query)
        return Ok(())


def _manifest(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
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
    }
    base.update(overrides)
    return base


def _activate_inspect(ctx: PluginContext) -> None:
    assert isinstance(ctx, DaemonPluginContext)
    ctx.register_tool("inspect", {"name": "inspect"})


def _activate_cite(ctx: PluginContext) -> None:
    assert isinstance(ctx, DaemonPluginContext)
    ctx.register_tool("cite", {"name": "cite"})


def _live_hit(loader: PluginLoader) -> ContributionHit:
    rows = [row for row in loader.published_contributions() if row.qualified_id]
    assert rows
    built = ContributionHit.try_create(
        plugin_id=rows[0].plugin_id,
        point=rows[0].point,
        qualified_id=rows[0].qualified_id,
        package_id=rows[0].package_id,
        package_version=rows[0].package_version,
        availability_revision=rows[0].availability_revision,
        availability=rows[0].availability,
    )
    assert is_ok(built)
    return built.value


def test_inspect_sha_and_no_sixth_store() -> None:
    assert CONTRIBUTION_PIN_WIRED_AT_INSPECT_SHA is False
    assert CONTRIBUTION_PIN_IS_GRANT is False
    assert CONTRIBUTION_PIN_SIXTH_STORE_MINTED is False
    assert PIN_LEASE_STORE == "plugin_install_records"
    assert PIN_LEASE_STORE in DEFINITION_STORE_MEMBERS
    assert PIN_LEASE_STORE in CLOSED_STORE_NAMES
    assert "pin_leases" not in CLOSED_STORE_NAMES
    assert "contribution_pins" not in CLOSED_STORE_NAMES


def test_pin_stores_tuple_and_invoke_is_not_a_grant() -> None:
    loader = PluginLoader()
    enabled = loader.enable(_manifest(), activator=_activate_inspect)
    assert is_ok(enabled)
    pins = ContributionPinService(loader)
    hit = _live_hit(loader)
    pinned = pins.pin(hit)
    assert is_ok(pinned)
    pin = pinned.value
    assert pin.as_tuple() == (
        "research-corpus:inspect",
        "0.1.0",
        hit.availability_revision,
    )
    assert "fp1" not in pin.to_payload()
    invoked = pins.invoke(pin)
    assert is_ok(invoked)
    admission = invoked.value
    assert admission.is_grant is False
    assert admission.grant_id is None
    assert admission.grant_checks_pending is True
    assert admission.live.qualified_id == pin.qualified_id
    assert admission.live.package_version == pin.package_version
    assert admission.live.availability_revision == pin.availability_revision
    assert pins.pin_is_grant is False


def test_disable_yields_unavailable_never_another_version(tmp_path: Path) -> None:
    knowledge = _knowledge(tmp_path)
    loader = PluginLoader()
    enabled = loader.enable(_manifest(), activator=_activate_inspect)
    assert is_ok(enabled)
    pins = ContributionPinService(loader)
    pin = pins.pin(_live_hit(loader))
    assert is_ok(pin)

    disabled = pins.disable("research-corpus")
    assert is_ok(disabled)
    assert disabled.value.availability == "unavailable"
    assert disabled.value.cause == "disabled"
    assert disabled.value.is_grant is False

    later = pins.invoke(pin.value)
    assert is_refusal(later)
    assert later.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert later.context["availability"] == "unavailable"
    assert later.context["silent_retarget"] is False
    assert later.context["package_version"] == "0.1.0"

    # Enabling another version of the same qualified_id must not retarget the pin.
    second = loader.enable(
        _manifest(
            id="research-notes",
            version="2.0.0",
            entrypoint="research_notes.activate",
            contributions=[{"point": "tool", "local_id": "inspect"}],
            contributes=[
                {
                    "point": "tool",
                    "local_id": "inspect",
                    "qualified_id": "research-corpus:inspect",
                }
            ],
        ),
        activator=_activate_inspect,
    )
    assert is_ok(second)
    retarget = pins.invoke(pin.value)
    assert is_refusal(retarget)
    assert retarget.context["availability"] in {"unavailable", "tombstone"}
    assert retarget.context["package_version"] == "0.1.0"
    assert retarget.context.get("other_package_version") == "2.0.0"
    assert retarget.context.get("retarget_refused") is True
    assert "fp1" not in retarget.context

    facade = FederatedDiscoveryService(
        knowledge=knowledge,
        artifacts=_FakeArtifactPort(),
        contributions=loader,
    )
    snapped = knowledge.snapshot("strats")
    assert is_ok(snapped)
    found = facade.search("liquidity", source_id="strats", snapshot=snapped.value)
    assert is_ok(found)
    live = [hit for hit in found.value.hits if isinstance(hit, ContributionHit)]
    assert live
    assert all(hit.package_version != "0.1.0" or hit.plugin_id != "research-corpus" for hit in live)


def test_uninstall_yields_tombstone() -> None:
    loader = PluginLoader()
    enabled = loader.enable(_manifest(), activator=_activate_inspect)
    assert is_ok(enabled)
    pins = ContributionPinService(loader)
    pin = pins.pin(_live_hit(loader))
    assert is_ok(pin)
    gone = pins.uninstall("research-corpus")
    assert is_ok(gone)
    assert gone.value.availability == "tombstone"
    assert gone.value.cause == "uninstalled"
    later = pins.invoke(pin.value)
    assert is_refusal(later)
    assert later.context["availability"] == "tombstone"
    assert later.context["silent_retarget"] is False
    assert later.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_inflight_lease_keeps_started_bytes_and_gc_gate() -> None:
    loader = PluginLoader()
    first = loader.enable(_manifest(), activator=_activate_inspect)
    assert is_ok(first)
    pins = ContributionPinService(loader)
    pin = pins.pin(_live_hit(loader))
    assert is_ok(pin)
    lease = pins.acquire_lease(pin.value, lease_id="run-1")
    assert is_ok(lease)
    assert lease.value.started_bytes["package_version"] == "0.1.0"
    assert lease.value.started_bytes["qualified_id"] == "research-corpus:inspect"
    assert pins.pin_lease_store == PIN_LEASE_STORE == "plugin_install_records"

    disabled = pins.disable("research-corpus")
    assert is_ok(disabled)
    assert disabled.value.bytes_retained is True
    assert disabled.value.scope_disposed is False
    assert disabled.value.pin_leases == ("run-1",)
    assert disabled.value.gc_eligible is False
    parked = pins.inflight_plugin("research-corpus", "0.1.0")
    assert parked is not None
    assert parked.manifest.version == "0.1.0"
    held = pins.started_bytes("run-1")
    assert held is not None
    assert held["package_version"] == "0.1.0"

    later = pins.invoke(pin.value)
    assert is_refusal(later)
    assert later.context["availability"] == "unavailable"

    refused_gc = pins.gc("research-corpus", "0.1.0")
    assert is_refusal(refused_gc)

    released = pins.release_lease("run-1")
    assert is_ok(released)
    assert pins.gc_eligible("research-corpus", "0.1.0") is True
    cleaned = pins.gc("research-corpus", "0.1.0")
    assert is_ok(cleaned)
    assert pins.inflight_plugin("research-corpus", "0.1.0") is None


def test_dependants_block_gc_and_side_by_side_versions_remain() -> None:
    loader = PluginLoader()
    base = loader.enable(_manifest(), activator=_activate_inspect)
    assert is_ok(base)
    dependant = loader.enable(
        _manifest(
            id="research-notes",
            version="0.2.0",
            entrypoint="research_notes.activate",
            dependencies=["research-corpus"],
            contributions=[{"point": "tool", "local_id": "cite"}],
            contributes=[{"point": "tool", "local_id": "cite"}],
        ),
        activator=_activate_cite,
    )
    assert is_ok(dependant)
    pins = ContributionPinService(loader)
    pin = pins.pin(_live_hit(loader))
    assert is_ok(pin)
    named = pins.uninstall("research-corpus")
    assert is_ok(named)
    assert "research-notes" in named.value.dependants
    assert named.value.bytes_retained is True
    assert named.value.gc_eligible is False
    assert named.value.availability == "tombstone"
    later = pins.invoke(pin.value)
    assert is_refusal(later)
    assert later.context["availability"] == "tombstone"

    # Side-by-side: a different package_version can be live while parked bytes stay.
    parked = pins.inflight_plugin("research-corpus", "0.1.0")
    assert parked is not None
    assert parked.manifest.version == "0.1.0"
    notes = [row for row in loader.published_contributions() if row.plugin_id == "research-notes"]
    assert notes
    assert all(row.package_version == "0.2.0" for row in notes)


def test_module_never_imports_qmb_occupancy_none() -> None:
    source = _PINS_SRC.read_text(encoding="utf-8")
    assert "import qmb" not in source
    assert "from qmb" not in source
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append(node.module)
    assert not any(name == "qmb" or name.startswith("qmb.") for name in imports)
    assert FEDERATED_SEARCH_OCCUPANCY == "none"
    assert qmb_opens_daemon_sqlite() is False


def test_reference_usage_example_runs() -> None:
    import runpy

    namespace = runpy.run_path(str(_EXAMPLE))
    namespace["main"]()
