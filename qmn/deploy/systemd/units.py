"""Systemd unit template inventory, render, and IaC/security inspection.

DevOps surface only (TN-16 / AR-78 / NFR-14). Never imports the composition
root or doors. Tests exercise check-mode rendering against fixtures — no SSH,
no live Contabo host.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

__all__ = [
    "CREDENTIAL_SEAL_FLAG",
    "FORBIDDEN_SEAL_FLAG",
    "HARDENING_KEYS",
    "NODE_SERVICE_ACCOUNT",
    "NODE_UNIT_ROLES",
    "OBSERVABILITY_SERVICE_ACCOUNT",
    "OBSERVABILITY_UNIT",
    "POWERS_SOCKET_PATH",
    "READ_WRITE_PATHS_NODE",
    "READ_WRITE_PATHS_OBS",
    "REQUIRED_RESTRICT_FAMILIES",
    "TEMPLATES_DIR",
    "WRITABLE_TREE_NAMES",
    "UnitInspection",
    "duration_to_systemd_sec",
    "inspect_rendered_units",
    "inspect_unit_text",
    "list_template_files",
    "node_unit_names",
    "render_all_templates",
    "render_template",
    "templates_dir",
]

TEMPLATES_DIR: Final[str] = "templates"
NODE_SERVICE_ACCOUNT: Final[str] = "qmx"
OBSERVABILITY_SERVICE_ACCOUNT: Final[str] = "qmxobs"
OBSERVABILITY_UNIT: Final[str] = "qmx-observability.service"
POWERS_SOCKET_PATH: Final[str] = "/run/qmn/powers.sock"
READ_WRITE_PATHS_NODE: Final[str] = "/var/lib/qmx"
READ_WRITE_PATHS_OBS: Final[str] = "/var/lib/qmx-observability"
REQUIRED_RESTRICT_FAMILIES: Final[frozenset[str]] = frozenset(
    {"AF_UNIX", "AF_INET", "AF_INET6"}
)
HARDENING_KEYS: Final[frozenset[str]] = frozenset(
    {
        "ProtectSystem",
        "NoNewPrivileges",
        "PrivateTmp",
        "ProtectHome",
        "RestrictAddressFamilies",
        "ReadWritePaths",
    }
)
CREDENTIAL_SEAL_FLAG: Final[str] = "--with-key=host"
FORBIDDEN_SEAL_FLAG: Final[str] = "--with-key=auto"

WRITABLE_TREE_NAMES: Final[tuple[str, ...]] = (
    "rooms",
    "evidence",
    "hub-inbox",
    "hub-published",
    "archive",
    "state",
    "staging",
)

# Five node unit *roles* (service + paired timers where applicable).
NODE_UNIT_ROLES: Final[tuple[str, ...]] = (
    "qmn",
    "qmn-news-calendar",
    "qmn-backup",
    "qmn-restore-sample",
    "qmn-restore-full",
)

_PLACEHOLDER_DRAIN: Final[str] = "@DRAIN_WINDOW_SEC@"
_PLACEHOLDER_WATCHDOG: Final[str] = "@WATCHDOG_INTERVAL_SEC@"
_DURATION_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>ns|us|µs|ms|s|m|h|d)?\s*$",
    re.IGNORECASE,
)


def templates_dir(deploy_root: Path | None = None) -> Path:
    """Absolute path to checked-in unit templates."""
    root = deploy_root if deploy_root is not None else Path(__file__).resolve().parent
    return root / TEMPLATES_DIR


def list_template_files(deploy_root: Path | None = None) -> tuple[Path, ...]:
    """Every template file under templates/, sorted."""
    directory = templates_dir(deploy_root)
    return tuple(sorted(p for p in directory.iterdir() if p.is_file()))


def node_unit_names() -> frozenset[str]:
    """Rendered unit basenames that count as the five node units."""
    names: set[str] = {"qmn.service"}
    for role in NODE_UNIT_ROLES:
        if role == "qmn":
            continue
        names.add(f"{role}.service")
        names.add(f"{role}.timer")
    return frozenset(names)


def duration_to_systemd_sec(value: object) -> str:
    """Render a duration into a systemd seconds token (e.g. ``30s``).

    Accepts integer/float seconds, or strings like ``30s`` / ``5m`` / ``1h``.
    Refuses blank or unknown shapes — blank drain/watchdog blocks boot.
    """
    if value is None:
        raise ValueError("duration value is blank")
    if isinstance(value, bool):
        raise ValueError("duration value must not be bool")
    if isinstance(value, (int, float)):
        if value <= 0:
            raise ValueError("duration value must be positive")
        seconds = int(value) if float(value).is_integer() else float(value)
        return f"{seconds}s"
    text = str(value).strip()
    if not text:
        raise ValueError("duration value is blank")
    match = _DURATION_RE.match(text)
    if match is None:
        raise ValueError(f"unrecognized duration: {text!r}")
    amount = float(match.group("value"))
    unit = (match.group("unit") or "s").lower()
    multipliers = {
        "ns": 1e-9,
        "us": 1e-6,
        "µs": 1e-6,
        "ms": 1e-3,
        "s": 1.0,
        "m": 60.0,
        "h": 3600.0,
        "d": 86400.0,
    }
    seconds = amount * multipliers[unit]
    if seconds <= 0:
        raise ValueError("duration value must be positive")
    if seconds == int(seconds):
        return f"{int(seconds)}s"
    return f"{seconds}s"


def render_template(
    template_text: str,
    *,
    drain_window: object | None = None,
    watchdog_interval: object | None = None,
) -> str:
    """Substitute rendered TimeoutStopSec / WatchdogSec placeholders."""
    out = template_text
    if _PLACEHOLDER_DRAIN in out:
        if drain_window is None:
            raise ValueError("drain_window required to render TimeoutStopSec")
        out = out.replace(_PLACEHOLDER_DRAIN, duration_to_systemd_sec(drain_window))
    if _PLACEHOLDER_WATCHDOG in out:
        if watchdog_interval is None:
            raise ValueError("watchdog_interval required to render WatchdogSec")
        out = out.replace(
            _PLACEHOLDER_WATCHDOG, duration_to_systemd_sec(watchdog_interval)
        )
    return out


def render_all_templates(
    *,
    drain_window: object,
    watchdog_interval: object,
    deploy_root: Path | None = None,
) -> dict[str, str]:
    """Render every template to ``{basename_without_.in: text}``."""
    rendered: dict[str, str] = {}
    for path in list_template_files(deploy_root):
        text = path.read_text(encoding="utf-8")
        name = path.name.removesuffix(".in")
        rendered[name] = render_template(
            text,
            drain_window=drain_window,
            watchdog_interval=watchdog_interval,
        )
    return rendered


@dataclass(frozen=True, slots=True)
class UnitInspection:
    """IaC/security contract verdict for one rendered unit file."""

    name: str
    is_node_unit: bool
    is_timer: bool
    ok: bool
    findings: tuple[str, ...]


def _setting(text: str, key: str) -> str | None:
    pattern = re.compile(rf"^{re.escape(key)}=(.*)$", re.MULTILINE)
    match = pattern.search(text)
    if match is None:
        return None
    return match.group(1).strip()


def _all_settings(text: str, key: str) -> tuple[str, ...]:
    pattern = re.compile(rf"^{re.escape(key)}=(.*)$", re.MULTILINE)
    return tuple(m.group(1).strip() for m in pattern.finditer(text))


def inspect_unit_text(name: str, text: str) -> UnitInspection:
    """Inspect one rendered unit against the ratified hardening contract."""
    findings: list[str] = []
    is_timer = name.endswith(".timer")
    is_obs = name == OBSERVABILITY_UNIT
    is_node = name in node_unit_names()

    if is_timer:
        # Timers have no Service hardening block; paired .service carries it.
        if "[Timer]" not in text:
            findings.append("timer missing [Timer] section")
        return UnitInspection(
            name=name,
            is_node_unit=is_node,
            is_timer=True,
            ok=not findings,
            findings=tuple(findings),
        )

    user = _setting(text, "User")
    expected_user = OBSERVABILITY_SERVICE_ACCOUNT if is_obs else NODE_SERVICE_ACCOUNT
    if user != expected_user:
        findings.append(f"User={user!r} expected {expected_user!r}")
    if re.search(r"^DynamicUser\s*=\s*yes\b", text, re.MULTILINE | re.IGNORECASE):
        findings.append("DynamicUser=yes is forbidden")

    protect = _setting(text, "ProtectSystem")
    if protect != "strict":
        findings.append(f"ProtectSystem={protect!r} expected 'strict'")
    for key in ("NoNewPrivileges", "PrivateTmp", "ProtectHome"):
        got = _setting(text, key)
        if got is None or got.lower() not in {"true", "yes", "1"}:
            findings.append(f"{key} missing or not enabled ({got!r})")

    rwp = _setting(text, "ReadWritePaths")
    expected_rwp = READ_WRITE_PATHS_OBS if is_obs else READ_WRITE_PATHS_NODE
    if rwp != expected_rwp:
        findings.append(f"ReadWritePaths={rwp!r} expected {expected_rwp!r}")

    families_raw = _setting(text, "RestrictAddressFamilies")
    if families_raw is None:
        findings.append("RestrictAddressFamilies missing")
    else:
        families = frozenset(families_raw.split())
        if families != REQUIRED_RESTRICT_FAMILIES:
            findings.append(
                f"RestrictAddressFamilies={families_raw!r} "
                f"expected {' '.join(sorted(REQUIRED_RESTRICT_FAMILIES))!r}"
            )

    if name == "qmn.service":
        if _setting(text, "Type") != "notify":
            findings.append("qmn.service must be Type=notify")
        if _setting(text, "RuntimeDirectory") != "qmn":
            findings.append("qmn.service must declare RuntimeDirectory=qmn")
        if "@DRAIN_WINDOW_SEC@" in text or "@WATCHDOG_INTERVAL_SEC@" in text:
            findings.append("placeholders not rendered")
        if _setting(text, "TimeoutStopSec") is None:
            findings.append("TimeoutStopSec missing")
        if _setting(text, "WatchdogSec") is None:
            findings.append("WatchdogSec missing")
        if POWERS_SOCKET_PATH not in text:
            findings.append("powers socket path not referenced")

    # Credential-consuming units: only LoadCredentialEncrypted, never plaintext
    # LoadCredential for secret material; seal flag is provision-time.
    load_plain = _all_settings(text, "LoadCredential")
    load_enc = _all_settings(text, "LoadCredentialEncrypted")
    if load_plain:
        findings.append(
            f"LoadCredential= present ({load_plain!r}); secrets must use "
            "LoadCredentialEncrypted="
        )
    if is_obs and not load_enc:
        findings.append(
            "observability unit must LoadCredentialEncrypted its own material"
        )
    credential_units = {
        "qmn.service",
        "qmn-backup.service",
        "qmn-restore-sample.service",
        "qmn-restore-full.service",
    }
    if name in credential_units and not load_enc:
        findings.append(f"{name} must declare LoadCredentialEncrypted")
    if name == "qmn-news-calendar.service" and load_enc:
        findings.append("news-calendar unit must not receive credentials")

    # Cross-unit credential isolation: venue material only on qmn.service.
    venue_creds = {
        "venue-client-id",
        "venue-client-secret",
        "venue-access-token",
        "venue-refresh-token",
        "venue-ctid-accounts",
    }
    if not is_obs and name != "qmn.service":
        for cred in load_enc:
            cred_id = cred.split(":", 1)[0]
            if cred_id in venue_creds or cred_id == "kek":
                findings.append(f"{name} must not receive venue/kek credential {cred_id!r}")

    return UnitInspection(
        name=name,
        is_node_unit=is_node,
        is_timer=False,
        ok=not findings,
        findings=tuple(findings),
    )


def inspect_rendered_units(rendered: Mapping[str, str]) -> tuple[UnitInspection, ...]:
    """Inspect every rendered unit; order follows sorted names."""
    return tuple(inspect_unit_text(name, text) for name, text in sorted(rendered.items()))
