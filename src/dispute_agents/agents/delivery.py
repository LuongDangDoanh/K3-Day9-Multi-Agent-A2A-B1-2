from __future__ import annotations

from ..contracts import DeliveryFinding, ItemRecord
from ..money import csv_timestamp
from ..repository import CsvRepository


class DeliveryAgent:
    name = "delivery"

    def __init__(self, repository: CsvRepository) -> None:
        self.repository = repository

    def inspect(self, order_id: str, items: tuple[ItemRecord, ...]) -> DeliveryFinding:
        order = self.repository.order(self.name, order_id)
        if order is None:
            raise ValueError(f"Unknown order: {order_id}")
        carrier = csv_timestamp(order["order_delivered_carrier_date"])
        delivered = csv_timestamp(order["order_delivered_customer_date"])
        estimated = csv_timestamp(order["order_estimated_delivery_date"])
        delivered_late = delivered is not None and estimated is not None and delivered > estimated
        violating = tuple(
            i for i in items
            if carrier is not None and csv_timestamp(i.shipping_limit_date) is not None
            and carrier > csv_timestamp(i.shipping_limit_date)
        )
        return DeliveryFinding(
            order_id=order_id,
            delivered_carrier_date=order["order_delivered_carrier_date"] or None,
            delivered_customer_date=order["order_delivered_customer_date"] or None,
            estimated_delivery_date=order["order_estimated_delivery_date"] or None,
            delivered_late=delivered_late,
            violating_item_ids=tuple(i.order_item_id for i in violating),
            violating_seller_ids=tuple(sorted({i.seller_id for i in violating})),
        )
