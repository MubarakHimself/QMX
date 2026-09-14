"""Story 32.1 — laptop-off continuation is a daemon property (FR-W35)."""

from __future__ import annotations

from qma.core.ontology import CONTINUATION_BOUND_KEYS, is_continuation_bound_key
from qma.core.ports.continuation_host import (
    CONTINUATION_LAPTOP_OFF_PROMISED_KEY,
    GAP_0062_ALWAYS_ON_HOST,
    GAP_0062_HOST_MACHINE,
    LAPTOP_OFF_OWNERS,
    ContinuationDoor,
    ContinuationEnvView,
    DurableOutboxPosture,
    JobLifetime,
    classify_job_lifetime,
    evaluate_laptop_off_configuration,
    is_laptop_off_continuation,
    is_remote_continuation_kind,
    is_workstation_colocated_kind,
    parse_laptop_off_promised,
)
from qma.core.refusals import LaptopOffContinuationRefused
from qma.core.vocabulary.enums import ExecutionEnvironmentKind
from qmf.core import is_ok, is_refusal


def _outbox(*, present: bool = True) -> DurableOutboxPosture:
    return DurableOutboxPosture(present=present, ordered=present, fsynced=present)


def _docker(*, reachable: bool = True) -> ContinuationEnvView:
    return ContinuationEnvView(
        env_id="docker",
        kind=ExecutionEnvironmentKind.DOCKER,
        colocated_with_daemon=True,
        reachable=reachable,
    )


def _remote(*, reachable: bool) -> ContinuationEnvView:
    return ContinuationEnvView(
        env_id="fixture-remote",
        kind=ExecutionEnvironmentKind.REMOTE_HOST,
        colocated_with_daemon=False,
        reachable=reachable,
    )


def test_laptop_off_key_is_not_a_story_46_7_bound() -> None:
    assert CONTINUATION_LAPTOP_OFF_PROMISED_KEY == "registry:continuation.laptop_off_promised"
    assert CONTINUATION_LAPTOP_OFF_PROMISED_KEY not in CONTINUATION_BOUND_KEYS
    assert is_continuation_bound_key(CONTINUATION_LAPTOP_OFF_PROMISED_KEY) is False
    assert is_continuation_bound_key("continuation.laptop_off_promised") is False


def test_gap_0062_host_is_operator_config_not_a_machine_name() -> None:
    assert GAP_0062_HOST_MACHINE == "operator_config"
    assert GAP_0062_ALWAYS_ON_HOST["gap"] == "GAP-0062"
    assert GAP_0062_ALWAYS_ON_HOST["status"] == "deferred"
    assert GAP_0062_ALWAYS_ON_HOST["host_machine"] == "operator_config"
    assert "vps" not in GAP_0062_ALWAYS_ON_HOST["effect"].casefold()
    assert LAPTOP_OFF_OWNERS == (
        "qma-daemon",
        "remote_execution_environment",
        "durable_outbox",
    )


def test_governed_orchestrator_spawn_is_process_per_run_not_laptop_off() -> None:
    classified = classify_job_lifetime(ContinuationDoor.GOVERNED_ORCHESTRATOR)
    assert is_ok(classified)
    assert classified.value is JobLifetime.QMB_PROCESS_PER_RUN
    assert is_laptop_off_continuation(classified.value) is False
    admitted = evaluate_laptop_off_configuration(
        promised=True,
        daemon_present=True,
        daemon_on_workstation=True,
        envs=(_remote(reachable=True),),
        outbox=_outbox(),
        lifetime=classified.value,
    )
    assert is_ok(admitted)
    assert admitted.value.laptop_off is False
    assert admitted.value.lifetime is JobLifetime.QMB_PROCESS_PER_RUN
    assert admitted.value.reason == "qmb_process_per_run"
    assert admitted.value.host_machine == "operator_config"


def test_ct47_coordinated_is_daemon_continuation_candidate() -> None:
    classified = classify_job_lifetime("ct47_coordinated")
    assert is_ok(classified)
    assert classified.value is JobLifetime.DAEMON_CONTINUATION
    assert is_laptop_off_continuation(classified.value) is True


def test_unpromised_local_config_is_not_a_silent_promise() -> None:
    admitted = evaluate_laptop_off_configuration(
        promised=False,
        daemon_present=True,
        daemon_on_workstation=True,
        envs=(_docker(),),
        outbox=_outbox(present=False),
    )
    assert is_ok(admitted)
    assert admitted.value.promised is False
    assert admitted.value.laptop_off is False
    assert admitted.value.reason == "not_promised"


def test_promised_laptop_only_docker_is_typed_refusal() -> None:
    refused = evaluate_laptop_off_configuration(
        promised=True,
        daemon_present=True,
        daemon_on_workstation=True,
        envs=(_docker(),),
        outbox=_outbox(),
    )
    assert is_refusal(refused)
    assert LaptopOffContinuationRefused.matches(refused)
    assert refused.context["reason"] == "laptop_only"
    assert refused.context["detail"] == "no_remote_env"
    assert refused.context["host_machine"] == "operator_config"
    assert refused.context["gap"] == "GAP-0062"


def test_fixture_remote_marked_unreachable_is_typed_refusal() -> None:
    refused = evaluate_laptop_off_configuration(
        promised=True,
        daemon_present=True,
        daemon_on_workstation=True,
        envs=(_docker(), _remote(reachable=False)),
        outbox=_outbox(),
    )
    assert is_refusal(refused)
    assert LaptopOffContinuationRefused.matches(refused)
    assert refused.context["reason"] == "laptop_only"
    assert refused.context["detail"] == "remote_unreachable"
    assert refused.context["unreachable_env_ids"] == ("fixture-remote",)
    assert refused.context["host_machine"] == "operator_config"


def test_promised_requires_durable_outbox() -> None:
    refused = evaluate_laptop_off_configuration(
        promised=True,
        daemon_present=True,
        daemon_on_workstation=True,
        envs=(_remote(reachable=True),),
        outbox=_outbox(present=False),
    )
    assert is_refusal(refused)
    assert refused.context["reason"] == "outbox_missing"


def test_promised_with_reachable_remote_and_outbox_admits() -> None:
    admitted = evaluate_laptop_off_configuration(
        promised=True,
        daemon_present=True,
        daemon_on_workstation=True,
        envs=(_docker(), _remote(reachable=True)),
        outbox=_outbox(),
    )
    assert is_ok(admitted)
    assert admitted.value.laptop_off is True
    assert admitted.value.daemon is True
    assert admitted.value.remote_env is True
    assert admitted.value.outbox is True
    assert admitted.value.owners == LAPTOP_OFF_OWNERS
    assert admitted.value.host_machine == GAP_0062_HOST_MACHINE
    payload = admitted.value.to_payload()
    assert "vps" not in str(payload).casefold()


def test_kind_placement_and_promise_parse() -> None:
    assert is_workstation_colocated_kind(ExecutionEnvironmentKind.DOCKER) is True
    assert is_remote_continuation_kind("remote_host") is True
    assert is_ok(parse_laptop_off_promised(True))
    assert is_refusal(parse_laptop_off_promised("yes"))
