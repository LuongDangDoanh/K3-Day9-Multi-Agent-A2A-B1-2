"""Money and timestamp helpers shared by domain agents."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from .config import MONEY_QUANTUM


def money(value: str | int | float | Decimal) -> Decimal:
    return Decimal(str(value or "0")).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def money_float(value: Decimal) -> float:
    return float(money(value))


def csv_timestamp(value: str | None) -> datetime | None:
    if value is None or value == "":
        return None
    return datetime.fromisoformat(value)
