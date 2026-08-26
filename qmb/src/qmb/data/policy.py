"""Download-once policy: runs never fetch from a provider (B-11, AR-54)."""

from __future__ import annotations

from qmf.core.refusal import Result

from qmb._refuse import policy

__all__ = ["refuse_run_provider_fetch"]


def refuse_run_provider_fetch(*, request: object | None = None) -> Result[None]:
    """Refuse a run-loop / backtest / sweep attempt to fetch from a provider.

    ``data download`` is the sole provider-fetch surface. Runs read only
    qmf-data rooms; a provider fetch from a run is a ``policy rejection``.
    """
    context: dict[str, object] = {
        "signal": "refuse-run-provider-fetch",
        "sole_fetch_surface": "qmb data download",
        "contract": "B-11",
    }
    if request is not None:
        context["request"] = repr(request)
    return policy(
        "provider_fetch",
        "runs read only qmf-data rooms and never fetch from a provider; "
        "qmb data download is the sole provider-fetch surface (AR-54, DEC-0166)",
        **context,
    )
