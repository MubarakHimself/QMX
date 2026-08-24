"""Thin ``qmb`` CLI door (B-1).

Adaptation only: parsing, transport, and refusal rendering. The door holds no
cache and computes no run-id of its own (DEC-0159, DEC-0160). Click is pinned
by ``registry:qmb_cli_pin``; the pin value lives in the registry and the
distribution manifest, never restated here.
"""

from __future__ import annotations

import click

from qmb._display import __version__
from qmb.doors import CLI_PROG


@click.group(name=CLI_PROG)
@click.version_option(version=__version__, prog_name=CLI_PROG)
def main() -> None:
    """QMX experimentation/backtesting library and CLI (COMP-QMB)."""


@main.command("version")
def show_version() -> None:
    """Print display-only SemVer provenance. Never identity."""
    click.echo(__version__)
