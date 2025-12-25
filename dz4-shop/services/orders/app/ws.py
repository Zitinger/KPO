import asyncio
from dataclasses import dataclass, field
from typing import Dict, Set
from uuid import UUID

from fastapi import WebSocket


@dataclass
class WsManager:
    _by_order: Dict[str, Set[WebSocket]] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def connect(self, order_id: UUID, ws: WebSocket) -> None:
        await ws.accept()
        key = str(order_id)
        async with self._lock:
            self._by_order.setdefault(key, set()).add(ws)

    async def disconnect(self, order_id: UUID, ws: WebSocket) -> None:
        key = str(order_id)
        async with self._lock:
            if key in self._by_order:
                self._by_order[key].discard(ws)
                if not self._by_order[key]:
                    self._by_order.pop(key, None)

    async def broadcast(self, order_id: str, message: dict) -> None:
        async with self._lock:
            targets = list(self._by_order.get(order_id, set()))
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                try:
                    await ws.close()
                except Exception:
                    pass
