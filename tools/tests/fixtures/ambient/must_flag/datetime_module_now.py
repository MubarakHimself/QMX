"""MUST FLAG: datetime.datetime.now() reached through a whole-module import."""

import datetime


def stamp():
    return datetime.datetime.now(datetime.timezone.utc)
