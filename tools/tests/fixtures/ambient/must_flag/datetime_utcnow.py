"""MUST FLAG: datetime.utcnow() reads the system wall clock."""

from datetime import datetime


def stamp():
    return datetime.utcnow()
