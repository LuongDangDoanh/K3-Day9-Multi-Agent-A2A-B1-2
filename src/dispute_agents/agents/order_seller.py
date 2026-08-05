from __future__ import annotations

from decimal import Decimal

from ..contracts import ItemRecord, OrderSellerFinding
from ..money import money
from ..repository import CsvRepository


class OrderSellerAgent:
    name = "order_seller"

    def __init__(self, repository: CsvRepository) -> None:
        self.repository = repository

    def investigate(self, order_id: str) -> OrderSellerFinding:
        order = self.repository.order(self.name, order_id)
        if order is None:
            return OrderSellerFinding(False, order_id, "", (), money(0), money(0), ())
        items = tuple(
            ItemRecord(
                order_item_id=row["order_item_id"],
                seller_id=row["seller_id"],
                price_brl=money(row["price"]),
                freight_brl=money(row["freight_value"]),
                shipping_limit_date=row["shipping_limit_date"],
            )
            for row in self.repository.items(self.name, order_id)
        )
        sellers = tuple(sorted({item.seller_id for item in items}))
        for seller_id in sellers:
            if not self.repository.seller_exists(self.name, seller_id):
                raise ValueError(f"Unknown seller: {seller_id}")
        return OrderSellerFinding(
            order_found=True,
            order_id=order_id,
            order_status=order["order_status"],
            items=items,
            item_total_brl=money(sum((i.price_brl for i in items), Decimal("0"))),
            freight_total_brl=money(sum((i.freight_brl for i in items), Decimal("0"))),
            seller_ids=sellers,
        )
