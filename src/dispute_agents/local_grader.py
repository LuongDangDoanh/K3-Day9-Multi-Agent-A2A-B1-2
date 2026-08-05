"""Conservative local replica of the public K3 rubric.

The exact server-side partial-match formulas and hard-gate implementation are
not public. This grader recomputes the oracle from the README and CSV data and
requires exact component equality, which is stricter than partial credit.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agents.verifier import VerifierAgent
from .repository import CsvRepository
from .validation import validate_input, validate_output

WEIGHTS = {"assessment": 0.20, "entities": 0.20, "root": 0.15, "evidence": 0.15, "financial": 0.20, "actions": 0.10}


def grade(root: Path) -> dict[str, Any]:
    expected_names = [f"EC_{i:03d}.json" for i in range(1, 51)]
    input_paths = sorted((root / "input").glob("EC_*.json"))
    output_paths = sorted((root / "output").glob("EC_*.json"))
    archive_gate = [p.name for p in output_paths] == expected_names
    cases = {}
    hard_gate_errors: list[str] = []
    for path in input_paths:
        case = json.loads(path.read_text(encoding="utf-8-sig"))
        errors = validate_input(case, path.stem)
        if errors:
            hard_gate_errors.extend(f"{path.name}: {e}" for e in errors)
        cases[path.stem] = case
    if sorted(f"{key}.json" for key in cases) != expected_names:
        hard_gate_errors.append("input set is not exactly EC_001..EC_050")
    repository = CsvRepository(root / "data", [c["customer_request"]["claimed_order_id"] for c in cases.values()])
    verifier = VerifierAgent(repository)
    component_totals = {key: 0.0 for key in WEIGHTS}
    per_case = []
    hard_gate_count = 0
    for name in expected_names:
        case_id = name[:-5]
        path = root / "output" / name
        if not path.exists() or case_id not in cases:
            hard_gate_count += 1
            per_case.append({"case_id": case_id, "score": 0.0, "errors": ["missing input/output"]})
            continue
        try:
            output = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            hard_gate_count += 1
            per_case.append({"case_id": case_id, "score": 0.0, "errors": [f"invalid JSON: {exc}"]})
            continue
        schema_errors = validate_output(output, case_id)
        if schema_errors:
            hard_gate_count += 1
            per_case.append({"case_id": case_id, "score": 0.0, "errors": schema_errors})
            continue
        report = verifier.verify(cases[case_id], output)
        components = {key: 100.0 if report.checks.get(key, False) else 0.0 for key in WEIGHTS}
        for key, value in components.items():
            component_totals[key] += value
        score = sum(components[key] * WEIGHTS[key] for key in WEIGHTS)
        per_case.append({"case_id": case_id, "score": score, "components": components, "errors": list(report.errors)})
    component_means = {key: round(value / 50, 4) for key, value in component_totals.items()}
    final_score = round(sum(item["score"] for item in per_case) / 50, 4)
    return {
        "score": final_score if archive_gate and not hard_gate_errors else 0.0,
        "computed_score_before_global_gate": final_score,
        "hard_gate_count": hard_gate_count,
        "global_gate_passed": archive_gate and not hard_gate_errors,
        "components": component_means,
        "errors": hard_gate_errors,
        "cases": per_case,
        "disclaimer": "Exact private server partial-scoring and hard-gate code is unavailable; this is a strict README/CSV oracle.",
    }
