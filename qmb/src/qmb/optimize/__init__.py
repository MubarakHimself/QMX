"""Parameter schema, pure sampler port, and sensitivity-analysis home (B-8).

The default sampler adapter is TPE-class, pinned by ``registry:qmb_sampler_pin``.
Adapters run ``n_jobs=1``: process fan-out belongs to the orchestrator, never
the sampler (DEC-0168, DEC-0161). The pin value lives in the registry and
the distribution manifest, never restated here.

The typed parameter-space schema is ONE schema, authoritative in the CT-33
Bot definition — B-8 reads it; QMB never keeps a second local copy
(DEC-0173, DEC-0183).
"""

from __future__ import annotations

from typing import Final

from qmf.core.refusal import Ok, Result, is_refusal
from qml.declaration.bot import BotDefinition
from qml.declaration.parameters import ParameterSpec

__all__ = [
    "SAMPLER_JOBS",
    "SAMPLER_PIN_KEY",
    "parameter_space_from_bot",
    "sampler_identity",
]

SAMPLER_PIN_KEY: Final[str] = "qmb_sampler_pin"
SAMPLER_JOBS: Final[int] = 1


def parameter_space_from_bot(declaration: object) -> Result[tuple[ParameterSpec, ...]]:
    """Read the CT-33-authoritative parameter-space schema (B-8, DEC-0183).

    Mandatory defaults are the Bot definition's canonical assignment. A swept
    non-default assignment is a B-3 run-spec override, never a silent new default.
    """
    if isinstance(declaration, BotDefinition):
        bot = declaration
    else:
        parsed = BotDefinition.try_from_mapping(declaration)
        if is_refusal(parsed):
            return parsed
        bot = parsed.value
    return Ok(tuple(bot.parameter_space))


def sampler_identity() -> dict[str, object]:
    """Identity-bearing sampler-port fields. Package SemVer is omitted."""
    return {
        "pin_key": SAMPLER_PIN_KEY,
        "jobs": SAMPLER_JOBS,
        "stepping": "generation-barrier",
    }
