"""MUST FLAG: a direct system wall-clock read below the composition root."""

from datetime import datetime


def stamp():
    return datetime.now()
