"""Typed A2A handoff contracts.

Contracts are deliberately plain dataclasses so the pipeline has no runtime
dependency beyond Python. Each handoff is serialized into a signed-by-digest
envelope before it is traced.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class ItemRecord:
    order_item_id: str
    seller_id: str
    price_brl: Decimal
    freight_brl: Decimal
    shipping_limit_date: str


@dataclass(frozen=True)
class PaymentRecord:
    payment_sequential: str
    payment_value_brl: Decimal


@dataclass(frozen=True)
class OrderSellerFinding:
    order_found: bool
    order_id: str
    order_status: str
    items: tuple[ItemRecord, ...]
    item_total_brl: Decimal
    freight_total_brl: Decimal
    seller_ids: tuple[str, ...]


@dataclass(frozen=True)
class PaymentFinding:
    order_id: str
    rows: tuple[PaymentRecord, ...]
    payment_total_brl: Decimal
    expected_total_brl: Decimal
    delta_brl: Decimal
    reconciled: bool


@dataclass(frozen=True)
class DeliveryFinding:
    order_id: str
    delivered_carrier_date: str | None
    delivered_customer_date: str | None
    estimated_delivery_date: str | None
    delivered_late: bool
    violating_item_ids: tuple[str, ...]
    violating_seller_ids: tuple[str, ...]


@dataclass(frozen=True)
class ResolutionCandidate:
    primary_issue: str
    case_status: str
    cause_code: str
    responsible_parties: tuple[dict[str, str], ...]
    recommended_refund_brl: Decimal
    actions: tuple[str, ...]


@dataclass(frozen=True)
class VerificationReport:
    passed: bool
    checks: dict[str, bool]
    errors: tuple[str, ...] = field(default_factory=tuple)


def primitive(value: Any) -> Any:
    """Convert contract values into stable JSON-compatible primitives."""
    if isinstance(value, Decimal):
        return format(value, ".2f")
    if hasattr(value, "__dataclass_fields__"):
        return primitive(asdict(value))
    if isinstance(value, dict):
        return {str(k): primitive(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [primitive(v) for v in value]
    return value
