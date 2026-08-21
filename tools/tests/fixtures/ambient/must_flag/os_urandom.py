"""MUST FLAG: ``os.urandom()`` reads OS entropy (nondeterministic)."""

import os


def nonce() -> bytes:
    return os.urandom(16)
