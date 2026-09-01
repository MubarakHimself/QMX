"""Promotion and next-day activation (TN-20; Story 26.9).

Human-only promotion runs the silent battery and lands ADMITTED with no
intent, ledger, or exposure. Activation is a separate act that becomes
effective only at the next account-scoped day-boundary. Sandbox provenance
is refused at hub publish and at the promotion pull.
"""

from __future__ import annotations

from typing import Final

from qmn.promotion.battery import (
    ADMISSION_IMPACT_NONE,
    ADMISSION_IMPACT_RELINT,
    ADMISSION_IMPACT_RESIGN,
    ADMISSION_IMPACTS,
    DEMO_BASELINE_ENVIRONMENT,
    LIVE_BASELINE_ENVIRONMENT,
    AdmissionLayerFreshState,
    BatteryCheck,
    BatteryCheckId,
    ConfigGateFreshState,
    Ct18CapabilityFreshState,
    IdentityFingerprints,
    LiveBaselineFreshState,
    PromotionFreshState,
    ProtectionFreshState,
    SilentBatteryReport,
    live_gating_from_config,
    revalidate_fresh_state,
    run_silent_battery,
)
from qmn.promotion.hub import (
    HUB_CROSSINGS,
    SANDBOX_PROVENANCE,
    HubArtifact,
    PublishedHub,
    publish_hub_fragment,
    pull_published_as_of,
    refuse_sandbox_provenance,
)
from qmn.promotion.lifecycle import (
    AGENT_SIGNER_PREFIXES,
    FORBIDDEN_ACTIVATION_OVERRIDES,
    SAME_DAY_TRADE_PATH_EXISTS,
    ActivationAcceptance,
    ActivationReadiness,
    PromotionLanding,
    admit_first_intent,
    promote_to_admitted,
    refuse_invented_ksa_or_latency,
    request_activation,
    revalidate_before_first_intent,
)

__all__ = [
    "ADMISSION_IMPACTS",
    "ADMISSION_IMPACT_NONE",
    "ADMISSION_IMPACT_RELINT",
    "ADMISSION_IMPACT_RESIGN",
    "AGENT_SIGNER_PREFIXES",
    "DEMO_BASELINE_ENVIRONMENT",
    "FORBIDDEN_ACTIVATION_OVERRIDES",
    "HUB_CROSSINGS",
    "LIVE_BASELINE_ENVIRONMENT",
    "PROMOTION_SURFACE",
    "SAME_DAY_TRADE_PATH_EXISTS",
    "SANDBOX_PROVENANCE",
    "ActivationAcceptance",
    "ActivationReadiness",
    "AdmissionLayerFreshState",
    "BatteryCheck",
    "BatteryCheckId",
    "ConfigGateFreshState",
    "Ct18CapabilityFreshState",
    "HubArtifact",
    "IdentityFingerprints",
    "LiveBaselineFreshState",
    "PromotionFreshState",
    "PromotionLanding",
    "ProtectionFreshState",
    "PublishedHub",
    "SilentBatteryReport",
    "admit_first_intent",
    "live_gating_from_config",
    "promote_to_admitted",
    "publish_hub_fragment",
    "pull_published_as_of",
    "refuse_invented_ksa_or_latency",
    "refuse_sandbox_provenance",
    "request_activation",
    "revalidate_before_first_intent",
    "revalidate_fresh_state",
    "run_silent_battery",
]

PROMOTION_SURFACE: Final[str] = "qmn.promotion"
