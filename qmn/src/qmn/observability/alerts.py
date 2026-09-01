"""Closed alert allow-list generated from FAILURES.md (TN-15 / DEC-0200).

``FAILURES.md``'s notification-tier column is the sole home of alert-class
membership (AR-82 / DEC-0256). The push tier is exactly three classes —
money-boundary, protection-escalation, silent-degradation — and is GENERATED
from the register so the two cannot drift. An unregistered failure cannot be
alerted. No daily liveness digest and no quiet hours (DEC-0261).
"""

from __future__ import annotations

import os
import re
import stat
from collections.abc import Mapping, MutableSequence, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Final, Protocol

from qmf.core import Ok, Result
from qmf.core.refusal import is_refusal

from qmn.observability._refuse import clean_token, invalid, policy

__all__ = [
    "DAILY_LIVENESS_DIGEST_EXISTS",
    "NFR11_REQUIRED_FIELDS",
    "PUSH_ALERT_CLASSES",
    "QUIET_HOURS_EXIST",
    "AlertAllowList",
    "AlertPayload",
    "AlertPublisher",
    "FailureRegisterEntry",
    "NotificationChannel",
    "RecordingNotificationChannel",
    "default_failures_path",
    "generate_alert_allow_list",
    "load_alert_allow_list",
    "parse_failures_register",
    "push_classes_for_tier",
]

# Closed push vocabulary — the only classes that may leave the node (DEC-0200).
PUSH_ALERT_CLASSES: Final[tuple[str, ...]] = (
    "money-boundary",
    "protection-escalation",
    "silent-degradation",
)

# Rejected / deferred notification features (DEC-0261 / DEC-0200).
DAILY_LIVENESS_DIGEST_EXISTS: Final[bool] = False
QUIET_HOURS_EXIST: Final[bool] = False

NFR11_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "Failure class",
    "Detection",
    "Auto-recovery / retry",
    "Visible degraded state",
    "Notification tier",
    "Product-user affordance",
)

_ENTRY_HEADER = re.compile(r"^###\s+(FR-\d+)\s*:\s*(.+?)\s*$")
_FIELD_LINE = re.compile(r"^-\s+\*\*(.+?):\*\*\s*(.*)$")
_BACKTICK_ID = re.compile(r"`([A-Za-z][A-Za-z0-9_.\-:]*)`")

# Tokens inside a notification-tier cell that map onto a push class.
_TIER_TOKEN_TO_CLASS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "money-boundary": "money-boundary",
        "money-boundaries": "money-boundary",
        "money boundaries": "money-boundary",
        "protection-escalation": "protection-escalation",
        "protection escalation": "protection-escalation",
        "stand-down alarm": "protection-escalation",
        "stand-down": "protection-escalation",
        "silent-degradation": "silent-degradation",
        "silent degradation": "silent-degradation",
    }
)


@dataclass(frozen=True, slots=True)
class FailureRegisterEntry:
    """One NFR-11 failure-register entry parsed from FAILURES.md."""

    fr_id: str
    title: str
    failure_class: str
    detection: str
    auto_recovery: str
    visible_degraded_state: str
    notification_tier: str
    product_user_affordance: str

    @property
    def push_classes(self) -> frozenset[str]:
        return push_classes_for_tier(self.notification_tier)

    @property
    def detection_failure_ids(self) -> frozenset[str]:
        """Typed failure ids cited in backticks inside the Detection field."""
        return frozenset(_BACKTICK_ID.findall(self.detection))

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "fr_id": self.fr_id,
                "title": self.title,
                "failure_class": self.failure_class,
                "detection": self.detection,
                "auto_recovery": self.auto_recovery,
                "visible_degraded_state": self.visible_degraded_state,
                "notification_tier": self.notification_tier,
                "product_user_affordance": self.product_user_affordance,
                "push_classes": tuple(sorted(self.push_classes)),
                "detection_failure_ids": tuple(sorted(self.detection_failure_ids)),
            }
        )


@dataclass(frozen=True, slots=True)
class AlertAllowList:
    """Closed push allow-list generated from the register (AR-82)."""

    by_class: Mapping[str, frozenset[str]]
    member_ids: frozenset[str]
    entries: tuple[FailureRegisterEntry, ...]

    def alert_class_for(self, failure_id: str) -> str | None:
        token = clean_token(failure_id)
        if token is None:
            return None
        for class_name in PUSH_ALERT_CLASSES:
            if token in self.by_class.get(class_name, frozenset()):
                return class_name
        return None

    def may_alert(self, failure_id: object) -> bool:
        token = clean_token(failure_id)
        return token is not None and token in self.member_ids

    def registered_ids(self) -> frozenset[str]:
        ids: set[str] = set()
        for entry in self.entries:
            ids.add(entry.fr_id)
            ids |= set(entry.detection_failure_ids)
        return frozenset(ids)


