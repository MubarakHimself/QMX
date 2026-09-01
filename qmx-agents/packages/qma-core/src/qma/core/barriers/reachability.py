"""Money-path reachability barrier (AD-28; DEC-0327; FR-Q47).

Environment, image, host, and computer-use profile checks are code, never
settings. Every violation is a registration or placement refusal — never a
hook deny at runtime. Role, Mission, plugin, permission policy, and hook
cannot waive a host denial. OpenRouter is not a QMA path.
"""

from __future__ import annotations

import fnmatch
from collections.abc import Iterable, Mapping, Sequence
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Literal, cast
from urllib.parse import urlparse

from qma.core.barriers.credential_allowlist import OUT_OF_SCOPE_CREDENTIAL_REF_PREFIXES
from qma.core.ports.execution import (
    ComputerUseProfile,
    ExecutionEnvironmentDeclaration,
    WorkerImageManifest,
)
from qma.core.refusals.variants import ProhibitedReachability
from qma.core.vocabulary.enums import ExecutionEnvironmentKind, NetworkPolicy
from qma.core.vocabulary.registry import VocabularyError
from qmf.core import Ok, Result

__all__ = [
    "DENIED_HOST_PATTERNS",
    "FORBIDDEN_IMAGE_TOKENS",
    "FORBIDDEN_MODEL_ADAPTERS",
    "GAP_0070_DESKTOP_EXCLUSION",
    "HANDED_VIA_SURFACES",
    "HOST_IDENTITY_KINDS",
    "OPEN_NETWORK_TOKENS",
    "REACHABILITY_DENIAL_NOT_LIFTABLE_BY",
    "REACHABILITY_DENY_LIST_OWNER",
    "REACHABILITY_STAGES",
    "DeniedHostClass",
    "ReachabilityBarrierError",
    "assert_deny_list_not_waivable",
    "classify_denied_host",
    "is_denied_host",
    "is_forbidden_image_token",
    "is_forbidden_model_adapter",
    "is_open_network_token",
    "normalize_host",
    "parse_declaration",
    "refuse_forbidden_model_adapter",
    "refuse_handed_venue_login",
    "refuse_reachability",
    "refuse_reachability_waiver",
    "validate_computer_use_profile",
    "validate_execution_environment_declaration",
    "validate_host_identity",
    "validate_network_posture",
    "validate_worker_image",
]


class DeniedHostClass(StrEnum):
    """Code-declared deny-list classes no allowlist may name (AD-28)."""

    VENUE = "venue"
    BROKER = "broker"
    EXCHANGE = "exchange"
    TRADING_NODE = "trading_node"
    PLATFORM_REGISTRY = "platform_registry"
    OPENROUTER = "openrouter"


REACHABILITY_DENY_LIST_OWNER: Final[str] = "AD-28"

REACHABILITY_STAGES: Final[frozenset[str]] = frozenset({"registration", "placement"})

HOST_IDENTITY_KINDS: Final[frozenset[ExecutionEnvironmentKind]] = frozenset(
    {
        ExecutionEnvironmentKind.REMOTE_HOST,
        ExecutionEnvironmentKind.DESKTOP,
    }
)

# Surfaces that may propose a grant but cannot lift a host denial (FR-Q47).
REACHABILITY_DENIAL_NOT_LIFTABLE_BY: Final[frozenset[str]] = frozenset(
    {
        "role",
        "mission",
        "plugin",
        "permission_policy",
        "hook",
    }
)

HANDED_VIA_SURFACES: Final[frozenset[str]] = frozenset(
    {
        "knowledge",
        "memory",
        "ledger",
        "tool_result",
    }
)

# Invented network tokens that would be an open default — refused.
OPEN_NETWORK_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "open",
        "all",
        "any",
        "unrestricted",
        "public",
        "internet",
        "*",
        "0.0.0.0/0",
        "::/0",
    }
)

