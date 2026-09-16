"""Host-passed cited-byte decode shared by Stage 0 research helpers."""

from __future__ import annotations

from typing import Final

from qmf.core.refusal import Ok, Result

from qml._refuse import invalid

__all__ = ["FIELD_CITED_BYTES", "decode_cited_buffer"]

FIELD_CITED_BYTES: Final[str] = "cited_bytes"

_NON_BYTES_REASON: Final[str] = (
    "host-passed cited bytes are resolved in-process; lookup does not read a filesystem path"
)
_BAD_UTF8_REASON: Final[str] = "cited bytes are UTF-8 text"


def decode_cited_buffer(cited_bytes: object) -> Result[str]:
    """Admit a host-passed str/bytes buffer. Never opens a path."""
    if isinstance(cited_bytes, str):
        return Ok(cited_bytes)
    if not isinstance(cited_bytes, bytes):
        return invalid(
            FIELD_CITED_BYTES,
            _NON_BYTES_REASON,
            given=type(cited_bytes).__name__,
        )
    try:
        return Ok(cited_bytes.decode("utf-8"))
    except UnicodeDecodeError:
        return invalid(
            FIELD_CITED_BYTES,
            _BAD_UTF8_REASON,
            given="bytes",
        )
