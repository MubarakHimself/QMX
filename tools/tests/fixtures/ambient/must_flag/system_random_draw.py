"""MUST FLAG: a draw off ``random.SystemRandom()`` reads OS entropy — the opposite
of a seeded instance, so it is not the sanctioned deterministic path.
"""

import random


def token() -> float:
    return random.SystemRandom().random()
