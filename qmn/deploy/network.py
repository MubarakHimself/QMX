"""VPS network posture contract (FR-067/069 / NFR-14 / DEC-0201).

Inbound default-deny with three SSH identities; doors stay loopback / unix
socket; egress is an exhaustive allow-list. Observability exposes no public
inbound authority path. Pure data — no host mutation, no SSH.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

__all__ = [
    "EGRESS_ALLOW_CLASSES",
    "INBOUND_SSH_IDENTITIES",
    "LOOPBACK_ONLY_LISTENERS",
    "POWERS_TRANSPORT",
    "NetworkPosture",
    "default_network_posture",
    "validate_network_posture",
]

INBOUND_SSH_IDENTITIES: Final[tuple[str, ...]] = (
    "operator",
    "provisioning",
    "hub-inbox-write",
)

EGRESS_ALLOW_CLASSES: Final[frozenset[str]] = frozenset(
    {
        "ctrader",
        "notification-liveness-heartbeat",
        "backblaze-b2",
        "dukascopy-history",
        "forex-factory-news",
        "pinned-distribution-index",
        "observability-image-registry",
        "ntp",
    }
)

LOOPBACK_ONLY_LISTENERS: Final[frozenset[str]] = frozenset(
    {
        "evidence-http",
        "observability-prometheus",
        "observability-grafana",
        "observability-loki",
    }
)

POWERS_TRANSPORT: Final[str] = "unix-socket"


@dataclass(frozen=True, slots=True)
class NetworkPosture:
    """Declarative network posture validated by node-install check mode."""

    inbound_default: str
    ssh_identities: tuple[str, ...]
    ssh_password_auth: bool
    public_node_doors: bool
    powers_transport: str
    loopback_listeners: frozenset[str]
    egress_default: str
    egress_allow: frozenset[str]
    observability_public_inbound: bool

    def to_jsonable(self) -> dict[str, object]:
        return {
            "inbound_default": self.inbound_default,
            "ssh_identities": list(self.ssh_identities),
            "ssh_password_auth": self.ssh_password_auth,
            "public_node_doors": self.public_node_doors,
            "powers_transport": self.powers_transport,
            "loopback_listeners": sorted(self.loopback_listeners),
            "egress_default": self.egress_default,
            "egress_allow": sorted(self.egress_allow),
            "observability_public_inbound": self.observability_public_inbound,
        }


def default_network_posture() -> NetworkPosture:
    """Ratified VPS posture (DEC-0201 / DEC-0261)."""
    return NetworkPosture(
        inbound_default="deny",
        ssh_identities=INBOUND_SSH_IDENTITIES,
        ssh_password_auth=False,
        public_node_doors=False,
        powers_transport=POWERS_TRANSPORT,
        loopback_listeners=LOOPBACK_ONLY_LISTENERS,
        egress_default="deny",
        egress_allow=EGRESS_ALLOW_CLASSES,
        observability_public_inbound=False,
    )


def validate_network_posture(posture: NetworkPosture) -> tuple[str, ...]:
    """Return findings; empty means the posture matches the contract."""
    findings: list[str] = []
    if posture.inbound_default != "deny":
        findings.append(f"inbound_default={posture.inbound_default!r} expected 'deny'")
    if posture.egress_default != "deny":
        findings.append(f"egress_default={posture.egress_default!r} expected 'deny'")
    if posture.ssh_password_auth:
        findings.append("SSH password auth must be disabled (key-only)")
    if frozenset(posture.ssh_identities) != frozenset(INBOUND_SSH_IDENTITIES):
        findings.append(
            f"ssh_identities={posture.ssh_identities!r} "
            f"expected {INBOUND_SSH_IDENTITIES!r}"
        )
    if posture.public_node_doors:
        findings.append("node doors must not be public")
    if posture.powers_transport != POWERS_TRANSPORT:
        findings.append(
            f"powers_transport={posture.powers_transport!r} expected {POWERS_TRANSPORT!r}"
        )
    missing_listeners = LOOPBACK_ONLY_LISTENERS - posture.loopback_listeners
    if missing_listeners:
        findings.append(f"missing loopback listeners: {sorted(missing_listeners)}")
    extra_egress = posture.egress_allow - EGRESS_ALLOW_CLASSES
    missing_egress = EGRESS_ALLOW_CLASSES - posture.egress_allow
    if extra_egress:
        findings.append(f"egress allow-list has unknown classes: {sorted(extra_egress)}")
    if missing_egress:
        findings.append(f"egress allow-list missing classes: {sorted(missing_egress)}")
    if posture.observability_public_inbound:
        findings.append("observability must expose no public inbound authority path")
    return tuple(findings)
