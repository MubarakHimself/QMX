"""Sandbox-provenance refusal at hub publish and promotion pull (TN-20).

The node's only inbound live path is a click-gated pull of the registry as-of
set from the hub's published area. ``provenance = sandbox`` is refused at
publish and again at pull; an as-of set containing one sandbox artifact
refuses the whole pull. Each pulled artifact's ``fp1`` is verified against
the promotion card before a seat may land (DEC-0188, DEC-0205).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Fingerprint, Ok, Result, is_refusal

from qmn.promotion._refuse import clean_token, invalid, policy, unavailable

__all__ = [
    "HUB_CROSSINGS",
    "SANDBOX_PROVENANCE",
    "HubArtifact",
    "PublishedHub",
    "publish_hub_fragment",
    "pull_published_as_of",
    "refuse_sandbox_provenance",
]

SANDBOX_PROVENANCE: Final[str] = "sandbox"
HUB_CROSSINGS: Final[frozenset[str]] = frozenset({"publish", "pull"})


@dataclass(frozen=True, slots=True)
class HubArtifact:
    """One published (or candidate) hub fragment with provenance and ``fp1``."""

    artifact_key: str
    fp1: Fingerprint
    provenance: str

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "artifact_key": self.artifact_key,
                "fp1": self.fp1.value,
                "provenance": self.provenance,
            }
        )

    @classmethod
    def try_create(
        cls,
        *,
        artifact_key: object,
        fp1: object,
        provenance: object,
    ) -> Result[HubArtifact]:
        key = clean_token(artifact_key)
        if key is None:
            return invalid(
                "artifact_key",
                "a hub artifact names a non-empty artifact key",
                given=repr(artifact_key),
            )
        if not isinstance(fp1, Fingerprint):
            return invalid(
                "fp1",
                "a hub artifact carries an fp1 fingerprint",
                given=repr(fp1),
            )
        token = clean_token(provenance)
        if token is None:
            return invalid(
                "provenance",
                "a hub artifact declares a non-empty provenance token",
                given=repr(provenance),
            )
        return Ok(cls(artifact_key=key, fp1=fp1, provenance=token))


@dataclass(frozen=True, slots=True)
class PublishedHub:
    """Read-only published area — the only source a promotion pull may read."""

    artifacts: tuple[HubArtifact, ...]

    def by_key(self) -> Mapping[str, HubArtifact]:
        return MappingProxyType({item.artifact_key: item for item in self.artifacts})


def refuse_sandbox_provenance(provenance: object, *, crossing: object) -> Result[None]:
    """Refuse ``provenance = sandbox`` at publish or pull (DEC-0188, DEC-0205)."""
    gate = clean_token(crossing)
    if gate is None or gate not in HUB_CROSSINGS:
        return invalid(
            "crossing",
            "sandbox provenance is refused at publish and at pull",
            given=repr(crossing),
            allowed=sorted(HUB_CROSSINGS),
        )
    if not isinstance(provenance, str):
        return Ok(None)
    if provenance.strip().lower() != SANDBOX_PROVENANCE:
        return Ok(None)
    return policy(
        "provenance",
        f"sandbox provenance is refused at {gate}",
        provenance=SANDBOX_PROVENANCE,
        crossing=gate,
    )


def publish_hub_fragment(artifact: object) -> Result[HubArtifact]:
    """Operator ``hub_publish`` domain check — sandbox fragments never publish."""
    if not isinstance(artifact, HubArtifact):
        return invalid(
            "artifact",
            "hub publish takes a HubArtifact",
            given=repr(artifact),
        )
    refused = refuse_sandbox_provenance(artifact.provenance, crossing="publish")
    if is_refusal(refused):
        return refused
    return Ok(artifact)


def pull_published_as_of(
    hub: object,
    *,
    artifact_keys: object,
    attested_fp1: object,
    template_fp1: object,
) -> Result[tuple[HubArtifact, ...]]:
    """Node-initiated as-of pull. Sandbox in the set refuses the whole pull."""
    if not isinstance(hub, PublishedHub):
        return invalid(
            "hub",
            "a promotion pull reads the hub published area",
            given=repr(type(hub).__name__),
        )
    if not isinstance(attested_fp1, Fingerprint):
        return invalid(
            "attested_fp1",
            "the pull verifies artifacts against the card's attested fp1",
            given=repr(attested_fp1),
        )
    if template_fp1 is not None and not isinstance(template_fp1, Fingerprint):
        return invalid(
            "template_fp1",
            "the pull verifies the attested Book or BMS definition fp1",
            given=repr(template_fp1),
        )
    keys = _as_keys(artifact_keys)
    if is_refusal(keys):
        return keys
    if not keys.value:
        return invalid(
            "artifact_keys",
            "a promotion pull names the as-of set to land",
        )
    index = hub.by_key()
    pulled: list[HubArtifact] = []
    attested_seen = False
    template_seen = template_fp1 is None
    allowed: set[str] = {attested_fp1.value}
    if isinstance(template_fp1, Fingerprint):
        allowed.add(template_fp1.value)
    for key in keys.value:
        artifact = index.get(key)
        if artifact is None:
            return unavailable(
                "artifact_key",
                "the published area does not hold the named as-of artifact",
                artifact_key=key,
            )
        sandbox = refuse_sandbox_provenance(artifact.provenance, crossing="pull")
        if is_refusal(sandbox):
            return sandbox
        if artifact.fp1.value not in allowed:
            return policy(
                "fp1",
                "each pulled artifact's fp1 is verified against the promotion card "
                "before the seat lands",
                artifact_key=key,
                artifact_fp1=artifact.fp1.value,
            )
        if artifact.fp1 == attested_fp1:
            attested_seen = True
        if isinstance(template_fp1, Fingerprint) and artifact.fp1 == template_fp1:
            template_seen = True
        pulled.append(artifact)
    if not attested_seen:
        return policy(
            "attested_fp1",
            "the as-of pull must include the artifact the promotion card attests",
            attested_fp1=attested_fp1.value,
        )
    if not template_seen:
        return policy(
            "template_fp1",
            "the as-of pull must include the attested Book or BMS definition",
            template_fp1=cast("Fingerprint", template_fp1).value,
        )
    return Ok(tuple(pulled))


def _as_keys(value: object) -> Result[tuple[str, ...]]:
    if isinstance(value, str):
        token = clean_token(value)
        if token is None:
            return invalid("artifact_keys", "an as-of key is a non-empty token")
        return Ok((token,))
    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return invalid(
            "artifact_keys",
            "an as-of pull names a sequence of artifact keys",
            given=repr(type(value).__name__),
        )
    keys: list[str] = []
    for item in cast("Sequence[object]", value):
        token = clean_token(item)
        if token is None:
            return invalid(
                "artifact_keys",
                "each as-of key is a non-empty token",
                given=repr(item),
            )
        keys.append(token)
    return Ok(tuple(keys))
