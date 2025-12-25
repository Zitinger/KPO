from datetime import datetime
from uuid import UUID, uuid4

from .db import PaymentsDb


async def handle_payment_request(*, db: PaymentsDb, payload: dict) -> None:
    data = payload.get("data") or {}
    msg_id_raw = payload.get("message_id")
    order_id_raw = data.get("order_id")
    user_id = data.get("user_id")
    amount = data.get("amount")
    description = data.get("description") or ""

    if not msg_id_raw or not order_id_raw or not user_id or amount is None:
        return

    message_id = UUID(msg_id_raw)
    order_id = UUID(order_id_raw)
    amount_int = int(amount)

    result_message_id = uuid4()
    result_payload = {
        "message_id": str(result_message_id),
        "event_type": "payment.result",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "data": {
            "order_id": str(order_id),
            "user_id": user_id,
            "amount": amount_int,
            "status": "FAIL",
            "reason": None,
        },
    }

    await db.process_payment_request(
        message_id=message_id,
        order_id=order_id,
        user_id=user_id,
        amount=amount_int,
        description=description,
        result_message_id=result_message_id,
        result_payload=result_payload,
    )