# Deferred GAP-0070: planned Windows VPS is not provisioned in this story.
GAP_0070_DESKTOP_EXCLUSION: Final[Mapping[str, str]] = MappingProxyType(
    {
        "gap": "GAP-0070",
        "status": "deferred",
        "provisioned": "false",
        "effect": (
            "planned Windows VPS desktop host is not provisioned; computer-use "
            "tools fail check_fn until a non-money-path desktop environment is "
            "registered; every reachability violation remains a placement or "
            "registration refusal"
        ),
    }
)

# Pattern → class. Wildcards are fnmatch. Membership is the deny-list.
_DENIED_HOST_ROWS: Final[tuple[tuple[str, DeniedHostClass], ...]] = (
    ("demo.ctraderapi.com", DeniedHostClass.VENUE),
    ("live.ctraderapi.com", DeniedHostClass.VENUE),
    ("*.ctraderapi.com", DeniedHostClass.VENUE),
    ("ctraderapi.com", DeniedHostClass.VENUE),
    ("*.spotware.com", DeniedHostClass.VENUE),
    ("spotware.com", DeniedHostClass.VENUE),
    ("icmarkets.com", DeniedHostClass.BROKER),
    ("*.icmarkets.com", DeniedHostClass.BROKER),
    ("broker", DeniedHostClass.BROKER),
    ("*.exchange", DeniedHostClass.EXCHANGE),
    ("exchange", DeniedHostClass.EXCHANGE),
    ("trading-node-vps", DeniedHostClass.TRADING_NODE),
    ("trading-node", DeniedHostClass.TRADING_NODE),
    ("*.trading-node", DeniedHostClass.TRADING_NODE),
    ("qmn-vps", DeniedHostClass.TRADING_NODE),
    ("qmn", DeniedHostClass.TRADING_NODE),
    ("platform-registry", DeniedHostClass.PLATFORM_REGISTRY),
    ("openrouter.ai", DeniedHostClass.OPENROUTER),
    ("*.openrouter.ai", DeniedHostClass.OPENROUTER),
    ("openrouter.com", DeniedHostClass.OPENROUTER),
    ("openrouter", DeniedHostClass.OPENROUTER),
)

DENIED_HOST_PATTERNS: Final[frozenset[str]] = frozenset(pattern for pattern, _ in _DENIED_HOST_ROWS)

# Image / import / package tokens that fail image validation (AD-28; DEC-0347).
FORBIDDEN_IMAGE_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "qmf-venue",
        "qmf.venue",
        "qmf_venue",
        "qmn",
        "qmn-client",
        "qmn.client",
        "qmn.venue",
        "trading-node",
        "trading_node",
        "ctrader",
        "spotware",
        "ctrader-open-api",
        "ccxt",
        "python-binance",
        "ibapi",
        "ib_insync",
        "metatrader5",
        "openrouter",
    }
)

FORBIDDEN_MODEL_ADAPTERS: Final[frozenset[str]] = frozenset({"openrouter"})

_VENUE_PROFILE_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "venue",
        "broker",
        "exchange",
        "ctrader",
        "spotware",
        "icmarkets",
        "trading-node",
        "qmn",
        "openrouter",
    }
)


class ReachabilityBarrierError(ValueError):
    """Raised when the deny-list constant is misused or illegally waived."""


StageName = Literal["registration", "placement"]


def refuse_reachability(
    *,
    surface: str,
    reason: str,
    stage: StageName = "registration",
    host: str | None = None,
    kind: str | None = None,
    via: str | None = None,
    matched: str | None = None,
) -> ProhibitedReachability:
    """Build the placement/registration refusal (never a hook deny)."""
    return ProhibitedReachability.of(
        surface=surface,
        reason=reason,
        stage=stage,
        host=host,
        kind=kind,
        via=via,
        matched=matched,
    )


