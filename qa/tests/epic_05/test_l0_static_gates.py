"""Epic 5 — L0 static / documentation gates (PLAN Section 4: G1, G2, G3).

These read the backup-surface source as static evidence only; no source is edited.
Surface under gate: the four modules that make up COMP-QMF-DATA-BACKUP / the CT-26 input
seam — backup.py, store/backup_input.py, verify.py, cycle.py.

G1 — import/provider gate: the surface imports only qmf.core + its own qmf.data seam;
     no object-storage-provider SDK and no crypto-provider is baked in (DEC-0045, DEC-0120).
G2 — no-credential gate: no secret value, provider credential, or encryption key literal
     appears in the surface (DEC-0136); only reference ids may appear.
G3 — no-schedule/no-runtime gate: no scheduler, cron, event loop, thread, or daemon runtime
     lives in the surface — the schedule is application/ops-owned (DEC-0008, DEC-0022; FM-6).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import qmf.data as qdata

_SRC_ROOT = Path(qdata.__file__).resolve().parent  # .../qmf-data/src/qmf/data

# The COMP-QMF-DATA-BACKUP surface + the CT-26 store-to-backup input seam.
_SURFACE = [
    _SRC_ROOT / "backup.py",
    _SRC_ROOT / "store" / "backup_input.py",
    _SRC_ROOT / "verify.py",
    _SRC_ROOT / "cycle.py",
]

# Only these qmf.* prefixes are allowed: qmf.core (fp1 + refusal vocabulary) and the
# module's own qmf.data.* seam. Any other qmf.* import is a default-deny breach.
_ALLOWED_QMF_PREFIXES = ("qmf.core", "qmf.data")

# Object-storage provider SDKs and crypto providers that must NEVER be imported into the
# backup surface — the target stays external and replaceable, key custody stays node/ops.
_FORBIDDEN_THIRD_PARTY = (
    "boto3", "botocore", "s3transfer", "google.cloud", "google.auth", "azure",
    "minio", "b2sdk", "boxsdk", "dropbox", "paramiko", "fabric",
    "cryptography", "nacl", "pynacl", "Crypto", "cryptodome", "gnupg", "openssl",
    "requests", "urllib3", "httpx", "aiohttp",
)


def _imports(path: Path) -> tuple[set[str], set[str]]:
    """(all top-level imported module roots, qmf.* module names) for one file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    qmf_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
                if alias.name.startswith("qmf."):
                    qmf_names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level != 0 or node.module is None:
                continue
            roots.add(node.module.split(".")[0])
            if node.module.startswith("qmf."):
                qmf_names.add(node.module)
    return roots, qmf_names


def test_surface_files_exist() -> None:
    """The four backup-surface modules are present (else the gate would vacuously pass)."""
    missing = [str(p) for p in _SURFACE if not p.is_file()]
    assert missing == [], f"expected the backup surface files to exist; missing: {missing}"


def test_g1_only_qmf_core_and_own_seam() -> None:
    """G1: no backup-surface module imports any qmf.* package but qmf.core / qmf.data (DEC-0120)."""
    offenders: dict[str, set[str]] = {}
    for path in _SURFACE:
        _, qmf_names = _imports(path)
        bad = {
            name
            for name in qmf_names
            if not any(name == p or name.startswith(p + ".") for p in _ALLOWED_QMF_PREFIXES)
        }
        if bad:
            offenders[path.name] = bad
    assert offenders == {}, (
        "the backup surface must import only qmf.core and its own qmf.data.* seam "
        f"(default-deny, DEC-0120); cross-package imports found: {offenders}"
    )


def test_g1_no_provider_or_crypto_sdk_baked_in() -> None:
    """G1: no object-storage-provider SDK and no crypto-provider is imported (DEC-0045, AR-37)."""
    offenders: dict[str, set[str]] = {}
    for path in _SURFACE:
        roots, _ = _imports(path)
        bad = {tok for tok in _FORBIDDEN_THIRD_PARTY if tok.split(".")[0] in roots}
        if bad:
            offenders[path.name] = bad
    assert offenders == {}, (
        "the backup surface bakes in no provider/crypto SDK — the object-storage target "
        f"stays external and key custody node/ops (DEC-0045); forbidden imports: {offenders}"
    )


# G2 — a value that looks like an embedded secret/credential/key literal. Reference ids
# (e.g. "encryption-required", registry keys) are fine; an actual key/token value is not.
_SECRET_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key id
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),  # PEM private key
    re.compile(r"(?i)\b(aws_secret_access_key|secret_key|private_key|api_key|password|passwd|token)\b\s*=\s*['\"][^'\"]{8,}['\"]"),
)


def test_g2_no_credential_or_key_literal_in_surface() -> None:
    """G2: no secret value / provider credential / encryption key literal in the surface (DEC-0136)."""
    hits: dict[str, list[str]] = {}
    for path in _SURFACE:
        text = path.read_text(encoding="utf-8")
        found = [m.group(0) for pat in _SECRET_PATTERNS for m in pat.finditer(text)]
        if found:
            hits[path.name] = found
    assert hits == {}, (
        f"the backup surface must embed no credential/key literal (DEC-0136); found: {hits}"
    )


# G3 — runtime/scheduler machinery that must never live in the surface.
_FORBIDDEN_RUNTIME_ROOTS = (
    "threading", "asyncio", "sched", "subprocess", "multiprocessing",
    "signal", "selectors", "socketserver", "concurrent",
)
_FORBIDDEN_RUNTIME_CALLS = ("crontab", "schedule.every", "time.sleep", "Timer(")


def test_g3_no_scheduler_or_runtime_in_surface() -> None:
    """G3: no scheduler / event loop / thread / daemon runtime in the surface (FM-6; DEC-0008)."""
    import_offenders: dict[str, set[str]] = {}
    call_offenders: dict[str, list[str]] = {}
    for path in _SURFACE:
        roots, _ = _imports(path)
        bad = {r for r in _FORBIDDEN_RUNTIME_ROOTS if r in roots}
        if bad:
            import_offenders[path.name] = bad
        text = path.read_text(encoding="utf-8")
        calls = [c for c in _FORBIDDEN_RUNTIME_CALLS if c in text]
        if calls:
            call_offenders[path.name] = calls
    assert import_offenders == {} and call_offenders == {}, (
        "the backup surface owns no scheduler/thread/cron runtime — the schedule is "
        f"application/ops-owned (FM-6); import offenders: {import_offenders}; "
        f"call offenders: {call_offenders}"
    )
