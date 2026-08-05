import json
from pathlib import Path

import pytest

from dispute_agents.repository import AccessViolation, CsvRepository


ROOT = Path(__file__).resolve().parents[1]


def test_repository_access_allowlist_rejects_cross_domain_read():
    repository = object.__new__(CsvRepository)
    repository.on_access = None
    with pytest.raises(AccessViolation):
        repository._authorize("payment", "orders", "order-a")


def test_latest_trace_is_valid_jsonl_and_contains_no_secret():
    path = ROOT / "logging" / "trace.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 500
    events = [json.loads(line) for line in lines]
    assert len({event["sequence"] for event in events}) == len(events)
    assert all("OPENAI_API_KEY" not in line and "sk-" not in line for line in lines)
    writes = [event for event in events if event["event_type"] == "write"]
    assert len(writes) == 50
    assert all(event["validation"].get("verifier_passed") is True for event in writes)
