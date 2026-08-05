import copy
import json
from pathlib import Path

from dispute_agents.validation import validate_input, validate_output


ROOT = Path(__file__).resolve().parents[1]


def test_official_input_is_valid():
    case = json.loads((ROOT / "input" / "EC_001.json").read_text(encoding="utf-8"))
    assert validate_input(case, "EC_001") == []


def test_generated_output_is_valid():
    output = json.loads((ROOT / "output" / "EC_001.json").read_text(encoding="utf-8"))
    assert validate_output(output, "EC_001") == []


def test_unknown_key_and_out_of_range_confidence_are_rejected():
    output = json.loads((ROOT / "output" / "EC_001.json").read_text(encoding="utf-8"))
    bad = copy.deepcopy(output)
    bad["unexpected"] = True
    assert validate_output(bad, "EC_001")
    bad = copy.deepcopy(output)
    bad["assessment"]["confidence"] = 1.1
    assert any("confidence" in error for error in validate_output(bad, "EC_001"))
