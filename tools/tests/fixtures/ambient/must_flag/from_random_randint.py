"""MUST FLAG: a from-imported global-RNG draw called by bare name."""

from random import randint


def roll():
    return randint(1, 6)
