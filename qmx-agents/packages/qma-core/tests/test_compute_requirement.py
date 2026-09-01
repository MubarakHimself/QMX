"""Story 45.3 — ComputeRequirement declaration and matching (FR-Q50)."""

from __future__ import annotations

import pytest
from qma.core.ports.compute import (
    COMPUTE_REQUIREMENT_FIELDS,
    ComputeRequirement,
    GpuRequirement,
    environment_isolation,
    match_compute_requirement,
    parse_compute_requirement,
)
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.refusals import NoEnvironment
from qma.core.vocabulary.enums import (
    ExecutionEnvironmentKind,
    IsolationMode,
)
from qma.core.vocabulary.registry import VocabularyError
from qmf.core import is_ok, is_refusal
from qmf.core.chrono import Duration


def _requirement(**overrides: object) -> ComputeRequirement:
    values: dict[str, object] = {
        "kind": "docker",
        "cpu": 1,
        "memory": 512,
        "disk": 1024,
        "capabilities": ("cpu",),
        "timeout": 1_000_000_000,
        "max_memory": 512,
        "isolation": "required",
    }
    values.update(overrides)
    return ComputeRequirement.try_parse(**values)  # type: ignore[arg-type]


def _docker(**overrides: object) -> ExecutionEnvironmentDeclaration:
    values: dict[str, object] = {
        "kind": "docker",
        "network": "none",
        "reachable_hosts": (),
        "provider_ref": "local-docker",
        "image": "qma-worker:isolated",
        "capabilities": ("cpu",),
    }
    values.update(overrides)
    return ExecutionEnvironmentDeclaration.try_parse(**values)  # type: ignore[arg-type]


def test_requirement_carries_ct46_fields_gpu_optional() -> None:
    requirement = _requirement()
    surface = requirement.surface()
    assert tuple(surface) == COMPUTE_REQUIREMENT_FIELDS
    assert requirement.kind is ExecutionEnvironmentKind.DOCKER
    assert requirement.cpu == 1
    assert requirement.memory == 512
    assert requirement.disk == 1024
    assert requirement.gpu is None
    assert requirement.capabilities == ("cpu",)
    assert requirement.timeout == Duration(value_ns=1_000_000_000)
    assert requirement.max_memory == 512
    assert requirement.isolation is IsolationMode.REQUIRED
    with_gpu = _requirement(gpu={"count": 1, "kind": "cuda"})
    assert with_gpu.gpu == GpuRequirement(count=1, kind="cuda")
    payload = with_gpu.to_payload()
    assert "host" not in payload
    assert "vendor" not in payload
    assert "machine" not in payload


def test_host_or_vendor_on_requirement_is_refused() -> None:
    with pytest.raises(VocabularyError, match="host, machine, or vendor"):
        _requirement(host="agent-box")
    with pytest.raises(VocabularyError, match="host, machine, or vendor"):
        _requirement(vendor="modal")
    with pytest.raises(VocabularyError, match="host, machine, or vendor"):
        _requirement(machine="e2b-box")
    refused = parse_compute_requirement(
        kind="docker",
        cpu=1,
        memory=1,
        disk=1,
        timeout=1,
        max_memory=1,
        isolation="required",
        agent_vendor="daytona",
    )
    assert is_refusal(refused)


def test_invented_isolation_and_kind_refused() -> None:
    with pytest.raises(VocabularyError):
        _requirement(isolation="bare-metal")
    with pytest.raises(VocabularyError):
        _requirement(kind="lambda")
    with pytest.raises(VocabularyError):
        _requirement(cpu=0)
    with pytest.raises(VocabularyError):
        _requirement(memory=8, max_memory=4)


def test_match_against_declared_capabilities() -> None:
    docker = _docker(capabilities=("cpu", "memory"), cpu=2, memory=1024, disk=4096)
    matched = match_compute_requirement(_requirement(), docker)
    assert is_ok(matched)
    assert matched.value.kind is ExecutionEnvironmentKind.DOCKER
    unmet = match_compute_requirement(
        _requirement(capabilities=("cpu", "gpu"), gpu={"count": 1}),
        docker,
    )
    assert is_refusal(unmet)
    assert NoEnvironment.matches(unmet)
    assert unmet.context["kind"] == "docker"
    assert unmet.context["reason"] == "unmet"
    unmet_fields = unmet.context["unmet"]
    assert isinstance(unmet_fields, tuple)
    assert "capabilities" in unmet_fields
    assert "gpu" in unmet_fields


def test_named_kind_is_not_broadened() -> None:
    docker = _docker()
    desktop_req = _requirement(kind="desktop", isolation="shared", capabilities=("display",))
    refused = match_compute_requirement(desktop_req, docker)
    assert is_refusal(refused)
    assert NoEnvironment.matches(refused)
    assert refused.context["kind"] == "desktop"


def test_isolation_and_resource_ceilings() -> None:
    docker = _docker(cpu=1, memory=256)
    isolation = environment_isolation(docker)
    assert isolation is IsolationMode.REQUIRED
    short = match_compute_requirement(_requirement(cpu=4, max_memory=512, memory=512), docker)
    assert is_refusal(short)
    short_fields = short.context["unmet"]
    assert isinstance(short_fields, tuple)
    assert "cpu" in short_fields
    desktop = ExecutionEnvironmentDeclaration.try_parse(
        kind="desktop",
        network="none",
        reachable_hosts=(),
        provider_ref="research-box",
        host="research-box",
        lifecycle="persistent",
        capabilities=("display",),
    )
    assert environment_isolation(desktop) is IsolationMode.SHARED
    shared_ok = match_compute_requirement(
        _requirement(kind="desktop", isolation="shared", capabilities=("display",)),
        desktop,
    )
    assert is_ok(shared_ok)
    required_on_desktop = match_compute_requirement(
        _requirement(kind="desktop", isolation="required", capabilities=("display",)),
        desktop,
    )
    assert is_refusal(required_on_desktop)
    isolation_fields = required_on_desktop.context["unmet"]
    assert isinstance(isolation_fields, tuple)
    assert "isolation" in isolation_fields
