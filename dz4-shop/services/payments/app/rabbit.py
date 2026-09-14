import asyncio
import json
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import AbstractIncomingMessage

from .constants import (
    EXCHANGE_NAME,
    QUEUE_PAYMENT_REQUESTS,
    QUEUE_PAYMENT_RESULTS,
    RK_PAYMENT_REQUESTED,
    RK_PAYMENT_RESULT,
)


@dataclass
class Rabbit:
    url: str
    _conn: Optional[aio_pika.RobustConnection] = None
    _channel: Optional[aio_pika.RobustChannel] = None
    _exchange: Optional[aio_pika.Exchange] = None
    _q_payment_requests: Optional[aio_pika.Queue] = None

    async def connect(self) -> None:
        while True:
            try:
                self._conn = await aio_pika.connect_robust(self.url)
                self._channel = await self._conn.channel()
                await self._channel.set_qos(prefetch_count=50)

                self._exchange = await self._channel.declare_exchange(
                    EXCHANGE_NAME, ExchangeType.DIRECT, durable=True
                )

                q_requests = await self._channel.declare_queue(QUEUE_PAYMENT_REQUESTS, durable=True)
                await q_requests.bind(self._exchange, routing_key=RK_PAYMENT_REQUESTED)
                self._q_payment_requests = q_requests

                q_results = await self._channel.declare_queue(QUEUE_PAYMENT_RESULTS, durable=True)
                await q_results.bind(self._exchange, routing_key=RK_PAYMENT_RESULT)
                return
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"[payments] rabbitmq connect failed: {e}; retrying in 1s", flush=True)
                await asyncio.sleep(1.0)

    async def close(self) -> None:
        if self._channel is not None:
            await self._channel.close()
        if self._conn is not None:
            await self._conn.close()
        self._conn = None
        self._channel = None
        self._exchange = None
        self._q_payment_requests = None

    async def publish_payment_result(self, payload: dict) -> None:
        if self._exchange is None:
            raise RuntimeError("Rabbit not connected")
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        msg = Message(
            body=body,
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type="application/json",
            message_id=str(payload.get("message_id")) if payload.get("message_id") else None,
        )
        await self._exchange.publish(msg, routing_key=RK_PAYMENT_RESULT)

    async def consume_payment_requests(self, handler: Callable[[dict], Awaitable[None]]) -> None:
        if self._q_payment_requests is None:
            raise RuntimeError("Rabbit not connected")

        async def _on_message(message: AbstractIncomingMessage) -> None:
            async with message.process(requeue=True):
                payload = json.loads(message.body.decode("utf-8"))
                await handler(payload)

        await self._q_payment_requests.consume(_on_message, no_ack=False)
