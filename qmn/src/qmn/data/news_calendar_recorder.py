"""``qmn-news-calendar.timer`` oneshot — Forex Factory free weekly file only.

ExecStart: ``python -m qmn.data.news_calendar_recorder``. HTTPS is confined to
this module; the ingest core in :mod:`qmn.data.news_calendar` takes an injected
byte fetch so factory tests never open the live CDN.
"""

from __future__ import annotations

import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from typing import Final

from qmf.core import Ok, Result, is_refusal

from qmn.data.news_calendar import (
    FAILED_REFRESH_FAILURE_ID,
    FOREX_FACTORY_WEEKLY_JSON,
    NEWS_CALENDAR_ALARM_CLASS,
    fetch_unavailable_refusal,
    rate_limited_refusal,
    require_weekly_file_url,
)

__all__ = [
    "FOREX_FACTORY_WEEKLY_JSON",
    "NEWS_CALENDAR_USER_AGENT",
    "HttpsForexFactoryTransport",
    "main",
]

NEWS_CALENDAR_USER_AGENT: Final[str] = "Mozilla/5.0 (compatible; QMX-qmn-news-calendar/1.0)"
_TIMEOUT_SECONDS: Final[int] = 45


class HttpsForexFactoryTransport:
    """Pinned weekly-JSON fetch. Any other URL is refused before the socket."""

    def __init__(
        self,
        *,
        url: str = FOREX_FACTORY_WEEKLY_JSON,
        opener: Callable[[str], Result[bytes]] | None = None,
    ) -> None:
        self.url = url
        self._opener = opener if opener is not None else urllib_open_weekly_file

    def fetch_snapshot(self, bounds: Mapping[str, object], /) -> Result[bytes]:
        del bounds
        pinned = require_weekly_file_url(self.url)
        if is_refusal(pinned):
            return pinned
        return self._opener(pinned.value)


def urllib_open_weekly_file(url: str) -> Result[bytes]:
    """Production opener. Tests inject a fixture opener and never call this."""
    pinned = require_weekly_file_url(url)
    if is_refusal(pinned):
        return pinned
    # Taint boundary: require_weekly_file_url admits only this constant; the
    # opener never forwards the parameter (or Result.value) to the socket.
    weekly_file = FOREX_FACTORY_WEEKLY_JSON
    if pinned.value != weekly_file:
        return fetch_unavailable_refusal(retryable=False)
    request = urllib.request.Request(  # noqa: S310
        weekly_file, headers={"User-Agent": NEWS_CALENDAR_USER_AGENT}
    )
    try:
        # S310 / SKY-D216: URL is the pinned Forex Factory weekly-file constant.
        # skylos: ignore[SKY-D216] pinned weekly-file constant
        with urllib.request.urlopen(  # noqa: S310
            request, timeout=_TIMEOUT_SECONDS
        ) as response:
            status = int(response.status)
            body = response.read()
    except urllib.error.HTTPError as error:
        if error.code in {429, 403}:
            return rate_limited_refusal(http_status=int(error.code))
        return fetch_unavailable_refusal(retryable=error.code >= 500)
    except (urllib.error.URLError, TimeoutError, OSError):
        return fetch_unavailable_refusal(retryable=True)
    if status in {429, 403}:
        return rate_limited_refusal(http_status=status)
    if status >= 500:
        return fetch_unavailable_refusal(retryable=True)
    if status != 200:
        return fetch_unavailable_refusal(retryable=False)
    return Ok(body)


def main(argv: list[str] | None = None) -> int:
    """Systemd oneshot. Factory tests drive :class:`NewsCalendarRecorder.fire`."""
    del argv
    # Unbound oneshot refuses rather than inventing a live skip or a second
    # source; ``news_calendar_max_staleness`` then fail-closes entries.
    _ = (FOREX_FACTORY_WEEKLY_JSON, NEWS_CALENDAR_ALARM_CLASS, FAILED_REFRESH_FAILURE_ID)
    return 1


if __name__ == "__main__":
    sys.exit(main())
