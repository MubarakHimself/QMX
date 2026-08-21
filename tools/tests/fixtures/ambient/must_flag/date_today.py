"""MUST FLAG: date.today() reads the system wall clock."""

from datetime import date


def business_day():
    return date.today()
