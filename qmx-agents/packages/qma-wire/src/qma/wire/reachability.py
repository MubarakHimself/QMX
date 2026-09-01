"""Remote dial-out reachability (CT-40; AD-5, AD-25; FR-Q18).

A remote worker or deployed Quant dials OUT to its daemon. The daemon never
dials in. The daemon listener is the single inbound port; the deployed side
exposes no listener and no second transport channel.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
)

__all__ = [
    "DAEMON_DIAL_DIRECTION",
    "REMOTE_DIAL_DIRECTION",
    "DeployedSideConfig",
    "ReachabilityPosture",
    "validate_deployed_side",
    "validate_remote_dial_out",
]


REMOTE_DIAL_DIRECTION: Final[Literal["out"]] = "out"
DAEMON_DIAL_DIRECTION: Final[Literal["never_in"]] = "never_in"


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


@dataclass(frozen=True, slots=True)
class DeployedSideConfig:
    """Declared reachability of a remote worker / deployed Quant.

    The deployed side holds the daemon address and its own credential reference.
    It must not open an inbound listener or a second transport.
    """

    dials_out_to_daemon: bool = True
    exposes_inbound_listener: bool = False
    second_transport_channel: bool = False
    daemon_address: str = ""

    @classmethod
    def try_create(
        cls,
        *,
        dials_out_to_daemon: object = True,
        exposes_inbound_listener: object = False,
        second_transport_channel: object = False,
        daemon_address: object = "",
    ) -> Result[DeployedSideConfig]:
        if not isinstance(dials_out_to_daemon, bool):
            return _policy(
                "dials_out_to_daemon",
                "dials_out_to_daemon must be a bool",
                given=repr(dials_out_to_daemon),
            )
        if not isinstance(exposes_inbound_listener, bool):
            return _policy(
                "exposes_inbound_listener",
                "exposes_inbound_listener must be a bool",
                given=repr(exposes_inbound_listener),
            )
        if not isinstance(second_transport_channel, bool):
            return _policy(
                "second_transport_channel",
                "second_transport_channel must be a bool",
                given=repr(second_transport_channel),
            )
        if not isinstance(daemon_address, str):
            return _policy(
                "daemon_address",
                "daemon_address must be a string",
                given=repr(daemon_address),
            )
        return Ok(
            cls(
                dials_out_to_daemon=dials_out_to_daemon,
                exposes_inbound_listener=exposes_inbound_listener,
                second_transport_channel=second_transport_channel,
                daemon_address=daemon_address,
            )
        )


@dataclass(frozen=True, slots=True)
class ReachabilityPosture:
    """Validated dial-out posture: daemon is the sole inbound port."""

    remote_dial_direction: Literal["out"]
    daemon_dial_direction: Literal["never_in"]
    daemon_is_sole_inbound: bool
    deployed_exposes_listener: bool
    deployed_second_transport: bool
    daemon_address: str


def validate_deployed_side(config: object) -> Result[ReachabilityPosture]:
    """Refuse a deployed side that listens inbound or opens a second transport."""
    if not isinstance(config, DeployedSideConfig):
        return _policy(
            "deployed_side",
            "validate_deployed_side requires DeployedSideConfig",
            given=repr(config),
        )
    if not config.dials_out_to_daemon:
        return _policy(
            "dials_out_to_daemon",
            "remote worker or deployed Quant must dial out to the daemon",
        )
    if config.exposes_inbound_listener:
        return _policy(
            "exposes_inbound_listener",
            "deployed side must expose no inbound listener; daemon listener is sole inbound",
        )
    if config.second_transport_channel:
        return _policy(
            "second_transport_channel",
            "deployed side must expose no second transport channel",
        )
    if config.daemon_address.strip() == "":
        return _policy(
            "daemon_address",
            "deployed side must hold the daemon address to dial out",
        )
    return Ok(
        ReachabilityPosture(
            remote_dial_direction=REMOTE_DIAL_DIRECTION,
            daemon_dial_direction=DAEMON_DIAL_DIRECTION,
            daemon_is_sole_inbound=True,
            deployed_exposes_listener=False,
            deployed_second_transport=False,
            daemon_address=config.daemon_address,
        )
    )


def validate_remote_dial_out(config: object) -> Result[ReachabilityPosture]:
    """Alias: remote dial-out is the only sanctioned reachability posture."""
    return validate_deployed_side(config)
