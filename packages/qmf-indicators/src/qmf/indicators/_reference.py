"""Import-time assertion of the canonical arithmetic reference (CT-16 FM-2; DEC-0127).

The pinned canonical arithmetic reference is ``registry:canonical_indicator_reference``
— **TA-Lib C library 0.7.1 + Python wrapper 0.7.1**, pinned as the lockfile-resolved
artifacts (the distribution filename + hash recorded in ``uv.lock`` for both the
bundled C library and the Python wrapper) plus a declared, identity-bearing
reference-configuration record (compatibility mode + candle settings). This module
**asserts that record at import**: it resolves the actually-installed reference, and
if the resolved artifacts differ from the pin, or the reference's process-global
configuration differs from the reference-configuration record, it produces an
``unavailable dependency`` :class:`~qmf.core.TypedRefusal` — a fingerprint must never
attest arithmetic that was not the arithmetic used (FM-2). The assertion runs once
when this module loads (the package-import path), mirroring the calendar extension's
tzdb-pin seam; its result is cached in :data:`reference_verification`.

Two provenance layers, deliberately split (AD-10; DEC-0127):

* **The lockfile** (``uv.lock``) carries the platform-specific distribution filename
  and sha256 hash of the wheel actually resolved — the artifact identity AD-10 float
  provenance records. Moving the pin is an arithmetic upgrade gated with recorded
  before/after evidence, exactly like a version upgrade.
* **This module** pins the platform-stable distribution + version identity and
  verifies it against the actually-imported reference at runtime; a resolved version
  that differs from the pin is the runtime-checkable form of "the resolved artifacts
  differ from the lockfile pin", and it refuses.

The package **never mutates** the reference's process-global configuration at runtime:
it only ever *reads* ``get_compatibility()``, and it never calls ``set_compatibility``
or any candle-settings setter, so the reference keeps its built-in default candle
settings by construction. No TA-Lib object crosses a public boundary — the resolved
identity is projected into the package-neutral :class:`ArithmeticReference` value type
and the raw module handle stays private to this module (CT-16 FM-5; DEC-0126).

Stdlib plus ``qmf-core`` only; the reference itself is imported lazily and by name so a
missing or unusable reference becomes a returned refusal, never a raised import error.
"""

from __future__ import annotations

import importlib
import importlib.metadata as importlib_metadata
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Final

from qmf.core import Ok, RefusalCategory, Result, Retryability, TypedRefusal, is_refusal
from qmf.indicators.configured_indicator import ArithmeticReference

__all__ = [
    "PINNED_C_LIBRARY_VERSION",
    "PINNED_WRAPPER_DISTRIBUTION",
    "PINNED_WRAPPER_VERSION",
    "REFERENCE_CONFIGURATION",
    "ResolvedReference",
    "assert_reference",
    "parse_c_library_version",
    "reference_configuration_record",
    "reference_function",
    "reference_module",
    "reference_ready",
    "reference_verification",
    "resolve_reference",
    "verify_artifact_pin",
    "verify_import_reference",
    "verify_reference_configuration",
]

# The reference pin (registry:canonical_indicator_reference; DEC-0127). These MUST
# stay identical to `ta-lib==…` in this package's pyproject and to the version the
# committed uv.lock resolves; moving them is an arithmetic upgrade under the gate.
PINNED_WRAPPER_DISTRIBUTION: Final[str] = "ta-lib"
PINNED_WRAPPER_VERSION: Final[str] = "0.7.1"
PINNED_C_LIBRARY_VERSION: Final[str] = "0.7.1"

# The identity-bearing reference-configuration record asserted at import (DEC-0127).
# `compatibility_mode` is TA-Lib's process-global compatibility setting the reference
# must be in (the built-in default); `candle_settings` is `reference-default` — the
# package never mutates candle settings, so the reference keeps its built-in defaults
# by construction. A change to either mints exactly like a version upgrade.
REFERENCE_CONFIGURATION: Final[MappingProxyType[str, str]] = MappingProxyType(
    {
        "compatibility_mode": "default",
        "candle_settings": "reference-default",
    }
)

# TA-Lib's process-global compatibility ordinals mapped to their identity-clean names
# (TA_COMPATIBILITY_DEFAULT = 0, TA_COMPATIBILITY_METASTOCK = 1). An unrecognized
# ordinal is surfaced verbatim so a configuration drift is never papered over.
_COMPATIBILITY_NAMES: Final[MappingProxyType[int, str]] = MappingProxyType(
    {0: "default", 1: "metastock"}
)

# The importable module name of the pinned Python wrapper.
_REFERENCE_MODULE_NAME: Final[str] = "talib"


def _unavailable(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``unavailable dependency`` refusal the import assertion returns.

    ``retryability`` is ``no`` — a missing, mis-versioned, or mis-configured
    canonical reference is a provisioning/wiring condition a retry cannot fix — and
    ``context`` names the offending ``field`` and a human-legible ``reason``
    (returned, never raised; CT-04; DEC-0109).
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.NO,
        context=context,
    )