@dataclass(frozen=True, slots=True)
class AlertPayload:
    """One push-tier alert — evidence of a designed failure, never authority."""

    failure_id: str
    alert_class: str
    summary: str
    correlation_id: str | None = None

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "failure_id": self.failure_id,
            "alert_class": self.alert_class,
            "summary": self.summary,
            "authorizes": False,
            "erases_evidence_on_loss": False,
        }
        if self.correlation_id is not None:
            body["correlation_id"] = self.correlation_id
        return MappingProxyType(body)


class NotificationChannel(Protocol):
    """Node-minted push port (HTTPS webhook / console / file)."""

    def deliver(self, alert: AlertPayload, /) -> Result[None]:
        """Deliver one allow-listed alert. Never grants trading authority."""
        ...


@dataclass
class RecordingNotificationChannel:
    """Test / console double that records deliveries without leaving the process."""

    delivered: MutableSequence[AlertPayload] = field(default_factory=list[AlertPayload])
    fail_next: bool = False

    def deliver(self, alert: AlertPayload, /) -> Result[None]:
        if self.fail_next:
            self.fail_next = False
            return policy("notification", "injected notification-channel failure")
        self.delivered.append(alert)
        return Ok(None)


@dataclass(frozen=True, slots=True)
class AlertPublisher:
    """Push only allow-listed failures through the notification channel."""

    allow_list: AlertAllowList
    channel: NotificationChannel

    def publish(
        self,
        *,
        failure_id: object,
        summary: object,
        correlation_id: object | None = None,
    ) -> Result[AlertPayload]:
        token = clean_token(failure_id)
        if token is None:
            return invalid("failure_id", "alert failure_id is a non-blank string")
        text = clean_token(summary)
        if text is None:
            return invalid("summary", "alert summary is a non-blank string")
        if not self.allow_list.may_alert(token):
            return policy(
                "failure_id",
                "unregistered or non-push failure cannot be alerted",
                failure_id=token,
                registered=token in self.allow_list.registered_ids(),
            )
        alert_class = self.allow_list.alert_class_for(token)
        if alert_class is None:
            return policy(
                "failure_id",
                "failure is registered but not on the closed push allow-list",
                failure_id=token,
            )
        corr = clean_token(correlation_id) if correlation_id is not None else None
        if correlation_id is not None and corr is None:
            return invalid("correlation_id", "correlation_id is a non-blank string when set")
        payload = AlertPayload(
            failure_id=token,
            alert_class=alert_class,
            summary=text,
            correlation_id=corr,
        )
        delivered = self.channel.deliver(payload)
        if is_refusal(delivered):
            return delivered
        return Ok(payload)


_MAX_FAILURES_BYTES: Final[int] = 1 << 20  # 1 MiB


def default_failures_path() -> Path:
    """``qmn/FAILURES.md`` beside the distribution root (not under ``src/``)."""
    return Path(__file__).resolve().parents[3] / "FAILURES.md"


def _failures_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read_failures_path(path: Path) -> Result[str]:
    """Read FAILURES.md via O_NOFOLLOW as a regular in-root file under a size cap."""
    root = _failures_root()
    try:
        resolved = Path(os.path.realpath(path))
        root_real = Path(os.path.realpath(root))
    except OSError as exc:
        return invalid(
            "failures_path",
            f"cannot resolve FAILURES.md path: {exc}",
        )
    if path.is_symlink() or not resolved.is_relative_to(root_real):
        return invalid(
            "failures_path",
            "refusing to follow a symlink or read FAILURES.md outside the qmn root",
            path=str(path),
        )
    try:
        # getattr keeps the "O_NOFOLLOW" token on this open so SKY-D324/D325
        # see the no-follow flag; Windows has no O_NOFOLLOW (value 0).
        fd = os.open(  # skylos: ignore[SKY-D215] contained, no-follow read
            path,
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_BINARY", 0),
        )
    except OSError as exc:
        return invalid("failures_path", f"cannot read FAILURES.md: {exc}")
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            return invalid(
                "failures_path",
                "FAILURES.md must be a regular in-root file",
                path=str(path),
            )
        size = info.st_size
        if size > _MAX_FAILURES_BYTES:
            return invalid(
                "failures_path",
                "refusing to read FAILURES.md above the size cap",
                path=str(path),
                size=size,
                max_bytes=_MAX_FAILURES_BYTES,
            )
        limit = (
            _MAX_FAILURES_BYTES if size <= 0 else min(size, _MAX_FAILURES_BYTES)
        )
        buf = bytearray()
        while len(buf) < limit:
            chunk = os.read(fd, limit - len(buf))
            if not chunk:
                break
            buf.extend(chunk)
        if size <= 0 and len(buf) >= _MAX_FAILURES_BYTES:
            extra = os.read(fd, 1)
            if extra:
                return invalid(
                    "failures_path",
                    "refusing to read FAILURES.md above the size cap",
                    path=str(path),
                    max_bytes=_MAX_FAILURES_BYTES,
                )
    except OSError as exc:
        return invalid("failures_path", f"cannot read FAILURES.md: {exc}")
    finally:
        os.close(fd)
    try:
        return Ok(bytes(buf).decode("utf-8"))
    except UnicodeDecodeError as exc:
        return invalid("failures_path", f"FAILURES.md is not UTF-8 text: {exc}")


