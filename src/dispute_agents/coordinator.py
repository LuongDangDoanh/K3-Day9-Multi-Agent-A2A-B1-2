"""Coordinator orchestration, handoffs, verification, and artifact writes."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .agents import DeliveryAgent, OrderSellerAgent, PaymentAgent, PolicyAgent, VerifierAgent
from .config import (
    CONFIDENCE, MODEL_NAME, MODEL_PARAMETER_COMPLIANCE, MODEL_PARAMETER_LIMIT_B,
    MODEL_PARAMETER_SIZE, MODEL_PROVIDER, POLICY_VERSION,
)
from .contracts import primitive
from .llm_audit import OpenAIAuditClient
from .money import money_float
from .repository import CsvRepository
from .tracing import TraceWriter, envelope
from .validation import validate_input


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class Coordinator:
    name = "coordinator"

    def __init__(self, root: Path, *, llm_audit: bool = False) -> None:
        self.root = root.resolve()
        self.input_dir = self.root / "input"
        self.output_dir = self.root / "output"
        self.logging_dir = self.root / "logging"
        self.run_id = str(uuid4())
        self.cases = self._load_cases()
        order_ids = [c["customer_request"]["claimed_order_id"] for c in self.cases]
        self.repository = CsvRepository(self.root / "data", order_ids)
        self.order_seller = OrderSellerAgent(self.repository)
        self.payment = PaymentAgent(self.repository)
        self.delivery = DeliveryAgent(self.repository)
        self.policy = PolicyAgent()
        self.verifier = VerifierAgent(self.repository)
        self.trace = TraceWriter(self.logging_dir / "trace.jsonl", self.run_id)
        self.llm = None
        if llm_audit:
            load_dotenv(self.root / ".env")
            self.llm = OpenAIAuditClient()
        self.llm_invocations = 0

    def _load_cases(self) -> list[dict[str, Any]]:
        expected = [f"EC_{i:03d}" for i in range(1, 51)]
        paths = sorted(self.input_dir.glob("EC_*.json"))
        if [p.stem for p in paths] != expected:
            raise ValueError("input/ must contain exactly EC_001.json through EC_050.json")
        cases = []
        for path in paths:
            case = json.loads(path.read_text(encoding="utf-8-sig"))
            errors = validate_input(case, path.stem)
            if errors:
                raise ValueError(f"Invalid {path.name}: {'; '.join(errors)}")
            cases.append(case)
        return cases

    def _handoff(
        self, *, case_id: str, trace_id: str, source: str, target: str,
        contract: str, payload: Any, data_access: list[str] | None = None,
    ) -> dict[str, Any]:
        message = envelope(
            run_id=self.run_id, trace_id=trace_id, case_id=case_id,
            source=source, target=target, contract_name=contract, payload=payload,
        )
        self.trace.event(
            case_id=case_id, trace_id=trace_id, agent=source, event_type="handoff",
            handoff=message, data_access=data_access,
        )
        return message

    @staticmethod
    def _build_output(case: dict[str, Any], order, payment, decision) -> dict[str, Any]:
        order_id = order.order_id
        item_ids = [f"{order_id}:{i.order_item_id}" for i in order.items]
        payment_ids = [f"{order_id}:{p.payment_sequential}" for p in payment.rows]
        evidence = (
            [f"order:{order_id}"]
            + [f"item:{value}" for value in item_ids]
            + [f"payment:{value}" for value in payment_ids]
            + ([f"seller:{seller_id}" for seller_id in order.seller_ids]
               if decision.primary_issue == "late_delivery_seller" else [])
            + [f"policy:{decision.cause_code}"]
        )
        return {
            "case_id": case["case_id"],
            "assessment": {
                "primary_issue": decision.primary_issue,
                "case_status": decision.case_status,
                "confidence": float(CONFIDENCE),
            },
            "affected_entities": {
                "order_ids": [order_id],
                "item_ids": item_ids[:5],
                "seller_ids": list(order.seller_ids[:5]),
                "payment_ids": payment_ids[:5],
            },
            "root_cause_analysis": {
                "ranked_causes": [{"cause_code": decision.cause_code, "rank": 1}],
                "responsible_parties": list(decision.responsible_parties[:3]),
            },
            "evidence_ids": evidence[:10],
            "financial_resolution": {
                "currency": "BRL",
                "item_total_brl": money_float(order.item_total_brl),
                "freight_total_brl": money_float(order.freight_total_brl),
                "payment_total_brl": money_float(payment.payment_total_brl),
                "recommended_refund_brl": money_float(decision.recommended_refund_brl),
            },
            "resolution_actions": list(decision.actions[:5]),
        }

    def run_case(self, case: dict[str, Any]) -> dict[str, Any]:
        case_id = case["case_id"]
        trace_id = str(uuid4())
        order_id = case["customer_request"]["claimed_order_id"]
        self._handoff(
            case_id=case_id, trace_id=trace_id, source=self.name, target="order_seller",
            contract="CaseEnvelope", payload=case,
        )
        order = self.order_seller.investigate(order_id)
        self._handoff(
            case_id=case_id, trace_id=trace_id, source="order_seller", target=self.name,
            contract="OrderSellerFinding", payload=order,
            data_access=["orders", "order_items", "sellers"],
        )
        expected_total = order.item_total_brl + order.freight_total_brl
        self._handoff(
            case_id=case_id, trace_id=trace_id, source=self.name, target="payment",
            contract="PaymentRequest", payload={"order_id": order_id, "expected_total_brl": expected_total},
        )
        payment = self.payment.reconcile(order_id, expected_total)
        self._handoff(
            case_id=case_id, trace_id=trace_id, source="payment", target=self.name,
            contract="PaymentFinding", payload=payment, data_access=["order_payments"],
        )
        self._handoff(
            case_id=case_id, trace_id=trace_id, source=self.name, target="delivery",
            contract="DeliveryRequest", payload={"order_id": order_id, "items": primitive(order.items)},
        )
        delivery = self.delivery.inspect(order_id, order.items)
        self._handoff(
            case_id=case_id, trace_id=trace_id, source="delivery", target=self.name,
            contract="DeliveryFinding", payload=delivery, data_access=["orders"],
        )
        bundle = {"order": order, "payment": payment, "delivery": delivery}
        self._handoff(
            case_id=case_id, trace_id=trace_id, source=self.name, target="policy",
            contract="PolicyBundle", payload=bundle,
        )
        decision = self.policy.decide(order, payment, delivery)
        self._handoff(
            case_id=case_id, trace_id=trace_id, source="policy", target=self.name,
            contract="ResolutionCandidate", payload=decision,
        )
        output = self._build_output(case, order, payment, decision)
        self._handoff(
            case_id=case_id, trace_id=trace_id, source=self.name, target="verifier",
            contract="ResolutionCandidate", payload=output,
        )
        report = self.verifier.verify(case, output)
        self._handoff(
            case_id=case_id, trace_id=trace_id, source="verifier", target=self.name,
            contract="VerificationReport", payload=report,
            data_access=["orders", "order_items", "order_payments", "sellers"],
        )
        if not report.passed:
            raise ValueError(f"Verifier rejected {case_id}: {'; '.join(report.errors)}")
        if self.llm:
            audit = self.llm.review(case_id, output)
            self.llm_invocations += 1
            self.trace.event(
                case_id=case_id, trace_id=trace_id, agent="llm_auditor", event_type="result",
                validation=audit,
            )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        final_path = self.output_dir / f"{case_id}.json"
        temp_path = self.output_dir / f".{case_id}.{self.run_id}.tmp"
        temp_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temp_path, final_path)
        self.trace.event(
            case_id=case_id, trace_id=trace_id, agent=self.name, event_type="write",
            validation={"verifier_passed": True}, artifact_refs=[str(final_path.relative_to(self.root))],
        )
        return output

    def run(self) -> list[dict[str, Any]]:
        outputs = [self.run_case(case) for case in self.cases]
        self._write_metadata(len(outputs))
        return outputs

    def _write_metadata(self, output_count: int) -> None:
        data_files = sorted((self.root / "data").glob("*.csv"))
        input_files = sorted(self.input_dir.glob("EC_*.json"))
        try:
            git_commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=self.root, text=True, stderr=subprocess.DEVNULL,
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            git_commit = None
        metadata = {
            "schema_version": "1.0",
            "run_id": self.run_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "policy_version": POLICY_VERSION,
            "decision_engine": "deterministic_csv_policy",
            "model": {
                "provider": MODEL_PROVIDER,
                "name": MODEL_NAME,
                "usage": "optional_structured_output_audit",
                "invocation_count": self.llm_invocations,
                "parameter_size": MODEL_PARAMETER_SIZE,
                "parameter_limit_b": MODEL_PARAMETER_LIMIT_B,
                "parameter_compliance": MODEL_PARAMETER_COMPLIANCE,
                "temperature": 0,
            },
            "framework": {"name": "custom_typed_a2a", "version": "1.0"},
            "runtime": {"python": sys.version.split()[0], "platform": platform.platform()},
            "git_commit_at_run": git_commit,
            "counts": {"inputs": len(input_files), "outputs": output_count, "trace_events": self.trace.event_count},
            "trace_path": "logging/trace.jsonl",
            "entrypoint": "python -m dispute_agents.cli run",
            "checksums": {
                "inputs_sha256": {p.name: sha256_file(p) for p in input_files},
                "datasets_sha256": {p.name: sha256_file(p) for p in data_files},
            },
        }
        path = self.logging_dir / "metadata.json"
        temp = self.logging_dir / f".metadata.{self.run_id}.tmp"
        temp.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, path)
