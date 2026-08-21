"""Tier-1 tests for the content-addressed identity guard (AC2; DEC-0108)."""

from __future__ import annotations

from qmf.core import Fingerprint, TypedRefusal, canonical_bytes, fingerprint, is_ok, is_refusal
from qmf.data.store.engines import StoreEngineError
from qmf.data.store.identity import Admission, admit, canonical_identity, resolve_fingerprint


def _fp_of(content: object) -> Fingerprint:
    result = fingerprint(content)
    assert is_ok(result)
    return result.value


def _bytes_of(content: object) -> bytes:
    result = canonical_bytes(content)
    assert is_ok(result)
    return result.value


def test_canonical_identity_returns_fp_and_bytes() -> None:
    content = {"a": 1, "b": 2}
    result = canonical_identity(content)
    assert is_ok(result)
    fp, canonical = result.value
    assert fp == _fp_of(content)
    assert canonical == _bytes_of(content)


def test_canonical_identity_refuses_float() -> None:
    result = canonical_identity({"weight": 1.5})
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "invalid input"


def test_admit_first_write_is_stored_and_persists() -> None:
    seen: dict[str, bytes] = {}
    content = {"kind": "producer", "n": 1}

    def existing(digest: str) -> bytes | None:
        return seen.get(digest)

    def persist(fp: Fingerprint, canonical: bytes) -> None:
        seen[fp.digest] = canonical

    result = admit(content, existing_bytes=existing, persist=persist)
    assert is_ok(result)
    admission = result.value
    assert isinstance(admission, Admission)
    assert admission.outcome.value == "stored"
    assert admission.fingerprint.digest in seen


def test_admit_byte_identical_rewrite_is_idempotent_and_does_not_persist_again() -> None:
    store: dict[str, bytes] = {}
    content = {"kind": "producer", "n": 1}
    persist_calls = 0

    def existing(digest: str) -> bytes | None:
        return store.get(digest)

    def persist(fp: Fingerprint, canonical: bytes) -> None:
        nonlocal persist_calls
        persist_calls += 1
        store[fp.digest] = canonical

    first = admit(content, existing_bytes=existing, persist=persist)
    assert is_ok(first)
    again = admit(content, existing_bytes=existing, persist=persist)
    assert is_ok(again)
    assert again.value.outcome.value == "idempotent"
    assert persist_calls == 1  # the second write did not persist


def test_admit_true_collision_is_refused_and_alarmed() -> None:
    content = {"kind": "producer", "n": 1}
    fp = _fp_of(content)

    def existing(digest: str) -> bytes | None:
        # Same digest already addresses DIFFERENT bytes — a true collision.
        return b"different-stored-bytes" if digest == fp.digest else None

    def persist(_fp: Fingerprint, _canonical: bytes) -> None:  # pragma: no cover - never reached
        raise AssertionError("a collision must never persist")

    result = admit(content, existing_bytes=existing, persist=persist)
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "policy rejection"
    assert result.context.get("alarm") is True


def test_admit_presented_fingerprint_mismatch_is_invalid_input() -> None:
    content = {"kind": "producer", "n": 1}
    wrong = _fp_of({"kind": "other"})

    def existing(_digest: str) -> bytes | None:  # pragma: no cover - never reached
        return None

    def persist(_fp: Fingerprint, _canonical: bytes) -> None:  # pragma: no cover - never reached
        raise AssertionError("a mismatch must never persist")

    result = admit(content, existing_bytes=existing, persist=persist, presented_fingerprint=wrong)
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "invalid input"
    assert result.context.get("field") == "fingerprint"


def test_admit_presented_fingerprint_match_is_accepted() -> None:
    content = {"kind": "producer", "n": 1}
    fp = _fp_of(content)
    store: dict[str, bytes] = {}
    result = admit(
        content,
        existing_bytes=store.get,
        persist=lambda f, c: store.__setitem__(f.digest, c),
        presented_fingerprint=fp.value,  # the fp1 string form
    )
    assert is_ok(result)


def test_admit_unparseable_presented_fingerprint_is_invalid_input() -> None:
    result = admit(
        {"a": 1},
        existing_bytes=lambda _d: None,
        persist=lambda _f, _c: None,
        presented_fingerprint="not-a-fingerprint",
    )
    assert isinstance(result, TypedRefusal)
    assert result.context.get("field") == "fingerprint"


def test_admit_refuses_float_content_before_touching_engine() -> None:
    def existing(_digest: str) -> bytes | None:  # pragma: no cover - never reached
        raise AssertionError("identity refusal must precede any lookup")

    result = admit({"weight": 1.5}, existing_bytes=existing, persist=lambda _f, _c: None)
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "invalid input"


def test_admit_propagates_engine_error_from_persist() -> None:
    def existing(_digest: str) -> bytes | None:
        return None

    def persist(_fp: Fingerprint, _canonical: bytes) -> None:
        raise StoreEngineError("disk full", engine="test")

    try:
        admit({"a": 1}, existing_bytes=existing, persist=persist)
    except StoreEngineError as exc:
        assert exc.engine == "test"
    else:  # pragma: no cover - the raise above always fires
        raise AssertionError("admit must let a StoreEngineError propagate")


def test_resolve_fingerprint_accepts_fingerprint_and_string() -> None:
    fp = _fp_of({"a": 1})
    assert is_ok(resolve_fingerprint(fp))
    assert is_ok(resolve_fingerprint(fp.value))
    assert is_refusal(resolve_fingerprint("nope"))
    assert is_refusal(resolve_fingerprint(123))
