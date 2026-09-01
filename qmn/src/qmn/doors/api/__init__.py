"""In-process Python API door — thin re-export surface (TN-17)."""

from __future__ import annotations

from typing import Final

__all__ = ["API_DOOR", "api_door_name"]

API_DOOR: Final[str] = "python_api"


def api_door_name() -> str:
    return API_DOOR
