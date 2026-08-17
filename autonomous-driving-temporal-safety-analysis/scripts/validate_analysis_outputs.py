#!/usr/bin/env python3
"""Validate TCPS-PA v2.1 artifacts as schemas, computations, and arguments."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Set, Tuple

from inference_core import claim_audit_markdown, validate_argument_rows
from construct_dynamic_deadline import construct_row
from recompute_l5_metrics import recompute_analysis


REQUIRED_FILES = {
    "report/six_layer_analysis_report.md",
    "tables/run_level_observed.csv",
    "tables/run_level_model_predicted.csv",
    "tables/evidence_ledger.csv",
    "tables/claim_ledger.csv",
    "tables/claim_edges.csv",
    "tables/defeater_ledger.csv",
    "tables/temporal_fault_signature.csv",
    "tables/pre_hazard_state_audit.csv",
    "tables/functional_correctness_audit.csv",
    "tables/clock_alignment_audit.csv",
    "tables/phase_audit.csv",
    "tables/dynamic_deadline_construction.csv",
    "tables/velocity_trajectory_observed.csv",
    "tables/l5_recomputation.csv",
    "tables/diagnosis_hypothesis_ledger.csv",
    "tables/diagnosis_edges.csv",
    "tables/requirement_registry.csv",
    "tables/event_timeline.csv",
    "tables/stage_timing_and_freshness.csv",
    "tables/record_timing_diagnostics.csv",
    "tables/group_summary_observed.csv",
    "tables/realtime_rag_summary.csv",
    "tables/space_budget_decomposition_observed.csv",
    "tables/space_budget_group_decomposition.csv",
    "tables/method_completeness_matrix.csv",
    "tables/exclusions_and_missing.csv",
    "validation/input_inventory.json",
    "validation/data_quality_audit.md",
}

OBSERVED_REQUIRED_COLUMNS = {
    "run_id", "analysis_status", "T_e2e_data_observed_ms", "time_basis_main",
}

EVIDENCE_MATRIX_REQUIRED_COLUMNS = {
    "layer", "metric", "run_id_or_group", "evidence_type", "time_basis",
    "source_file", "availability",
}

SCHEMAS: Dict[str, Set[str]] = {
    "tables/evidence_ledger.csv": {
        "evidence_id", "run_id", "layer", "metric", "value", "unit",
        "evidence_class", "clock_domain", "source_file", "source_locator",
        "availability", "confidence", "supports_claim_ids", "challenges_claim_ids",
        "limitations", "semantic_role",
    },
    "tables/claim_ledger.csv": {
        "claim_id", "layer", "run_id_or_group", "proposition",
        "prerequisite_claim_ids", "required_evidence_classes",
        "supporting_evidence_ids", "challenging_evidence_ids", "defeater_ids",
        "inference_rule_id", "verdict", "confidence", "confidence_ceiling",
        "maximum_claim_level", "residual_uncertainty", "allowed_language",
        "forbidden_language", "gate_inputs", "gate_metrics",
        "admissible_evidence", "gate_criterion", "next_gate_condition",
    },
    "tables/claim_edges.csv": {
        "parent_claim_id", "child_claim_id", "relation", "required", "notes",
    },
    "tables/defeater_ledger.csv": {
        "defeater_id", "claim_id", "description", "type", "evidence_ids",
        "status", "resolution", "residual_risk", "impact_on_claim", "notes",
    },
    "tables/temporal_fault_signature.csv": {
        "run_id", "fault_type", "injection_location", "requested_magnitude",
        "actual_magnitude", "actual_distribution", "fault_onset_wall",
        "fault_end_wall", "t1_wall", "trigger_relative_t1_s", "duration",
        "persistent_or_transient", "one_shot_or_repeated", "affected_channel",
        "affected_message_count", "queue_behavior", "drop_status", "reorder_status",
        "evidence_class", "confidence",
    },
    "tables/pre_hazard_state_audit.csv": {
        "run_id", "state_variable", "window_start_wall", "window_end_wall",
        "value_at_fault", "value_at_t1", "delta", "source_file", "availability",
        "causal_role", "evidence_class", "confidence", "notes",
    },
    "tables/functional_correctness_audit.csv": {
        "run_id", "physical_target_identity", "perception_target_present",
        "perception_tracking_continuity", "prediction_target_present",
        "prediction_semantics_valid", "planning_stop_present",
        "planning_stop_target_correct", "planning_stop_location_reasonable",
        "planning_trajectory_valid", "planning_fallback_status",
        "control_received_relevant_trajectory", "control_braking_command_present",
        "control_command_continuity", "bridge_payload_received",
        "bridge_payload_applied", "physical_response_observed", "p_func_verdict",
        "confidence", "source_evidence_ids", "notes",
    },
    "tables/clock_alignment_audit.csv": {
        "run_id_or_group", "clock_domain", "host", "timestamp_type", "sync_method",
        "offset_estimate_ms", "offset_bound_ms", "drift_estimate_ppm",
        "dispersion_or_sync_distance_ms", "alignment_residual_ms",
        "timestamp_resolution_ms", "measurement_window", "source_evidence_ids",
        "confidence", "p_clock_verdict", "notes",
    },
    "tables/phase_audit.csv": {
        "run_id_or_group", "producer_period_ms", "consumer_period_ms",
        "bridge_tick_period_ms", "phase_definition", "phase_bins_or_offsets",
        "scan_performed", "matched_repeats_per_phase", "phase_effect_metric",
        "phase_effect_estimate", "uncertainty_interval", "phase_effect_verdict",
        "source_evidence_ids", "p_phase_verdict", "notes",
    },
    "tables/dynamic_deadline_construction.csv": {
        "construction_id", "requirement_id", "run_id_or_group", "method",
        "method_version", "state_time", "state_time_basis", "state_available_by_t1",
        "input_cutoff_time", "latest_input_time", "input_provenance_json",
        "parameter_selection_time", "parameter_selection_locked_by_t1",
        "current_run_post_t1_data_used", "current_run_outcome_used",
        "d_clear_m", "v_ego_mps", "v_front_mps", "d_safe_m",
        "a_ego_response_max_mps2", "b_ego_min_mps2", "b_front_max_mps2",
        "parameter_bounds_json", "uncertainty_method", "uncertainty_sample_count",
        "braking_envelope_id", "braking_envelope_provenance",
        "braking_envelope_status", "validation_dataset_independent",
        "validation_scope", "target_motion_assumption", "road_condition_assumption",
        "calibration_run_ids", "evaluation_run_ids",
        "tau_req_low_ms", "tau_req_center_ms", "tau_req_high_ms",
        "parameter_bounds_complete", "construction_status", "qualification",
        "source_evidence_ids", "notes",
    },
    "tables/velocity_trajectory_observed.csv": {
        "run_id", "sample_index", "t_wall_s", "speed_mps", "clock_domain",
        "source_file", "source_locator", "availability", "quality_flags",
    },
    "tables/l5_recomputation.csv": {
        "run_id", "requirement_id", "t1_wall_s", "t_deadline_wall_s", "te_wall_s",
        "D_response_recomputed_m", "D_debt_recomputed_m", "D_response_reported_m",
        "D_debt_reported_m", "D1_observed_m", "D_brake_observed_m",
        "M0_recomputed_m", "M0_reported_m", "endpoint_coverage", "max_abs_error_m",
        "tolerance_m", "recomputation_status", "notes",
    },
    "tables/diagnosis_hypothesis_ledger.csv": {
        "hypothesis_id", "run_id_or_group", "seed_claim_id", "seed_evidence_ids",
        "candidate_layer", "candidate_component", "candidate_fault_type", "hypothesis",
        "path_claim_ids", "supporting_evidence_ids", "challenging_evidence_ids",
        "alternative_hypothesis_ids", "required_prerequisite_claim_ids",
        "diagnosability_class", "equivalence_class_id", "status", "rank_score",
        "rank_method", "maximum_diagnosis_strength", "discriminating_test",
        "residual_uncertainty", "allowed_language", "forbidden_language",
    },
    "tables/diagnosis_edges.csv": {
        "parent_id", "child_id", "relation", "time_direction", "required", "notes",
    },
    "tables/requirement_registry.csv": {
        "requirement_id", "run_id_or_group", "requirement_name", "requirement_value",
        "unit", "requirement_provenance", "pre_registered", "external_or_internal",
        "safety_meaning", "deadline_type", "evidence_class", "tau_req_low_ms",
        "tau_req_center_ms", "tau_req_high_ms", "validation_scope",
        "p_deadline_qualification", "notes",
    },
    "tables/realtime_rag_summary.csv": {
        "dimension", "metric", "source_column", "unit", "semantics",
        "group_name", "n_total_runs", "n_available_runs", "p50", "p90",
        "p95", "p99", "max", "iqr",
    },
    "tables/space_budget_decomposition_observed.csv": {
        "run_id", "group_name", "included_main_analysis",
        "outcome_data_observed", "D1_clear_data_observed_m",
        "D_response_wall_integral_data_observed_m", "D_brake_data_observed_m",
        "M0_recomputed_observed_m", "endpoint_compatible_full_stop",
        "decomposition_scope",
    },
    "tables/space_budget_group_decomposition.csv": {
        "comparison_group", "n", "D1_mean_m", "D_response_mean_m",
        "D_brake_mean_m", "M0_mean_m",
    },
    "tables/method_completeness_matrix.csv": {
        "requirement", "status", "evidence_or_gap",
    },
}


def read_csv(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def nonempty(value: Any) -> bool:
    return str(value or "").strip().lower() not in {"", "na", "nan", "none", "null"}


def add_schema_error(
    errors: List[Dict[str, str]], relative: str, columns: Sequence[str], required: Set[str]
) -> None:
    missing = sorted(required - set(columns))
    if missing:
        errors.append(
            {"check": "schema", "path": relative,
             "message": "missing columns: %s" % ", ".join(missing)}
        )


def validate_record_only(root: Path) -> Dict[str, Any]:
    """Validate a reduced Apollo-record availability audit without fake physics tables."""

    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []
    profiles_dir = root / "record_profiles"
    profile_paths = sorted(profiles_dir.glob("*.json")) if profiles_dir.exists() else []
    diagnostics = root / "tables/record_timing_diagnostics.csv"
    if not profile_paths:
        errors.append(
            {"check": "record_profile", "path": str(profiles_dir),
             "message": "no record profile JSON files found"}
        )
    if not diagnostics.exists():
        errors.append(
            {"check": "record_diagnostics", "path": str(diagnostics), "message": "missing"}
        )
    else:
        diagnostic_columns, _diagnostic_rows = read_csv(diagnostics)
        required_diagnostic_columns = {
            "run_id", "record_dir", "record_evidence_class",
            "l2_reference_qualification", "l3_causal_lineage_grade",
        }
        missing_diagnostic_columns = sorted(
            required_diagnostic_columns - set(diagnostic_columns)
        )
        if missing_diagnostic_columns:
            errors.append(
                {"check": "record_diagnostics_schema", "path": str(diagnostics),
                 "message": "missing columns: %s" % ", ".join(missing_diagnostic_columns)}
            )

    for path in profile_paths:
        try:
            profile = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(
                {"check": "record_profile_json", "path": str(path), "message": str(exc)}
            )
            continue
        if profile.get("evidence_class") != "OBSERVED_DERIVED":
            errors.append(
                {"check": "record_evidence_class", "path": str(path),
                 "message": "record profile must be OBSERVED_DERIVED diagnostic evidence"}
            )
        eligibility = profile.get("claim_eligibility") or {}
        expected_eligibility = "NOT_TESTABLE_FROM_RECORD_PROFILE_ALONE"
        for claim_id in ("C4", "C5", "C6"):
            verdict = str(eligibility.get(claim_id) or "").upper()
            if verdict != expected_eligibility:
                errors.append(
                    {"check": "record_claim_ceiling", "path": str(path),
                     "message": "%s must equal %s" % (claim_id, expected_eligibility)}
                )
        warning = str(profile.get("scope_warning") or "")
        if not warning:
            errors.append(
                {"check": "record_scope_warning", "path": str(path), "message": "missing"}
            )

    # A reduced-mode caller may still place claims/report beside the profile.
    # Validate those artifacts rather than silently ignoring contradictory claims.
    claim_path = root / "tables/claim_ledger.csv"
    if claim_path.exists():
        _columns, claim_rows = read_csv(claim_path)
        for row in claim_rows:
            base = str(row.get("claim_id") or "").split(".", 1)[0].upper()
            verdict = str(row.get("verdict") or "").upper()
            if base in {"C4", "C5", "C6"} and verdict != "NOT_TESTABLE":
                errors.append(
                    {"check": "record_claim_ledger_ceiling", "path": str(claim_path),
                     "message": "%s must be NOT_TESTABLE in record-only mode" % row.get("claim_id")}
                )
            if base == "C7":
                level = row.get("maximum_claim_level")
                try:
                    exceeds = float(str(level)) > 2
                except (TypeError, ValueError):
                    exceeds = True
                if verdict not in {"NOT_TESTABLE", "UNCERTAIN"} or exceeds:
                    errors.append(
                        {"check": "record_attribution_ceiling", "path": str(claim_path),
                         "message": "C7 must be NOT_TESTABLE/UNCERTAIN and no higher than Level 2"}
                    )

    report_path = root / "report/six_layer_analysis_report.md"
    if report_path.exists():
        report_text = report_path.read_text(encoding="utf-8", errors="replace")
        assertion_patterns = (
            r"(?:control command|control message|控制命令).{0,50}(?:proves?|establishes?|证明|证实).{0,20}(?:collision|碰撞)",
            r"(?:collision|碰撞).{0,30}(?:proven|established|已证明|已证实).{0,30}(?:control|控制)",
        )
        if any(re.search(pattern, report_text, flags=re.IGNORECASE | re.DOTALL) for pattern in assertion_patterns):
            errors.append(
                {"check": "record_report_claim_ceiling", "path": str(report_path),
                 "message": "report asserts a physical collision conclusion from Control/record evidence"}
            )

    return {
        "protocol": "TCPS-PA Diagnostic Protocol v2",
        "validation_mode": "record-only",
        "analysis_dir": str(root.resolve()),
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "summary": {"record_profile_count": len(profile_paths)},
    }


def validate(root: Path) -> Dict[str, Any]:
    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []
    loaded: Dict[str, List[Dict[str, str]]] = {}

    # L5 is validator-authoritative: recompute from the saved wall-clock velocity
    # trajectory (or extract it from traceable Localization sources) before any
    # semantic judgment.  An inability to recompute remains an explicit row.
    try:
        recompute_analysis(root, tolerance_m=0.02, write_output=True)
    except (OSError, ValueError, csv.Error) as exc:
        errors.append(
            {"check": "l5_recomputation", "path": "tables/l5_recomputation.csv",
             "message": "validator could not recompute L5: %s" % exc}
        )

    for relative in sorted(REQUIRED_FILES):
        if not (root / relative).exists():
            errors.append({"check": "required_file", "path": relative, "message": "missing"})

    for relative, required_columns in SCHEMAS.items():
        columns, rows = read_csv(root / relative)
        loaded[relative] = rows
        add_schema_error(errors, relative, columns, required_columns)

    deadline_rows = loaded.get("tables/dynamic_deadline_construction.csv", [])
    recomputed_deadline_rows = [construct_row(row) for row in deadline_rows]
    for source, recomputed in zip(deadline_rows, recomputed_deadline_rows):
        mismatched_fields = [
            field for field in (
                "tau_req_low_ms", "tau_req_center_ms", "tau_req_high_ms",
                "construction_status", "qualification",
            )
            if str(source.get(field) or "").strip() != str(recomputed.get(field) or "").strip()
        ]
        if mismatched_fields:
            errors.append(
                {"check": "dynamic_deadline_recomputation",
                 "path": "tables/dynamic_deadline_construction.csv",
                 "message": "stored deadline construction differs from validator recomputation: %s" %
                 ", ".join(mismatched_fields)}
            )

    rag_rows = loaded.get("tables/realtime_rag_summary.csv", [])
    rag_dimensions = {str(row.get("dimension") or "").strip().upper() for row in rag_rows}
    missing_rag = sorted({"R", "A", "G"} - rag_dimensions)
    if missing_rag:
        errors.append(
            {"check": "realtime_rag_coverage", "path": "tables/realtime_rag_summary.csv",
             "message": "missing explicit dimensions: %s" % ", ".join(missing_rag)}
        )

    method_rows = loaded.get("tables/method_completeness_matrix.csv", [])
    if len(method_rows) < 10:
        errors.append(
            {"check": "method_completeness", "path": "tables/method_completeness_matrix.csv",
             "message": "expected at least 10 explicit method requirements; found %d" % len(method_rows)}
        )
    for index, row in enumerate(method_rows, start=2):
        if any(not nonempty(row.get(field)) for field in ("requirement", "status", "evidence_or_gap")):
            errors.append(
                {"check": "method_completeness", "path": "tables/method_completeness_matrix.csv",
                 "message": "row %d must state requirement, status, and evidence_or_gap" % index}
            )

    observed_path = root / "tables/run_level_observed.csv"
    observed_columns, observed_rows = read_csv(observed_path)
    loaded["tables/run_level_observed.csv"] = observed_rows
    add_schema_error(errors, "tables/run_level_observed.csv", observed_columns, OBSERVED_REQUIRED_COLUMNS)

    space_rows = loaded.get("tables/space_budget_decomposition_observed.csv", [])
    observed_run_ids = {
        str(row.get("run_id") or "").strip() for row in observed_rows
        if str(row.get("run_id") or "").strip()
    }
    space_run_ids = {
        str(row.get("run_id") or "").strip() for row in space_rows
        if str(row.get("run_id") or "").strip()
    }
    missing_space_runs = sorted(observed_run_ids - space_run_ids)
    if missing_space_runs:
        errors.append(
            {"check": "space_budget_coverage",
             "path": "tables/space_budget_decomposition_observed.csv",
             "message": "run rows missing from explicit space-budget availability audit: %s" %
             ", ".join(missing_space_runs)}
        )
    response_fields = {
        "D_response_wall_integral_data_observed_m",
        "D_delay_wall_integral_data_observed_m",
    }
    if not response_fields & set(observed_columns):
        errors.append(
            {"check": "observed_schema", "path": str(observed_path),
             "message": "missing canonical D_response wall-integral field and legacy alias"}
        )
    elif "D_response_wall_integral_data_observed_m" not in observed_columns:
        warnings.append(
            {"check": "legacy_distance_alias", "path": str(observed_path),
             "message": "only deprecated D_delay alias exists; new analyses must emit canonical D_response"}
        )

    forbidden_observed = [
        column for column in observed_columns
        if any(
            marker in column.lower()
            for marker in (
                "model_predicted", "predicted_", "_predicted", "tau_model",
                "model_deadline", "model_debt", "predicted_braking",
            )
        )
        or column.lower().endswith("_model")
    ]
    if forbidden_observed:
        errors.append(
            {"check": "observed_model_separation", "path": str(observed_path),
             "message": "model columns found in observed table: %s" % forbidden_observed}
        )

    for index, row in enumerate(observed_rows, start=2):
        run_id = row.get("run_id", "row-%d" % index)
        status = (row.get("analysis_status") or "").strip().upper()
        included = (row.get("included_main_analysis") or "").strip().lower()
        reason = row.get("missing_reason") or row.get("exclusion_reason")
        if (included in {"false", "0", "no"} or status not in {"ANALYZED", "AVAILABLE"}) and not nonempty(reason):
            warnings.append(
                {"check": "missing_or_exclusion_reason", "path": str(observed_path),
                 "message": "run %s has status=%r, included=%r, but no reason" % (run_id, status, included)}
            )

    model_path = root / "tables/run_level_model_predicted.csv"
    model_columns, _ = read_csv(model_path)
    if model_columns and not any(
        "model" in column.lower() or "predicted" in column.lower() for column in model_columns
    ):
        errors.append(
            {"check": "model_schema", "path": str(model_path),
             "message": "model table has no explicitly model/predicted column"}
        )

    matrix_path = root / "tables/layer_evidence_matrix.csv"
    if matrix_path.exists():
        matrix_columns, matrix_rows = read_csv(matrix_path)
        add_schema_error(errors, "tables/layer_evidence_matrix.csv", matrix_columns, EVIDENCE_MATRIX_REQUIRED_COLUMNS)
        layers = {row.get("layer", "").strip().upper() for row in matrix_rows}
        absent_layers = sorted({"L%d" % index for index in range(1, 7)} - layers)
        if absent_layers:
            warnings.append(
                {"check": "compatibility_view_coverage", "path": str(matrix_path),
                 "message": "compatibility view lacks layers: %s" % ", ".join(absent_layers)}
            )

    report_path = root / "report/six_layer_analysis_report.md"
    report_text = report_path.read_text(encoding="utf-8", errors="replace") if report_path.exists() else ""
    report_sections = {
        "method completeness": r"(?:method[- ]completeness|方法(?:完备性|完成度))",
        "R/A/G": r"(?:R\s*/\s*A\s*/\s*G|实时性三元组)",
        "space budget": r"(?:space[- ]budget|空间预算)",
        "reproducibility": r"(?:reproducibility|复现)",
    }
    for label, pattern in report_sections.items():
        if report_text and not re.search(pattern, report_text, flags=re.IGNORECASE):
            errors.append(
                {"check": "realtime_report_contract", "path": str(report_path),
                 "message": "full report is missing %s coverage" % label}
            )
    semantic_issues = validate_argument_rows(
        claims=loaded.get("tables/claim_ledger.csv", []),
        evidence=loaded.get("tables/evidence_ledger.csv", []),
        edges=loaded.get("tables/claim_edges.csv", []),
        defeaters=loaded.get("tables/defeater_ledger.csv", []),
        fault_signatures=loaded.get("tables/temporal_fault_signature.csv", []),
        pre_hazard_rows=loaded.get("tables/pre_hazard_state_audit.csv", []),
        functional_rows=loaded.get("tables/functional_correctness_audit.csv", []),
        clock_rows=loaded.get("tables/clock_alignment_audit.csv", []),
        requirement_rows=loaded.get("tables/requirement_registry.csv", []),
        observed_rows=observed_rows,
        report_text=report_text,
        phase_rows=loaded.get("tables/phase_audit.csv", []),
        dynamic_deadline_rows=recomputed_deadline_rows,
        l5_rows=loaded.get("tables/l5_recomputation.csv", []),
        diagnosis_rows=loaded.get("tables/diagnosis_hypothesis_ledger.csv", []),
        diagnosis_edges=loaded.get("tables/diagnosis_edges.csv", []),
    )
    for item in semantic_issues:
        target = errors if item.get("severity") == "ERROR" else warnings
        target.append(
            {"check": "semantic_argument:%s" % item.get("rule", "UNKNOWN"),
             "path": "tables/claim_ledger.csv",
             "message": "%s%s%s" % (
                 item.get("message", ""),
                 " [claim=%s]" % item["claim_id"] if item.get("claim_id") else "",
                 " [evidence=%s]" % item["evidence_id"] if item.get("evidence_id") else "",
             )}
        )

    validation_dir = root / "validation"
    validation_dir.mkdir(parents=True, exist_ok=True)
    claims = loaded.get("tables/claim_ledger.csv", [])
    evidence = loaded.get("tables/evidence_ledger.csv", [])
    defeaters = loaded.get("tables/defeater_ledger.csv", [])
    if claims:
        (validation_dir / "claim_audit.md").write_text(
            claim_audit_markdown(claims, evidence, defeaters), encoding="utf-8"
        )

    return {
        "protocol": "TCPS-PA Diagnostic Protocol v2.1",
        "analysis_dir": str(root.resolve()),
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "observed_run_count": len(observed_rows),
            "evidence_row_count": len(evidence),
            "claim_row_count": len(claims),
            "defeater_row_count": len(defeaters),
            "semantic_issue_count": len(semantic_issues),
            "required_file_count": len(REQUIRED_FILES),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate TCPS-PA v2.1 analysis outputs")
    parser.add_argument("--analysis-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=("full", "record-only"), default="full")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.analysis_dir.resolve()
    result = validate_record_only(root) if args.mode == "record-only" else validate(root)
    output = root / "validation/validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
