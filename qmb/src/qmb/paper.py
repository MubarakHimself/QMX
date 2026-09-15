"""Research-paper naming, hub inbox fragments, notebooks, alias identity (Story 36.6).

Governed QMB replay (``world=replay``) outside the node is **research-paper**.
Node-paper stays COMP-QMN. QMA-paper does not exist here. WriterId-scoped
fragments may enter the B-15 hub inbox; ``hub_publish`` is human.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Literal, cast

from qmf.core.chrono import WriterId
from qmf.core.fingerprint import World
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok

from qmb._refuse import invalid, policy
from qmb.registryread.as_of import RegistryFragment
from qmb.workbench import WORKBENCH_LANE_COORDINATED, WORKBENCH_LANE_GOVERNED

__all__ = [
    "CONTROLLED_ROOM_HOST",
    "DISPLAY_ALIAS_KINDS",
    "EXPLORATORY_NOTEBOOK_IMPORTS",
    "HUB_CROSSINGS",
    "HUB_PUBLISH_IS_HUMAN",
    "NODE_PAPER_NOUN",
    "NODE_PAPER_OWNER",
    "PAPER_NOUN_RESEARCH",
    "QMA_PAPER_EXISTS",
    "QMB_NOTEBOOK_MODULE",
    "RESEARCH_PAPER_WORLD",
    "SANDBOX_PROVENANCE",
    "WORKSPACE_DEFAULTS_ARE_IDENTITY",
    "WORKSPACE_DEFAULTS_LAYER",
    "DisplayAlias",
    "ExploratoryNotebook",
    "HubInbox",
    "InboxFragment",
    "admit_exploratory_notebook",
    "append_hub_inbox_fragment",
    "name_research_paper",
    "publish_hub_inbox",
    "refuse_qma_paper",
    "refuse_qmb_notebook_module",
    "refuse_sandbox_provenance",
    "resolve_display_alias",
]

PAPER_NOUN_RESEARCH: Final[str] = "research-paper"
NODE_PAPER_NOUN: Final[str] = "node-paper"
NODE_PAPER_OWNER: Final[str] = "COMP-QMN"
QMA_PAPER_EXISTS: Final[Literal[False]] = False
RESEARCH_PAPER_WORLD: Final[str] = World.REPLAY.value
HUB_PUBLISH_IS_HUMAN: Final[Literal[True]] = True
SANDBOX_PROVENANCE: Final[str] = "sandbox"
HUB_CROSSINGS: Final[frozenset[str]] = frozenset({"publish", "pull"})
CONTROLLED_ROOM_HOST: Final[str] = "controlled-room"
EXPLORATORY_NOTEBOOK_IMPORTS: Final[frozenset[str]] = frozenset({"qmb", "qml"})
QMB_NOTEBOOK_MODULE: Final[Literal[False]] = False
WORKSPACE_DEFAULTS_ARE_IDENTITY: Final[Literal[False]] = False
WORKSPACE_DEFAULTS_LAYER: Final[str] = "config-compiler"
DISPLAY_ALIAS_KINDS: Final[frozenset[str]] = frozenset({"project", "workspace"})
_QMA_PAPER: Final[frozenset[str]] = frozenset(
    {"qma-paper", "qma_paper", "agent-paper", "quantconnect-paper", "paper-brokerage"}
)


def _fold(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().casefold().replace(" ", "-").replace("_", "-")


def refuse_qma_paper(*, given: object = "qma-paper") -> TypedRefusal:
    """QMA-paper does not exist. Research-paper is QMB governed replay."""
    return policy(
        "paper",
        "QMA-paper does not exist; governed QMB replay outside the node is "
        "research-paper, not an agent execution tool (FR-W13; DEC-0275)",
        given=repr(given),
        exists=QMA_PAPER_EXISTS,
        research_paper=PAPER_NOUN_RESEARCH,
        node_paper=NODE_PAPER_NOUN,
        node_paper_owner=NODE_PAPER_OWNER,
    )


def name_research_paper(
    *,
    world: object,
    location: object = "outside_node",
    noun: object = None,
) -> Result[str]:
    """Name governed QMB replay outside the node as research-paper."""
    asked = _fold(noun) if noun is not None else ""
    if asked in _QMA_PAPER or asked == "qma-paper":
        return refuse_qma_paper(given=noun)
    if asked == NODE_PAPER_NOUN:
        return policy(
            "paper",
            "node-paper remains COMP-QMN / CONNECT; a QMB replay is research-paper "
            "(FR-W13; DEC-0275)",
            given=repr(noun),
            owner=NODE_PAPER_OWNER,
        )
    loc = _fold(location)
    if loc in {"node", "qmn", "comp-qmn", "trading-node"}:
        return policy(
            "paper",
            "governed QMB replay (world=replay) outside the node is research-paper, "
            "not node-paper (FR-W13; DEC-0275)",
            location=repr(location),
        )
    world_token = world.value if isinstance(world, World) else _fold(world)
    if world_token != RESEARCH_PAPER_WORLD:
        return invalid(
            "world",
            "research-paper is governed QMB replay with world=replay (FR-W13; DEC-0275)",
            given=repr(world),
        )
    return Ok(PAPER_NOUN_RESEARCH)


def refuse_sandbox_provenance(*, provenance: object, crossing: object) -> Result[None]:
    """Sandbox-provenance fragments stay refused at publish and pull."""
    gate = _fold(crossing)
    if gate not in HUB_CROSSINGS:
        return invalid(
            "crossing",
            "sandbox provenance is refused at publish and at pull (FR-W14; DEC-0275)",
            given=repr(crossing),
            allowed=sorted(HUB_CROSSINGS),
        )
    if _fold(provenance) != SANDBOX_PROVENANCE:
        return Ok(None)
    return policy(
        "provenance",
        f"sandbox provenance is refused at {gate} (FR-W14; DEC-0275)",
        provenance=SANDBOX_PROVENANCE,
        crossing=gate,
    )


def publish_hub_inbox(*_args: object, **_kwargs: object) -> Result[None]:
    """hub_publish is human. QMB does not publish the inbox."""
    return policy(
        "hub_publish",
        "hub_publish is a human act; QMB may append WriterId-scoped fragments to "
        "the B-15 hub inbox and does not publish them (FR-W14; DEC-0275)",
        principal="human",
        is_human=HUB_PUBLISH_IS_HUMAN,
    )


@dataclass(frozen=True, slots=True)
class InboxFragment:
    """One WriterId-scoped fragment sitting in the B-15 hub inbox."""

    writer: WriterId
    fragment: RegistryFragment
    provenance: str

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "writer": list(self.writer.order_tuple()),
                "fragment_fp1": self.fragment.fingerprint.value,
                "provenance": self.provenance,
            }
        )

    @classmethod
    def try_create(
        cls,
        *,
        writer: object,
        fragment: object,
        provenance: object = "live",
    ) -> Result[InboxFragment]:
        if not isinstance(writer, WriterId):
            return invalid(
                "writer",
                "each hub inbox fragment is WriterId-scoped (FR-W14; DEC-0275)",
                given=repr(type(writer).__name__),
            )
        if not isinstance(fragment, RegistryFragment):
            return invalid(
                "fragment",
                "the hub inbox holds WriterId-scoped registry fragments",
                given=repr(type(fragment).__name__),
            )
        if not isinstance(provenance, str) or provenance.strip() == "":
            return invalid(
                "provenance",
                "a hub fragment declares a non-empty provenance token",
                given=repr(provenance),
            )
        return Ok(cls(writer=writer, fragment=fragment, provenance=provenance.strip()))


@dataclass(frozen=True, slots=True)
class HubInbox:
    """Write-only B-15 inbox value. Dumb storage, never a service, never publish."""

    fragments: tuple[InboxFragment, ...] = ()
    kind: str = "passive-inbox"

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "kind": self.kind,
                "count": len(self.fragments),
                "publish_is_human": HUB_PUBLISH_IS_HUMAN,
            }
        )


def append_hub_inbox_fragment(
    inbox: HubInbox | None,
    *,
    writer: object,
    fragment: object,
    provenance: object = "live",
) -> Result[HubInbox]:
    """Append a WriterId-scoped fragment. Does not publish."""
    minted = InboxFragment.try_create(writer=writer, fragment=fragment, provenance=provenance)
    if not is_ok(minted):
        return minted
    current = inbox if inbox is not None else HubInbox()
    fp = minted.value.fragment.fingerprint.value
    existing = tuple(item for item in current.fragments if item.fragment.fingerprint.value == fp)
    if existing:
        if existing[0] == minted.value:
            return Ok(current)
        return invalid(
            "fragment",
            "a true fp1 collision on differing hub inbox fragments is refused",
            fingerprint=fp,
        )
    return Ok(HubInbox(fragments=(*current.fragments, minted.value)))


def refuse_qmb_notebook_module(*, given: object = "qmb.notebook") -> TypedRefusal:
    """Exploratory notebooks import qmb; they are not a QMB notebook module."""
    return policy(
        "notebook",
        "exploratory notebooks import qmb / import qml on a controlled-room host; "
        "a managed interpreter lifecycle is a QMA ExecutionEnvironment, not a "
        "QMB module (FR-W15; DEC-0279)",
        given=repr(given),
        qmb_module=QMB_NOTEBOOK_MODULE,
    )


@dataclass(frozen=True, slots=True)
class ExploratoryNotebook:
    """``import qmb`` / ``import qml`` on a controlled-room host."""

    host: str
    imports: tuple[str, ...]

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType({"host": self.host, "imports": list(self.imports)})


def admit_exploratory_notebook(
    *,
    imports: object,
    host: object = CONTROLLED_ROOM_HOST,
    as_qmb_module: object = False,
    jupyter_product: object = None,
) -> Result[ExploratoryNotebook]:
    """Admit ungoverned notebook imports. Refuse a QMB module or Jupyter product."""
    if as_qmb_module is True:
        return refuse_qmb_notebook_module()
    if jupyter_product is not None:
        return policy(
            "notebook",
            "a managed interpreter lifecycle is not a pinned Jupyter product (FR-W15; DEC-0279)",
            given=repr(jupyter_product),
            pinned_jupyter=False,
        )
    if _fold(host) != CONTROLLED_ROOM_HOST:
        return policy(
            "host",
            "exploratory notebooks run on a controlled-room host (FR-W15; DEC-0279)",
            given=repr(host),
            required=CONTROLLED_ROOM_HOST,
        )
    if isinstance(imports, str):
        items = (imports,)
    elif isinstance(imports, Sequence) and not isinstance(imports, (bytes, bytearray)):
        items = tuple(str(item) for item in cast("Sequence[object]", imports))
    else:
        return invalid("imports", "notebook imports are qmb and/or qml", given=repr(imports))
    admitted: list[str] = []
    for item in items:
        token = item.strip().casefold()
        if token not in EXPLORATORY_NOTEBOOK_IMPORTS:
            return policy(
                "imports",
                "exploratory notebooks import qmb / import qml (FR-W15; DEC-0279)",
                given=item,
                allowed=sorted(EXPLORATORY_NOTEBOOK_IMPORTS),
            )
        admitted.append(token)
    if not admitted:
        return invalid("imports", "exploratory notebooks import qmb / import qml")
    return Ok(
        ExploratoryNotebook(
            host=CONTROLLED_ROOM_HOST,
            imports=tuple(dict.fromkeys(admitted)),
        )
    )


@dataclass(frozen=True, slots=True)
class DisplayAlias:
    """project/workspace overlay ExperimentSpec (coordinated) or bot fp1 (governed)."""

    display: str
    lane: str
    over: str
    mints_record: Literal[False] = False
    workspace_defaults_are_identity: Literal[False] = False

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "display": self.display,
                "lane": self.lane,
                "over": self.over,
                "mints_record": self.mints_record,
                "workspace_defaults_layer": WORKSPACE_DEFAULTS_LAYER,
            }
        )


def resolve_display_alias(
    *,
    display: object,
    lane: object,
    over: object,
    mint_record: object = False,
) -> Result[DisplayAlias]:
    """UX aliases only. Workspace defaults stay a config-compiler layer."""
    if mint_record is True:
        return policy(
            "tab",
            "UI tabs may group project/workspace aliases; they must not mint a "
            "record (FR-W16; UX-DR8; DEC-0284)",
            given=repr(display),
            mints_record=False,
        )
    token = _fold(display)
    if token not in DISPLAY_ALIAS_KINDS:
        return invalid(
            "display",
            "display names project / workspace are UX aliases (FR-W16; DEC-0284)",
            given=repr(display),
        )
    lane_token = _fold(lane)
    if not isinstance(over, str) or over.strip() == "":
        return invalid(
            "over",
            "a display alias overlays ExperimentSpec fp1 (coordinated) or bot fp1 "
            "(governed) (FR-W16; DEC-0284)",
            given=repr(over),
        )
    if lane_token == WORKBENCH_LANE_COORDINATED:
        return Ok(DisplayAlias(display=token, lane=WORKBENCH_LANE_COORDINATED, over=over.strip()))
    if lane_token == WORKBENCH_LANE_GOVERNED:
        return Ok(DisplayAlias(display=token, lane=WORKBENCH_LANE_GOVERNED, over=over.strip()))
    return policy(
        "continuity",
        "there is no Project kind and no Workspace kind; QMB workspace defaults "
        "are a config-compiler layer, never identity (FR-W16; DEC-0284)",
        given=repr(lane),
        workspace_defaults_are_identity=WORKSPACE_DEFAULTS_ARE_IDENTITY,
        layer=WORKSPACE_DEFAULTS_LAYER,
    )
