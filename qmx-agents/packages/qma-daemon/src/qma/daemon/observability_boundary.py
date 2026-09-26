"""Story 61.3 — logs are not evidence; QMN allow-list stays QMN.

Mini-app typed failure first ids live in the owning package FAILURES.md and
are never added to ``qmn/FAILURES.md``. QMA telemetry is harness-authored: a
model-authored hook that emits it is refused. Operator JSON-lines remain logs;
QMB LogSink may remain; daemon code does not invent a third logger.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from qma.core.plugins.hooks import HookSource
from qma.core.ports.telemetry import TelemetryRecord
from qma.daemon.operator_log import (
    LOGS_ARE_NOT_EVIDENCE,
    LOGS_ARE_NOT_JOURNALS,
    QMN_FAILURES_MD_EXTENDED,
    JsonLineFormatter,
)
from qma.daemon.telemetry.store import TelemetryStore
from qmf.core import Ok, Result
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "ALLOWED_LOGGER_PRODUCTS",
    "DAEMON_OPERATOR_LOGGER",
    "LOGS_REMAIN_LOGS",
    "MINI_APP_FAILURE_MARKERS",
    "MINI_APP_FIRST_FAILURE_FLOOR",
    "OWNING_FAILURES_MD",
    "PLUGIN_FAILURES_MD_TEMPLATE",
    "QMB_LOGSINK_CLASS",
    "QMB_LOGSINK_MAY_REMAIN",
    "QMB_LOGSINK_SOURCE",
    "QMN_ALERT_ALLOW_LIST_OWNER",
    "QMN_FAILURES_MD",
    "QMN_FAILURES_MD_EXTENDED",
    "THIRD_LOGGER_MINTED",
    "emit_telemetry_from_hook",
    "mint_third_logger",
    "owning_failures_md",
    "page_qmn_alert_with_mini_app_failure",
    "parse_failure_entries",
    "place_typed_failure",
    "qmn_allow_list_overlap",
    "refuse_qmn_allow_list_extension",
    "refuse_third_logger",
]


DAEMON_OPERATOR_LOGGER: Final[str] = "stdlib.logging"
QMB_LOGSINK_CLASS: Final[str] = "LogSink"
QMB_LOGSINK_SOURCE: Final[str] = "qmb/src/qmb/orchestrator/log.py"
QMB_LOGSINK_MAY_REMAIN: Final[bool] = True
THIRD_LOGGER_MINTED: Final[bool] = False
LOGS_REMAIN_LOGS: Final[bool] = LOGS_ARE_NOT_JOURNALS and LOGS_ARE_NOT_EVIDENCE
QMN_ALERT_ALLOW_LIST_OWNER: Final[str] = "qmn"
QMN_FAILURES_MD: Final[str] = "qmn/FAILURES.md"
PLUGIN_FAILURES_MD_TEMPLATE: Final[str] = "qmx-agents/plugins/{pack_id}/FAILURES.md"
MINI_APP_FIRST_FAILURE_FLOOR: Final[int] = 74

OWNING_FAILURES_MD: Final[Mapping[str, str]] = MappingProxyType(
    {
        "qma-daemon": "qmx-agents/packages/qma-daemon/FAILURES.md",
        "qma-core": "qmx-agents/packages/qma-core/FAILURES.md",
        "qma-wire": "qmx-agents/packages/qma-wire/FAILURES.md",
        "qmb": "qmb/FAILURES.md",
        "qmn": QMN_FAILURES_MD,
    }
)

ALLOWED_LOGGER_PRODUCTS: Final[frozenset[str]] = frozenset(
    {
        DAEMON_OPERATOR_LOGGER,
        QMB_LOGSINK_CLASS,
        "qma.daemon.operator",
    }
)

# Phrases that identify mini-app / kit diagnosis failures. None may appear in
# qmn/FAILURES.md (SCN-0027 Then 3 / Branch C).
MINI_APP_FAILURE_MARKERS: Final[tuple[str, ...]] = (
    "operator JSON-lines",
    "kit AD-5",
    "FR-PG-22",
    "get_diagnosis",
    "mint_third_logger",
    "model-authored hook",
    "failure_class plus JobHandle",
    "qmn/FAILURES.md is not extended",
)

_FR_HEADER = re.compile(r"^###\s+(FR-\d+)\s*:\s*(.+?)\s*$", re.MULTILINE)
_FR_NUMBER = re.compile(r"^FR-(\d+)$")


def parse_failure_entries(text: str) -> tuple[tuple[str, str], ...]:
    """Parse ``### FR-N: title`` headers from a FAILURES.md body."""
    return tuple((match.group(1), match.group(2)) for match in _FR_HEADER.finditer(text))


def _fr_number(fr_id: str) -> int | None:
    matched = _FR_NUMBER.fullmatch(fr_id)
    if matched is None:
        return None
    return int(matched.group(1))


def _normalize_failures_path(path: str) -> str:
    return path.strip().replace("\\", "/")


