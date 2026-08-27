"""Reference usage — tier-2 door-parity contract (Story 16.5).

Executable::

    python qmb/examples/door_parity_usage.py

Shows the things Story 16.5 / B-1 / AR-58 pin down:

1. The CLI tree and the Python API door expose the same product capabilities
   over the same library functions.
2. A capability on one shipped door missing from the other is a parity
   failure.
3. Refusals render per transport: CLI nonzero exit plus stderr JSON; Python
   returns the refusal union verbatim.
4. The parity door-set is the shipped doors (CLI + Python API). MCP stays
   out until it ships.
"""

from __future__ import annotations

import json

from click.testing import CliRunner
from qmb.doors import (
    MCP_SHIPPED,
    SHIPPED_DOORS,
    api,
    capability_gaps,
    cli_capability_surface,
    flatten_capabilities,
)
from qmb.doors.cli import command_tree, invoke_config_compile, main, render_refusal
from qmf.core.refusal import TypedRefusal, is_refusal


def shipped_doors_share_the_catalog() -> None:
    # Both surfaces are DERIVED and reconciled (R-006; OR-08): the default call
    # walks the CLI tree/adapters and introspects the API door — no hand catalog.
    tree = command_tree()
    cli = {f"{group}.{name}" for group, names in tree.items() for name in names}
    gaps = capability_gaps()
    assert gaps == {"missing_api": ()}
    assert set(flatten_capabilities()) == cli
    assert SHIPPED_DOORS == ("cli", "api")
    assert MCP_SHIPPED is False
    print("CLI and Python API reconcile derived surfaces: " + ", ".join(flatten_capabilities()))
    print("shipped doors: " + ", ".join(SHIPPED_DOORS) + "; MCP not in the door-set")


def missing_capability_is_a_parity_failure() -> None:
    gaps = capability_gaps(cli_names={*cli_capability_surface(), "secret_only"})
    assert gaps["missing_api"] == ("secret_only",)
    print("a capability on one door missing from the other fails")


def refusals_render_per_transport() -> None:
    python_refusal = api.compile_run_config(
        1,
        book_fragment=1,
        bms_fragment=1,
        run_spec={"bot": "x"},
    )
    assert is_refusal(python_refusal)
    assert isinstance(python_refusal, TypedRefusal)
    sequenced = invoke_config_compile(
        port=1,
        book_fragment=1,
        bms_fragment=1,
        run_spec={"bot": "x"},
    )
    assert sequenced == python_refusal
    runner = CliRunner()
    clicked = runner.invoke(
        main,
        ["config", "compile"],
        obj={
            "port": 1,
            "book_fragment": 1,
            "bms_fragment": 1,
            "run_spec": {"bot": "x"},
        },
    )
    assert clicked.exit_code != 0
    assert clicked.stdout.strip() == ""
    payload = json.loads(clicked.stderr)
    assert payload == json.loads(render_refusal(python_refusal))
    print("CLI: nonzero exit + stderr JSON")
    print("Python: refusal union verbatim")


def catalog_and_config_show_match() -> None:
    identity = api.run_config_identity()
    runner = CliRunner()
    shown = runner.invoke(main, ["config", "show"])
    assert shown.exit_code == 0, shown.output
    assert shown.stdout.strip() == identity["class"]
    print("config show class: " + str(identity["class"]))


if __name__ == "__main__":
    shipped_doors_share_the_catalog()
    missing_capability_is_a_parity_failure()
    refusals_render_per_transport()
    catalog_and_config_show_match()
    print("qmb door parity ok")
