"""Strict input/output shape checks used before business verification."""

from __future__ import annotations

import math
import re
from typing import Any


ISSUES = {
    "canceled_order_paid", "unavailable_order_paid", "late_delivery_seller",
    "late_delivery_logistics", "valid_split_payment", "unsupported_late_claim",
}
CAUSES = {
    "SELLER_HANDOFF_AFTER_LIMIT", "CARRIER_DELIVERED_AFTER_ESTIMATE",
    "ORDER_CANCELED_AFTER_PAYMENT", "ORDER_UNAVAILABLE_AFTER_PAYMENT",
    "MULTIPLE_PAYMENTS_RECONCILED", "DELIVERY_WITHIN_ESTIMATE",
}
ACTIONS = {
    "issue_full_refund", "refund_freight", "explain_valid_split_payment", "reject_late_refund",
}
PARTY_TYPES = {"seller", "platform", "logistics_provider"}

TOP_KEYS = {
    "case_id", "assessment", "affected_entities", "root_cause_analysis",
    "evidence_ids", "financial_resolution", "resolution_actions",
}


def _exact_keys(value: Any, keys: set[str], label: str, errors: list[str]) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return False
    if set(value) != keys:
        errors.append(f"{label} keys mismatch: {sorted(set(value) ^ keys)}")
        return False
    return True


def _unique_strings(value: Any, label: str, maximum: int, errors: list[str]) -> None:
    if not isinstance(value, list) or len(value) > maximum:
        errors.append(f"{label} must be an array with at most {maximum} entries")
        return
    if any(not isinstance(v, str) or not v for v in value):
        errors.append(f"{label} entries must be non-empty strings")
    if len(value) != len(set(value)):
        errors.append(f"{label} entries must be unique")


def validate_input(case: Any, expected_case_id: str | None = None) -> list[str]:
    errors: list[str] = []
    if not _exact_keys(case, {"case_id", "opened_at", "customer_request", "policy_version"}, "input", errors):
        return errors
    if expected_case_id and case["case_id"] != expected_case_id:
        errors.append("input case_id does not match filename")
    req = case["customer_request"]
    if _exact_keys(req, {"language", "message", "claimed_order_id"}, "customer_request", errors):
        if req["language"] != "vi":
            errors.append("customer_request.language must be vi")
        if not isinstance(req["message"], str) or not req["message"]:
            errors.append("customer_request.message must be non-empty")
        if not isinstance(req["claimed_order_id"], str) or not re.fullmatch(r"[0-9a-f]{32}", req["claimed_order_id"]):
            errors.append("claimed_order_id must be a 32-character lowercase hex ID")
    if case["policy_version"] != "EC_POLICY_V1":
        errors.append("unsupported policy_version")
    return errors


def validate_output(output: Any, expected_case_id: str | None = None) -> list[str]:
    errors: list[str] = []
    if not _exact_keys(output, TOP_KEYS, "output", errors):
        return errors
    if not isinstance(output["case_id"], str) or (expected_case_id and output["case_id"] != expected_case_id):
        errors.append("output case_id does not match filename/input")

    assessment = output["assessment"]
    if _exact_keys(assessment, {"primary_issue", "case_status", "confidence"}, "assessment", errors):
        if assessment["primary_issue"] not in ISSUES:
            errors.append("invalid primary_issue")
        if assessment["case_status"] not in {"action_required", "no_action"}:
            errors.append("invalid case_status")
        confidence = assessment["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
            errors.append("confidence must be finite and in [0,1]")

    entities = output["affected_entities"]
    if _exact_keys(entities, {"order_ids", "item_ids", "seller_ids", "payment_ids"}, "affected_entities", errors):
        for name in ("order_ids", "item_ids", "seller_ids", "payment_ids"):
            _unique_strings(entities[name], f"affected_entities.{name}", 5, errors)

    root = output["root_cause_analysis"]
    if _exact_keys(root, {"ranked_causes", "responsible_parties"}, "root_cause_analysis", errors):
        causes = root["ranked_causes"]
        if not isinstance(causes, list) or not 1 <= len(causes) <= 3:
            errors.append("ranked_causes must contain 1..3 entries")
        else:
            for idx, cause in enumerate(causes, 1):
                if not _exact_keys(cause, {"cause_code", "rank"}, f"ranked_causes[{idx}]", errors):
                    continue
                if cause["cause_code"] not in CAUSES or cause["rank"] != idx:
                    errors.append(f"invalid ranked_causes[{idx}]")
        parties = root["responsible_parties"]
        if not isinstance(parties, list) or len(parties) > 3:
            errors.append("responsible_parties must have at most 3 entries")
        else:
            for idx, party in enumerate(parties):
                if _exact_keys(party, {"party_type", "party_id"}, f"responsible_parties[{idx}]", errors):
                    if party["party_type"] not in PARTY_TYPES or not isinstance(party["party_id"], str):
                        errors.append(f"invalid responsible_parties[{idx}]")

    _unique_strings(output["evidence_ids"], "evidence_ids", 10, errors)
    financial = output["financial_resolution"]
    money_keys = {"item_total_brl", "freight_total_brl", "payment_total_brl", "recommended_refund_brl"}
    if _exact_keys(financial, {"currency", *money_keys}, "financial_resolution", errors):
        if financial["currency"] != "BRL":
            errors.append("currency must be BRL")
        for key in money_keys:
            value = financial[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                errors.append(f"{key} must be a finite nonnegative number")
            elif round(value, 2) != value:
                errors.append(f"{key} must have at most two decimal places")
    actions = output["resolution_actions"]
    _unique_strings(actions, "resolution_actions", 5, errors)
    if isinstance(actions, list) and any(a not in ACTIONS for a in actions):
        errors.append("invalid resolution action")
    return errors
