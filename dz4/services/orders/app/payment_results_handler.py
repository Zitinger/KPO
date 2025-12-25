from uuid import UUID

from .db import OrdersDb
from .redis_pubsub import RedisPubSub


async def handle_payment_result(*, db: OrdersDb, redis_pubsub: RedisPubSub, payload: dict) -> None:
    data = payload.get("data") or {}
    order_id_raw = data.get("order_id")
    status = data.get("status")
    reason = data.get("reason")

    if not order_id_raw or status not in ("SUCCESS", "FAIL"):
        return

    order_id = UUID(order_id_raw)
    new_status = "FINISHED" if status == "SUCCESS" else "CANCELLED"

    updated = await db.apply_payment_result(order_id=order_id, new_status=new_status)
    if updated:
        await redis_pubsub.publish_order_update({
            "type": "status_update",
            "order_id": str(order_id),
            "status": new_status,
            "reason": reason,
        })
