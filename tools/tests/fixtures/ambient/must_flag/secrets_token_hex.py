"""MUST FLAG: ``secrets.token_hex()`` draws from the OS-entropy CSPRNG."""

import secrets


def api_key() -> str:
    return secrets.token_hex()
