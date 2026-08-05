"""Read-only, access-controlled CSV repository."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Callable, Iterable


TABLE_FILES = {
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
}

ACCESS = {
    "order_seller": frozenset({"orders", "items", "sellers"}),
    "payment": frozenset({"payments"}),
    "delivery": frozenset({"orders"}),
    "verifier": frozenset({"orders", "items", "payments", "sellers"}),
}


class AccessViolation(PermissionError):
    pass


class CsvRepository:
    """Indexes only data needed by the current input set.

    The initial indexing step is infrastructure, not an agent handoff. Every
    subsequent domain read is checked against the agent allowlist and can be
    reported to the trace callback.
    """

    def __init__(
        self,
        data_dir: Path,
        target_order_ids: Iterable[str],
        on_access: Callable[[str, str, str], None] | None = None,
    ) -> None:
        self.data_dir = data_dir
        self.target_order_ids = frozenset(target_order_ids)
        self.on_access = on_access
        self._orders: dict[str, dict[str, str]] = {}
        self._items: dict[str, list[dict[str, str]]] = defaultdict(list)
        self._payments: dict[str, list[dict[str, str]]] = defaultdict(list)
        self._sellers: dict[str, dict[str, str]] = {}
        self._load()

    def _csv(self, table: str):
        return (self.data_dir / TABLE_FILES[table]).open(encoding="utf-8", newline="")

    def _load(self) -> None:
        with self._csv("orders") as handle:
            for row in csv.DictReader(handle):
                if row["order_id"] in self.target_order_ids:
                    self._orders[row["order_id"]] = row
        with self._csv("items") as handle:
            for row in csv.DictReader(handle):
                if row["order_id"] in self.target_order_ids:
                    self._items[row["order_id"]].append(row)
        with self._csv("payments") as handle:
            for row in csv.DictReader(handle):
                if row["order_id"] in self.target_order_ids:
                    self._payments[row["order_id"]].append(row)
        required_sellers = {row["seller_id"] for rows in self._items.values() for row in rows}
        with self._csv("sellers") as handle:
            for row in csv.DictReader(handle):
                if row["seller_id"] in required_sellers:
                    self._sellers[row["seller_id"]] = row

        missing = self.target_order_ids.difference(self._orders)
        if missing:
            raise ValueError(f"Orders missing from CSV: {sorted(missing)}")

    def _authorize(self, agent: str, table: str, key: str) -> None:
        if table not in ACCESS.get(agent, frozenset()):
            raise AccessViolation(f"{agent} cannot read {table}")
        if self.on_access:
            self.on_access(agent, table, key)

    def order(self, agent: str, order_id: str) -> dict[str, str] | None:
        self._authorize(agent, "orders", order_id)
        row = self._orders.get(order_id)
        return dict(row) if row else None

    def items(self, agent: str, order_id: str) -> list[dict[str, str]]:
        self._authorize(agent, "items", order_id)
        return [dict(r) for r in sorted(self._items.get(order_id, []), key=lambda x: int(x["order_item_id"]))]

    def payments(self, agent: str, order_id: str) -> list[dict[str, str]]:
        self._authorize(agent, "payments", order_id)
        return [dict(r) for r in sorted(self._payments.get(order_id, []), key=lambda x: int(x["payment_sequential"]))]

    def seller_exists(self, agent: str, seller_id: str) -> bool:
        self._authorize(agent, "sellers", seller_id)
        return seller_id in self._sellers
