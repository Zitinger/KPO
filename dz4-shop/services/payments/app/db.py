import json

import asyncpg
from typing import Any, Dict, List, Optional
from uuid import UUID


CREATE_SQL = [
    """
    CREATE TABLE IF NOT EXISTS accounts (
        user_id TEXT PRIMARY KEY,
        balance BIGINT NOT NULL DEFAULT 0 CHECK (balance >= 0),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS inbox (
        message_id UUID PRIMARY KEY,
        received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        payload JSONB NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS payment_operations (
        order_id UUID PRIMARY KEY,
        user_id TEXT NOT NULL,
        amount BIGINT NOT NULL CHECK (amount >= 0),
        status TEXT NOT NULL,
        reason TEXT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
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


class PaymentsDb:
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
            lock_key = 42424202
            try:
                await conn.execute("SELECT pg_advisory_lock($1)", lock_key)
                for sql in CREATE_SQL:
                    await conn.execute(sql)
            finally:
                await conn.execute("SELECT pg_advisory_unlock($1)", lock_key)

    async def create_account(self, *, user_id: str) -> Dict[str, Any]:
        if self._pool is None:
            raise RuntimeError("DB pool is not initialized")
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO accounts (user_id, balance)
                VALUES ($1, 0)
                RETURNING user_id, balance, created_at;
                """,
                user_id
            )
            return dict(row)

    async def get_account(self, *, user_id: str) -> Optional[Dict[str, Any]]:
        if self._pool is None:
            raise RuntimeError("DB pool is not initialized")
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT user_id, balance, created_at
                FROM accounts
                WHERE user_id = $1;
                """,
                user_id
            )
            return dict(row) if row is not None else None

    async def deposit(self, *, user_id: str, amount: int) -> Dict[str, Any]:
        if self._pool is None:
            raise RuntimeError("DB pool is not initialized")
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE accounts
                SET balance = balance + $2
                WHERE user_id = $1
                RETURNING user_id, balance, created_at;
                """,
                user_id, amount
            )
            if row is None:
                raise KeyError("account_not_found")
            return dict(row)

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

    async def process_payment_request(
        self,
        *,
        message_id: UUID,
        order_id: UUID,
        user_id: str,
        amount: int,
        description: str,
        result_message_id: UUID,
        result_payload: Dict[str, Any],
    ) -> None:
        if self._pool is None:
            raise RuntimeError("DB pool is not initialized")

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                ins = await conn.execute(
                    """
                    INSERT INTO inbox (message_id, payload)
                    VALUES ($1, $2)
                    ON CONFLICT DO NOTHING;
                    """,
                    message_id, json.dumps({"order_id": str(order_id), "user_id": user_id, "amount": amount, "description": description})
                )
                if ins.endswith("0"):
                    return

                existing = await conn.fetchrow(
                    """
                    SELECT status, reason
                    FROM payment_operations
                    WHERE order_id = $1;
                    """,
                    order_id
                )
                if existing is not None:
                    status = existing["status"]
                    reason = existing["reason"]
                    result_payload["data"]["status"] = status
                    result_payload["data"]["reason"] = reason

                    await conn.execute(
                        """
                        INSERT INTO outbox (message_id, event_type, aggregate_id, payload)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT DO NOTHING;
                        """,
                        result_message_id, "payment.result", order_id, json.dumps(result_payload)
                    )
                    return

                updated = await conn.fetchrow(
                    """
                    UPDATE accounts
                    SET balance = balance - $2
                    WHERE user_id = $1 AND balance >= $2
                    RETURNING balance;
                    """,
                    user_id, amount
                )

                status = "SUCCESS"
                reason = None

                if updated is None:
                    acc = await conn.fetchrow(
                        """
                        SELECT 1 FROM accounts WHERE user_id = $1;
                        """,
                        user_id
                    )
                    status = "FAIL"
                    reason = "NO_ACCOUNT" if acc is None else "INSUFFICIENT_FUNDS"

                await conn.execute(
                    """
                    INSERT INTO payment_operations (order_id, user_id, amount, status, reason)
                    VALUES ($1, $2, $3, $4, $5);
                    """,
                    order_id, user_id, amount, status, reason
                )

                result_payload["data"]["status"] = status
                result_payload["data"]["reason"] = reason

                await conn.execute(
                    """
                    INSERT INTO outbox (message_id, event_type, aggregate_id, payload)
                    VALUES ($1, $2, $3, $4);
                    """,
                    result_message_id, "payment.result", order_id, json.dumps(result_payload)
                )
