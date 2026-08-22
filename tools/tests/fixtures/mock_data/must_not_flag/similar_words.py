"""MUST NOT FLAG: identifiers that merely open with a banned word. The match is on
whole words, so these are ordinary names, not test doubles."""

from __future__ import annotations


class Faker:
    """A name, not the word ``fake``."""


def stubborn_retry(attempts: int) -> int:
    return attempts


mockingbird = "song"
