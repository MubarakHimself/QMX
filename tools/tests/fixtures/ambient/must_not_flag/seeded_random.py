"""MUST NOT FLAG: a seeded RNG instance is deterministic; seeding is not a draw."""

import random


def deterministic_stream(seed):
    rng = random.Random(seed)
    return [rng.random() for _ in range(3)]


def one_shot(seed):
    return random.Random(seed).randint(0, 9)


def reseed():
    random.seed(1234)
