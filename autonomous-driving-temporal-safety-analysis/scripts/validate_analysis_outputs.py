#!/usr/bin/env python3
"""Validate the minimum six-layer analysis artifact contract."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


REQUIRED_FILES = {
    "report/six_layer_analysis_report.md",
    "tables/run_level_observed.csv",
    "tables/run_level_model_predicted.csv",
    "tables/layer_evidence_matrix.csv",
    "tables/event_timeline.csv",
    "tables/stage_timing_and_freshness.csv",
    "tables/record_timing_diagnostics.csv",
    "tables/group_summary_observed.csv",
    "tables/exclusions_and_missing.csv",
    "validation/input_inventory.json",
    "validation/data_quality_audit.md",
}

OBSERVED_REQUIRED_COLUMNS = {
    "run_id",
    "analysis_status",
    "T_e2e_data_observed_ms",
    "D_delay_wall_integral_data_observed_m",
    "time_basis_main",
}

EVIDENCE_REQUIRED_COLUMNS = {
    "layer",
    "metric",
    "run_id_or_group",
    "evidence_type",
    "time_basis",
    "source_file",
    "availability",
}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def nonempty(value: Any) -> bool:
    return str(value or "").strip().lower() not in {"", "na", "nan", "none", "null"}


def validate(root: Path) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    for relative in sorted(REQUIRED_FILES):
        path = root / relative
        if not path.exists():
            errors.append({"check": "required_file", "path": relative, "message": "missing"})

    observed_path = root / "tables/run_level_observed.csv"
    observed_columns, observed_rows = read_csv(observed_path)
    missing_columns = sorted(OBSERVED_REQUIRED_COLUMNS - set(observed_columns))
    if missing_columns:
        errors.append(
            {
                "check": "observed_schema",
                "path": str(observed_path),
                "message": f"missing columns: {', '.join(missing_columns)}",
            }
        )
    forbidden_observed = [
        column
        for column in observed_columns
        if "model_predicted" in column.lower() or column.lower().endswith("_model")
    ]
    if forbidden_observed:
        errors.append(
            {
                "check": "observed_model_separation",
                "path": str(observed_path),
                "message": f"model columns found in observed table: {forbidden_observed}",
            }
        )

    for index, row in enumerate(observed_rows, start=2):
        run_id = row.get("run_id", f"row-{index}")
        status = (row.get("analysis_status") or "").strip().upper()
        included = (row.get("included_main_analysis") or "").strip().lower()
        reason = row.get("missing_reason") or row.get("exclusion_reason")
        if (included in {"false", "0", "no"} or status not in {"ANALYZED", "AVAILABLE"}) and not nonempty(reason):
            warnings.append(
                {
                    "check": "missing_or_exclusion_reason",
                    "path": str(observed_path),
                    "message": f"run {run_id} has status={status!r}, included={included!r}, but no reason",
                }
            )
        collision = (row.get("collision_event_data_observed") or "").strip().lower()
        full_brake = row.get("D_brake_data_observed_m")
        if collision in {"true", "1", "yes"} and nonempty(full_brake):
            warnings.append(
                {
                    "check": "collision_full_stop_claim",
                    "path": str(observed_path),
                    "message": (
                        f"run {run_id} is an observed collision but has full observed braking "
                        "distance; verify that the endpoint is not merely truncated to collision"
                    ),
                }
            )

    model_path = root / "tables/run_level_model_predicted.csv"
    model_columns, _ = read_csv(model_path)
    if model_columns and not any(
        "model" in column.lower() or "predicted" in column.lower() for column in model_columns
    ):
        errors.append(
            {
                "check": "model_schema",
                "path": str(model_path),
                "message": "model table has no explicitly model/predicted column",
            }
        )

    evidence_path = root / "tables/layer_evidence_matrix.csv"
    evidence_columns, evidence_rows = read_csv(evidence_path)
    missing_evidence = sorted(EVIDENCE_REQUIRED_COLUMNS - set(evidence_columns))
    if missing_evidence:
        errors.append(
            {
                "check": "evidence_schema",
                "path": str(evidence_path),
                "message": f"missing columns: {', '.join(missing_evidence)}",
            }
        )
    layers = {row.get("layer", "").strip().upper() for row in evidence_rows}
    absent_layers = sorted({f"L{index}" for index in range(1, 7)} - layers)
    if absent_layers:
        errors.append(
            {
                "check": "six_layer_coverage",
                "path": str(evidence_path),
                "message": f"layers without evidence/unavailable rows: {', '.join(absent_layers)}",
            }
        )

    report_path = root / "report/six_layer_analysis_report.md"
    if report_path.exists():
        report = report_path.read_text(encoding="utf-8", errors="replace")
        for required_text in (
            "L1",
            "L2",
            "L3",
            "L4",
            "L5",
            "L6",
            "observed",
            "model",
        ):
            if required_text.lower() not in report.lower():
                warnings.append(
                    {
                        "check": "report_content",
                        "path": str(report_path),
                        "message": f"report does not contain marker {required_text!r}",
                    }
                )

    return {
        "analysis_dir": str(root.resolve()),
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "observed_run_count": len(observed_rows),
            "evidence_row_count": len(evidence_rows),
            "required_file_count": len(REQUIRED_FILES),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate six-layer analysis outputs")
    parser.add_argument("--analysis-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.analysis_dir.resolve()
    result = validate(root)
    output = root / "validation/validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
