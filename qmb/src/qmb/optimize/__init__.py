"""Parameter schema, pure sampler port, and sensitivity-analysis home (B-8).

The default sampler adapter is TPE-class, pinned by ``registry:qmb_sampler_pin``.
Adapters run ``n_jobs=1``: process fan-out belongs to the orchestrator, never
the sampler (DEC-0168, DEC-0161). The pin value lives in the registry and
the distribution manifest, never restated here.
"""

from __future__ import annotations

from typing import Final

__all__ = ["SAMPLER_JOBS", "SAMPLER_PIN_KEY", "sampler_identity"]

SAMPLER_PIN_KEY: Final[str] = "qmb_sampler_pin"
SAMPLER_JOBS: Final[int] = 1


def sampler_identity() -> dict[str, object]:
    """Identity-bearing sampler-port fields. Package SemVer is omitted."""
    return {
        "pin_key": SAMPLER_PIN_KEY,
        "jobs": SAMPLER_JOBS,
        "stepping": "generation-barrier",
    }
