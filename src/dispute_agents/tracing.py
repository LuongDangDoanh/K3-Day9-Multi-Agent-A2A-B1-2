"""Latest-run JSONL trace and A2A envelope helpers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .config import CONTRACT_VERSION, PROTOCOL_VERSION
from .contracts import primitive


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(payload: Any) -> str:
    canonical = json.dumps(primitive(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def envelope(
    *, run_id: str, trace_id: str, case_id: str, source: str, target: str,
    contract_name: str, payload: Any, status: str = "success",
) -> dict[str, Any]:
    body = primitive(payload)
    return {
        "protocol_version": PROTOCOL_VERSION,
        "run_id": run_id,
        "trace_id": trace_id,
        "message_id": str(uuid4()),
        "sent_at": utc_now(),
        "from_agent": source,
        "to_agent": target,
        "case_id": case_id,
        "contract_name": contract_name,
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "payload": body,
        "payload_sha256": digest(body),
        "errors": [],
    }


class TraceWriter:
    def __init__(self, path: Path, run_id: str) -> None:
        self.path = path
        self.run_id = run_id
        self.sequence = 0
        self.event_count = 0
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    def event(
        self, *, case_id: str, trace_id: str, agent: str, event_type: str,
        status: str = "success", handoff: dict[str, Any] | None = None,
        validation: dict[str, Any] | None = None, artifact_refs: list[str] | None = None,
        data_access: list[str] | None = None, error: str | None = None,
    ) -> None:
        self.sequence += 1
        self.event_count += 1
        record = {
            "schema_version": "1.0",
            "run_id": self.run_id,
            "trace_id": trace_id,
            "span_id": str(uuid4()),
            "parent_span_id": None,
            "sequence": self.sequence,
            "timestamp_utc": utc_now(),
            "case_id": case_id,
            "agent": agent,
            "event_type": event_type,
            "status": status,
            "from_agent": handoff.get("from_agent") if handoff else None,
            "to_agent": handoff.get("to_agent") if handoff else None,
            "contract_name": handoff.get("contract_name") if handoff else None,
            "contract_version": handoff.get("contract_version") if handoff else None,
            "input_digest": None,
            "output_digest": handoff.get("payload_sha256") if handoff else None,
            "data_access": data_access or [],
            "model": None,
            "token_usage": None,
            "latency_ms": None,
            "validation": validation or {},
            "artifact_refs": artifact_refs or [],
            "error": error,
        }
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
