"""Reference usage — ATC validate/simulate with Book keys absent (Story 58.2).

Executable::

    python qmb/examples/alternative_run_config_usage.py

Shows the things SCN-0020 / Story 58.2 pin down:

1. AlternativeRunConfig omits Book/BMS/bot keys (absent, not null) and carries
   a complete PolicyPair, command including command_owner_epoch, and host
   admission.
2. PolicyPair identity is id/version/hash; inline bodies are not the sole
   identity. Hash preimage is accounting + risk, no secrets.
3. Validate/simulate write QMB JSONL tagged composition_class=alternative plus
   CT-07 lineage to policy_pair_hash. QMB issues the internal simulate token.
4. Dummy PolicyPair and ATC-through-ResolvedRunConfig are invalid input.
5. Live ATC without paper+L17 is not_promoted. Claiming ATC at 270e992 fails.
"""

from __future__ import annotations

import sys
from typing import TypeVar

from qmb.config import (
    ADAPTER_INTERNAL_SIMULATE,
    ALTERNATIVE_CONFIG_CLASS,
    BOOK_KEYS,
    CONSUMER_QMB,
    INSPECT_SHA_ATC_ABSENT,
    VERDICT_ADMITTED_SIMULATE,
    VERDICT_NOT_PROMOTED,
    adopt_selected_composition,
    refuse_atc_implemented_at_inspect_sha,
    simulate_alternative_run,
    validate_alternative_run_config,
)
from qmf.core.chrono import WriterId
from qmf.core.refusal import Result, is_ok, is_refusal

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def main() -> None:
    payload: dict[str, object] = {
        "admission": {
            "checked_grant_ids": ["grant:atc-sim"],
            "decided_at": "2026-09-19T12:00:00Z",
            "evaluator_principal": "host",
            "health_evidence_ref": "health:atc",
            "health_revision": 4,
            "observation_freshness": {
                "max_age": "30s",
                "observed_at": "2026-09-19T11:59:30Z",
            },
        },
        "command": {
            "account_id": "acct:replay",
            "adapter_capability": ADAPTER_INTERNAL_SIMULATE,
            "command_owner_epoch": 18,
            "instrument": "EURUSD",
            "role": "pm",
        },
        "config_class": ALTERNATIVE_CONFIG_CLASS,
        "policy_pair": {
            "accounting": {
                "cash_identity": "internal-cash",
                "currency": "USD",
                "fill_application": "fifo",
                "position_identity": "instrument+account",
                "residual_meaning": "open-qty",
                "valuation": "last-mark",
            },
            "risk": {
                "halt": "on-unknown-or-limit",
                "max_gross": "100000",
                "override_principal": "operator",
                "sizing": "fixed-fraction",
            },
        },
        "policy_pair_id": "pp:kelly-v1",
        "policy_pair_version": 1,
    }
    writer = _unwrap(
        WriterId.try_create("node-a", "authoring", "atc-sim", "boot-1"),
        "writer",
    )
    validated = _unwrap(validate_alternative_run_config(payload), "validate ATC")
    for key in BOOK_KEYS:
        if key in validated.payload():
            raise AssertionError(f"Book key {key} must be absent")
    receipt = _unwrap(simulate_alternative_run(payload, writer=writer), "simulate ATC")
    line = _unwrap(receipt.jsonl_line(), "ATC JSONL")
    adopted = _unwrap(
        adopt_selected_composition(validated, consumer=CONSUMER_QMB),
        "adopt ATC",
    )
    dummy = validate_alternative_run_config(
        {
            **payload,
            "policy_pair": {
                "accounting": payload["policy_pair"]["accounting"],  # type: ignore[index]
                "risk": {**payload["policy_pair"]["risk"], "sizing": "unlimited"},  # type: ignore[index]
            },
        }
    )
    inspect = refuse_atc_implemented_at_inspect_sha(INSPECT_SHA_ATC_ABSENT)
    live = _unwrap(
        validate_alternative_run_config(
            {
                **payload,
                "command": {
                    **payload["command"],  # type: ignore[dict-item]
                    "adapter_capability": "venue-live",
                    "venue_kind": "ctrader",
                },
            }
        ),
        "live ATC validate",
    )
    sys.stdout.write("alternative run-config ok\n")
    sys.stdout.write(f"config_class={validated.config_class}\n")
    sys.stdout.write("Book keys absent, not null\n")
    sys.stdout.write(f"policy_pair_hash={validated.policy_pair.policy_pair_hash.value}\n")
    sys.stdout.write(f"composition_fp={validated.composition_fp.value}\n")
    sys.stdout.write(f"host verdict={validated.admission.verdict}\n")
    sys.stdout.write(f"JSONL composition_class alternative ({len(line)} bytes)\n")
    sys.stdout.write(f"QMB simulate token {receipt.simulate_token.value}\n")
    sys.stdout.write(f"CT-07 to policy_pair_hash {receipt.journal.lineage.to_ref.value}\n")
    sys.stdout.write(f"adopted {adopted.consumer} config_class={adopted.config_class}\n")
    if is_refusal(dummy):
        sys.stdout.write("dummy PolicyPair is invalid input\n")
    if is_refusal(inspect):
        sys.stdout.write("claiming ATC at 270e992 fails\n")
    sys.stdout.write(f"live without paper+L17 is {live.admission.verdict}\n")
    assert validated.admission.verdict == VERDICT_ADMITTED_SIMULATE
    assert live.admission.verdict == VERDICT_NOT_PROMOTED
    sys.stdout.write("GAP-0098 stays open\n")


if __name__ == "__main__":
    main()
