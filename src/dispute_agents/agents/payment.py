from __future__ import annotations

from decimal import Decimal

from ..config import PAYMENT_TOLERANCE
from ..contracts import PaymentFinding, PaymentRecord
from ..money import money
from ..repository import CsvRepository


class PaymentAgent:
    name = "payment"

    def __init__(self, repository: CsvRepository) -> None:
        self.repository = repository

    def reconcile(self, order_id: str, expected_total_brl: Decimal) -> PaymentFinding:
        rows = tuple(
            PaymentRecord(row["payment_sequential"], money(row["payment_value"]))
            for row in self.repository.payments(self.name, order_id)
        )
        total = money(sum((r.payment_value_brl for r in rows), Decimal("0")))
        expected = money(expected_total_brl)
        delta = money(total - expected)
        return PaymentFinding(order_id, rows, total, expected, delta, abs(delta) <= PAYMENT_TOLERANCE)
