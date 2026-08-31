"""Closed-and-addable ``host_request`` verb registry (AD-14; DEC-0313).

Ownership of this vocabulary sits in ``qma-wire``. Each verb maps to exactly one
daemon-owned primitive and runs that primitive's ``before_*`` hook. A host call
whose verb is not a member returns ``UnknownHostRequest`` at the daemon boundary;
this module rejects invented members at parse time.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "HOST_REQUEST_OWNING_AD",
    "HOST_REQUEST_VERBS",
    "HOST_REQUEST_VOCABULARY_OWNER",
    "HostRequestVerbError",
    "parse_host_request_verb",
]

HOST_REQUEST_VOCABULARY_OWNER: Final[str] = "qma-wire"
HOST_REQUEST_OWNING_AD: Final[str] = "AD-14"

# Seed is empty until concrete RLM bridge verbs are minted in a later story.
# Membership is the only source of truth: addability is a registry edit here.
HOST_REQUEST_VERBS: Final[frozenset[str]] = frozenset()


class HostRequestVerbError(ValueError):
    """Raised when a host_request verb is not in the closed qma-wire set."""


def parse_host_request_verb(value: object) -> str:
    """Accept only a verb declared in the closed-and-addable qma-wire set."""
    if not isinstance(value, str) or not value:
        raise HostRequestVerbError(f"{value!r} is not a host_request verb")
    if value not in HOST_REQUEST_VERBS:
        raise HostRequestVerbError(
            f"{value!r} is not a member of the closed host_request verb set "
            f"(owner={HOST_REQUEST_VOCABULARY_OWNER})"
        )
    return value
