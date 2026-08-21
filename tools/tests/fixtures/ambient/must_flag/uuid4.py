"""MUST FLAG: ``uuid.uuid4()`` draws from OS entropy (nondeterministic)."""

import uuid


def new_id() -> uuid.UUID:
    return uuid.uuid4()