def owning_failures_md(owner: str) -> Result[str]:
    """Return the FAILURES.md path that owns ``owner``'s first typed ids."""
    token = owner.strip()
    if token == "":
        return invalid_input("owner", "typed-failure owner is a non-empty package id")
    if token.startswith("plugin:"):
        pack_id = token.removeprefix("plugin:").strip()
        if pack_id == "" or "/" in pack_id or "\\" in pack_id or ".." in pack_id:
            return invalid_input(
                "owner",
                "plugin typed-failure owner is plugin:<pack_id> with no path",
                given=token,
            )
        return Ok(PLUGIN_FAILURES_MD_TEMPLATE.format(pack_id=pack_id))
    path = OWNING_FAILURES_MD.get(token)
    if path is None:
        return invalid_input(
            "owner",
            "typed-failure owner is a known package or plugin:<pack_id>",
            given=token,
            legal=sorted(OWNING_FAILURES_MD),
        )
    return Ok(path)


def refuse_qmn_allow_list_extension(**extra: object) -> Result[None]:
    """Mini-app failures are never added to qmn/FAILURES.md (SCN-0027 Branch C)."""
    extra.setdefault("extended", QMN_FAILURES_MD_EXTENDED)
    extra.setdefault("qmn_failures_md", QMN_FAILURES_MD)
    extra.setdefault("allow_list_owner", QMN_ALERT_ALLOW_LIST_OWNER)
    return policy_rejection(
        str(extra.pop("field", "qmn_failures")),
        "mini-app typed failure ids live in the owning package FAILURES.md and "
        "are never added to qmn/FAILURES.md (FR-PG-22; DEC-0456; SCN-0027 "
        "Then 3; Branch C)",
        **extra,
    )


def place_typed_failure(*, owner: str, target_failures_md: str) -> Result[str]:
    """Admit a first typed-failure id only into that owner's FAILURES.md."""
    home = owning_failures_md(owner)
    if not isinstance(home, Ok):
        return home
    target = _normalize_failures_path(target_failures_md)
    if target == "" or target.endswith("/"):
        return invalid_input(
            "target_failures_md",
            "typed-failure target is a FAILURES.md path",
            given=repr(target_failures_md),
        )
    if owner != QMN_ALERT_ALLOW_LIST_OWNER and target.endswith(QMN_FAILURES_MD):
        return policy_rejection(
            "qmn_failures",
            "mini-app typed failure ids live in the owning package FAILURES.md and "
            "are never added to qmn/FAILURES.md (FR-PG-22; DEC-0456; SCN-0027 "
            "Then 3; Branch C)",
            owner=owner,
            home=home.value,
            target=target,
            extended=QMN_FAILURES_MD_EXTENDED,
            qmn_failures_md=QMN_FAILURES_MD,
            allow_list_owner=QMN_ALERT_ALLOW_LIST_OWNER,
        )
    if target != _normalize_failures_path(home.value):
        return policy_rejection(
            "target_failures_md",
            "typed failure first ids live in that owning package's FAILURES.md "
            "(FR-PG-22; SCN-0027 Then 3)",
            owner=owner,
            home=home.value,
            target=target,
        )
    return Ok(home.value)


def page_qmn_alert_with_mini_app_failure(failure_id: object) -> Result[None]:
    """A pack cannot page the node with a mini-app failure (SCN-0027 Then 3)."""
    token = failure_id if isinstance(failure_id, str) else repr(failure_id)
    return refuse_qmn_allow_list_extension(
        field="failure_id",
        given=token,
        on_qmn_allow_list=False,
        pages_node=False,
    )


def qmn_allow_list_overlap(
    mini_app_failures_md: str,
    qmn_failures_md: str,
    *,
    floor: int = MINI_APP_FIRST_FAILURE_FLOOR,
) -> frozenset[str]:
    """Titles of mini-app first ids that were copied onto qmn/FAILURES.md."""
    mini_titles = {
        title
        for fr_id, title in parse_failure_entries(mini_app_failures_md)
        if (number := _fr_number(fr_id)) is not None and number >= floor
    }
    qmn_titles = {title for _, title in parse_failure_entries(qmn_failures_md)}
    return frozenset(mini_titles & qmn_titles)


def emit_telemetry_from_hook(
    store: TelemetryStore,
    raw: Mapping[str, object] | TelemetryRecord,
    *,
    source: HookSource | str,
    authored_by: str,
) -> Result[TelemetryRecord]:
    """Harness-only telemetry. Mission/model/agent hook authors are refused."""
    return store.append_from_hook(raw, source=source, authored_by=authored_by)


def refuse_third_logger(**extra: object) -> Result[None]:
    """Daemon code does not invent a third logger besides JSON-lines and LogSink."""
    extra.setdefault("minted", THIRD_LOGGER_MINTED)
    extra.setdefault("qmb_logsink_may_remain", QMB_LOGSINK_MAY_REMAIN)
    extra.setdefault("daemon_logger", DAEMON_OPERATOR_LOGGER)
    extra.setdefault("logs_remain_logs", LOGS_REMAIN_LOGS)
    extra.setdefault("formatter", JsonLineFormatter.__name__)
    extra.setdefault("stdlib_formatter", True)
    return policy_rejection(
        str(extra.pop("field", "logger")),
        "logs remain logs; QMB LogSink may remain; new daemon code does not "
        "invent a third logger (FR-PG-22; kit AD-5; DEC-0456)",
        **extra,
    )


def mint_third_logger(name: object = None) -> Result[None]:
    """Always refused — no third logger product is minted on the daemon."""
    return refuse_third_logger(given=repr(name), allowed=sorted(ALLOWED_LOGGER_PRODUCTS))
