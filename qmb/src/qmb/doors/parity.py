"""Door-parity DERIVATION for the shipped CLI and Python API doors (B-1, AR-58).

Every product capability lives once in the library. The CLI tree and the
Python API door must name the same capabilities and call the same library
entry points — and both surfaces are DERIVED programmatically and reconciled,
never asserted from a hand-maintained capability map (R-006; OR-08
2026-08-27). The CLI side derives from the command tree plus the AST of the
``invoke_*`` adapters in ``doors/cli/tree.py``; the API side derives by
``is``-identity introspection against ``qmb``. The retired hand catalog is
exactly what masked the ``data.generate`` API-door gap (QMX-F016/QMX-F017):
its row omitted the library-function element every sibling row carried, so
the reconciliation had nothing to compare and reported clean. MCP is
scaffolded and stays out of the door-set until it ships.
"""

from __future__ import annotations

import ast
import inspect
import textwrap
from collections.abc import Iterable
from typing import Final

__all__ = [
    "CLI_ADAPTATION_COMMANDS",
    "MCP_IN_DOOR_SET",
    "SHIPPED_DOORS",
    "api_capability_surface",
    "capability_gaps",
    "cli_capability_surface",
    "cli_library_adaptations",
    "door_parity_identity",
    "flatten_capabilities",
    "required_library_names",
]

SHIPPED_DOORS: Final[tuple[str, ...]] = ("cli", "api")
CLI_ADAPTATION_COMMANDS: Final[tuple[str, ...]] = ("version",)
MCP_IN_DOOR_SET: Final[bool] = False


def flatten_capabilities() -> tuple[str, ...]:
    """Product capabilities as CLI ``group.command`` names, DERIVED from the tree.

    The command tree is the single declaration of the product surface (its
    ``data`` group already derives from the library's ``DATA_COMMANDS``), so a
    capability added to the tree appears here with no second list to update.
    """
    from qmb.doors.cli.tree import command_tree  # noqa: PLC0415 — import-cycle with the door

    return tuple(
        f"{group}.{command}" for group, commands in command_tree().items() for command in commands
    )


def _cli_import_map() -> dict[str, str]:
    """Local name → real library name for every ``qmb``-package import in the tree.

    Aliases resolve to their real names (``from qmb.data import generate as
    run_generate`` maps ``run_generate`` → ``generate``); private adaptation
    vocabulary (imports from ``qmb._*`` modules) is excluded.
    """
    from qmb.doors.cli import tree as tree_mod  # noqa: PLC0415 — import-cycle with the door

    source = textwrap.dedent(inspect.getsource(tree_mod))
    out: dict[str, str] = {}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("qmb"):
            if node.module.split(".")[-1].startswith("_"):
                continue
            for alias in node.names:
                out[alias.asname or alias.name] = alias.name
    return out


def cli_library_adaptations() -> dict[str, str]:
    """Library names the CLI door adapts, DERIVED from the adapters' AST.

    Walks every ``invoke_*`` function in ``doors/cli/tree.py`` and collects each
    referenced name the module imported from a ``qmb`` package, resolved to its
    real library name — ``{real_library_name: local_name}``. No catalog is
    consulted: this IS the CLI door's capability surface projected onto the
    library (R-006).
    """
    from qmb.doors.cli import tree as tree_mod  # noqa: PLC0415 — import-cycle with the door

    import_map = _cli_import_map()
    source = textwrap.dedent(inspect.getsource(tree_mod))
    out: dict[str, str] = {}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("invoke_"):
            for ref in ast.walk(node):
                if isinstance(ref, ast.Name) and ref.id in import_map:
                    out[import_map[ref.id]] = ref.id
    return out


def cli_capability_surface() -> frozenset[str]:
    """The CLI door's derived library-capability surface (B-1)."""
    return frozenset(cli_library_adaptations())


def api_capability_surface() -> frozenset[str]:
    """The API door's derived surface: names re-exported ``is``-identical to ``qmb``.

    A name counts only when the API door's attribute IS the library's attribute
    — the pure-re-export contract — so a stale or shadowed re-export never
    reads as parity.
    """
    import qmb  # noqa: PLC0415 — import-cycle with the package root
    from qmb.doors import api  # noqa: PLC0415 — import-cycle with the door

    out: set[str] = set()
    for name in api.__all__:
        if getattr(api, name, None) is getattr(qmb, name, object()):
            out.add(name)
    return frozenset(out)


def required_library_names() -> frozenset[str]:
    """Library attributes every shipped door must expose — the DERIVED CLI surface."""
    return cli_capability_surface()


def capability_gaps(
    *,
    cli_names: Iterable[str] | None = None,
    api_names: Iterable[str] | None = None,
) -> dict[str, tuple[str, ...]]:
    """Reconcile the two DERIVED door surfaces (B-1).

    ``missing_api`` is every library name the CLI door adapts that the Python
    API door does not re-export identity-equal — any non-empty tuple is a
    parity failure. Both sides DEFAULT to their derived surfaces; the
    parameters exist only so a counter-case test can inject a synthetic gap.
    """
    cli_set = frozenset(cli_names) if cli_names is not None else cli_capability_surface()
    api_set = frozenset(api_names) if api_names is not None else api_capability_surface()
    return {"missing_api": tuple(sorted(cli_set - api_set))}


def door_parity_identity() -> dict[str, object]:
    """Identity-bearing door-parity fields. Package SemVer is omitted."""
    return {
        "adaptation": ("parsing", "transport", "refusal-rendering", "autocomplete"),
        "capabilities": flatten_capabilities(),
        "derived_reconciliation": True,
        "mcp_in_door_set": MCP_IN_DOOR_SET,
        "shipped_doors": SHIPPED_DOORS,
    }
