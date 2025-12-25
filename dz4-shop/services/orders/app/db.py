import json

import asyncpg
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from datetime import datetime


CREATE_SQL = [
    """
    CREATE TABLE IF NOT EXISTS orders (
        id UUID PRIMARY KEY,
        user_id TEXT NOT NULL,
        amount BIGINT NOT NULL CHECK (amount >= 0),
        description TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS outbox (
        id BIGSERIAL PRIMARY KEY,
        message_id UUID NOT NULL UNIQUE,
        event_type TEXT NOT NULL,
        aggregate_id UUID NOT NULL,
        payload JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        published_at TIMESTAMPTZ NULL,
        publish_attempts INT NOT NULL DEFAULT 0,
        last_error TEXT NULL
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_outbox_published_at ON outbox(published_at);
    """,
]


class OrdersDb:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(dsn=self._dsn, min_size=1, max_size=10)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def init_schema(self) -> None:
        if self._pool is None:
            raise RuntimeError("DB pool is not initialized")
        async with self._pool.acquire() as conn:
            lock_key = 42424201
            try:
                await conn.execute("SELECT pg_advisory_lock($1)", lock_key)
                for sql in CREATE_SQL:
                    await conn.execute(sql)
            finally:
                await conn.execute("SELECT pg_advisory_unlock($1)", lock_key)


    async def create_order_with_outbox(
        self, *, order_id: UUID, user_id: str, amount: int, description: str, message_id: UUID, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        if self._pool is None:
            raise RuntimeError("DB pool is not initialized")
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    INSERT INTO orders (id, user_id, amount, description, status)
                    VALUES ($1, $2, $3, $4, 'NEW')
                    RETURNING id, user_id, amount, description, status, created_at;
                    """,
                    order_id, user_id, amount, description
                )
                await conn.execute(
                    """
                    INSERT INTO outbox (message_id, event_type, aggregate_id, payload)
                    VALUES ($1, $2, $3, $4);
                    """,
                    message_id, "payment.requested", order_id, json.dumps(payload)
                )
                return dict(row)

    async def list_orders(self, *, user_id: str) -> List[Dict[str, Any]]:
        if self._pool is None:
            raise RuntimeError("DB pool is not initialized")
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, amount, description, status, created_at
                FROM orders
                WHERE user_id = $1
                ORDER BY created_at DESC;
                """,
                user_id
            )
            return [dict(r) for r in rows]

    async def get_order(self, *, order_id: UUID, user_id: str) -> Optional[Dict[str, Any]]:
        if self._pool is None:
            raise RuntimeError("DB pool is not initialized")
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, amount, description, status, created_at
                FROM orders
                WHERE id = $1 AND user_id = $2;
                """,
                order_id, user_id
            )
            return dict(row) if row is not None else None

    async def get_order_any_user(self, *, order_id: UUID) -> Optional[Dict[str, Any]]:
        if self._pool is None:
            raise RuntimeError("DB pool is not initialized")
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, amount, description, status, created_at
                FROM orders
                WHERE id = $1;
                """,
                order_id
            )
            return dict(row) if row is not None else None

    async def fetch_outbox_batch(self, *, limit: int) -> List[Dict[str, Any]]:
        if self._pool is None:
            raise RuntimeError("DB pool is not initialized")
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                rows = await conn.fetch(
                    """
                    SELECT id, message_id, event_type, aggregate_id, payload
                    FROM outbox
                    WHERE published_at IS NULL
                    ORDER BY created_at
                    LIMIT $1
                    FOR UPDATE SKIP LOCKED;
                    """,
                    limit
                )
                return [dict(r) for r in rows]

    async def mark_outbox_published(self, *, outbox_id: int) -> None:
        if self._pool is None:
            raise RuntimeError("DB pool is not initialized")
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE outbox
                SET published_at = NOW(),
                    publish_attempts = publish_attempts + 1,
                    last_error = NULL
                WHERE id = $1;
                """,
                outbox_id
            )

    async def mark_outbox_failed(self, *, outbox_id: int, error: str) -> None:
        if self._pool is None:
            raise RuntimeError("DB pool is not initialized")
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE outbox
                SET publish_attempts = publish_attempts + 1,
                    last_error = $2
                WHERE id = $1;
                """,
                outbox_id, error[:2000]
            )

    async def apply_payment_result(
        self, *, order_id: UUID, new_status: str
    ) -> bool:
        if self._pool is None:
            raise RuntimeError("DB pool is not initialized")
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                res = await conn.execute(
                    """
                    UPDATE orders
                    SET status = $2
                    WHERE id = $1 AND status = 'NEW';
                    """,
                    order_id, new_status
                )
                updated = res.split()[-1] == "1"
                return updated
