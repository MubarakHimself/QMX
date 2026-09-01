"""Zero-authority observability stack inventory (TN-15 / DEC-0200 / AR-83).

Compose + dashboard seeds under ``qmn/deploy/observability/`` — the ONLY VPS
surface allowed to use containers. The trading node stays a plain systemd
service and must run and pass with this stack stopped. DevOps surface only:
never imports ``qmn.host`` / ``qmn.doors``, never places or protects.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

__all__ = [
    "COMPOSE_FILE_NAME",
    "CONTAINER_IMAGES",
    "CONTAINER_RUNTIME_PIN",
    "DASHBOARD_SEED_NAMES",
    "EVIDENCE_METRICS_SCRAPE",
    "JOURNAL_NAMESPACE",
    "LOOPBACK_PORTS",
    "OBSERVABILITY_SERVICE_ACCOUNT",
    "OBSERVABILITY_STORAGE",
    "OBSERVABILITY_UNIT",
    "PINNED_IMAGE_REFS",
    "STACK_SURFACE",
    "ZERO_AUTHORITY_INVARIANTS",
    "StackInspection",
    "inspect_compose_text",
    "inspect_stack_tree",
    "list_required_files",
    "observability_root",
    "pinned_image_ref",
]

STACK_SURFACE: Final[str] = "qmn.deploy.observability"
COMPOSE_FILE_NAME: Final[str] = "compose.yml"
OBSERVABILITY_UNIT: Final[str] = "qmx-observability.service"
OBSERVABILITY_SERVICE_ACCOUNT: Final[str] = "qmxobs"
OBSERVABILITY_STORAGE: Final[str] = "/var/lib/qmx-observability"
JOURNAL_NAMESPACE: Final[str] = "qmn"

# Evidence HTTP listener the stack scrapes — loopback only (DEC-0200/DEC-0202).
# Port is stack configuration; the node binds the same address at boot.
EVIDENCE_METRICS_SCRAPE: Final[str] = "127.0.0.1:8787"

# Container runtime pin (external tool; not a Python dependency).
CONTAINER_RUNTIME_PIN: Final[Mapping[str, str]] = {
    "engine": "docker-ce",
    "engine_version": "28.3.3",
    "compose_plugin_version": "2.39.2",
}

# Pinned image tags — never floating (DEC-0200). Versions are implementation-gate
# evidence pins registered in DEPENDENCIES.md.
CONTAINER_IMAGES: Final[Mapping[str, Mapping[str, str]]] = {
    "prometheus": {
        "repository": "prom/prometheus",
        "tag": "v3.5.5",
        "licence": "Apache-2.0",
    },
    "grafana": {
        "repository": "grafana/grafana",
        "tag": "13.1.4",
        "licence": "AGPL-3.0-only",
    },
    "loki": {
        "repository": "grafana/loki",
        "tag": "3.7.7",
        "licence": "AGPL-3.0-only",
    },
    "promtail": {
        "repository": "grafana/promtail",
        "tag": "3.6.11",
        "licence": "AGPL-3.0-only",
    },
}

PINNED_IMAGE_REFS: Final[tuple[str, ...]] = tuple(
    f"{meta['repository']}:{meta['tag']}" for meta in CONTAINER_IMAGES.values()
)

LOOPBACK_PORTS: Final[Mapping[str, int]] = {
    "prometheus": 9090,
    "grafana": 3000,
    "loki": 3100,
}

DASHBOARD_SEED_NAMES: Final[tuple[str, ...]] = (
    "qmn-overview.json",
    "qmn-health-process.json",
)

ZERO_AUTHORITY_INVARIANTS: Final[tuple[str, ...]] = (
    "network_mode_host",
    "loopback_listen_only",
    "scrapes_metrics_path_only",
    "read_only_journal_namespace",
    "distinct_non_qmx_account",
    "own_storage_and_quota",
    "own_credentials_only",
    "no_node_write_path",
    "no_public_inbound",
    "node_runs_without_stack",
)

_REQUIRED_RELATIVE: Final[tuple[str, ...]] = (
    "compose.yml",
    "README.txt",
    "stack.py",
    "prometheus/prometheus.yml",
    "prometheus/alerts.yml",
    "loki/loki.yml",
    "promtail/promtail.yml",
    "grafana/provisioning/datasources/datasources.yml",
    "grafana/provisioning/dashboards/dashboards.yml",
    "grafana/dashboards/qmn-overview.json",
    "grafana/dashboards/qmn-health-process.json",
    "journald/qmn-namespace.conf",
    "quota.txt",
)


def observability_root(deploy_root: Path | None = None) -> Path:
    """Absolute path to ``qmn/deploy/observability/``."""
    if deploy_root is not None:
        return deploy_root
    return Path(__file__).resolve().parent


def pinned_image_ref(name: str) -> str:
    """Return ``repository:tag`` for a named stack image."""
    meta = CONTAINER_IMAGES[name]
    return f"{meta['repository']}:{meta['tag']}"


def list_required_files(root: Path | None = None) -> tuple[Path, ...]:
    """Every checked-in path the stack inventory requires."""
    base = observability_root(root)
    return tuple(base / rel for rel in _REQUIRED_RELATIVE)


@dataclass(frozen=True, slots=True)
class StackInspection:
    """Result of inspecting the compose file / tree."""

    ok: bool
    findings: tuple[str, ...]
    image_refs: tuple[str, ...]
    missing_files: tuple[str, ...]


def inspect_compose_text(text: str) -> tuple[str, ...]:
    """Return findings for a compose.yml body; empty means contract-ok."""
    findings: list[str] = []
    lowered = text.lower()

    if "network_mode: host" not in lowered and "network_mode:host" not in lowered:
        findings.append("compose must set network_mode: host (DEC-0200)")

    for name, meta in CONTAINER_IMAGES.items():
        ref = f"{meta['repository']}:{meta['tag']}"
        if ref not in text:
            findings.append(f"missing pinned image ref for {name}: {ref}")

    wildcard = ".".join(("0", "0", "0", "0"))
    for token in ("latest", "main", "master"):
        # Floating tags are forbidden; allow the word only inside comments.
        needle = f":{token}"
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or "repository" in stripped.lower():
                continue
            lower = stripped.lower()
            if needle in lower or lower.endswith(f"/{token}"):
                findings.append(f"floating tag fragment {needle!r} forbidden")
                break

    # Prometheus + Grafana declare listen addresses in compose command/env.
    # Loki declares them in loki/loki.yml — checked in inspect_stack_tree.
    for name, port in LOOPBACK_PORTS.items():
        if name == "loki":
            continue
        bind = f"127.0.0.1:{port}"
        if bind not in text:
            findings.append(f"loopback bind {bind} missing from compose")

    if f"{wildcard}:" in text or f"{wildcard}'" in text or f'{wildcard}"' in text:
        findings.append(f"compose must not bind {wildcard} (no public inbound)")

    if JOURNAL_NAMESPACE not in text and "qmn" not in text:
        findings.append("compose/promtail must reference journal namespace qmn")

    # Authority-free: no volume mounts into /var/lib/qmx node trees.
    forbidden_mounts = (
        "/var/lib/qmx/rooms",
        "/var/lib/qmx/state",
        "/var/lib/qmx/evidence",
        "/run/qmn",
    )
    for mount in forbidden_mounts:
        if mount in text:
            findings.append(f"compose must not mount node path {mount}")

    return tuple(dict.fromkeys(findings))


def inspect_stack_tree(root: Path | None = None) -> StackInspection:
    """Inspect the observability tree for AR-83 completeness."""
    base = observability_root(root)
    missing = tuple(
        rel for rel in _REQUIRED_RELATIVE if not (base / rel).is_file()
    )
    findings: list[str] = []
    if missing:
        findings.extend(f"missing required file: {rel}" for rel in missing)

    compose_path = base / COMPOSE_FILE_NAME
    image_refs: tuple[str, ...] = PINNED_IMAGE_REFS
    if compose_path.is_file():
        text = compose_path.read_text(encoding="utf-8")
        findings.extend(inspect_compose_text(text))
        present = tuple(ref for ref in PINNED_IMAGE_REFS if ref in text)
        image_refs = present

    loki_cfg = base / "loki" / "loki.yml"
    if loki_cfg.is_file():
        loki_text = loki_cfg.read_text(encoding="utf-8")
        if "http_listen_address: 127.0.0.1" not in loki_text:
            findings.append("loki.yml must listen on 127.0.0.1")
        if "http_listen_port: 3100" not in loki_text:
            findings.append("loki.yml must listen on port 3100")
        wildcard = ".".join(("0", "0", "0", "0"))
        if wildcard in loki_text:
            findings.append(f"loki.yml must not bind {wildcard}")

    promtail_cfg = base / "promtail" / "promtail.yml"
    if promtail_cfg.is_file():
        pt = promtail_cfg.read_text(encoding="utf-8")
        if JOURNAL_NAMESPACE not in pt:
            findings.append("promtail.yml must name journal namespace qmn")
        if "_SYSTEMD_UNIT=qmn.service" not in pt:
            findings.append("promtail.yml must match qmn.service only")

    quota = base / "quota.txt"
    if quota.is_file():
        body = quota.read_text(encoding="utf-8")
        if OBSERVABILITY_STORAGE not in body:
            findings.append("quota.txt must name /var/lib/qmx-observability")
        if "qmxobs" not in body:
            findings.append("quota.txt must name the qmxobs account")

    return StackInspection(
        ok=not findings,
        findings=tuple(findings),
        image_refs=image_refs,
        missing_files=missing,
    )
