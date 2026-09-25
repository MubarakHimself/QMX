"""Reference usage — Library kinds are the existing fp1 list (Story 34.1).

Executable::

    python qmb/examples/library_kinds_usage.py

Shows the things Story 34.1 / FR-W17 / FR-W18 pin down:

1. Enumerated Library kinds are exactly the existing fp1 list: CT-33 bot,
   CT-34 confluence, strategy-family, CT-22 Book, CT-27 BMS, CT-28 binding,
   CT-12 split, CT-10 observation, CT-32 result, and CT-47 ExperimentSpec
   (coordinated lane only).
2. Logic source-manifests are cited from CT-33, not a sibling Library kind.
3. QMA staging, handles, Graph Templates, Skills, Routines, saved views,
   publications, and derived datasets are refused and must not be presented
   as registry records.
4. STRATS remains a KnowledgeSource corpus and writes no registry kinds.
5. Project / Workspace names are aliases, not kinds.
6. There is no COMP-LIB / qmx-library package; owner stays COMP-QMF-REGISTRY.
"""

from __future__ import annotations

import sys
from typing import TypeVar

from qmb.registryread import (
    KIND_OWNER,
    LIBRARY_KIND_NAMES,
    LOGIC_SOURCE_MANIFEST_CITES,
    STRATS_CORPUS,
    enumerate_library_kinds,
    register_library_kind,
)
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def main() -> None:
    roster = enumerate_library_kinds()
    assert roster.owner == KIND_OWNER == "COMP-QMF-REGISTRY"
    assert roster.qmx_library_package is False
    assert roster.occupancy == "query"
    names = tuple(item.kind for item in roster.kinds)
    assert names == LIBRARY_KIND_NAMES
    sys.stdout.write(str("library kinds: " + ", ".join(names)) + "\n")
    spec = next(item for item in roster.kinds if item.kind == "experiment-spec")
    assert spec.coordinated_lane_only is True
    sys.stdout.write(f"experiment-spec lane: coordinated only ({spec.contract})\n")

    bot = _unwrap(register_library_kind("bot-definition"), "bot library kind")
    assert bot.kind == "bot-definition"
    sys.stdout.write(f"admitted existing kind: {bot.kind} {bot.contract}\n")

    manifest = register_library_kind("logic-source-manifest")
    assert is_refusal(manifest) and manifest.category is RefusalCategory.POLICY_REJECTION
    assert manifest.context["cites"] == LOGIC_SOURCE_MANIFEST_CITES == "CT-33"
    sys.stdout.write("logic source-manifest cites CT-33, not a Library kind\n")

    staging = register_library_kind("staging")
    assert is_refusal(staging)
    assert staging.context["present_as_registry"] is False
    sys.stdout.write("staging refused; not presented as a registry record\n")

    strats = register_library_kind("STRATS")
    assert is_refusal(strats)
    assert strats.context["strats_corpus"] == STRATS_CORPUS
    assert strats.context["writes_registry_kinds"] is False
    sys.stdout.write("STRATS remains KnowledgeSource; writes no registry kinds\n")

    project = register_library_kind("project")
    assert is_refusal(project)
    assert project.context["display_alias"] is True
    sys.stdout.write("project/workspace remain display aliases\n")

    package = register_library_kind("qmx-library")
    assert is_refusal(package)
    assert package.context["qmx_library_package"] is False
    sys.stdout.write("no qmx-library package; owner COMP-QMF-REGISTRY\n")
    sys.stdout.write(f"qmb {qmb.__version__}\n")
    sys.stdout.write("library kinds ok\n")


if __name__ == "__main__":
    main()
