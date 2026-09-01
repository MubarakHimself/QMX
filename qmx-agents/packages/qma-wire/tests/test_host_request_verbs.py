"""host_request closed-and-addable verb set ownership (Story 40.2 / FR-Q08)."""

from __future__ import annotations

import pytest
import qma.wire
from qma.core.vocabulary import (
    HOST_REQUEST_OWNING_AD as CORE_HOST_REQUEST_AD,
)
from qma.core.vocabulary import (
    HOST_REQUEST_VOCABULARY_OWNER as CORE_HOST_REQUEST_OWNER,
)
from qma.wire import (
    HOST_REQUEST_OWNING_AD,
    HOST_REQUEST_PRIMITIVE_MAP,
    HOST_REQUEST_VERBS,
    HOST_REQUEST_VOCABULARY_OWNER,
    HostRequestVerbError,
    parse_host_request_verb,
)


def test_ownership_declared_in_wire_and_mirrored_in_core() -> None:
    assert HOST_REQUEST_VOCABULARY_OWNER == "qma-wire"
    assert HOST_REQUEST_OWNING_AD == "AD-14"
    assert CORE_HOST_REQUEST_OWNER == HOST_REQUEST_VOCABULARY_OWNER
    assert CORE_HOST_REQUEST_AD == HOST_REQUEST_OWNING_AD
    assert qma.wire.HOST_REQUEST_VOCABULARY_OWNER == "qma-wire"


def test_invented_host_request_verb_rejected() -> None:
    assert isinstance(HOST_REQUEST_VERBS, frozenset)
    assert HOST_REQUEST_VERBS == frozenset(HOST_REQUEST_PRIMITIVE_MAP)
    assert "subagent_spawn" in HOST_REQUEST_VERBS
    assert parse_host_request_verb("subagent_spawn") == "subagent_spawn"
    with pytest.raises(HostRequestVerbError):
        parse_host_request_verb("invented_spawn")
    with pytest.raises(HostRequestVerbError):
        parse_host_request_verb("")