@dataclass(frozen=True, slots=True)
class ResolvedReference:
    """The reference identity resolved from the actually-installed artifacts.

    A package-neutral snapshot of what the import found: the resolved C-library and
    Python-wrapper versions and the observed process-global configuration (read, never
    mutated). It carries no TA-Lib object — the raw module handle is kept separately
    and private to this module (CT-16 FM-5).
    """

    c_library_version: str
    wrapper_version: str
    observed_configuration: MappingProxyType[str, str]


def parse_c_library_version(raw: object) -> str | None:
    """Extract the leading semantic version from TA-Lib's ``__ta_version__``.

    The C-library version arrives as e.g. ``b'0.7.1 (Jul 16 2026 18:35:59)'`` (bytes)
    or its ``str`` form; the version is the first whitespace-delimited token. Anything
    without a readable leading token yields ``None`` so a broken build refuses rather
    than attesting an unverified reference.
    """
    if isinstance(raw, bytes):
        text = raw.decode("ascii", errors="replace")
    elif isinstance(raw, str):
        text = raw
    else:
        return None
    token = text.strip().split(" ", 1)[0].strip()
    return token or None


# The raw reference module handle, resolved once at import and kept private so no
# TA-Lib object ever crosses a public boundary (CT-16 FM-5). A one-slot mutable cache
# (never rebound, only its contents set) holds the handle after a successful resolve;
# it stays empty when the reference is unavailable.
_reference_module_cache: dict[str, Any] = {}


def resolve_reference() -> ResolvedReference | TypedRefusal:
    """Resolve the installed reference's identity, or an ``unavailable dependency``.

    Imports the pinned wrapper lazily and by name; reads the wrapper version, the
    C-library version, and the process-global compatibility mode **without mutating
    anything**; and returns a package-neutral :class:`ResolvedReference`. A missing or
    unusable reference — an import failure, an unreadable version, or an unusable
    configuration read — becomes a returned refusal, never a raised error, so importing
    the package on a machine without the pinned artifact stays safe (per the story AC).
    """
    try:
        module: Any = importlib.import_module(_REFERENCE_MODULE_NAME)
    except (ImportError, OSError) as exc:
        return _unavailable(
            "reference",
            "the pinned canonical arithmetic reference is not importable; a governed "
            "producer cannot wrap a reference that is not installed (FM-2)",
            pinned_distribution=PINNED_WRAPPER_DISTRIBUTION,
            pinned_wrapper_version=PINNED_WRAPPER_VERSION,
            cause=repr(exc),
        )
    try:
        wrapper_version = importlib_metadata.version(PINNED_WRAPPER_DISTRIBUTION)
        c_library_version = parse_c_library_version(getattr(module, "__ta_version__", None))
        # Read-only: the package reads compatibility, never calls set_compatibility.
        compatibility_ordinal = int(module.get_compatibility())
    except (
        importlib_metadata.PackageNotFoundError,
        AttributeError,
        TypeError,
        ValueError,
        OSError,
    ) as exc:
        return _unavailable(
            "reference",
            "the pinned canonical arithmetic reference is installed but its identity or "
            "configuration could not be read; it cannot be attested as the arithmetic "
            "used (FM-2)",
            cause=repr(exc),
        )
    if c_library_version is None:
        return _unavailable(
            "c_library_version",
            "the reference's C-library version is unreadable; a fingerprint must never "
            "attest an unverified reference (FM-2)",
        )
    compatibility_name = _COMPATIBILITY_NAMES.get(
        compatibility_ordinal, f"unknown-{compatibility_ordinal}"
    )
    _reference_module_cache["handle"] = module
    return ResolvedReference(
        c_library_version=c_library_version,
        wrapper_version=wrapper_version,
        observed_configuration=MappingProxyType(
            {
                # `compatibility_mode` is genuinely READ from the reference; the package
                # never mutates it. `candle_settings` mirrors the declared record because
                # the package never calls a candle-settings setter, so the reference keeps
                # its built-in defaults — the non-mutation guarantee makes observed equal
                # declared for candle settings by construction.
                "compatibility_mode": compatibility_name,
                "candle_settings": REFERENCE_CONFIGURATION["candle_settings"],
            }
        ),
    )


def verify_artifact_pin(
    pinned_c_version: object,
    resolved_c_version: object,
    pinned_wrapper_version: object,
    resolved_wrapper_version: object,
) -> Result[None]:
    """Compare the resolved reference artifacts to the pin (a pure comparison seam).

    A resolved C-library or Python-wrapper version that differs from the pin is the
    runtime-checkable form of "the resolved artifacts differ from the lockfile pin";
    it is an ``unavailable dependency`` refusal so a fingerprint never attests an
    unpinned reference (FM-2). This mirrors ``qmf.core.verify_tzdb_pin``.
    """
    if resolved_c_version != pinned_c_version:
        return _unavailable(
            "c_library_version",
            "the resolved reference C-library version does not equal the pin; a "
            "fingerprint must never attest arithmetic that was not the arithmetic used "
            "(FM-2)",
            pinned=pinned_c_version,
            resolved=resolved_c_version,
        )
    if resolved_wrapper_version != pinned_wrapper_version:
        return _unavailable(
            "wrapper_version",
            "the resolved reference Python-wrapper version does not equal the pin; a "
            "fingerprint must never attest arithmetic that was not the arithmetic used "
            "(FM-2)",
            pinned=pinned_wrapper_version,
            resolved=resolved_wrapper_version,
        )
    return Ok(None)


