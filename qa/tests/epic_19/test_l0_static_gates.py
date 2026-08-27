"""L0 static / structural gates for Epic 19 (S1, S2, S3).

These read the results/ source as READ-ONLY evidence and assert structural
invariants. Each gate names the concrete counter-case it would catch and proves
the scanner CAN fail against a planted violation in the TEST's own fake string.
"""

from __future__ import annotations

import re

import pytest

from conftest import results_src_dir

from qmf.core.refusal import RefusalCategory, is_ok, is_refusal
from qmb.results.measures import MEASURE_IDENTITIES, emit_measure

RESULT_MODULES = ("ct32.py", "measures.py", "accounting.py", "charts.py", "render.py", "interpret.py")

# A local recompute of identity would INVOKE one of these; qmf-core's fingerprint
# is the only sanctioned path (R4, AR-14). Match hashing *calls* / imports, not the
# descriptive substring "fp1:sha256:<hex>" that appears in reason strings.
_LOCAL_HASH = re.compile(r"\bhashlib\b|\.hexdigest\(|\bsha256\(|\bsha1\(|\bblake2[bs]?\(|\bmd5\(")

# The composite tokens DEC-0162 / R-RPT-10 forbid from expressing a result.
FORBIDDEN_COMPOSITE = ("score", "grade", "tier", "weighted", "rating", "composite")

# Structural isolation: results/ spins up no concurrency of its own and holds no
# module-global mutable state (publish-only, per-run isolated — R28, R29).
_CONCURRENCY = re.compile(r"\bthreading\b|\bmultiprocessing\b|Thread\(|Process\(")


def _read(name: str) -> str:
    return (results_src_dir() / name).read_text(encoding="utf-8")


# --- T19-S1: no local identity recompute [R4] --------------------------------


def test_s1_no_local_hashing_only_qmf_core_fingerprint() -> None:
    # Falsifiability: the scanner must flag a planted local hash.
    assert _LOCAL_HASH.search("digest = hashlib.sha256(payload).hexdigest()") is not None

    offenders = {name: _LOCAL_HASH.findall(_read(name)) for name in RESULT_MODULES}
    assert all(hits == [] for hits in offenders.values()), offenders

    # The one identity path is a call into qmf-core's canonical fingerprint.
    ct32 = _read("ct32.py")
    assert "from qmf.core.fingerprint import" in ct32
    assert "fingerprint" in ct32


# --- T19-S2: no composite-score surface [R13] --------------------------------


def test_s2_measure_roster_has_no_composite_token() -> None:
    for identity in MEASURE_IDENTITIES:
        low = identity.casefold()
        assert not any(tok in low for tok in FORBIDDEN_COMPOSITE), identity


def test_s2_emit_measure_refuses_the_enforced_composite_tokens() -> None:
    from conftest import money

    good = emit_measure("net_profit", money(10), unit_kind="money(currency)")
    assert is_ok(good)  # the accept arm is reachable

    # these composite identities ARE rejected by the guard today
    for token in ("composite_score", "tier_band", "weighted_rating", "perf_score",
                  "overall_rating", "quality_tier"):
        refused = emit_measure(token, money(10), unit_kind="money(currency)")
        assert is_refusal(refused), token
        assert refused.category is RefusalCategory.POLICY_REJECTION, token
        assert refused.context["field"] == "measure_identity"


def test_s2_emit_measure_refuses_every_composite_the_ac_names() -> None:
    # AC 19.2 / R-RPT-10 / DEC-0162 forbid "no single composite score, GRADE, tier
    # band, or WEIGHTED rating." A grade-named composite and an underscore-spelled
    # weighted composite must both be a policy rejection expressing a result.
    from conftest import money

    for token in ("overall_grade", "letter_grade", "weighted_aggregate", "weighted_composite"):
        refused = emit_measure(token, money(10), unit_kind="money(currency)")
        assert is_refusal(refused), f"{token} was accepted as a measure identity"
        assert refused.category is RefusalCategory.POLICY_REJECTION, token


# --- T19-S3: publish-only + isolation, structural [R29, R28] ------------------


def test_s3_no_concurrency_or_mutable_global_in_results() -> None:
    # Falsifiability: the scanner must flag a planted Thread spawn.
    assert _CONCURRENCY.search("t = threading.Thread(target=f)") is not None

    for name in RESULT_MODULES:
        src = _read(name)
        assert _CONCURRENCY.search(src) is None, name
        # No module-level `global` rebinding — publish-only functions keep no
        # shared mutable state a concurrent sibling could observe.
        assert re.search(r"^\s*global\s+\w", src, re.MULTILINE) is None, name


def test_s3_results_declares_no_ledger_or_log_writer() -> None:
    # A publish-only producer imports no ledger-append or operational-log sink.
    banned = ("append_ledger", "ledger_line", "write_log", "operational_log", "emit_log")
    for name in RESULT_MODULES:
        src = _read(name)
        for token in banned:
            assert token not in src, (name, token)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
