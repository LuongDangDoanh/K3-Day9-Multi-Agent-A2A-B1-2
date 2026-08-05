from decimal import Decimal

import pytest

from dispute_agents.agents.policy import PolicyAgent
from dispute_agents.contracts import (
    DeliveryFinding, ItemRecord, OrderSellerFinding, PaymentFinding, PaymentRecord,
)


def findings(status="delivered", *, late=False, violations=(), payments=(Decimal("115.00"),), reconciled=True):
    item = ItemRecord("1", "seller-a", Decimal("100.00"), Decimal("15.00"), "2018-01-02 00:00:00")
    order = OrderSellerFinding(True, "order-a", status, (item,), Decimal("100.00"), Decimal("15.00"), ("seller-a",))
    rows = tuple(PaymentRecord(str(i), value) for i, value in enumerate(payments, 1))
    payment = PaymentFinding("order-a", rows, sum(payments), Decimal("115.00"), Decimal("0.00"), reconciled)
    delivery = DeliveryFinding(
        "order-a", "2018-01-03 00:00:00", "2018-01-10 00:00:00", "2018-01-09 00:00:00",
        late, tuple("1" for _ in violations), tuple(violations),
    )
    return order, payment, delivery


@pytest.mark.parametrize(
    "args,issue",
    [
        ({"status": "canceled"}, "canceled_order_paid"),
        ({"status": "unavailable"}, "unavailable_order_paid"),
        ({"late": True, "violations": ("seller-a",)}, "late_delivery_seller"),
        ({"late": True}, "late_delivery_logistics"),
        ({"payments": (Decimal("50.00"), Decimal("65.00"))}, "valid_split_payment"),
        ({}, "unsupported_late_claim"),
    ],
)
def test_policy_branches(args, issue):
    assert PolicyAgent().decide(*findings(**args)).primary_issue == issue


def test_canceled_precedes_late_seller():
    assert PolicyAgent().decide(*findings(status="canceled", late=True, violations=("seller-a",))).primary_issue == "canceled_order_paid"


def test_split_precedes_unsupported():
    assert PolicyAgent().decide(*findings(payments=(Decimal("50.00"), Decimal("65.00")))).primary_issue == "valid_split_payment"
