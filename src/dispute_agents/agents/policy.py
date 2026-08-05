from __future__ import annotations

from ..contracts import DeliveryFinding, OrderSellerFinding, PaymentFinding, ResolutionCandidate
from ..money import money


class PolicyAgent:
    name = "policy"

    def decide(
        self,
        order: OrderSellerFinding,
        payment: PaymentFinding,
        delivery: DeliveryFinding,
    ) -> ResolutionCandidate:
        if order.order_status == "canceled" and payment.payment_total_brl > 0:
            return ResolutionCandidate(
                "canceled_order_paid", "action_required", "ORDER_CANCELED_AFTER_PAYMENT",
                ({"party_type": "platform", "party_id": "OLIST_PLATFORM"},),
                payment.payment_total_brl, ("issue_full_refund",),
            )
        if order.order_status == "unavailable" and payment.payment_total_brl > 0:
            return ResolutionCandidate(
                "unavailable_order_paid", "action_required", "ORDER_UNAVAILABLE_AFTER_PAYMENT",
                ({"party_type": "platform", "party_id": "OLIST_PLATFORM"},),
                payment.payment_total_brl, ("issue_full_refund",),
            )
        if delivery.delivered_late and delivery.violating_seller_ids:
            parties = tuple(
                {"party_type": "seller", "party_id": sid}
                for sid in delivery.violating_seller_ids
            )
            return ResolutionCandidate(
                "late_delivery_seller", "action_required", "SELLER_HANDOFF_AFTER_LIMIT",
                parties, order.freight_total_brl, ("refund_freight",),
            )
        if delivery.delivered_late:
            return ResolutionCandidate(
                "late_delivery_logistics", "action_required", "CARRIER_DELIVERED_AFTER_ESTIMATE",
                ({"party_type": "logistics_provider", "party_id": "LOGISTICS_PROVIDER"},),
                order.freight_total_brl, ("refund_freight",),
            )
        if len(payment.rows) >= 2 and payment.reconciled:
            return ResolutionCandidate(
                "valid_split_payment", "no_action", "MULTIPLE_PAYMENTS_RECONCILED",
                (), money(0), ("explain_valid_split_payment",),
            )
        delivered = delivery.delivered_customer_date
        estimated = delivery.estimated_delivery_date
        if delivered and estimated and not delivery.delivered_late and payment.reconciled:
            return ResolutionCandidate(
                "unsupported_late_claim", "no_action", "DELIVERY_WITHIN_ESTIMATE",
                (), money(0), ("reject_late_refund",),
            )
        raise ValueError(f"No EC_POLICY_V1 rule matched order {order.order_id}")
