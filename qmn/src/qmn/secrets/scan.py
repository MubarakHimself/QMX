"""Secret-surface scanner: holders, presence metadata, no values (TN-12).

Preflight and this scanner together prove only the four named holders resolve
their exact references, and that config / evidence / logs / health / metrics /
refusals carry reference ids or ``is_set`` booleans — never secret values.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Final, cast

from qmf.core.refusal import Ok, Result, TypedRefusal

from qmn.secrets._refuse import policy
from qmn.secrets.holders import extra_holders, refuse_fifth_holder
from qmn.secrets.store import NodeSecretStore

__all__ = [
    "FORBIDDEN_SURFACE_KEYS",
    "scan_holder_declaration",
    "scan_payload_for_secret_values",
    "scan_store_presence",
]

FORBIDDEN_SURFACE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "secret",
        "secret_value",
        "password",
        "token",
        "credential",
        "account_number",
        "raw_account",
        "api_key",
        "private_key",
        "client_secret",
        "access_token",
        "refresh_token",
    }
)


def scan_holder_declaration(declared: Iterable[str]) -> Result[tuple[str, ...]]:
    """Refuse a fifth or unnamed holder; otherwise return the declared set."""
    names = tuple(declared)
    extra = extra_holders(names)
    if extra:
        return refuse_fifth_holder(extra)
    return Ok(names)


def scan_store_presence(store: NodeSecretStore) -> Mapping[str, bool]:
    """Preflight ``is_set`` map — reference ids to booleans, never values."""
    return store.presence()


def scan_payload_for_secret_values(
    payload: object,
    plaintexts: Sequence[str],
    *,
    surface: str,
) -> Result[None]:
    """Fail when a secret value or forbidden key appears on a public surface."""
    needles = tuple(item for item in plaintexts if item)
    findings = _walk(payload, needles, path="$")
    if findings:
        return policy(
            "surface",
            "a secret value or forbidden key appeared on a public surface",
            failure_id="secrets.surface.value_leak",
            surface=surface,
            findings=findings,
        )
    return Ok(None)


def _walk(node: object, needles: Sequence[str], *, path: str) -> tuple[str, ...]:
    hits: list[str] = []
    if isinstance(node, Mapping):
        mapping = cast("Mapping[object, object]", node)
        for key, value in mapping.items():
            key_text = str(key)
            folded = key_text.casefold()
            child = f"{path}.{key_text}"
            if folded in FORBIDDEN_SURFACE_KEYS:
                hits.append(child)
            hits.extend(_walk(value, needles, path=child))
        return tuple(hits)
    if isinstance(node, (list, tuple)):
        sequence = cast("Sequence[object]", node)
        for index, item in enumerate(sequence):
            hits.extend(_walk(item, needles, path=f"{path}[{index}]"))
        return tuple(hits)
    if isinstance(node, str):
        for needle in needles:
            if needle and needle in node:
                hits.append(path)
                break
        return tuple(hits)
    if isinstance(node, TypedRefusal):
        hits.extend(_walk(dict(node.context), needles, path=f"{path}.context"))
        return tuple(hits)
    return ()
