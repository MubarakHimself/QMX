"""Static AST/import-scan rules for Layer 2 (QL-8).

Pure: the host supplies an in-memory source tree. This module never opens a
file, never spawns a process, and never starts a thread. Findings name a
denied capability from the library-owned denial set. A dynamically-evasive
bot is out of V1's threat model (DEC-0178).
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from qmf.core.refusal import Ok, Result, is_refusal

from qml._refuse import invalid
from qml.conformance.contract import CONFORMANCE_FORMAT_VERSION, DENIAL_SET
from qml.logic import normalize_source_manifest

__all__ = [
    "AST_SCAN_RULES_CLASS",
    "DENIED_CALL_SUFFIXES",
    "DENIED_IMPORTS",
    "DENIED_NAME_CALLS",
    "ScanFinding",
    "ScanReport",
    "ast_scan_rules_identity",
    "scan_logic_source",
]

AST_SCAN_RULES_CLASS: Final[str] = "qml-ast-import-scan-rules"

DENIED_IMPORTS: Final[Mapping[str, frozenset[str]]] = MappingProxyType(
    {
        "clock": frozenset({"time"}),
        "io": frozenset(
            {
                "os",
                "io",
                "pathlib",
                "shutil",
                "tempfile",
                "fileinput",
                "mmap",
                "subprocess",
                "threading",
                "multiprocessing",
                "concurrent",
                "fcntl",
                "msvcrt",
                "winreg",
            }
        ),
        "network": frozenset(
            {
                "socket",
                "ssl",
                "select",
                "selectors",
                "http",
                "urllib",
                "ftplib",
                "smtplib",
                "imaplib",
                "nntplib",
                "poplib",
                "telnetlib",
                "xmlrpc",
                "asyncio",
                "aiohttp",
                "requests",
                "httpx",
                "websockets",
            }
        ),
        "undeclared_randomness": frozenset({"random", "secrets"}),
    }
)

DENIED_CALL_SUFFIXES: Final[Mapping[str, frozenset[tuple[str, ...]]]] = MappingProxyType(
    {
        "clock": frozenset(
            {
                ("time", "time"),
                ("time", "time_ns"),
                ("time", "monotonic"),
                ("time", "monotonic_ns"),
                ("time", "perf_counter"),
                ("time", "perf_counter_ns"),
                ("time", "process_time"),
                ("time", "process_time_ns"),
                ("time", "clock_gettime"),
                ("time", "gmtime"),
                ("time", "localtime"),
                ("datetime", "now"),
                ("datetime", "utcnow"),
                ("datetime", "today"),
            }
        ),
        "io": frozenset(
            {
                ("Path", "read_text"),
                ("Path", "write_text"),
                ("Path", "read_bytes"),
                ("Path", "write_bytes"),
                ("Path", "open"),
                ("os", "open"),
                ("os", "read"),
                ("os", "write"),
                ("os", "remove"),
                ("os", "unlink"),
                ("io", "open"),
                ("builtins", "open"),
            }
        ),
        "undeclared_randomness": frozenset(
            {
                ("random", "random"),
                ("random", "randint"),
                ("random", "choice"),
                ("random", "randrange"),
                ("random", "shuffle"),
                ("random", "seed"),
                ("secrets", "token_bytes"),
                ("secrets", "token_hex"),
                ("os", "urandom"),
            }
        ),
    }
)

DENIED_NAME_CALLS: Final[Mapping[str, frozenset[str]]] = MappingProxyType(
    {
        "io": frozenset({"open"}),
    }
)

_PYTHON_SUFFIX: Final[str] = ".py"


def ast_scan_rules_identity() -> dict[str, object]:
    """Canonical identity of the AST/import-scan rules. Package SemVer never enters."""
    return {
        "class": AST_SCAN_RULES_CLASS,
        "contract_format_version": CONFORMANCE_FORMAT_VERSION,
        "denial_set": sorted(DENIAL_SET),
        "denied_imports": {
            capability: sorted(modules) for capability, modules in sorted(DENIED_IMPORTS.items())
        },
        "denied_name_calls": {
            capability: sorted(names) for capability, names in sorted(DENIED_NAME_CALLS.items())
        },
        "denied_call_suffixes": {
            capability: [".".join(suffix) for suffix in sorted(suffixes)]
            for capability, suffixes in sorted(DENIED_CALL_SUFFIXES.items())
        },
    }


@dataclass(frozen=True, slots=True)
class ScanFinding:
    """One static denial: a capability from the denial set at a source location."""

    capability: str
    path: str
    lineno: int
    detail: str

    def fp1_identity(self) -> dict[str, object]:
        return {
            "capability": self.capability,
            "path": self.path,
            "lineno": self.lineno,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class ScanReport:
    """Result of scanning an in-memory logic source tree (DEC-0178)."""

    findings: tuple[ScanFinding, ...]
    rules_format_version: int = CONFORMANCE_FORMAT_VERSION

    @property
    def clean(self) -> bool:
        return not self.findings

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "qml-ast-import-scan-report",
            "contract_format_version": self.rules_format_version,
            "findings": [item.fp1_identity() for item in self.findings],
        }


def scan_logic_source(
    source_tree: object,
    *,
    declared_seed: object = False,
) -> Result[ScanReport]:
    """Scan bot logic source for denied clock/I-O/network/randomness uses.

    ``declared_seed`` is true when the Bot definition names a seed parameter;
    ``random`` is then permitted (a stochastic bot declares its seed). ``secrets``
    and ``os.urandom`` stay denied. Syntax errors are ``invalid input``.
    """
    if declared_seed is not True and declared_seed is not False:
        return invalid(
            "declared_seed",
            "declared_seed is a bool: true when the parameter space names a seed",
            given=repr(declared_seed),
        )
    normalized = normalize_source_manifest(source_tree)
    if is_refusal(normalized):
        return normalized
    findings: list[ScanFinding] = []
    for path, content in sorted(normalized.value.items()):
        if not path.endswith(_PYTHON_SUFFIX):
            continue
        scanned = _scan_file(path, content, declared_seed=declared_seed)
        if is_refusal(scanned):
            return scanned
        findings.extend(scanned.value)
    return Ok(ScanReport(findings=tuple(findings)))


def _scan_file(path: str, content: str, *, declared_seed: bool) -> Result[tuple[ScanFinding, ...]]:
    try:
        tree = ast.parse(content, filename=path)
    except SyntaxError as exc:
        return invalid(
            "source_tree",
            "bot logic source must parse as Python; a syntax error is invalid input",
            path=path,
            lineno=exc.lineno,
            layer=2,
        )
    found: list[ScanFinding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _record_module(found, path, node.lineno, alias.name, declared_seed)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue
            module = node.module or ""
            if module:
                _record_module(found, path, node.lineno, module, declared_seed)
            for alias in node.names:
                if module:
                    _record_module(
                        found, path, node.lineno, f"{module}.{alias.name}", declared_seed
                    )
        elif isinstance(node, ast.Call):
            _record_call(found, path, node, declared_seed)
    return Ok(tuple(found))


def _record_module(
    found: list[ScanFinding],
    path: str,
    lineno: int,
    module: str,
    declared_seed: bool,
) -> None:
    capability = _capability_for_module(module)
    if capability is None:
        return
    if capability == "undeclared_randomness" and declared_seed and _is_random_module(module):
        return
    found.append(
        ScanFinding(
            capability=capability,
            path=path,
            lineno=lineno,
            detail=f"import {module}",
        )
    )


def _record_call(
    found: list[ScanFinding],
    path: str,
    node: ast.Call,
    declared_seed: bool,
) -> None:
    func = node.func
    if isinstance(func, ast.Name):
        for capability, names in DENIED_NAME_CALLS.items():
            if func.id in names:
                found.append(
                    ScanFinding(
                        capability=capability,
                        path=path,
                        lineno=node.lineno,
                        detail=f"call {func.id}()",
                    )
                )
        if func.id == "__import__":
            imported = _const_str_arg(node)
            if imported is not None:
                _record_module(found, path, node.lineno, imported, declared_seed)
        return
    chain = _attr_chain(func)
    if not chain:
        return
    if chain[-1] == "import_module":
        imported = _const_str_arg(node)
        if imported is not None:
            _record_module(found, path, node.lineno, imported, declared_seed)
    for capability, suffixes in DENIED_CALL_SUFFIXES.items():
        if not _chain_matches(chain, suffixes):
            continue
        if capability == "undeclared_randomness" and declared_seed and chain[0] == "random":
            continue
        found.append(
            ScanFinding(
                capability=capability,
                path=path,
                lineno=node.lineno,
                detail=f"call {'.'.join(chain)}()",
            )
        )


def _capability_for_module(module: str) -> str | None:
    for capability, modules in DENIED_IMPORTS.items():
        if module in modules:
            return capability
        if any(module.startswith(name + ".") for name in modules):
            return capability
    return None


def _is_random_module(module: str) -> bool:
    return module == "random" or module.startswith("random.")


def _const_str_arg(node: ast.Call) -> str | None:
    if not node.args:
        return None
    first = node.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value
    return None


def _attr_chain(node: ast.AST) -> tuple[str, ...] | None:
    parts: list[str] = []
    current: ast.AST = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        parts.reverse()
        return tuple(parts)
    return None


def _chain_matches(chain: tuple[str, ...], suffixes: frozenset[tuple[str, ...]]) -> bool:
    return any(len(chain) >= len(suffix) and chain[-len(suffix) :] == suffix for suffix in suffixes)
