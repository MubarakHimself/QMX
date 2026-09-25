"""L27 reference usage: three door-derived lanes and two honest labels."""

from __future__ import annotations

import sys

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
    sys.stdout.write("workbench lanes ok\n")
    sys.stdout.write("ungoverned writes nothing\n")
    sys.stdout.write("qmb ledger workbench_lane=governed\n")
    sys.stdout.write("experiment ledger workbench_lane=coordinated\n")
    sys.stdout.write("caller-declared lane refused\n")
    sys.stdout.write("L33 is not this spawn\n")


if __name__ == "__main__":
    main()
