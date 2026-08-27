"""Epic 14 · Group H — host conformant bots (Story 14.8, R34-R37) [BLOCKED].

Story 14.8 (QL-7 host adapter + DEC-0183 config-compiler extensions + host-owned
conformance sandbox) depends on Epics 11/12 (QML CT-33 Bot + host-owned
conformance runner) and Epic 13 (config compiler); epics.md itself marks 14.8 as
waiting on Epics 12 and 13. These are recorded scaffolds, executed when the
dependencies land — NOT omissions. See RESULTS.md for the blocked-with-owning-
epic ledger. They are skipped (not failed, not passed) so the audit records them
honestly rather than asserting an unratified cross-epic surface.
"""

from __future__ import annotations

import pytest

_BLOCKED_11_12 = "Story 14.8 R34 (QL-7 CT-33 host factory) — blocked on Epics 11/12; scaffold."
_BLOCKED_13 = "Story 14.8 R35 (DEC-0183 compiler extensions) — blocked on Epic 13; scaffold."
_BLOCKED_12 = "Story 14.8 R36 (host-owned conformance sandbox) — blocked on Epic 12; scaffold."
_BLOCKED_QML = (
    "Story 14.8 R37 (plain-Python ungoverned tunnel bot) — QML tunnel territory (QL-1, "
    "FR-047/048); not assertable in runloop/ isolation. Execute at QML/Epic-15 integration."
)


@pytest.mark.skip(reason=_BLOCKED_11_12)
def test_t148a_ql7_host_factory_drives_ct33_bot() -> None:  # pragma: no cover - blocked scaffold
    raise AssertionError("scaffold: implement when Epics 11/12 land")


@pytest.mark.skip(reason=_BLOCKED_13)
def test_t148b_dec0183_compiler_extensions() -> None:  # pragma: no cover - blocked scaffold
    raise AssertionError("scaffold: implement when Epic 13 lands")


@pytest.mark.skip(reason=_BLOCKED_12)
def test_t148c_host_owned_conformance_sandbox() -> None:  # pragma: no cover - blocked scaffold
    raise AssertionError("scaffold: implement when Epic 12 lands")


@pytest.mark.skip(reason=_BLOCKED_QML)
def test_t148d_plain_python_tunnel_bot_ungated() -> None:  # pragma: no cover - blocked scaffold
    raise AssertionError("scaffold: execute at QML/Epic-15 integration")
