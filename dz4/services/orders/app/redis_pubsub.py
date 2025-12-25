import json
from dataclasses import dataclass
from typing import AsyncIterator, Optional

import redis.asyncio as redis

from .constants import REDIS_CHANNEL_ORDER_UPDATES


@dataclass
class RedisPubSub:
    url: str
    _client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        self._client = redis.from_url(self.url, decode_responses=True)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
        self._client = None

    async def publish_order_update(self, event: dict) -> None:
        if self._client is None:
            raise RuntimeError("Redis not connected")
        await self._client.publish(REDIS_CHANNEL_ORDER_UPDATES, json.dumps(event, ensure_ascii=False))

    async def subscribe_updates(self) -> AsyncIterator[dict]:
        if self._client is None:
            raise RuntimeError("Redis not connected")
        pubsub = self._client.pubsub()
        await pubsub.subscribe(REDIS_CHANNEL_ORDER_UPDATES)
        try:
            async for message in pubsub.listen():
                if message is None:
                    continue
                if message.get("type") != "message":
                    continue
                data = message.get("data")
                if not isinstance(data, str):
                    continue
                try:
                    yield json.loads(data)
                except json.JSONDecodeError:
                    continue
        finally:
            await pubsub.close()
