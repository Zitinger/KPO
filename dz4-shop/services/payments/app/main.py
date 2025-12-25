import asyncio
from datetime import datetime
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .config import load_settings
from .db import PaymentsDb
from .rabbit import Rabbit
from .outbox_publisher import OutboxPublisher
from .payment_requests_handler import handle_payment_request


class DepositRequest(BaseModel):
    amount: int = Field(gt=0)


def create_app() -> FastAPI:
    settings = load_settings()

    db = PaymentsDb(settings.database_dsn)
    rabbit = Rabbit(settings.rabbit_url)
    outbox_publisher = OutboxPublisher(
        db, rabbit,
        interval_sec=settings.outbox_publish_interval_sec,
        batch_size=settings.outbox_batch_size,
    )

    async def lifespan(app: FastAPI):
        await db.connect()
        await db.init_schema()
        await rabbit.connect()

        await rabbit.consume_payment_requests(lambda payload: handle_payment_request(db=db, payload=payload))
        outbox_publisher.start()
        try:
            yield
        finally:
            await outbox_publisher.stop()
            await rabbit.close()
            await db.close()

    app = FastAPI(title=f"Payments Service ({settings.service_name})", lifespan=lifespan)

    def _require_user_id(x_user_id: str | None) -> str:
        if not x_user_id:
            raise HTTPException(status_code=400, detail="X-User-Id header is required")
        return x_user_id

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": settings.service_name}

    @app.post("/account")
    async def create_account(x_user_id: str | None = Header(default=None, alias="X-User-Id")):
        user_id = _require_user_id(x_user_id)
        existing = await db.get_account(user_id=user_id)
        if existing is not None:
            raise HTTPException(status_code=409, detail="Account already exists")
        acc = await db.create_account(user_id=user_id)
        return acc

    @app.get("/account")
    async def get_balance(x_user_id: str | None = Header(default=None, alias="X-User-Id")):
        user_id = _require_user_id(x_user_id)
        acc = await db.get_account(user_id=user_id)
        if acc is None:
            raise HTTPException(status_code=404, detail="Account not found")
        return acc

    @app.post("/account/deposit")
    async def deposit(req: DepositRequest, x_user_id: str | None = Header(default=None, alias="X-User-Id")):
        user_id = _require_user_id(x_user_id)
        try:
            acc = await db.deposit(user_id=user_id, amount=int(req.amount))
        except KeyError:
            raise HTTPException(status_code=404, detail="Account not found")
        return acc

    return app


app = create_app()