def normalize_host(value: str) -> str:
    """Lowercase host identity: strip scheme, path, port, and trailing dot."""
    raw = value.strip().casefold()
    if not raw:
        return ""
    if "://" in raw:
        parsed = urlparse(raw)
        raw = parsed.hostname or parsed.netloc or raw
    if "/" in raw:
        raw = raw.split("/", 1)[0]
    if raw.startswith("[") and "]" in raw:
        raw = raw[1 : raw.index("]")]
    elif raw.count(":") == 1:
        raw = raw.rsplit(":", 1)[0]
    return raw.rstrip(".")


def is_open_network_token(value: object) -> bool:
    """True when ``value`` names an open/unrestricted network posture."""
    if not isinstance(value, str):
        return False
    token = value.strip().casefold()
    return token in OPEN_NETWORK_TOKENS


def _pattern_matches(host: str, pattern: str) -> bool:
    if not host or not pattern:
        return False
    if host == pattern or fnmatch.fnmatchcase(host, pattern):
        return True
    return "*" not in pattern and "." in pattern and host.endswith("." + pattern)


def classify_denied_host(host: object) -> DeniedHostClass | None:
    """Return the deny-list class for ``host``, or ``None`` when admitted."""
    if not isinstance(host, str) or not host.strip():
        return None
    normalized = normalize_host(host)
    if not normalized:
        return None
    if normalized in OPEN_NETWORK_TOKENS:
        return DeniedHostClass.VENUE
    for pattern, cls in _DENIED_HOST_ROWS:
        if _pattern_matches(normalized, pattern):
            return cls
        # Allowlist wildcard covering a denied host is itself denied.
        if "*" in normalized and _pattern_matches(pattern, normalized):
            return cls
    return None


def is_denied_host(host: object) -> bool:
    """True when ``host`` (direct name or wildcard) sits on the deny-list."""
    return classify_denied_host(host) is not None


def _first_denied(hosts: Iterable[str]) -> tuple[str, DeniedHostClass] | None:
    for host in hosts:
        cls = classify_denied_host(host)
        if cls is not None:
            return host, cls
    return None


def is_forbidden_image_token(token: object) -> str | None:
    """Return the matched forbidden image/import token, or ``None``."""
    if not isinstance(token, str) or not token.strip():
        return None
    lowered = token.strip().casefold()
    image_name = lowered.split("@", 1)[0]
    segment = image_name.rsplit("/", 1)[-1].split(":", 1)[0]
    # Exact hits beat hyphen/underscore aliases; frozenset walk order is unstable.
    if lowered in FORBIDDEN_IMAGE_TOKENS:
        return lowered
    if segment in FORBIDDEN_IMAGE_TOKENS:
        return segment
    dotted = lowered.replace("-", ".").replace("_", ".")
    for forbidden in FORBIDDEN_IMAGE_TOKENS:
        f = forbidden.casefold()
        f_dot = f.replace("-", ".").replace("_", ".")
        if dotted == f_dot:
            return forbidden
        if lowered.startswith((f + ".", f + "-", f + "_")):
            return forbidden
        if dotted.startswith(f_dot + "."):
            return forbidden
        if segment.startswith((f + "-", f + "_")):
            return forbidden
    return None


def is_forbidden_model_adapter(adapter: object) -> bool:
    """True when ``adapter`` is OpenRouter or another banned model path."""
    if not isinstance(adapter, str) or not adapter.strip():
        return False
    return adapter.strip().casefold() in FORBIDDEN_MODEL_ADAPTERS


def refuse_forbidden_model_adapter(
    adapter: object,
    *,
    stage: StageName = "registration",
) -> ProhibitedReachability | None:
    """Refuse an OpenRouter (or otherwise banned) model adapter."""
    if not is_forbidden_model_adapter(adapter):
        return None
    return refuse_reachability(
        surface="model_deployment",
        reason="openrouter_forbidden",
        stage=stage,
        matched=str(adapter).strip().casefold(),
    )


