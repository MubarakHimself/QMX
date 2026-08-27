"""Group G — Cross-cutting CT-04 refusal register (cross) -> R34.

Every refusal produced on an Epic-21 path is a RETURNED CT-04 typed value: a category
in the seven, machine-readable context present and non-null, retryability present, and
RETURNED across the public boundary rather than raised. Reaching each assertion at all
proves the refusal was not raised.
"""

from __future__ import annotations

from conftest import (
    RefusalCategory,
    Retryability,
    TypedRefusal,
    assert_ct04_refusal,
    bot_universe,
    categorical_param,
    fp,
    int_param,
    is_refusal,
    money_param,
    unwrap,
)

from qmb.optimize.objective import StudyObjective, coerce_study_criteria
from qmb.optimize.sampler import StudyStepper, admit_study
from qmb.optimize.space import coerce_study_space
from qmb.optimize.splits import admit_study_world, coerce_study_splits
from qmf.core.fingerprint import World, fingerprint


def test_t21_333_every_epic21_refusal_is_a_valid_returned_ct04_value() -> None:
    """Each Epic-21 refusal surface returns a valid CT-04 value of the right category.

    Counter-case that would FAIL: any surface raising instead of returning, or returning
    a value that is not a TypedRefusal with a category in the seven, a valid retryability,
    and a present non-null context.
    """
    # Build the one stepper whose second ask is refused.
    stepper = StudyStepper(
        space=unwrap(coerce_study_space([int_param("a", lo=0, hi=10, step=1, default=5)])),
        seed=1,
        direction="max",
        study_fp=unwrap(fingerprint({"s": 1})),
        batch_size=2,
    )
    outstanding = unwrap(stepper.ask(), "first ask")[0]
    port, _bot = bot_universe("mr")
    admitted = unwrap(admit_study(stepper.space, 1, port, bot="mr"), "admitted")

    cases: list[tuple[object, RefusalCategory, str]] = [
        (coerce_study_space([int_param("x", lo=20, hi=1, step=1, default=1)]), RefusalCategory.INVALID_INPUT, "min>max"),
        (coerce_study_space([categorical_param("m", [], "t")]), RefusalCategory.INVALID_INPUT, "empty options"),
        (coerce_study_space([money_param("s", lo=1.5)]), RefusalCategory.INVALID_INPUT, "money float"),
        (StudyObjective.try_create("net_profit", "sideways"), RefusalCategory.INVALID_INPUT, "bad direction"),
        (coerce_study_criteria({"objective": {"measure": "bogus", "direction": "max"}}), RefusalCategory.INVALID_INPUT, "off-roster metric"),
        (admit_study_world(World.SIMULATED), RefusalCategory.POLICY_REJECTION, "world=simulated"),
        (coerce_study_splits({"train": fp("t").value, "test": fp("u").value, "world": "simulated"}), RefusalCategory.POLICY_REJECTION, "simulated split"),
        (outstanding.ask(), RefusalCategory.UNSUPPORTED_CAPABILITY, "parallel ask"),
        (admitted.port.resolve("mr"), RefusalCategory.INVALID_INPUT, "post-admit alias"),
    ]

    seen_categories: set[RefusalCategory] = set()
    for result, expected, what in cases:
        refusal = assert_ct04_refusal(result, expected, what=what)
        # CT-04 completeness: retryability present & valid, context present & non-null.
        assert isinstance(refusal.retryability, Retryability)
        assert refusal.context is not None
        seen_categories.add(refusal.category)

    # the register exercises more than one category (invalid input, policy, unsupported).
    assert {
        RefusalCategory.INVALID_INPUT,
        RefusalCategory.POLICY_REJECTION,
        RefusalCategory.UNSUPPORTED_CAPABILITY,
    } <= seen_categories
