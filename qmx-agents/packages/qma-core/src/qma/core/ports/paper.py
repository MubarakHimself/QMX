"""Paper trinity, hub write law, notebooks, and alias identity (Story 36.6).

research-paper is governed QMB replay (``world=replay``) outside the node.
node-paper remains COMP-QMN / CONNECT Book-level demo routing. QMA-paper does
not exist: no execution tool at any account role, paper-only included.
QMA never writes the B-15 hub; it holds candidate refs. Promotion stays a
human act outside QMA. Display names project/workspace are UX aliases.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Literal, cast

from qma.core.barriers.money_path import is_money_path_act_denied
from qma.core.vocabulary.enums import ExecutionEnvironmentKind
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "CONTROLLED_ROOM_HOST",
    "DISPLAY_ALIAS_KINDS",
    "EPIC_PROMOTION_AUTHORITY",
    "EXPLORATORY_NOTEBOOK_IMPORTS",
    "HUB_CROSSINGS",
    "HUB_PUBLISH_PRINCIPAL",
    "NODE_PAPER_ACCOUNT_ROLE",
    "NODE_PAPER_OWNER",
    "NODE_PAPER_WORLD",
    "NOTEBOOK_NEW_COMP",
    "PAPER_NOUN_NODE",
    "PAPER_NOUN_RESEARCH",
    "PER_BOT_PAPER_LANE_ON_NODE",
    "PINNED_JUPYTER_PRODUCT",
    "QMA_PAPER_EXISTS",
    "QMA_PAPER_TOKENS",
    "QMA_WRITES_HUB",
    "QMB_NOTEBOOK_MODULE",
    "QUANTCONNECT_PAPER_IS_QMX_LANE",
    "RESEARCH_PAPER_OWNER",
    "RESEARCH_PAPER_WORLD",
    "SANDBOX_PROVENANCE",
    "UI_TAB_MINTS_RECORD",
    "DisplayAlias",
    "ExploratoryNotebook",
    "HubCandidateRef",
    "ManagedInterpreter",
    "PaperNoun",
    "admit_exploratory_notebook",
    "admit_hub_candidate_ref",
    "admit_managed_interpreter",
    "is_qma_paper_token",
    "match_qma_paper_tool",
    "mint_ui_tab_record",
    "name_paper_noun",
    "notebook_joins_undertaking",
    "refuse_hub_publish_from_qma",
    "refuse_jupyter_product",
    "refuse_notebook_comp",
    "refuse_per_bot_paper_lane",
    "refuse_qma_hub_write",
    "refuse_qma_paper",
    "refuse_qma_promotion",
    "refuse_qmb_notebook_module",
    "refuse_quantconnect_paper",
    "refuse_sandbox_provenance",
    "resolve_display_alias",
]


class PaperNoun(StrEnum):
    """The two paper nouns that exist. QMA-paper is not a member."""

    RESEARCH_PAPER = "research-paper"
    NODE_PAPER = "node-paper"


PAPER_NOUN_RESEARCH: Final[str] = PaperNoun.RESEARCH_PAPER.value
PAPER_NOUN_NODE: Final[str] = PaperNoun.NODE_PAPER.value
QMA_PAPER_EXISTS: Final[Literal[False]] = False
QUANTCONNECT_PAPER_IS_QMX_LANE: Final[Literal[False]] = False
PER_BOT_PAPER_LANE_ON_NODE: Final[Literal[False]] = False
EPIC_PROMOTION_AUTHORITY: Final[Literal[False]] = False
QMA_WRITES_HUB: Final[Literal[False]] = False
HUB_PUBLISH_PRINCIPAL: Final[str] = "human"
SANDBOX_PROVENANCE: Final[str] = "sandbox"
HUB_CROSSINGS: Final[frozenset[str]] = frozenset({"publish", "pull"})
RESEARCH_PAPER_WORLD: Final[str] = "replay"
RESEARCH_PAPER_OWNER: Final[str] = "COMP-QMB"
NODE_PAPER_OWNER: Final[str] = "COMP-QMN"
NODE_PAPER_ACCOUNT_ROLE: Final[str] = "demo"
NODE_PAPER_WORLD: Final[str] = "live"
CONTROLLED_ROOM_HOST: Final[str] = "controlled-room"
EXPLORATORY_NOTEBOOK_IMPORTS: Final[frozenset[str]] = frozenset({"qmb", "qml"})
PINNED_JUPYTER_PRODUCT: Final[Literal[False]] = False
QMB_NOTEBOOK_MODULE: Final[Literal[False]] = False
NOTEBOOK_NEW_COMP: Final[Literal[False]] = False
DISPLAY_ALIAS_KINDS: Final[frozenset[str]] = frozenset({"project", "workspace"})
LANE_COORDINATED: Final[str] = "coordinated"
LANE_GOVERNED: Final[str] = "governed"
UI_TAB_MINTS_RECORD: Final[Literal[False]] = False
QMA_PAPER_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "qma-paper",
        "qma_paper",
        "qmapaper",
        "agent-paper",
        "agent_paper",
        "quantconnect-paper",
        "quantconnect_paper",
        "lean-paper",
        "lean_paper",
        "paper-brokerage",
        "paper_brokerage",
    }
)
_QMA_PAPER_ALIASES: Final[frozenset[str]] = QMA_PAPER_TOKENS | frozenset(
    {"qma paper", "agent paper", "paper only qma", "qma-paper-lane"}
)
_NODE_LOCATIONS: Final[frozenset[str]] = frozenset(
    {"node", "qmn", "comp-qmn", "trading-node", "trading_node"}
)
_OUTSIDE_NODE: Final[frozenset[str]] = frozenset(
    {"outside_node", "outside-node", "qmb", "comp-qmb", "research", "workbench"}
)
_RLM_KERNEL_TOKENS: Final[frozenset[str]] = frozenset(
    {"rlm_kernel", "rlm-kernel", "analysis_rlm_kernel", "analysis-rlm-kernel"}
)
_JUPYTER_PRODUCTS: Final[frozenset[str]] = frozenset(
    {
        "jupyter",
        "jupyterlab",
        "notebook",
        "colab",
        "google_colab",
        "hosted_jupyter",
        "jupyterhub",
        "jupyterhub_saas",
        "sagemaker_studio",
        "databricks_notebook",
        "kaggle_notebook",
        "pinned_jupyter",
    }
)
_HUB_WRITE_ACTS: Final[frozenset[str]] = frozenset(
    {
        "hub_write",
        "hub.write",
        "write_hub",
        "hub_publish",
        "hub.publish",
        "inbox_append",
        "hub_inbox",
    }
)
_FP1_PREFIX: Final[str] = "fp1:"


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def _normalize(value: object) -> str:
    if isinstance(value, str):
        token = value.strip().casefold().replace(" ", "_").replace("-", "_")
        while "__" in token:
            token = token.replace("__", "_")
        return token.strip("_")
    return ""


def is_qma_paper_token(value: object) -> bool:
    """True when ``value`` names the nonexistent QMA-paper lane."""
    token = _normalize(value).replace("_", "-")
    underscored = {item.replace("-", "_") for item in QMA_PAPER_TOKENS}
    return token in QMA_PAPER_TOKENS or _normalize(value) in underscored


def match_qma_paper_tool(
    *,
    tool_id: object = None,
    acts: object = (),
    tags: object = (),
    schema: Mapping[str, object] | None = None,
) -> str | None:
    """Return the matched QMA-paper token, or ``None`` when the tool is not that lane."""
    candidates: list[object] = [tool_id]
    if isinstance(acts, (str, bytes)):
        candidates.append(acts)
    elif isinstance(acts, Iterable):
        candidates.extend(cast("Iterable[object]", acts))
    if isinstance(tags, (str, bytes)):
        candidates.append(tags)
    elif isinstance(tags, Iterable):
        candidates.extend(cast("Iterable[object]", tags))
    if schema is not None:
        candidates.append(schema.get("name"))
        candidates.append(schema.get("lane"))
        candidates.append(schema.get("paper"))
    for item in candidates:
        if item is None:
            continue
        token = str(item)
        if is_qma_paper_token(token):
            return _normalize(token).replace("_", "-")
        folded = _normalize(token)
        for banned in QMA_PAPER_TOKENS:
            needle = banned.replace("-", "_")
            if needle in folded:
                return banned
    return None


def refuse_qma_paper(
    *,
    tool_id: object | None = None,
    given: object = "qma-paper",
    account_role: object = None,
) -> TypedRefusal:
    """QMA-paper does not exist — no execution tool at any account role (DEC-0275)."""
    return _policy(
        "paper",
        "QMA-paper does not exist; any QMA execution tool at any account role, "
        "paper only included, is refused (FR-W13; DEC-0275; DEC-0341)",
        given=repr(given),
        tool_id=None if tool_id is None else str(tool_id),
        account_role=None if account_role is None else str(account_role),
        exists=QMA_PAPER_EXISTS,
        research_paper=PAPER_NOUN_RESEARCH,
        node_paper=PAPER_NOUN_NODE,
        node_paper_owner=NODE_PAPER_OWNER,
    )


def refuse_quantconnect_paper(*, given: object = "quantconnect-paper") -> TypedRefusal:
    """QuantConnect paper-brokerage is not a QMX lane."""
    return _policy(
        "paper",
        "QuantConnect paper-brokerage is not a QMX lane (FR-W13; DEC-0275)",
        given=repr(given),
        is_qmx_lane=QUANTCONNECT_PAPER_IS_QMX_LANE,
    )


def refuse_per_bot_paper_lane(*, given: object = "per-bot-paper-lane") -> TypedRefusal:
    """Node-paper stays Book-level; this epic mints no per-bot paper lane."""
    return _policy(
        "paper",
        "node-paper remains COMP-QMN / CONNECT Book-level demo routing plus soak; "
        "no per-bot paper lane is introduced (FR-W13; DEC-0261; DEC-0275)",
        given=repr(given),
        per_bot_paper_lane=PER_BOT_PAPER_LANE_ON_NODE,
        node_paper_owner=NODE_PAPER_OWNER,
        account_role=NODE_PAPER_ACCOUNT_ROLE,
        world=NODE_PAPER_WORLD,
    )


def name_paper_noun(
    *,
    world: object,
    location: object = "outside_node",
    role: object = None,
    account_role: object = None,
    noun: object = None,
) -> Result[str]:
    """Name a paper noun. QMA-paper and collapsed papers are refused."""
    if noun is not None:
        asked = _normalize(noun).replace("_", "-")
        if is_qma_paper_token(noun) or asked in {"qma-paper", "agent-paper"}:
            return refuse_qma_paper(given=noun)
        if asked in {"quantconnect-paper", "lean-paper", "paper-brokerage"}:
            return refuse_quantconnect_paper(given=noun)
        if asked in {"per-bot-paper", "per-bot-paper-lane", "bot-paper"}:
            return refuse_per_bot_paper_lane(given=noun)
        if asked == PAPER_NOUN_NODE:
            loc = _normalize(location).replace("_", "-")
            if loc not in _NODE_LOCATIONS and loc != "node":
                return _policy(
                    "paper",
                    "node-paper is COMP-QMN Book-level demo routing; a QMB replay "
                    "outside the node is research-paper (FR-W13; DEC-0275)",
                    given=repr(noun),
                    location=repr(location),
                    owner=NODE_PAPER_OWNER,
                )
        if asked not in {PAPER_NOUN_RESEARCH, PAPER_NOUN_NODE}:
            return _invalid(
                "paper",
                "paper nouns are research-paper and node-paper; QMA-paper does not exist",
                given=repr(noun),
            )
    loc = _normalize(location).replace("_", "-")
    world_token = _normalize(world)
    role_token = _normalize(role if account_role is None else account_role)
    if loc in _NODE_LOCATIONS:
        if world_token == RESEARCH_PAPER_WORLD:
            return _policy(
                "paper",
                "governed QMB replay (world=replay) outside the node is "
                "research-paper, not node-paper (FR-W13; DEC-0275)",
                world=world_token,
                location=loc,
                owner=RESEARCH_PAPER_OWNER,
            )
        if role_token and role_token not in {NODE_PAPER_ACCOUNT_ROLE, ""}:
            return refuse_per_bot_paper_lane(given=role_token)
        if world_token not in {NODE_PAPER_WORLD, ""}:
            return _invalid(
                "world",
                "node-paper is role=demo, world=live (FR-W13; DEC-0275)",
                given=repr(world),
            )
        return Ok(PAPER_NOUN_NODE)
    if loc not in _OUTSIDE_NODE and loc not in {"", "outside-node"}:
        return _invalid(
            "location",
            "paper location is outside the node (research-paper) or the node (node-paper)",
            given=repr(location),
        )
    if world_token != RESEARCH_PAPER_WORLD:
        return _invalid(
            "world",
            "research-paper is governed QMB replay with world=replay outside the node "
            "(FR-W13; DEC-0275)",
            given=repr(world),
            owner=RESEARCH_PAPER_OWNER,
        )
    return Ok(PAPER_NOUN_RESEARCH)


def refuse_qma_hub_write(*, act: object = "hub_write", given: object = None) -> TypedRefusal:
    """QMA never writes the B-15 hub; it holds candidate refs only."""
    return _policy(
        "hub",
        "QMA never writes the B-15 hub; it holds candidate refs only. "
        "hub_publish is human and sandbox-provenance stays refused at publish "
        "and pull (FR-W14; DEC-0275)",
        act=str(act),
        given=repr(given),
        writes_hub=QMA_WRITES_HUB,
        hub_publish_principal=HUB_PUBLISH_PRINCIPAL,
        holds="candidate_refs",
    )


def refuse_hub_publish_from_qma(*, given: object = "hub_publish") -> TypedRefusal:
    """hub_publish is a human act, never a QMA write."""
    return refuse_qma_hub_write(act="hub_publish", given=given)


def refuse_sandbox_provenance(*, provenance: object, crossing: object) -> Result[None]:
    """Refuse ``provenance=sandbox`` at publish and pull (TN-20; DEC-0275)."""
    gate = _normalize(crossing)
    if gate not in HUB_CROSSINGS:
        return _invalid(
            "crossing",
            "sandbox provenance is refused at publish and at pull (FR-W14; DEC-0275)",
            given=repr(crossing),
            allowed=sorted(HUB_CROSSINGS),
        )
    if _normalize(provenance) != SANDBOX_PROVENANCE:
        return Ok(None)
    return _policy(
        "provenance",
        f"sandbox provenance is refused at {gate} (FR-W14; DEC-0275; DEC-0188)",
        provenance=SANDBOX_PROVENANCE,
        crossing=gate,
    )


@dataclass(frozen=True, slots=True)
class HubCandidateRef:
    """A hub candidate reference. QMA stores the ref; it does not write the hub."""

    ref: str
    writes_hub: Literal[False] = False
    hub_publish_principal: str = HUB_PUBLISH_PRINCIPAL

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "ref": self.ref,
                "writes_hub": self.writes_hub,
                "hub_publish_principal": self.hub_publish_principal,
            }
        )


def admit_hub_candidate_ref(ref: object, *, act: object = None) -> Result[HubCandidateRef]:
    """Admit a candidate ``_ref``. Hub writes and hub_publish stay refused."""
    token = _normalize(act).replace("_", ".") if act is not None else ""
    if act is not None and (
        token in {item.replace("_", ".") for item in _HUB_WRITE_ACTS} or is_qma_paper_token(act)
    ):
        return refuse_qma_hub_write(act=act, given=ref)
    if not isinstance(ref, str) or ref.strip() == "":
        return _invalid(
            "ref",
            "QMA holds hub candidate refs only; a ref is a non-empty string (FR-W14; DEC-0275)",
            given=repr(ref),
        )
    folded_ref = ref.strip().casefold()
    if (
        not folded_ref.endswith("_ref")
        and _FP1_PREFIX not in folded_ref
        and (_normalize(ref) in _HUB_WRITE_ACTS or "inbox" in _normalize(ref))
    ):
        return refuse_qma_hub_write(act=ref, given=ref)
    return Ok(HubCandidateRef(ref=ref.strip()))


def refuse_qmb_notebook_module(*, given: object = "qmb.notebook") -> TypedRefusal:
    """A managed notebook lifecycle is not a QMB module."""
    return _policy(
        "notebook",
        "a managed interpreter lifecycle is a QMA ExecutionEnvironment, not a "
        "QMB module (FR-W15; DEC-0279)",
        given=repr(given),
        qmb_module=QMB_NOTEBOOK_MODULE,
        owner="COMP-QMA-CORE",
    )


def refuse_notebook_comp(*, given: object = "COMP-NOTEBOOK") -> TypedRefusal:
    """Notebooks mint no new COMP."""
    return _policy(
        "notebook",
        "a managed interpreter lifecycle is not a new COMP (FR-W15; DEC-0279)",
        given=repr(given),
        new_comp=NOTEBOOK_NEW_COMP,
    )


def refuse_jupyter_product(*, given: object = "jupyter") -> TypedRefusal:
    """No pinned Jupyter product."""
    return _policy(
        "notebook",
        "a managed interpreter lifecycle is not a pinned Jupyter product (FR-W15; DEC-0279)",
        given=repr(given),
        pinned_jupyter=PINNED_JUPYTER_PRODUCT,
    )


@dataclass(frozen=True, slots=True)
class ExploratoryNotebook:
    """Ungoverned notebook on a controlled-room host: ``import qmb`` / ``import qml``."""

    host: str
    imports: tuple[str, ...]
    ungoverned: bool = True
    mints_identity: bool = False

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "host": self.host,
                "imports": list(self.imports),
                "ungoverned": self.ungoverned,
                "mints_identity": self.mints_identity,
            }
        )


def admit_exploratory_notebook(
    *,
    imports: object,
    host: object = CONTROLLED_ROOM_HOST,
    jupyter_product: object = None,
    qmb_module: object = False,
    new_comp: object = None,
) -> Result[ExploratoryNotebook]:
    """Admit ``import qmb`` / ``import qml`` on a controlled-room host."""
    if jupyter_product is not None:
        return refuse_jupyter_product(given=jupyter_product)
    if qmb_module is True:
        return refuse_qmb_notebook_module()
    if new_comp is not None:
        return refuse_notebook_comp(given=new_comp)
    host_token = _normalize(host).replace("_", "-")
    if host_token != CONTROLLED_ROOM_HOST:
        return _policy(
            "host",
            "exploratory notebooks import qmb / import qml on a controlled-room "
            "host (FR-W15; DEC-0279)",
            given=repr(host),
            required=CONTROLLED_ROOM_HOST,
        )
    if isinstance(imports, str):
        items = (imports,)
    elif isinstance(imports, Sequence) and not isinstance(imports, (bytes, bytearray)):
        items = tuple(str(item) for item in cast("Sequence[object]", imports))
    else:
        return _invalid("imports", "notebook imports are qmb and/or qml", given=repr(imports))
    admitted: list[str] = []
    for item in items:
        token = item.strip().casefold()
        if token in _JUPYTER_PRODUCTS:
            return refuse_jupyter_product(given=item)
        if token not in EXPLORATORY_NOTEBOOK_IMPORTS:
            return _policy(
                "imports",
                "exploratory notebooks import qmb / import qml (FR-W15; DEC-0279)",
                given=item,
                allowed=sorted(EXPLORATORY_NOTEBOOK_IMPORTS),
            )
        admitted.append(token)
    if not admitted:
        return _invalid("imports", "exploratory notebooks import qmb / import qml")
    return Ok(
        ExploratoryNotebook(
            host=CONTROLLED_ROOM_HOST,
            imports=tuple(dict.fromkeys(admitted)),
        )
    )


@dataclass(frozen=True, slots=True)
class ManagedInterpreter:
    """Product-owned interpreter lifecycle: a QMA ExecutionEnvironment."""

    kind: str
    owner: str = "qma"
    qmb_module: Literal[False] = False
    new_comp: Literal[False] = False
    pinned_jupyter: Literal[False] = False

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "kind": self.kind,
                "owner": self.owner,
                "qmb_module": self.qmb_module,
                "new_comp": self.new_comp,
                "pinned_jupyter": self.pinned_jupyter,
            }
        )


def admit_managed_interpreter(
    *,
    kind: object,
    owner: object = "qma",
    as_qmb_module: object = False,
    as_comp: object = None,
    jupyter_product: object = None,
) -> Result[ManagedInterpreter]:
    """A managed interpreter, if product-owned, is a QMA ExecutionEnvironment."""
    if as_qmb_module is True:
        return refuse_qmb_notebook_module(given=kind)
    if as_comp is not None:
        return refuse_notebook_comp(given=as_comp)
    jupyter_given = jupyter_product if jupyter_product is not None else kind
    if jupyter_product is not None or _normalize(kind) in _JUPYTER_PRODUCTS:
        return refuse_jupyter_product(given=jupyter_given)
    owner_token = _normalize(owner)
    if owner_token not in {"qma", "qma-daemon", "qma_core", "comp-qma-core", "comp-qma-daemon"}:
        return _policy(
            "owner",
            "a managed interpreter lifecycle is a QMA ExecutionEnvironment (FR-W15; DEC-0279)",
            given=repr(owner),
        )
    if isinstance(kind, ExecutionEnvironmentKind):
        return Ok(ManagedInterpreter(kind=kind.value))
    token = _normalize(kind)
    if token in _RLM_KERNEL_TOKENS:
        return Ok(ManagedInterpreter(kind="rlm_kernel"))
    try:
        parsed = parse_closed(ExecutionEnvironmentKind, kind)
    except VocabularyError:
        return _invalid(
            "kind",
            "a managed interpreter is an ExecutionEnvironment kind or the Analysis "
            "RLM kernel (FR-W15; DEC-0279)",
            given=repr(kind),
        )
    return Ok(ManagedInterpreter(kind=parsed.value))


def notebook_joins_undertaking(
    *,
    as_identity: object = False,
    as_code_ref: object = False,
    as_environment_session: object = False,
) -> Result[str]:
    """A notebook file is not a fourth identity; it joins as code_ref or env session."""
    if as_identity is True:
        return _policy(
            "notebook",
            "a notebook file is an ungoverned working surface; it joins the "
            "undertaking only as code_ref or as an ExecutionEnvironment session, "
            "not as a fourth identity (FR-W16; DEC-0284)",
            fourth_identity=False,
        )
    if as_code_ref is True:
        return Ok("code_ref")
    if as_environment_session is True:
        return Ok("environment_session")
    return _invalid(
        "notebook",
        "a notebook joins as code_ref or as an ExecutionEnvironment session (FR-W16; DEC-0284)",
    )


@dataclass(frozen=True, slots=True)
class DisplayAlias:
    """UX alias over ExperimentSpec (coordinated) or bot fp1 (governed)."""

    display: str
    lane: str
    over: str
    mints_record: Literal[False] = False

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "display": self.display,
                "lane": self.lane,
                "over": self.over,
                "mints_record": self.mints_record,
            }
        )


def resolve_display_alias(
    *,
    display: object,
    lane: object,
    over: object,
    mint_record: object = False,
) -> Result[DisplayAlias]:
    """project/workspace are UX aliases. UI tabs must not mint a record."""
    if mint_record is True:
        return mint_ui_tab_record(display=display)
    token = _normalize(display)
    if token not in DISPLAY_ALIAS_KINDS:
        return _invalid(
            "display",
            "display names project / workspace are UX aliases (FR-W16; DEC-0284)",
            given=repr(display),
            allowed=sorted(DISPLAY_ALIAS_KINDS),
        )
    lane_token = _normalize(lane)
    if lane_token == LANE_COORDINATED:
        if not isinstance(over, str) or over.strip() == "":
            return _invalid(
                "over",
                "coordinated display aliases overlay ExperimentSpec fp1 (FR-W16; DEC-0284)",
                given=repr(over),
            )
        return Ok(DisplayAlias(display=token, lane=LANE_COORDINATED, over=over.strip()))
    if lane_token == LANE_GOVERNED:
        if not isinstance(over, str) or over.strip() == "":
            return _invalid(
                "over",
                "governed display aliases overlay a bot fp1 (FR-W16; DEC-0284)",
                given=repr(over),
            )
        return Ok(DisplayAlias(display=token, lane=LANE_GOVERNED, over=over.strip()))
    if lane_token in {"ungoverned", "project", "workspace"}:
        return _policy(
            "continuity",
            "there is no Project kind and no Workspace kind; display names are "
            "UX aliases over ExperimentSpec (coordinated) or bot fp1 (governed) "
            "(FR-W16; DEC-0284)",
            given=repr(lane),
            refused=sorted(DISPLAY_ALIAS_KINDS),
        )
    return _invalid(
        "lane",
        "display aliases overlay ExperimentSpec (coordinated) or bot fp1 (governed)",
        given=repr(lane),
    )


def mint_ui_tab_record(*, display: object = "tab") -> TypedRefusal:
    """UI tabs group aliases; they must not mint a record."""
    return _policy(
        "tab",
        "UI tabs may group project/workspace aliases; they must not mint a "
        "record (FR-W16; UX-DR8; DEC-0284)",
        given=repr(display),
        mints_record=UI_TAB_MINTS_RECORD,
    )


def refuse_qma_promotion(*, given: object = "promote") -> TypedRefusal:
    """Promotion remains a human act outside QMA onto the node."""
    _ = is_money_path_act_denied("promote")
    return _policy(
        "promotion",
        "promotion remains a human act outside QMA onto the node; this epic "
        "grants no promotion authority (FR-W02; UX-DR3; DEC-0285)",
        given=repr(given),
        epic_authority=EPIC_PROMOTION_AUTHORITY,
        promote_reserved="human_live_zone",
    )