def refuse_reachability_waiver(
    *,
    via: str,
    host: str,
    stage: StageName = "registration",
) -> ProhibitedReachability:
    """Refuse a Role/Mission/plugin/policy/hook attempt to lift a host denial."""
    return refuse_reachability(
        surface="host",
        reason="waiver_not_liftable",
        stage=stage,
        host=host,
        via=via,
    )


def assert_deny_list_not_waivable(
    proposed: frozenset[str] | set[str] | None = None,
) -> None:
    """Refuse any attempt to treat a wider host set as admitted.

    The deny-list is ``DENIED_HOST_PATTERNS``. Callers may not drop a pattern
    or waive a match through Role, Mission, plugin, permission, or hook.
    """
    if proposed is None:
        if not DENIED_HOST_PATTERNS:
            raise ReachabilityBarrierError("reachability deny-list must be non-empty")
        return
    missing = DENIED_HOST_PATTERNS - frozenset(proposed)
    if missing:
        raise ReachabilityBarrierError(
            "reachability deny-list is code-declared and may not be waived; "
            f"missing patterns={sorted(missing)!r} (owner={REACHABILITY_DENY_LIST_OWNER})"
        )


def validate_network_posture(
    network: NetworkPolicy | str | None,
    hosts: Sequence[str] | None,
    *,
    stage: StageName = "registration",
    kind: str | None = None,
) -> Result[tuple[NetworkPolicy, tuple[str, ...]]]:
    """Require ``none`` or ``allowlist`` with an enumerated host set."""
    if network is None:
        return refuse_reachability(
            surface="environment",
            reason="missing_network",
            stage=stage,
            kind=kind,
        )
    if is_open_network_token(network):
        return refuse_reachability(
            surface="environment",
            reason="open_network",
            stage=stage,
            kind=kind,
            matched=str(network),
        )
    if isinstance(network, NetworkPolicy):
        policy = network
    else:
        try:
            policy = NetworkPolicy(network.strip().casefold())
        except ValueError:
            return refuse_reachability(
                surface="environment",
                reason="invalid_network",
                stage=stage,
                kind=kind,
                matched=network,
            )

    if hosts is None:
        return refuse_reachability(
            surface="environment",
            reason="unenumerated_hosts",
            stage=stage,
            kind=kind,
        )
    enumerated = tuple(item.strip() for item in hosts if item.strip())
    if policy is NetworkPolicy.NONE:
        if enumerated:
            return refuse_reachability(
                surface="environment",
                reason="none_with_hosts",
                stage=stage,
                kind=kind,
                host=enumerated[0],
            )
        return Ok((policy, ()))
    # allowlist — must enumerate at least one host, none of them denied.
    if not enumerated:
        return refuse_reachability(
            surface="environment",
            reason="unenumerated_hosts",
            stage=stage,
            kind=kind,
        )
    hit = _first_denied(enumerated)
    if hit is not None:
        host, cls = hit
        return refuse_reachability(
            surface="environment",
            reason="denied_host",
            stage=stage,
            kind=kind,
            host=normalize_host(host) or host,
            matched=cls.value,
        )
    return Ok((policy, enumerated))


