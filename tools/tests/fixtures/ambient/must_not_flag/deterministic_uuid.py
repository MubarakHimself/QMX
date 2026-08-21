"""MUST NOT FLAG: deterministic, namespace-based UUIDs (``uuid3``/``uuid5``) carry
no ambient read, and a bare ``random.SystemRandom()`` that is never drawn from draws
nothing — only a draw off it would read OS entropy.
"""

import random
import uuid


def namespaced(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_DNS, name)


def namespaced_md5(name: str) -> uuid.UUID:
    return uuid.uuid3(uuid.NAMESPACE_DNS, name)


def unused_generator() -> random.SystemRandom:
    # Construction alone reads no entropy; only a draw would.
    return random.SystemRandom()