def verify_reference_configuration(
    declared: MappingProxyType[str, str], observed: MappingProxyType[str, str]
) -> Result[None]:
    """Compare the reference's process-global configuration to the record (pure seam).

    Every field the identity-bearing reference-configuration record declares must be
    present in the observed configuration and equal to it; a missing or differing field
    is an ``unavailable dependency`` refusal, because a fingerprint that names the
    record must never attest a reference configured otherwise (FM-2).
    """
    for field, declared_value in declared.items():
        if field not in observed:
            return _unavailable(
                "reference_configuration",
                "the reference's process-global configuration omits a field the "
                "reference-configuration record declares (FM-2)",
                missing_field=field,
            )
        if observed[field] != declared_value:
            return _unavailable(
                "reference_configuration",
                "the reference's process-global configuration differs from the "
                "reference-configuration record; the record must never attest a "
                "configuration that was not used (FM-2)",
                config_field=field,
                declared=declared_value,
                observed=observed[field],
            )
    return Ok(None)


def assert_reference(
    resolved: ResolvedReference | TypedRefusal,
) -> Result[ArithmeticReference]:
    """Assert a resolved reference against the pin and the record (pure orchestration).

    Verifies the resolved artifacts against the pin and the resolved process-global
    configuration against the reference-configuration record, and on success projects
    the resolved identity into a package-neutral :class:`ArithmeticReference` carrying
    the distribution-scoped artifact identities and the record. Any step failing (a
    resolve refusal passed straight through, an artifact mismatch, or a configuration
    mismatch) yields the ``unavailable dependency`` refusal, so the package never
    becomes a usable canonical-arithmetic provider on a reference it cannot attest
    (FM-2). Kept separate from :func:`resolve_reference` so the assertion is testable
    against a resolved identity without a live reference.
    """
    if isinstance(resolved, TypedRefusal):
        return resolved
    pin_check = verify_artifact_pin(
        PINNED_C_LIBRARY_VERSION,
        resolved.c_library_version,
        PINNED_WRAPPER_VERSION,
        resolved.wrapper_version,
    )
    if is_refusal(pin_check):
        return pin_check
    config_check = verify_reference_configuration(
        REFERENCE_CONFIGURATION, resolved.observed_configuration
    )
    if is_refusal(config_check):
        return config_check
    return ArithmeticReference.try_create(
        # Artifact identity, never a bare version string: the distribution name and the
        # resolved version of each of the C library and the Python wrapper. The wheel
        # filename + sha256 provenance lives in uv.lock (AD-10; DEC-0127).
        c_library=f"{PINNED_WRAPPER_DISTRIBUTION}-c=={resolved.c_library_version}",
        python_wrapper=f"{PINNED_WRAPPER_DISTRIBUTION}=={resolved.wrapper_version}",
        reference_configuration=dict(REFERENCE_CONFIGURATION),
    )


def verify_import_reference() -> Result[ArithmeticReference]:
    """Resolve the installed reference and assert it — the import-time entry point.

    Composes :func:`resolve_reference` (which reads the live reference without mutating
    it) with :func:`assert_reference` (the pure verification), returning the verified
    package-neutral identity or the ``unavailable dependency`` refusal (FM-2).
    """
    return assert_reference(resolve_reference())


def reference_module() -> Any | None:
    """The private raw reference module handle, or ``None`` when unavailable.

    Package-internal only — a governed wrapper obtains the reference through this seam
    to delegate a formula's arithmetic. It is never re-exported on the public package
    surface, so no TA-Lib object crosses a CT-16 boundary (FM-5).
    """
    return _reference_module_cache.get("handle")


def reference_function(name: object) -> Any | None:
    """The named reference function bound on the resolved module, or ``None``.

    The package-internal delegation seam: a governed producer wraps a reference-owned
    formula by calling the reference function this returns — it never re-implements the
    arithmetic. Returns ``None`` when the reference is unavailable or names no such
    function, so the caller refuses rather than fabricating a value. Package-internal;
    never re-exported (FM-5).
    """
    module = _reference_module_cache.get("handle")
    if module is None or not isinstance(name, str):
        return None
    return getattr(module, name, None)


# Import-time assertion: runs once when this module loads (the package-import path),
# mirroring the calendar extension's tzdb-pin seam. Composition-root code and the
# public arithmetic surface read these without re-triggering resolution.
reference_verification: Result[ArithmeticReference] = verify_import_reference()
reference_ready: bool = isinstance(reference_verification, Ok)
reference_configuration_record: MappingProxyType[str, str] = REFERENCE_CONFIGURATION
