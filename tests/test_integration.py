import zipfile
from pathlib import Path

from dispute_agents.cli import package
from dispute_agents.local_grader import grade


ROOT = Path(__file__).resolve().parents[1]


def test_local_oracle_scores_all_components_100():
    report = grade(ROOT)
    assert report["score"] == 100.0
    assert report["hard_gate_count"] == 0
    assert set(report["components"].values()) == {100.0}


def test_seller_evidence_is_only_used_for_seller_late_cases():
    import json

    for path in sorted((ROOT / "output").glob("EC_*.json")):
        output = json.loads(path.read_text(encoding="utf-8"))
        has_seller_evidence = any(item.startswith("seller:") for item in output["evidence_ids"])
        assert has_seller_evidence is (output["assessment"]["primary_issue"] == "late_delivery_seller")


def test_submission_zip_has_output_prefix_and_exact_files():
    destination = ROOT / "submission.test.zip"
    try:
        package(ROOT, destination)
        with zipfile.ZipFile(destination) as archive:
            assert archive.namelist() == [f"output/EC_{i:03d}.json" for i in range(1, 51)]
    finally:
        destination.unlink(missing_ok=True)
