"""MUST NOT FLAG: constructing datetimes/dates from explicit values is deterministic."""

from datetime import date, datetime, timedelta, timezone

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def at(seconds):
    return EPOCH + timedelta(seconds=seconds)


def civil():
    return date(2020, 1, 1)


def parsed(text):
    return date.fromisoformat(text)


def from_epoch(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc)
