"""A priority queue in front of the voice service.

Microsoft's service slows down and refuses connections when too many requests overlap, so at most
``limit`` run at once. Priorities: 3 = the spot the user just seeked to, 2 = play now,
1 = prepare what comes next, 0 = background warm-up.
"""

from __future__ import annotations

import asyncio
import itertools
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")

URGENT, PLAY, NEXT, WARM = 3, 2, 1, 0


class PriorityGate:
    def __init__(self, limit: int = 4):
        self.limit = limit
        self.active = 0
        self._queue: list[dict] = []
        self._seq = itertools.count()

    @property
    def waiting(self) -> int:
        return len(self._queue)

    async def run(self, priority: int, fn: Callable[[], Awaitable[T]], key: str | None = None) -> T:
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._queue.append({"priority": priority, "seq": next(self._seq), "key": key, "fn": fn, "fut": fut})
        self._sort()
        self._pump()
        return await fut

    def bump(self, key: str, priority: int) -> None:
        """An urgent request for a sentence already waiting at a lower priority: raise it."""
        for job in self._queue:
            if job["key"] == key and job["priority"] < priority:
                job["priority"] = priority
                self._sort()
                return

    def _sort(self) -> None:
        self._queue.sort(key=lambda j: (-j["priority"], j["seq"]))

    def _pump(self) -> None:
        while self.active < self.limit and self._queue:
            job = self._queue.pop(0)
            self.active += 1
            asyncio.ensure_future(self._run(job))

    async def _run(self, job: dict) -> None:
        try:
            res = await job["fn"]()
            if not job["fut"].done():
                job["fut"].set_result(res)
        except BaseException as e:  # noqa: BLE001 — delivered to the awaiting caller
            if not job["fut"].done():
                job["fut"].set_exception(e)
        finally:
            self.active -= 1
            self._pump()
