"""FTR-04 parent disposition — both loci carried, no silent choice (Story 24.1)."""

from __future__ import annotations

from qmf.core import is_ok, is_refusal
from qmn.venue import (
    ASYNC_EXEMPTION_MODULE,
    FTR04_DISPOSITION,
    TRANSPORT_LOCUS,
    ParentAsyncExemptionDisposition,
    resolve_transport_locus,
)
from qmn.venue.ctrader import host_transport_allowed, transport_contract_summary


def test_exemption_name_is_exactly_qmf_venue_connection() -> None:
    assert ASYNC_EXEMPTION_MODULE == "qmf.venue.connection"


def test_standing_disposition_is_accepted_per_dec0243() -> None:
    assert FTR04_DISPOSITION is ParentAsyncExemptionDisposition.ACCEPTED
    assert TRANSPORT_LOCUS == "qmf.venue.connection.ConnectionManager"


def test_resolve_accepted_lands_in_connection_manager() -> None:
    result = resolve_transport_locus(ParentAsyncExemptionDisposition.ACCEPTED)
    assert is_ok(result)
    assert result.value == "qmf.venue.connection.ConnectionManager"


def test_resolve_refused_lands_in_qmn_venue_ctrader() -> None:
    result = resolve_transport_locus(ParentAsyncExemptionDisposition.REFUSED)
    assert is_ok(result)
    assert result.value == "qmn.venue.ctrader"


def test_fallback_module_refuses_to_host_under_accepted_disposition() -> None:
    result = host_transport_allowed()
    assert is_refusal(result)
    assert result.context["active_locus"] == "qmf.venue.connection.ConnectionManager"


def test_fallback_module_allows_host_only_when_refused() -> None:
    result = host_transport_allowed(ParentAsyncExemptionDisposition.REFUSED)
    assert is_ok(result)
    assert result.value is True


def test_transport_contract_summary_is_credential_free() -> None:
    summary = transport_contract_summary()
    assert summary["tls_port"] == 5035
    assert summary["proto_tag_pinned"] == 91
    assert summary["protobuf_runtime"] == "protobuf==7.36.0"
    banned = summary["banned"]
    assert isinstance(banned, tuple)
    assert "Spotware SDK" in banned
    assert summary["standing_locus"] == "qmf.venue.connection.ConnectionManager"
