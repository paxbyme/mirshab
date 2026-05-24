"""Anti-flood hisoblagich — Redis yoki xotira ichida sliding window."""

from __future__ import annotations

import time
from collections import defaultdict, deque

try:  # redis opsional
    from redis.asyncio import Redis
except Exception:  # pragma: no cover
    Redis = None  # type: ignore[assignment, misc]


class FloodController:
    """N soniyalik oynada M+ xabar => flood deb belgilaydi."""

    def __init__(
        self,
        window_seconds: int,
        max_messages: int,
        redis_url: str = "",
    ) -> None:
        self.window = window_seconds
        self.max_messages = max_messages
        self._redis = None
        if redis_url and Redis is not None:
            self._redis = Redis.from_url(redis_url, decode_responses=True)
        # Xotira fallback: (chat_id, user_id) -> timestamp deque
        self._mem: dict[tuple[int, int], deque[float]] = defaultdict(deque)

    async def hit(self, chat_id: int, user_id: int) -> bool:
        """Bitta xabarni hisobga oladi. Flood chegarasidan oshsa True qaytaradi."""
        if self._redis is not None:
            return await self._hit_redis(chat_id, user_id)
        return self._hit_memory(chat_id, user_id)

    def _hit_memory(self, chat_id: int, user_id: int) -> bool:
        now = time.monotonic()
        dq = self._mem[(chat_id, user_id)]
        dq.append(now)
        cutoff = now - self.window
        while dq and dq[0] < cutoff:
            dq.popleft()
        return len(dq) >= self.max_messages

    async def _hit_redis(self, chat_id: int, user_id: int) -> bool:
        key = f"flood:{chat_id}:{user_id}"
        assert self._redis is not None
        pipe = self._redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, self.window)
        count, _ = await pipe.execute()
        return int(count) >= self.max_messages

    async def reset(self, chat_id: int, user_id: int) -> None:
        if self._redis is not None:
            await self._redis.delete(f"flood:{chat_id}:{user_id}")
        else:
            self._mem.pop((chat_id, user_id), None)

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
