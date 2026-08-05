from __future__ import annotations

from decimal import Decimal

from ..config import PAYMENT_TOLERANCE
from ..contracts import VerificationReport
from ..money import csv_timestamp, money, money_float
from ..repository import CsvRepository
from ..validation import validate_output


class VerifierAgent:
    """Independently re-query source rows and reject any inconsistent output."""

    name = "verifier"

    def __init__(self, repository: CsvRepository) -> None:
        self.repository = repository

    def verify(self, case: dict, output: dict) -> VerificationReport:
        case_id = case["case_id"]
        order_id = case["customer_request"]["claimed_order_id"]
        errors = validate_output(output, case_id)
        checks = {"schema": not errors}
        order = self.repository.order(self.name, order_id)
        items = self.repository.items(self.name, order_id)
        payments = self.repository.payments(self.name, order_id)
        for seller_id in {i["seller_id"] for i in items}:
            if not self.repository.seller_exists(self.name, seller_id):
                errors.append(f"seller evidence does not resolve: {seller_id}")
        if order is None:
            errors.append(f"order does not resolve: {order_id}")
            return VerificationReport(False, {**checks, "source_rows": False}, tuple(errors))
        checks["source_rows"] = True

        item_total = money(sum((money(i["price"]) for i in items), Decimal("0")))
        freight_total = money(sum((money(i["freight_value"]) for i in items), Decimal("0")))
        payment_total = money(sum((money(p["payment_value"]) for p in payments), Decimal("0")))
        reconciled = abs(money(payment_total - money(item_total + freight_total))) <= PAYMENT_TOLERANCE
        carrier = csv_timestamp(order["order_delivered_carrier_date"])
        delivered = csv_timestamp(order["order_delivered_customer_date"])
        estimated = csv_timestamp(order["order_estimated_delivery_date"])
        late = delivered is not None and estimated is not None and delivered > estimated
        violating_sellers = sorted({
            i["seller_id"] for i in items
            if carrier is not None and csv_timestamp(i["shipping_limit_date"]) is not None
            and carrier > csv_timestamp(i["shipping_limit_date"])
        })

        if order["order_status"] == "canceled" and payment_total > 0:
            expected = ("canceled_order_paid", "ORDER_CANCELED_AFTER_PAYMENT", "action_required", payment_total,
                        [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}], ["issue_full_refund"])
        elif order["order_status"] == "unavailable" and payment_total > 0:
            expected = ("unavailable_order_paid", "ORDER_UNAVAILABLE_AFTER_PAYMENT", "action_required", payment_total,
                        [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}], ["issue_full_refund"])
        elif late and violating_sellers:
            expected = ("late_delivery_seller", "SELLER_HANDOFF_AFTER_LIMIT", "action_required", freight_total,
                        [{"party_type": "seller", "party_id": sid} for sid in violating_sellers], ["refund_freight"])
        elif late:
            expected = ("late_delivery_logistics", "CARRIER_DELIVERED_AFTER_ESTIMATE", "action_required", freight_total,
                        [{"party_type": "logistics_provider", "party_id": "LOGISTICS_PROVIDER"}], ["refund_freight"])
        elif len(payments) >= 2 and reconciled:
            expected = ("valid_split_payment", "MULTIPLE_PAYMENTS_RECONCILED", "no_action", money(0), [],
                        ["explain_valid_split_payment"])
        elif delivered is not None and estimated is not None and delivered <= estimated and reconciled:
            expected = ("unsupported_late_claim", "DELIVERY_WITHIN_ESTIMATE", "no_action", money(0), [],
                        ["reject_late_refund"])
        else:
            errors.append("independent verifier found no policy match")
            return VerificationReport(False, {**checks, "business_policy": False}, tuple(errors))

        issue, cause, status, refund, parties, actions = expected
        entities = {
            "order_ids": [order_id],
            "item_ids": [f"{order_id}:{i['order_item_id']}" for i in items],
            "seller_ids": sorted({i["seller_id"] for i in items}),
            "payment_ids": [f"{order_id}:{p['payment_sequential']}" for p in payments],
        }
        evidence = (
            [f"order:{order_id}"]
            + [f"item:{order_id}:{i['order_item_id']}" for i in items]
            + [f"payment:{order_id}:{p['payment_sequential']}" for p in payments]
            + ([f"seller:{sid}" for sid in entities["seller_ids"]]
               if issue == "late_delivery_seller" else [])
            + [f"policy:{cause}"]
        )
        expected_financial = {
            "currency": "BRL",
            "item_total_brl": money_float(item_total),
            "freight_total_brl": money_float(freight_total),
            "payment_total_brl": money_float(payment_total),
            "recommended_refund_brl": money_float(refund),
        }
        comparisons = {
            "assessment": output.get("assessment", {}).get("primary_issue") == issue
                and output.get("assessment", {}).get("case_status") == status,
            "entities": output.get("affected_entities") == entities,
            "root": output.get("root_cause_analysis") == {
                "ranked_causes": [{"cause_code": cause, "rank": 1}],
                "responsible_parties": parties,
            },
            "evidence": output.get("evidence_ids") == evidence,
            "financial": output.get("financial_resolution") == expected_financial,
            "actions": output.get("resolution_actions") == actions,
        }
        checks.update(comparisons)
        for label, passed in comparisons.items():
            if not passed:
                errors.append(f"{label} does not match independent CSV/policy computation")
        return VerificationReport(not errors, checks, tuple(errors))
