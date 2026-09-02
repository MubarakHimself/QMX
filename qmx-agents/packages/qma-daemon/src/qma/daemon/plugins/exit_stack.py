"""Per-plugin LIFO exit stack for scoped contribution disposers (CT-42; AD-21)."""

from __future__ import annotations

from dataclasses import dataclass, field

from qma.core.plugins.context import Disposer

__all__ = ["PluginExitStack"]


@dataclass
class PluginExitStack:
    """LIFO disposer stack backing one plugin activation scope.

    Registrations push sync disposers here. Unload closes LIFO so every
    contribution disappears together. ``aclose`` exists so the stack can sit on
    an asyncio exit path without a file watcher or reactive remount.
    """

    plugin_id: str
    _disposers: list[Disposer] = field(default_factory=list[Disposer], init=False)
    closed: bool = field(default=False, init=False)

    def push(self, disposer: Disposer) -> Disposer:
        if self.closed:
            msg = f"plugin exit stack for {self.plugin_id!r} is already closed"
            raise RuntimeError(msg)
        self._disposers.append(disposer)
        return disposer

    def close(self) -> int:
        """Invoke disposers LIFO; returns how many ran."""
        if self.closed:
            return 0
        self.closed = True
        count = 0
        while self._disposers:
            dispose = self._disposers.pop()
            dispose()
            count += 1
        return count

    async def aclose(self) -> int:
        """Async-compatible close — same LIFO unwind as ``close``."""
        return self.close()

    @property
    def depth(self) -> int:
        return len(self._disposers)
