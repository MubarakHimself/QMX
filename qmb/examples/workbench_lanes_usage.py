"""L27 reference usage: three door-derived lanes and two honest labels."""

from __future__ import annotations

from qmf.core import is_ok, is_refusal

import qmb


def main() -> None:
    ungoverned = qmb.ungoverned_run_identity()
    assert ungoverned["writes_qmb_ledger"] is False
    assert ungoverned["is_library_object"] is False
    governed = qmb.door_derived_labels(orchestrator=True)
    assert is_ok(governed)
    assert governed.value.qmb_ledger_workbench_lane == "governed"
    assert governed.value.experiment_ledger_workbench_lane is None
    coordinated = qmb.door_derived_labels(ct47=True)
    assert is_ok(coordinated)
    assert coordinated.value.qmb_ledger_workbench_lane == "governed"
    assert coordinated.value.experiment_ledger_workbench_lane == "coordinated"
    flagged = qmb.door_derived_labels(orchestrator=True, workbench_lane="governed")
    assert is_refusal(flagged)
    graduation = qmb.graduate_ungoverned_via_spawn()
    assert is_refusal(graduation)
    print("workbench lanes ok")
    print("ungoverned writes nothing")
    print("qmb ledger workbench_lane=governed")
    print("experiment ledger workbench_lane=coordinated")
    print("caller-declared lane refused")
    print("L33 is not this spawn")


if __name__ == "__main__":
    main()