def validate_worker_image(
    manifest: WorkerImageManifest | Mapping[str, object] | None,
    *,
    stage: StageName = "registration",
    kind: str | None = None,
) -> Result[WorkerImageManifest]:
    """Refuse an image that contains qmf-venue, a broker/exchange SDK, or qmn."""
    if manifest is None:
        resolved = WorkerImageManifest()
    elif isinstance(manifest, WorkerImageManifest):
        resolved = manifest
    else:
        image = manifest.get("image", "")
        packages = manifest.get("packages", ())
        imports = manifest.get("imports", ())
        pkg_tuple: tuple[str, ...] = ()
        imp_tuple: tuple[str, ...] = ()
        if isinstance(packages, Sequence) and not isinstance(packages, (str, bytes)):
            pkg_seq = cast(Sequence[object], packages)
            pkg_tuple = tuple(str(item) for item in pkg_seq)
        if isinstance(imports, Sequence) and not isinstance(imports, (str, bytes)):
            imp_seq = cast(Sequence[object], imports)
            imp_tuple = tuple(str(item) for item in imp_seq)
        resolved = WorkerImageManifest.from_values(
            image=str(image) if image is not None else "",
            packages=pkg_tuple,
            imports=imp_tuple,
        )
    tokens: list[str] = [resolved.image, *resolved.packages, *resolved.imports]
    for token in tokens:
        matched = is_forbidden_image_token(token)
        if matched is not None:
            return refuse_reachability(
                surface="image",
                reason="forbidden_image",
                stage=stage,
                kind=kind,
                matched=matched,
                host=token,
            )
    return Ok(resolved)


def validate_host_identity(
    kind: ExecutionEnvironmentKind | str,
    hosts: Sequence[str],
    *,
    carries_trading_credential: bool = False,
    running_node: bool = False,
    stage: StageName = "registration",
) -> Result[tuple[str, ...]]:
    """Refuse ``remote_host`` / ``desktop`` that name a trading-node identity."""
    resolved_kind = (
        kind if isinstance(kind, ExecutionEnvironmentKind) else ExecutionEnvironmentKind(kind)
    )
    kind_token = resolved_kind.value
    hit = _first_denied(hosts)
    if hit is not None:
        host, cls = hit
        reason = "trading_node_host" if cls is DeniedHostClass.TRADING_NODE else "denied_host"
        return refuse_reachability(
            surface="host",
            reason=reason,
            stage=stage,
            kind=kind_token,
            host=normalize_host(host) or host,
            matched=cls.value,
        )
    if resolved_kind in HOST_IDENTITY_KINDS and carries_trading_credential:
        return refuse_reachability(
            surface="host",
            reason="trading_credential_host",
            stage=stage,
            kind=kind_token,
            host=next((h for h in hosts if h), None),
        )
    if resolved_kind in HOST_IDENTITY_KINDS and running_node:
        return refuse_reachability(
            surface="host",
            reason="running_node_host",
            stage=stage,
            kind=kind_token,
            host=next((h for h in hosts if h), None),
        )
    return Ok(tuple(hosts))


def _profile_carries_authenticated_state(profile: ComputerUseProfile) -> str | None:
    if profile.venue_logins:
        return profile.venue_logins[0]
    for host in (*profile.cookie_hosts, *profile.session_hosts):
        if classify_denied_host(host) is not None:
            return host
        lowered = host.casefold()
        if any(token in lowered for token in _VENUE_PROFILE_TOKENS):
            return host
    for ref in profile.saved_credential_refs:
        if any(ref.startswith(prefix) for prefix in OUT_OF_SCOPE_CREDENTIAL_REF_PREFIXES):
            return ref
        lowered = ref.casefold()
        if any(token in lowered for token in _VENUE_PROFILE_TOKENS):
            return ref
    return None


def refuse_handed_venue_login(
    *,
    via: str,
    payload: str,
    stage: StageName = "registration",
) -> ProhibitedReachability:
    """Refuse a venue login handed through Knowledge, Memory, a ledger, or a tool."""
    return refuse_reachability(
        surface="profile",
        reason="handed_venue_login",
        stage=stage,
        via=via.casefold(),
        host=payload,
    )


