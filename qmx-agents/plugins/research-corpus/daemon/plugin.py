"""research-corpus daemon half — PluginContext registrations (FR-Q71; FR-RES-01).

Imports contribution types from ``qma-core`` only. Never imports ``qma-daemon``,
``qmb``, or ``qmf-venue``. Binds the seed corpus through the daemon-owned
plain-file adapter at operator-principal load-config ``root_path``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from qma.core.plugins import PluginContext, graph_template_payload, skill_payload
from qma.core.ports.memory import MemoryCandidate, refuse_memory_promote
from qma.core.ports.model import DeploymentRecord
from qma.core.vocabulary.enums import ModelClass
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

_PLUGIN_ID = "research-corpus"
# Adapter key — technical archaeology, not product brand (DEC-0383).
_SOURCE_ID = "strats"


def _missing(memory_id: str) -> TypedRefusal:
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context={"field": "memory_id", "reason": "unknown memory", "given": memory_id},
    )


@dataclass
class ResearchDeskMemory:
    """First-party in-process MemoryProvider for the research desk.

    Not an external backend (GAP-0072 stays Deferred). Candidates are admitted.
    There is no promote operation.
    """

    store: dict[str, MemoryCandidate] = field(default_factory=dict[str, MemoryCandidate])

    def propose(self, candidate: MemoryCandidate) -> Result[MemoryCandidate]:
        return Ok(candidate)

    def admit(self, candidate: MemoryCandidate) -> Result[MemoryCandidate]:
        self.store[candidate.id] = candidate
        return Ok(candidate)

    def recall(self, scope: str, token_budget: int) -> Result[tuple[MemoryCandidate, ...]]:
        hits = tuple(item for item in self.store.values() if item.scope == scope)
        if token_budget == 0:
            return Ok(())
        return Ok(hits[:token_budget])

    def get(self, memory_id: str) -> Result[MemoryCandidate]:
        current = self.store.get(memory_id)
        if current is None:
            return _missing(memory_id)
        return Ok(current)

    def list(self, scope: str) -> Result[tuple[MemoryCandidate, ...]]:
        return Ok(tuple(item for item in self.store.values() if item.scope == scope))

    def history(self, memory_id: str) -> Result[tuple[MemoryCandidate, ...]]:
        current = self.store.get(memory_id)
        return Ok((current,) if current is not None else ())

    def supersede(self, memory_id: str, successor: MemoryCandidate) -> Result[MemoryCandidate]:
        self.store[successor.id] = successor
        self.store.pop(memory_id, None)
        return Ok(successor)

    def invalidate(self, memory_id: str) -> Result[MemoryCandidate]:
        current = self.store.get(memory_id)
        if current is None:
            return _missing(memory_id)
        return Ok(current)

    def expire(self, memory_id: str) -> Result[MemoryCandidate]:
        current = self.store.get(memory_id)
        if current is None:
            return _missing(memory_id)
        return Ok(current)

    def scopes(self) -> Result[tuple[str, ...]]:
        return Ok(tuple(sorted({item.scope for item in self.store.values()})))

    def promote(self, *_args: object, **_kwargs: object) -> Result[None]:
        return refuse_memory_promote()


def activate(ctx: PluginContext) -> None:
    """Register research-corpus contributions through the core surface."""
    ctx.register_memory_provider("research", ResearchDeskMemory())
    root_path = ctx.load_config.get("root_path")
    if not isinstance(root_path, str) or root_path.strip() == "":
        msg = (
            "research-corpus requires operator-principal plugin/daemon load config "
            "root_path as a filesystem path (not an env var, git path, venue secret, "
            "or qmb setting)"
        )
        raise ValueError(msg)
    source = ctx.plain_file_library_source(
        root_path=root_path.strip(),
        source_id=_SOURCE_ID,
        kind="plain_file_library",
    )
    ctx.register_knowledge_source(_SOURCE_ID, source)
    ctx.register_tool(
        "search",
        {
            "name": "search",
            "acts": ("search",),
            "kind": "plugin",
            "tags": ("knowledge", "read_only"),
        },
    )
    ctx.register_skill(
        "survey-skill",
        skill_payload(
            _PLUGIN_ID,
            "survey-skill",
            summary="Survey the seed corpus with literal search",
            body="Search and cite. Never promote a registered artifact.",
        ),
    )
    ctx.register_graph_template(
        "survey",
        graph_template_payload(
            _PLUGIN_ID,
            "survey",
            nodes=(
                {"id": "search", "kind": "task"},
                {"id": "cite", "kind": "task"},
            ),
            edges=({"from": "search", "to": "cite"},),
        ),
    )
    ctx.register_model_deployment(
        "corpus-reader",
        DeploymentRecord(
            deployment_id=f"{_PLUGIN_ID}:corpus-reader",
            model_class=ModelClass.WORKHORSE_GENERAL,
            context_tokens=8_000,
            supports_tools=True,
        ),
    )
