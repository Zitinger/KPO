import asyncio
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from .config import load_settings
from .db import OrdersDb
from .rabbit import Rabbit
from .outbox_publisher import OutboxPublisher
from .redis_pubsub import RedisPubSub
from .ws import WsManager
from .payment_results_handler import handle_payment_result


class CreateOrderRequest(BaseModel):
    amount: int = Field(ge=0)
    description: str = Field(min_length=1, max_length=500)


class OrderResponse(BaseModel):
    id: UUID
    user_id: str
    amount: int
    description: str
    status: str
    created_at: datetime


def create_app() -> FastAPI:
    settings = load_settings()

    db = OrdersDb(settings.database_dsn)
    rabbit = Rabbit(settings.rabbit_url)
    redis_pubsub = RedisPubSub(settings.redis_url)
    ws_manager = WsManager()
    outbox_publisher = OutboxPublisher(
        db, rabbit,
        interval_sec=settings.outbox_publish_interval_sec,
        batch_size=settings.outbox_batch_size,
    )

    async def lifespan(app: FastAPI):
        await db.connect()
        await db.init_schema()
        await rabbit.connect()
        await redis_pubsub.connect()

        await rabbit.consume_payment_results(
            lambda payload: handle_payment_result(db=db, redis_pubsub=redis_pubsub, payload=payload)
        )

        stop_sub = asyncio.Event()

        async def redis_listener():
            async for event in redis_pubsub.subscribe_updates():
                if stop_sub.is_set():
                    break
                if event.get("type") != "status_update":
                    continue
                order_id = event.get("order_id")
                if not order_id:
                    continue
                await ws_manager.broadcast(order_id, event)

        redis_task = asyncio.create_task(redis_listener())

        outbox_publisher.start()
        try:
            yield
        finally:
            stop_sub.set()
            redis_task.cancel()
            try:
                await redis_task
            except asyncio.CancelledError:
                pass
            await outbox_publisher.stop()
            await redis_pubsub.close()
            await rabbit.close()
            await db.close()

    app = FastAPI(title=f"Orders Service ({settings.service_name})", lifespan=lifespan)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": settings.service_name}

    def _require_user_id(x_user_id: str | None) -> str:
        if not x_user_id:
            raise HTTPException(status_code=400, detail="X-User-Id header is required")
        return x_user_id

    @app.post("/orders", response_model=OrderResponse)
    async def create_order(req: CreateOrderRequest, x_user_id: str | None = Header(default=None, alias="X-User-Id")):
        user_id = _require_user_id(x_user_id)
        order_id = uuid4()
        message_id = uuid4()
        payload = {
            "message_id": str(message_id),
            "event_type": "payment.requested",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "data": {
                "order_id": str(order_id),
                "user_id": user_id,
                "amount": int(req.amount),
                "description": req.description,
            },
        }
        order = await db.create_order_with_outbox(
            order_id=order_id,
            user_id=user_id,
            amount=int(req.amount),
            description=req.description,
            message_id=message_id,
            payload=payload,
        )
        return OrderResponse(**order)

    @app.get("/orders")
    async def list_orders(x_user_id: str | None = Header(default=None, alias="X-User-Id")):
        user_id = _require_user_id(x_user_id)
        return await db.list_orders(user_id=user_id)

    @app.get("/orders/{order_id}")
    async def get_order(order_id: str, x_user_id: str | None = Header(default=None, alias="X-User-Id")):
        user_id = _require_user_id(x_user_id)
        try:
            oid = UUID(order_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid order_id")
        order = await db.get_order(order_id=oid, user_id=user_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    @app.websocket("/ws/orders/{order_id}")
    async def ws_order_status(ws: WebSocket, order_id: str, user_id: str | None = None):
        if not user_id:
            await ws.close(code=1008)
            return
        try:
            oid = UUID(order_id)
        except Exception:
            await ws.close(code=1008)
            return

        order = await db.get_order(order_id=oid, user_id=user_id)
        if order is None:
            await ws.close(code=1008)
            return

        await ws_manager.connect(oid, ws)
        try:
            await ws.send_json({
                "type": "snapshot",
                "order_id": str(oid),
                "status": order["status"],
            })
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await ws_manager.disconnect(oid, ws)

    return app


app = create_app()
