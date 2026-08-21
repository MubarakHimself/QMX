"""MUST FLAG: an aliased whole-module import does not hide the clock read."""

import datetime as dt


def stamp():
    return dt.datetime.now()