def validate_computer_use_profile(
    profile: ComputerUseProfile | None,
    *,
    stage: StageName = "registration",
    kind: str | None = None,
    require: bool = False,
) -> Result[ComputerUseProfile | None]:
    """Refuse a profile carrying venue/broker state or a handed venue login."""
    if profile is None:
        if require:
            return refuse_reachability(
                surface="profile",
                reason="missing_profile",
                stage=stage,
                kind=kind,
            )
        return Ok(None)
    hit = _first_denied(profile.reachable_hosts)
    if hit is not None:
        host, cls = hit
        return refuse_reachability(
            surface="profile",
            reason="denied_host",
            stage=stage,
            kind=kind,
            host=normalize_host(host) or host,
            matched=cls.value,
        )
    carried = _profile_carries_authenticated_state(profile)
    if carried is not None:
        return refuse_reachability(
            surface="profile",
            reason="venue_profile_state",
            stage=stage,
            kind=kind,
            host=carried,
        )
    if profile.handed_via is not None and profile.handed_via in HANDED_VIA_SURFACES:
        if profile.venue_logins:
            payload = profile.venue_logins[0]
        elif profile.saved_credential_refs:
            payload = profile.saved_credential_refs[0]
        else:
            payload = profile.handed_via
        return refuse_handed_venue_login(
            via=profile.handed_via,
            payload=payload,
            stage=stage,
        )
    return Ok(profile)


def validate_execution_environment_declaration(
    declaration: ExecutionEnvironmentDeclaration | None,
    *,
    stage: StageName = "registration",
    kind: ExecutionEnvironmentKind | str | None = None,
) -> Result[ExecutionEnvironmentDeclaration]:
    """Refuse a venue-reaching environment before it can host or expose a tool."""
    if declaration is None:
        kind_token = kind.value if isinstance(kind, ExecutionEnvironmentKind) else kind
        return refuse_reachability(
            surface="environment",
            reason="unenumerated_hosts",
            stage=stage,
            kind=kind_token,
        )
    kind_token = declaration.kind.value
    posture = validate_network_posture(
        declaration.network,
        declaration.reachable_hosts,
        stage=stage,
        kind=kind_token,
    )
    if not isinstance(posture, Ok):
        return posture
    image = validate_worker_image(
        declaration.image_manifest(),
        stage=stage,
        kind=kind_token,
    )
    if not isinstance(image, Ok):
        return image
    identity = validate_host_identity(
        declaration.kind,
        declaration.identity_hosts(),
        carries_trading_credential=declaration.carries_trading_credential,
        running_node=declaration.running_node,
        stage=stage,
    )
    if not isinstance(identity, Ok):
        return identity
    profile = validate_computer_use_profile(
        declaration.profile,
        stage=stage,
        kind=kind_token,
        require=False,
    )
    if not isinstance(profile, Ok):
        return profile
    return Ok(declaration)


def parse_declaration(
    *,
    kind: ExecutionEnvironmentKind | str,
    network: NetworkPolicy | str | None,
    reachable_hosts: Sequence[str] | None = None,
    provider_ref: str = "",
    image: str = "",
    host: str = "",
    carries_trading_credential: bool = False,
    running_node: bool = False,
    image_packages: Sequence[str] = (),
    image_imports: Sequence[str] = (),
    profile: ComputerUseProfile | None = None,
    stage: StageName = "registration",
) -> Result[ExecutionEnvironmentDeclaration]:
    """Parse then validate a declaration; invented network values are refusals."""
    kind_token = kind.value if isinstance(kind, ExecutionEnvironmentKind) else str(kind)
    posture = validate_network_posture(
        network,
        reachable_hosts,
        stage=stage,
        kind=kind_token,
    )
    if not isinstance(posture, Ok):
        return posture
    policy, hosts = posture.value
    try:
        declaration = ExecutionEnvironmentDeclaration.try_parse(
            kind=kind,
            network=policy,
            reachable_hosts=hosts,
            provider_ref=provider_ref,
            image=image,
            host=host,
            carries_trading_credential=carries_trading_credential,
            running_node=running_node,
            image_packages=image_packages,
            image_imports=image_imports,
            profile=profile,
        )
    except VocabularyError:
        return refuse_reachability(
            surface="environment",
            reason="invalid_kind",
            stage=stage,
            kind=kind_token,
            matched=repr(kind),
        )
    return validate_execution_environment_declaration(declaration, stage=stage)
