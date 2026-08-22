"""Typed failures for the Leadership Observation Ledger boundary."""

from __future__ import annotations

from typing import Any


class LobsError(ValueError):
    """A fail-closed ledger contract error with a stable machine code."""

    def __init__(self, code: str, message: str, *, path: str | None = None) -> None:
        self.code = str(code)
        self.message = str(message)
        self.path = None if path is None else str(path)
        location = "" if self.path is None else f" at {self.path}"
        super().__init__(f"{self.code}{location}: {self.message}")

    def as_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-compatible failure document."""

        return {
            "code": self.code,
            "message": self.message,
            "path": self.path,
        }
