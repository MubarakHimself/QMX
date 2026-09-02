"""Story 27.1 — two-layer SecretStore, rotation contract, holders, drill."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar

from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, Retryability, is_ok, is_refusal
from qmf.core.secret import SecretRef, SecretValue
from qmn.host.boot_ceremony import (
    FULL_PREFLIGHT_CHECKS,
    CompositionFingerprintInputs,
    InMemoryBootAttemptSink,
    PreflightFacts,
    run_boot_ceremony,
)
from qmn.secrets import (
    BACKUP_UNIT,
    COMPROMISE_DRILL_STEPS,
    CONNECTION_MANAGER,
    DEMO_CREDENTIAL_CLASS,
    KEK_SIZE,
    NAMED_HOLDERS,
    NEVER_VPS_MINTED_SLOTS,
    NOTIFICATION_PATH,
    OBSERVABILITY_STACK,
    SECRETS_SURFACE,
    VPS_MINTED_SLOTS,
    extra_holders,
    refuse_fifth_holder,
    run_compromise_drill,
    scan_holder_declaration,
    scan_payload_for_secret_values,
    scan_store_presence,
    try_create_secret_store,
)
from qmn.secrets._refuse import ROTATION_AFTER_CONDITION, unavailable
from qmn.secrets.rotation import RotationGate
from qmn.secrets.store import (
    AEAD_NONCE_SIZE,
    FilesystemBlobStore,
    NodeSecretStore,
    os_aead_nonce,
)

T = TypeVar("T")

_VPS = "vps-a"
_KEK = bytes(range(KEK_SIZE))


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _ref(token: str) -> SecretRef:
    return _ok(SecretRef.try_create(token))


def _value(ref: SecretRef, material: str) -> SecretValue:
    return _ok(SecretValue.try_create(ref, material))


def _plain(label: str) -> str:
    return f"fixture-{label}-zzzzzzzz"


def _fp(label: str) -> Fingerprint:
    return _ok(fingerprint({"class": "cite", "label": label}))


def _inputs(label: str = "boot-secrets") -> CompositionFingerprintInputs:
    return CompositionFingerprintInputs(
        config_fp=_fp(f"config-{label}"),
        distribution_identities={
            "qmf": "lockstep",
            "qmb": "0.1.0",
            "qml": "0.1.0",
            "qmn": "0.1.0",
        },
        extension_identities={"qmf-calendar-forex": "1.0.0"},
        proto_release_tag="proto-1",
        tzdata_version="2026a",
        adapter_capability_fps=(_fp("cap-ctrader"),),
        registry_as_of_fp=_fp("as-of-1"),
        calendar_code_identities={
            "market_hours_calendar": "mh-code-1",
            "day_boundary_calendar": "db-code-1",
            "news_calendar": "news-code-1",
        },
        os_cpu_class="linux-x86_64",
    )


def _streams() -> tuple[tuple[str, str], ...]:
    return (
        ("command", "venue-a:acct-1"),
        ("adapter", "venue-a:acct-1:feed"),
        ("risk", "binding-1"),
    )


class _Blobs:
    def __init__(self) -> None:
        self.data: dict[str, bytes] = {}
        self.fail_write = False

    def write_atomic(self, name: str, blob: bytes) -> Result[None]:
        if self.fail_write:
            return unavailable(
                "rotated",
                "write failed",
                failure_id="secrets.rotation.store_failed",
                retryability=Retryability.AFTER_CONDITION,
                after_condition_descriptor=ROTATION_AFTER_CONDITION,
            )
        self.data[name] = blob
        return Ok(None)

    def read(self, name: str) -> Result[bytes]:
        if name not in self.data:
            return unavailable("rotated", "missing", failure_id="secrets.store.missing")
        return Ok(self.data[name])

    def exists(self, name: str) -> bool:
        return name in self.data


class _Nonces:
    def __init__(self) -> None:
        self.n = 0

    def __call__(self, size: int) -> bytes:
        self.n += 1
        return self.n.to_bytes(size, "big")


def _make_store(
    *,
    holder: str = CONNECTION_MANAGER,
    slot: str = "venue-refresh-token",
    ref: SecretRef | None = None,
    bootstrap: Mapping[str, bytes] | None = None,
    blobs: _Blobs | None = None,
    machine: str = _VPS,
    roster: str = _VPS,
    gate: RotationGate | None = None,
) -> tuple[Result[NodeSecretStore], SecretRef, _Blobs]:
    handle = ref if ref is not None else _ref("cred-ref-vrefsh")
    backend = blobs if blobs is not None else _Blobs()
    created = try_create_secret_store(
        machine=machine,
        roster_vps_machine=roster,
        holder=holder,
        kek=_KEK,
        catalog={handle: slot},
        nonce_source=_Nonces(),
        rotated=backend,
        bootstrap=bootstrap or {},
        gate=gate,
    )
    return created, handle, backend


def test_secrets_surface_and_four_holders() -> None:
    assert SECRETS_SURFACE == "qmn.secrets"
    assert (
        frozenset(
            {
                CONNECTION_MANAGER,
                BACKUP_UNIT,
                NOTIFICATION_PATH,
                OBSERVABILITY_STACK,
            }
        )
        == NAMED_HOLDERS
    )
    assert extra_holders(NAMED_HOLDERS) == ()
    assert frozenset({"kek"}) == VPS_MINTED_SLOTS
    assert "backup-payload-key" in NEVER_VPS_MINTED_SLOTS
    refused = refuse_fifth_holder(("laptop_wallet",))
    assert refused.context["failure_id"] == "secrets.holder.fifth"
    scanned = scan_holder_declaration((*NAMED_HOLDERS, "laptop_wallet"))
    assert is_refusal(scanned)
    assert scanned.context["failure_id"] == "secrets.holder.fifth"


def test_off_host_venue_session_holder_refused() -> None:
    result, _, _ = _make_store(machine="workstation", roster=_VPS)
    assert is_refusal(result)
    assert result.context["failure_id"] == "secrets.store.off_host"


def test_unknown_holder_refused() -> None:
    result, _, _ = _make_store(holder="laptop_wallet")
    assert is_refusal(result)
    assert result.context["failure_id"] == "secrets.holder.unknown"


def test_holder_cannot_resolve_foreign_slot() -> None:
    result, _, _ = _make_store(holder=BACKUP_UNIT, slot="venue-refresh-token")
    assert is_refusal(result)
    assert result.context["failure_id"] == "secrets.holder.scope"


def test_read_bootstrap_and_is_set_metadata_only() -> None:
    ref = _ref("cred-ref-vrefsh")
    material = _plain("refresh")
    result, handle, _blobs = _make_store(
        ref=ref, bootstrap={"venue-refresh-token": material.encode("utf-8")}
    )
    store = _ok(result)
    assert handle == ref
    assert store.is_set(ref) is True
    presence = scan_store_presence(store)
    assert presence[ref.value] is True
    assert material not in repr(store)
    assert material not in str(dict(presence))
    value = _ok(store.read(ref))
    assert value.ref == ref
    assert value.reveal() == material
    assert material not in repr(value)
    leak = scan_payload_for_secret_values(
        {"secret_ref": ref.value, "is_set": True},
        (material,),
        surface="health",
    )
    assert is_ok(leak)


def test_value_on_health_or_refusal_fails_scanner() -> None:
    material = _plain("leaked")
    leaked = scan_payload_for_secret_values(
        {"health": {"token": material}},
        (material,),
        surface="health",
    )
    assert is_refusal(leaked)
    assert leaked.context["failure_id"] == "secrets.surface.value_leak"


def test_store_before_discard_keeps_old_on_failed_write() -> None:
    ref = _ref("cred-ref-vrefsh")
    old = _plain("oldrot")
    new = _plain("newrot")
    blobs = _Blobs()
    store = _ok(
        _make_store(
            ref=ref,
            bootstrap={"venue-refresh-token": old.encode("utf-8")},
            blobs=blobs,
        )[0]
    )
    _ok(store.atomic_replace(ref, _value(ref, old)))
    blobs.fail_write = True
    failed = store.atomic_replace(ref, _value(ref, new))
    assert is_refusal(failed)
    assert failed.context["failure_id"] == "secrets.rotation.store_failed"
    assert failed.retryability is Retryability.AFTER_CONDITION
    blobs.fail_write = False
    still = _ok(store.read(ref))
    assert still.reveal() == old


def test_one_refresher_per_reference() -> None:
    gate = RotationGate()
    ref = _ref("cred-ref-vrefsh")
    store = _ok(
        _make_store(
            ref=ref,
            bootstrap={"venue-refresh-token": _plain("oldrot").encode("utf-8")},
            gate=gate,
        )[0]
    )
    _ok(gate.acquire(ref))
    raced = store.atomic_replace(ref, _value(ref, _plain("newrot")))
    assert is_refusal(raced)
    assert raced.context["failure_id"] == "secrets.rotation.in_flight"
    gate.release(ref)
    _ok(store.atomic_replace(ref, _value(ref, _plain("newrot"))))


def test_rotated_layer_overrides_bootstrap() -> None:
    ref = _ref("cred-ref-vrefsh")
    store = _ok(
        _make_store(
            ref=ref,
            bootstrap={"venue-refresh-token": _plain("boot").encode("utf-8")},
        )[0]
    )
    rotated = _plain("rotated")
    _ok(store.atomic_replace(ref, _value(ref, rotated)))
    assert _ok(store.read(ref)).reveal() == rotated


def test_missing_credential_is_unavailable_with_ref_only() -> None:
    ref = _ref("cred-ref-vrefsh")
    store = _ok(_make_store(ref=ref, bootstrap={})[0])
    missing = store.read(ref)
    assert is_refusal(missing)
    assert missing.context["failure_id"] == "secrets.store.missing"
    assert missing.context["secret_ref"] == ref.value
    assert "fixture-" not in str(dict(missing.context))


def test_compromise_drill_demo_only() -> None:
    ref = _ref("cred-ref-vrefsh")
    store = _ok(
        _make_store(
            ref=ref,
            bootstrap={"venue-refresh-token": _plain("oldrot").encode("utf-8")},
        )[0]
    )
    live = run_compromise_drill(
        store,
        secret_ref=ref,
        replacement=_value(ref, _plain("newrot")),
        credential_class="live",
    )
    assert is_refusal(live)
    assert live.context["failure_id"] == "secrets.drill.not_demo"
    report = _ok(
        run_compromise_drill(
            store,
            secret_ref=ref,
            replacement=_value(ref, _plain("newrot")),
            credential_class=DEMO_CREDENTIAL_CLASS,
        )
    )
    assert report.steps == COMPROMISE_DRILL_STEPS
    assert report.store_replaced is True
    assert report.secret_ref == ref.value
    assert _plain("newrot") not in str(report.as_mapping())
    assert _ok(store.read(ref)).reveal() == _plain("newrot")


def test_filesystem_rotated_roundtrip(tmp_path: Path) -> None:
    ref = _ref("cred-ref-vrefsh")
    store = _ok(
        try_create_secret_store(
            machine=_VPS,
            roster_vps_machine=_VPS,
            holder=CONNECTION_MANAGER,
            kek=_KEK,
            catalog={ref: "venue-refresh-token"},
            nonce_source=_Nonces(),
            rotated=FilesystemBlobStore(tmp_path / "rotated"),
            bootstrap={"venue-refresh-token": _plain("boot").encode("utf-8")},
        )
    )
    rotated = _plain("diskrot")
    _ok(store.atomic_replace(ref, _value(ref, rotated)))
    assert _ok(store.read(ref)).reveal() == rotated
    assert store.is_set(ref) is True


def test_os_aead_nonce_length() -> None:
    assert len(os_aead_nonce()) == AEAD_NONCE_SIZE


def test_preflight_refuses_fifth_holder() -> None:
    assert "credential_is_set" in FULL_PREFLIGHT_CHECKS
    sink = InMemoryBootAttemptSink()
    outcome = _ok(
        run_boot_ceremony(
            boot_epoch_id="boot-secrets",
            machine=_VPS,
            composition_inputs=_inputs(),
            writer_streams=_streams(),
            boot_attempt_sink=sink,
            preflight=PreflightFacts(
                required_credential_refs=("cred-ref-vrefsh",),
                credential_is_set={"cred-ref-vrefsh": True},
                secret_holders=(CONNECTION_MANAGER, "laptop_wallet"),
            ),
        )
    )
    assert outcome.stand_down_alive is True
    assert outcome.failure_id == "secrets.holder.fifth"
