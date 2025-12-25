import asyncio
import json
from typing import Optional

from .db import OrdersDb
from .rabbit import Rabbit


class OutboxPublisher:
    def __init__(self, db: OrdersDb, rabbit: Rabbit, *, interval_sec: float, batch_size: int):
        self._db = db
        self._rabbit = rabbit
        self._interval_sec = interval_sec
        self._batch_size = batch_size
        self._task: Optional[asyncio.Task] = None
        self._stopped = asyncio.Event()

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stopped.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        while not self._stopped.is_set():
            try:
                batch = await self._db.fetch_outbox_batch(limit=self._batch_size)
                for row in batch:
                    outbox_id = int(row["id"])
                    raw_payload = row["payload"]
                    if isinstance(raw_payload, str):
                        payload = json.loads(raw_payload)
                    elif isinstance(raw_payload, dict):
                        payload = raw_payload
                    else:
                        payload = dict(raw_payload)
                    try:
                        await self._rabbit.publish_payment_request(payload)
                        await self._db.mark_outbox_published(outbox_id=outbox_id)
                    except Exception as e:
                        await self._db.mark_outbox_failed(outbox_id=outbox_id, error=str(e))
                await asyncio.sleep(self._interval_sec)
            except asyncio.CancelledError:
                raise
            except Exception:
                await asyncio.sleep(1.0)
