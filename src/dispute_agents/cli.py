from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from .coordinator import Coordinator
from .local_grader import grade


def _root(value: str | None) -> Path:
    return Path(value).resolve() if value else Path.cwd().resolve()


def package(root: Path, destination: Path) -> None:
    names = [f"EC_{i:03d}.json" for i in range(1, 51)]
    actual = sorted(p.name for p in (root / "output").glob("*.json"))
    if actual != names:
        raise ValueError("output/ must contain exactly EC_001.json through EC_050.json")
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in names:
            archive.write(root / "output" / name, arcname=f"output/{name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="K3 Olist multi-agent workflow")
    parser.add_argument("--root", help="Repository root (default: current directory)")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run", help="Run all 50 cases and overwrite latest trace")
    run_parser.add_argument("--llm-audit", action="store_true", help="Call gpt-4o-mini once per case for a non-authoritative structured audit")
    sub.add_parser("grade", help="Run strict local README/CSV oracle grader")
    pack_parser = sub.add_parser("package", help="Create a 50-JSON ZIP under output/")
    pack_parser.add_argument("--destination", default="submission.zip")
    args = parser.parse_args(argv)
    root = _root(args.root)
    if args.command == "run":
        outputs = Coordinator(root, llm_audit=args.llm_audit).run()
        print(json.dumps({"status": "ok", "outputs": len(outputs)}, ensure_ascii=False))
    elif args.command == "grade":
        report = grade(root)
        print(json.dumps({k: v for k, v in report.items() if k != "cases"}, ensure_ascii=False, indent=2))
        return 0 if report["score"] == 100.0 and report["hard_gate_count"] == 0 else 1
    elif args.command == "package":
        destination = (root / args.destination).resolve()
        package(root, destination)
        print(json.dumps({"status": "ok", "zip": str(destination)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
