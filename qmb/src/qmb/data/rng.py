"""QMX-owned, version-pinned deterministic RNG for the generator (Story 23.4).

Determinism is a platform property (NFR-03; R5). The Lean portability caveat (spec
section 2A.3) is that .NET's ``System.Random`` is not stable across runtimes, so the
generator MUST NOT draw randomness through a runtime's stdlib ``Random``. This module
is the QMX-owned, **version-pinned** generator every synthetic-data draw goes through:
a SplitMix64 core over pure 64-bit integer arithmetic whose output stream is identical
on every platform and Python build, independent of the stdlib ``random`` module's
MT19937 and its seeding. The algorithm name and version are recorded in the generator
config identity and the store provenance (R4/R5), so ``{process, seed, source-dataset
id, generator-config fp1}`` pins the exact bit-stream that produced an artifact.

Uniform integers use unbiased rejection sampling; Gaussian draws use the Marsaglia
polar transform over the integer stream (``sqrt`` and ``log`` only — no
platform-divergent ``sin`` / ``cos``). Every float a draw yields re-enters the integer
money path through the named AD-7 :meth:`~qmf.core.exact.Price.from_float` conversion
boundary under the config's declared rounding mode, where a sub-tick libm difference is
quantized away — so the produced bars reproduce bit-for-bit on the run platform.

This module holds no ambient state: a :class:`PinnedRng` is an explicitly-seeded,
instance-owned generator (never a module-global), and the substream of scenario ``k``
is seeded ``base_seed + k`` (:func:`derive_substream_seed`) so scenario ``k``
reproduces in isolation.
"""

from __future__ import annotations

import math
from typing import Final

__all__ = [
    "IS_QMX_OWNED",
    "IS_RUNTIME_STDLIB_RANDOM",
    "RNG_ALGORITHM",
    "RNG_FAMILY",
    "RNG_VERSION",
    "SEED_DERIVATION_RULE",
    "PinnedRng",
    "derive_substream_seed",
    "rng_provenance",
]

# --- the pinned RNG identity (R4/R5, AC2) ------------------------------------

# The QMX-owned algorithm family and its pinned version. ``RNG_FAMILY`` is the
# ``algorithm@version`` token recorded in artifact provenance; it deliberately does
# NOT name the stdlib MT19937, because the generator never draws through a runtime
# stdlib Random (spec section 2A.3).
RNG_ALGORITHM: Final[str] = "qmx-splitmix64"
RNG_VERSION: Final[int] = 1
RNG_FAMILY: Final[str] = f"{RNG_ALGORITHM}-v{RNG_VERSION}"

# The multi-scenario substream rule: scenario k draws from base_seed + k, so scenario
# k is bit-reproducible in isolation (R5; spec section 2B).
SEED_DERIVATION_RULE: Final[str] = "base_seed + scenario_index"

# Provenance flags recorded so a reader can assert the generator owns its RNG and
# never falls back to a runtime stdlib Random (AC2).
IS_QMX_OWNED: Final[bool] = True
IS_RUNTIME_STDLIB_RANDOM: Final[bool] = False

_MASK64: Final[int] = (1 << 64) - 1
# SplitMix64 constants (Steele, Lea & Flood 2014) — fixed by the pinned algorithm.
_GOLDEN_GAMMA: Final[int] = 0x9E3779B97F4A7C15
_MIX_A: Final[int] = 0xBF58476D1CE4E5B9
_MIX_B: Final[int] = 0x94D049BB133111EB
_TWO_POW_53: Final[float] = float(1 << 53)


class PinnedRng:
    """A QMX-owned, version-pinned SplitMix64 generator (AC2).

    Explicitly seeded and instance-owned — never a module-global, never the stdlib
    ``random`` module. The 64-bit output stream is a pure integer function of the seed,
    identical on every platform and Python build. :meth:`randrange` draws an unbiased
    uniform integer; :meth:`gauss` draws a normal deviate via the Marsaglia polar
    method (one cached spare per pair). Two instances seeded alike produce identical
    streams; different seeds produce independent streams.
    """

    __slots__ = ("_spare", "_state")

    def __init__(self, seed: int) -> None:
        self._state = int(seed) & _MASK64
        self._spare: float | None = None

    def next_u64(self) -> int:
        """The next 64-bit SplitMix64 output — the deterministic core draw."""
        self._state = (self._state + _GOLDEN_GAMMA) & _MASK64
        z = self._state
        z = ((z ^ (z >> 30)) * _MIX_A) & _MASK64
        z = ((z ^ (z >> 27)) * _MIX_B) & _MASK64
        return z ^ (z >> 31)

    def random(self) -> float:
        """A uniform double in ``[0, 1)`` from the top 53 bits of one output."""
        return (self.next_u64() >> 11) / _TWO_POW_53

    def randrange(self, n: int) -> int:
        """An unbiased uniform integer in ``[0, n)`` via rejection sampling.

        ``n`` must be a positive integer (a caller contract, not a domain value); the
        rejection window discards the small non-uniform tail so every residue class is
        equally likely.
        """
        if n <= 0:
            raise ValueError("randrange bound must be a positive integer")
        limit = ((1 << 64) // n) * n
        while True:
            draw = self.next_u64()
            if draw < limit:
                return draw % n

    def gauss(self, mu: float, sigma: float) -> float:
        """A normal deviate ``N(mu, sigma)`` via the Marsaglia polar transform.

        Uses only ``sqrt`` and ``log`` (no ``sin`` / ``cos``), so the transform does
        not diverge across libm implementations beyond a sub-tick ULP. The paired spare
        deviate is cached and returned on the next call.
        """
        spare = self._spare
        if spare is not None:
            self._spare = None
            return mu + sigma * spare
        while True:
            u = 2.0 * self.random() - 1.0
            v = 2.0 * self.random() - 1.0
            s = (u * u) + (v * v)
            if 0.0 < s < 1.0:
                break
        factor = math.sqrt(-2.0 * math.log(s) / s)
        self._spare = v * factor
        return mu + sigma * (u * factor)


def derive_substream_seed(base_seed: int, scenario_index: int) -> int:
    """Scenario ``k``'s substream seed, ``base_seed + scenario_index`` (SEED_DERIVATION_RULE).

    Deriving each scenario's substream from the master seed makes scenario ``k``
    bit-reproducible in isolation (R5; spec section 2B). Callers validate the inputs as
    non-negative integers before deriving; this is the one canonical rule.
    """
    return int(base_seed) + int(scenario_index)


def rng_provenance() -> dict[str, object]:
    """The pinned-RNG provenance recorded in artifact identity/provenance (R4/R5, AC2).

    Names the QMX-owned algorithm and its pinned version, the substream seed-derivation
    rule, and the flags asserting the generator never draws through a runtime stdlib
    Random. Package SemVer never enters.
    """
    return {
        "is_qmx_owned": IS_QMX_OWNED,
        "is_runtime_stdlib_random": IS_RUNTIME_STDLIB_RANDOM,
        "rng_algorithm": RNG_ALGORITHM,
        "rng_family": RNG_FAMILY,
        "rng_version": RNG_VERSION,
        "seed_derivation_rule": SEED_DERIVATION_RULE,
    }