def push_classes_for_tier(tier: object) -> frozenset[str]:
    """Map a notification-tier cell onto zero or more closed push classes."""
    text = clean_token(tier)
    if text is None:
        return frozenset()
    lowered = text.lower()
    found: set[str] = set()
    # Longest-token first so "stand-down alarm" wins over bare fragments.
    for token, class_name in sorted(_TIER_TOKEN_TO_CLASS.items(), key=lambda kv: -len(kv[0])):
        if token in lowered:
            found.add(class_name)
    return frozenset(found)


def parse_failures_register(source: str | Path) -> Result[tuple[FailureRegisterEntry, ...]]:
    """Parse FAILURES.md into typed register entries with all six NFR-11 fields."""
    if isinstance(source, Path):
        loaded = _read_failures_path(source)
        if is_refusal(loaded):
            return loaded
        text = loaded.value
    else:
        token = clean_token(source)
        if token is None:
            return invalid("failures_text", "FAILURES.md source is non-blank text or a Path")
        text = token

    entries: list[FailureRegisterEntry] = []
    current_id: str | None = None
    current_title: str | None = None
    fields: dict[str, str] = {}
    field_order_key: str | None = None

    def _flush() -> Result[None]:
        nonlocal current_id, current_title, fields, field_order_key
        if current_id is None or current_title is None:
            return Ok(None)
        missing = [name for name in NFR11_REQUIRED_FIELDS if name not in fields]
        if missing:
            return invalid(
                "failures_register",
                "every FAILURES.md entry needs all six NFR-11 fields",
                fr_id=current_id,
                missing=tuple(missing),
            )
        entries.append(
            FailureRegisterEntry(
                fr_id=current_id,
                title=current_title,
                failure_class=fields["Failure class"],
                detection=fields["Detection"],
                auto_recovery=fields["Auto-recovery / retry"],
                visible_degraded_state=fields["Visible degraded state"],
                notification_tier=fields["Notification tier"],
                product_user_affordance=fields["Product-user affordance"],
            )
        )
        current_id = None
        current_title = None
        fields = {}
        field_order_key = None
        return Ok(None)

    for raw_line in text.splitlines():
        header = _ENTRY_HEADER.match(raw_line)
        if header is not None:
            flushed = _flush()
            if is_refusal(flushed):
                return flushed
            current_id = header.group(1)
            current_title = header.group(2).strip()
            fields = {}
            field_order_key = None
            continue
        if current_id is None:
            continue
        field_match = _FIELD_LINE.match(raw_line)
        if field_match is not None:
            key = field_match.group(1)
            value = field_match.group(2)
            if key is None or value is None:
                return invalid("failures_register", "malformed FAILURES.md field line")
            active_key = key.strip()
            field_order_key = active_key
            fields[active_key] = value.strip()
            continue
        stripped = raw_line.strip()
        if field_order_key is not None and stripped and not stripped.startswith("#"):
            # Continuation of a multi-line field value.
            active_key = field_order_key
            fields[active_key] = f"{fields[active_key]} {stripped}".strip()

    flushed = _flush()
    if is_refusal(flushed):
        return flushed
    if not entries:
        return invalid("failures_register", "FAILURES.md carries no FR entries")
    return Ok(tuple(entries))


def generate_alert_allow_list(
    entries: Sequence[FailureRegisterEntry],
) -> Result[AlertAllowList]:
    """Build the closed push allow-list from parsed register entries (AR-82)."""
    if not entries:
        return invalid("entries", "allow-list generation requires at least one register entry")
    by_class: dict[str, set[str]] = {name: set() for name in PUSH_ALERT_CLASSES}
    member_ids: set[str] = set()
    seen_fr: set[str] = set()
    for entry in entries:
        if entry.fr_id in seen_fr:
            return invalid("fr_id", "duplicate FAILURES.md entry id", fr_id=entry.fr_id)
        seen_fr.add(entry.fr_id)
        classes = entry.push_classes
        if not classes:
            continue
        for class_name in classes:
            by_class[class_name].add(entry.fr_id)
            member_ids.add(entry.fr_id)
            for detection_id in entry.detection_failure_ids:
                by_class[class_name].add(detection_id)
                member_ids.add(detection_id)

    frozen = MappingProxyType(
        {name: frozenset(by_class[name]) for name in PUSH_ALERT_CLASSES}
    )
    # Vocabulary coverage: all three closed classes exist as keys even if empty.
    if tuple(frozen.keys()) != PUSH_ALERT_CLASSES:
        return policy("allow_list", "push class vocabulary drifted from PUSH_ALERT_CLASSES")
    return Ok(
        AlertAllowList(
            by_class=frozen,
            member_ids=frozenset(member_ids),
            entries=tuple(entries),
        )
    )


def load_alert_allow_list(path: Path | None = None) -> Result[AlertAllowList]:
    """Parse FAILURES.md and generate the closed allow-list in one step."""
    target = path if path is not None else default_failures_path()
    parsed = parse_failures_register(target)
    if is_refusal(parsed):
        return parsed
    return generate_alert_allow_list(parsed.value)
