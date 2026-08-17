#!/usr/bin/env python3
"""Synthetic regression tests A-J from the TCPS-PA v2 contract."""

from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from inference_core import (  # noqa: E402
    allowed_attribution_label,
    has_observed_reaction,
    temporal_correctness_classification,
    validate_argument_rows,
)
from construct_dynamic_deadline import construct_row  # noqa: E402
from recompute_l5_metrics import recompute_analysis  # noqa: E402


def evidence(evidence_id: str, klass: str, metric: str, supports: str, **extra: str) -> dict[str, str]:
    row = {
        "evidence_id": evidence_id,
        "evidence_class": klass,
        "metric": metric,
        "confidence": "HIGH",
        "supports_claim_ids": supports,
        "availability": "AVAILABLE",
        "value": "1",
        "unit": "ms",
        "source_file": "synthetic.csv",
        "source_locator": "synthetic row",
    }
    row.update(extra)
    return row


def claim(claim_id: str, verdict: str, support: str = "", prereqs: str = "", **extra: str) -> dict[str, str]:
    base = claim_id.split(".", 1)[0]
    layer = {"C1": "L1", "C2": "L2", "C3": "L3", "C4": "L4", "C5": "L5", "C6": "L6", "C7": "ATTRIBUTION"}.get(base, base)
    row = {
        "claim_id": claim_id,
        "layer": layer,
        "run_id_or_group": claim_id.split(".", 1)[1] if "." in claim_id else "",
        "proposition": "Synthetic proposition for %s" % claim_id,
        "inference_rule_id": "IR-%s" % base,
        "verdict": verdict,
        "supporting_evidence_ids": support,
        "prerequisite_claim_ids": prereqs,
        "required_evidence_classes": "",
        "confidence": "HIGH",
        "confidence_ceiling": "HIGH",
        "maximum_claim_level": "3",
        "gate_inputs": "Synthetic scoped inputs and prerequisites",
        "gate_metrics": "Synthetic metric with unit and endpoint semantics",
        "admissible_evidence": "Synthetic admissible evidence classes and links",
        "gate_criterion": "Apply the scoped synthetic inference rule",
        "next_gate_condition": "Proceed only when this gate and prerequisites are satisfied",
    }
    row.update(extra)
    return row


def edges_for(claims: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for child in claims:
        for parent in child.get("prerequisite_claim_ids", "").split("|"):
            if parent:
                rows.append(
                    {"parent_claim_id": parent, "child_claim_id": child["claim_id"],
                     "relation": "REQUIRES", "required": "TRUE"}
                )
    return rows


def rules(issues: list[dict[str, str]]) -> set[str]:
    return {item["rule"] for item in issues}


class SyntheticInferenceCases(unittest.TestCase):
    def test_case_a_slow_but_temporally_safe(self) -> None:
        classification, c4_hypothesis = temporal_correctness_classification(800.0, 1000.0, 1100.0)
        self.assertEqual(classification, "CLEARLY_WITHIN_REQUIREMENT")
        self.assertEqual(c4_hypothesis, "FAIL")  # failure proposition rejected; temporal gate is safe

    def test_case_b_deadline_miss_successful_stop_does_not_imply_collision(self) -> None:
        classification, c4_hypothesis = temporal_correctness_classification(900.0, 600.0, 700.0)
        self.assertEqual((classification, c4_hypothesis), ("CLEARLY_MISSED", "PASS"))
        c6 = claim("C6.run", "PASS", "EV.STOP")
        observed_stop = evidence(
            "EV.STOP", "DIRECT_OBSERVED", "M_SAFETY_6M_DATA_OBSERVED_M", "C6.run",
            semantic_role="PHYSICAL_OUTCOME",
        )
        self.assertNotIn("V13", rules(validate_argument_rows([c6], [observed_stop], [], [])))
        self.assertNotIn("collision", observed_stop["metric"].lower())

    def test_case_c_collision_with_functional_failure_is_not_timing_only(self) -> None:
        label, ceiling = allowed_attribution_label("FAIL", "PASS", "PASS", "PASS")
        self.assertEqual(label, "FUNCTIONAL_OR_MULTI_FACTOR_FAILURE")
        self.assertLessEqual(ceiling, 2)

    def test_case_d_retrospective_deadline_only(self) -> None:
        p_deadline = claim("P_DEADLINE.run", "NOT_TESTABLE", "EV.RETRO", confidence="MEDIUM", confidence_ceiling="MEDIUM")
        c4 = claim("C4.run", "PASS", "EV.TR|EV.RETRO", "P_DEADLINE.run")
        evs = [
            evidence(
                "EV.TR", "OBSERVED_DERIVED", "T_R", "C4.run",
                semantic_role="PHYSICAL_REACTION_INTERVAL",
            ),
            evidence("EV.RETRO", "RETROSPECTIVE_RECONSTRUCTION", "tau_retro", "P_DEADLINE.run|C4.run", confidence="MEDIUM"),
        ]
        issue_rules = rules(validate_argument_rows([p_deadline, c4], evs, edges_for([p_deadline, c4]), []))
        self.assertIn("V2", issue_rules)
        self.assertNotIn("REQUIREMENT_CONSTRAINED_DERIVED", {item["evidence_class"] for item in evs})

    def test_case_e_unvalidated_model_deadline(self) -> None:
        p_deadline = claim("P_DEADLINE.run", "NOT_TESTABLE", "EV.MODEL", confidence="LOW", confidence_ceiling="LOW")
        c4 = claim("C4.run", "PASS", "EV.TR|EV.MODEL", "P_DEADLINE.run")
        evs = [
            evidence(
                "EV.TR", "OBSERVED_DERIVED", "T_R", "C4.run",
                semantic_role="PHYSICAL_REACTION_INTERVAL",
            ),
            evidence("EV.MODEL", "UNVALIDATED_MODEL", "tau_model", "P_DEADLINE.run|C4.run", confidence="LOW"),
        ]
        self.assertIn("V3", rules(validate_argument_rows([p_deadline, c4], evs, edges_for([p_deadline, c4]), [])))

    def test_case_f_unknown_cross_host_clock_downgrades_stage_timing(self) -> None:
        p_clock = claim("P_CLOCK.run", "PARTIAL_PASS", "EV.CLOCK", confidence="MEDIUM", confidence_ceiling="MEDIUM")
        c3 = claim("C3.run", "PARTIAL_PASS", "EV.CLOCK", "P_CLOCK.run", causal_lineage_grade="C")
        evs = [evidence("EV.CLOCK", "CLOCK_UNVERIFIED", "cross_host_stage", "P_CLOCK.run|C3.run", confidence="MEDIUM")]
        self.assertIn("V8", rules(validate_argument_rows([p_clock, c3], evs, edges_for([p_clock, c3]), [])))

    def test_case_g_fault_before_t1_requires_causal_role_audit(self) -> None:
        faults = [{"run_id": "G", "fault_onset_wall": "9", "t1_wall": "10", "requested_magnitude": "300"}]
        self.assertIn("V9", rules(validate_argument_rows([], [], [], [], fault_signatures=faults)))
        audit = [
            {"run_id": "G", "state_variable": "D1", "causal_role": "POSSIBLE_MEDIATOR"},
            {"run_id": "G", "state_variable": "V1", "causal_role": "POST_TREATMENT_STATE"},
        ]
        issue_rules = rules(validate_argument_rows([], [], [], [], fault_signatures=faults, pre_hazard_rows=audit))
        self.assertNotIn("V9", issue_rules)
        self.assertNotIn("V10", issue_rules)

    def test_case_h_single_500ms_gap_without_reference_is_not_group_degradation(self) -> None:
        c2 = claim("C2.group", "PASS", "EV.GAP", run_id_or_group="all_runs")
        gap = evidence(
            "EV.GAP", "OBSERVED_DERIVED", "target_gap_max", "C2.group",
            reference_type="MISSING", distribution_scope="SINGLE_MAX",
        )
        self.assertIn("V12", rules(validate_argument_rows([c2], [gap], [], [])))

    def test_case_i_uncertain_target_identity_blocks_strong_c3(self) -> None:
        p_target = claim("P_TARGET.run", "PARTIAL_PASS", "EV.TARGET", confidence="MEDIUM", confidence_ceiling="MEDIUM")
        c3 = claim("C3.run", "PASS", "EV.ALIGN", "P_TARGET.run", causal_lineage_grade="C")
        evs = [
            evidence("EV.TARGET", "WEAK_TEMPORAL_ALIGNMENT", "target_identity", "P_TARGET.run", confidence="MEDIUM"),
            evidence("EV.ALIGN", "WEAK_TEMPORAL_ALIGNMENT", "alignment", "C3.run", confidence="MEDIUM"),
        ]
        self.assertIn("V7", rules(validate_argument_rows([p_target, c3], evs, edges_for([p_target, c3]), [])))

    def test_case_j_strong_ends_cannot_hide_weak_middle(self) -> None:
        claims = [
            claim("C1.group", "PASS"), claim("C4.group", "NOT_TESTABLE", confidence="LOW", confidence_ceiling="LOW"),
            claim("C5.group", "MODEL_SUPPORTED_ONLY", confidence="LOW", confidence_ceiling="LOW"),
            claim("C6.group", "PASS", "EV.OUTCOME"),
            claim("C7.group", "PASS", "EV.OUTCOME", maximum_claim_level="5"),
        ]
        evs = [evidence(
            "EV.OUTCOME", "DIRECT_OBSERVED", "COLLISION_EVENT_DATA_OBSERVED", "C6.group|C7.group",
            semantic_role="PHYSICAL_OUTCOME",
        )]
        self.assertIn("WEAKEST_LINK", rules(validate_argument_rows(claims, evs, [], [])))

    def test_adversarial_record_reaction_is_not_physical_tr(self) -> None:
        record_metric = evidence(
            "EV.RECORD", "OBSERVED_DERIVED", "sensor_to_control_reaction_age", "C4.run",
            semantic_role="MESSAGE_TIMING_DIAGNOSTIC",
        )
        self.assertFalse(has_observed_reaction([record_metric]))

    def test_adversarial_control_command_is_not_physical_outcome(self) -> None:
        c6 = claim("C6.run", "PASS", "EV.CONTROL")
        control = evidence(
            "EV.CONTROL", "DIRECT_OBSERVED", "control_braking_command_present", "C6.run",
            semantic_role="CONTROL_COMMAND",
        )
        self.assertIn("V13", rules(validate_argument_rows([c6], [control], [], [])))

    def test_adversarial_empty_claim_graph_fails(self) -> None:
        self.assertIn(
            "GRAPH_COMPLETENESS",
            rules(validate_argument_rows([], [], [], [], report_text="Six-Layer Inference Status Matrix")),
        )

    def test_adversarial_format_complete_claim_without_executable_gate_fails(self) -> None:
        c2 = claim("C2.group", "PARTIAL_PASS", gate_criterion="", next_gate_condition="")
        issue_rules = rules(validate_argument_rows([c2], [], [], []))
        self.assertIn("GATE_COMPLETENESS", issue_rules)

    def test_v21_clock_pass_does_not_require_phase_scan(self) -> None:
        p_clock = claim("P_CLOCK.run", "PASS", "EV.CLOCK")
        ev = evidence(
            "EV.CLOCK", "DIRECT_OBSERVED", "cross_host_clock_bound", "P_CLOCK.run",
            semantic_role="CLOCK_ALIGNMENT_BOUND",
        )
        clock_audit = [{
            "run_id_or_group": "run", "sync_method": "PTP_802_1AS",
            "offset_estimate_ms": "0.2", "drift_estimate_ppm": "2",
            "alignment_residual_ms": "0.3", "timestamp_resolution_ms": "0.001",
            "confidence": "HIGH",
        }]
        issue_rules = rules(validate_argument_rows(
            [p_clock], [ev], [], [], clock_rows=clock_audit, phase_rows=[]
        ))
        self.assertNotIn("V8", issue_rules)

    def test_v21_phase_pass_requires_active_scan(self) -> None:
        p_phase = claim("P_PHASE.run", "PASS")
        self.assertIn(
            "V19",
            rules(validate_argument_rows([p_phase], [], [], [], phase_rows=[])),
        )

    def test_v21_dynamic_deadline_contract_constructs_ordered_bounds(self) -> None:
        parameters = {
            "construction_id": "CONSTRUCTION.run", "requirement_id": "REQ.run",
            "run_id_or_group": "run", "state_time": "1.0",
            "state_time_basis": "wall_epoch_s", "state_available_by_t1": "TRUE",
            "input_cutoff_time": "1.0", "latest_input_time": "1.0",
            "parameter_selection_time": "0.5", "parameter_selection_locked_by_t1": "TRUE",
            "current_run_post_t1_data_used": "FALSE", "current_run_outcome_used": "FALSE",
            "d_clear_m": "60", "v_ego_mps": "12", "v_front_mps": "0",
            "d_safe_m": "6", "a_ego_response_max_mps2": "0.5",
            "b_ego_min_mps2": "4", "b_front_max_mps2": "8",
            "braking_envelope_id": "BE.1", "braking_envelope_provenance": "independent calibration",
            "braking_envelope_status": "QUALIFIED", "validation_dataset_independent": "TRUE",
            "validation_scope": "dry asphalt 8-14 m/s",
            "calibration_run_ids": "cal-1|cal-2", "evaluation_run_ids": "run",
            "target_motion_assumption": "stationary obstacle",
            "road_condition_assumption": "dry asphalt",
        }
        bounds = {
            "d_clear_m": [59, 61], "v_ego_mps": [11.8, 12.2], "v_front_mps": [0, 0],
            "d_safe_m": [5.5, 6.5], "a_ego_response_max_mps2": [0.4, 0.6],
            "b_ego_min_mps2": [3.8, 4.2], "b_front_max_mps2": [7.5, 8.5],
        }
        parameters["parameter_bounds_json"] = json.dumps(bounds)
        parameters["input_provenance_json"] = json.dumps({name: "calibration.csv:row1" for name in bounds})
        built = construct_row(parameters)
        self.assertEqual(built["qualification"], "QUALIFIED_DYNAMIC_PHYSICAL")
        self.assertLessEqual(float(built["tau_req_low_ms"]), float(built["tau_req_center_ms"]))
        self.assertLessEqual(float(built["tau_req_center_ms"]), float(built["tau_req_high_ms"]))

    def test_v21_qualified_dynamic_deadline_requires_matching_construction(self) -> None:
        requirement = {
            "requirement_id": "REQ.run", "run_id_or_group": "run",
            "deadline_type": "DYNAMIC_PHYSICAL_CONSTRUCTED",
            "p_deadline_qualification": "QUALIFIED_DYNAMIC_PHYSICAL",
            "tau_req_low_ms": "400", "tau_req_center_ms": "500", "tau_req_high_ms": "600",
        }
        self.assertIn(
            "V17",
            rules(validate_argument_rows([], [], [], [], requirement_rows=[requirement])),
        )

    def test_v21_l5_recomputation_from_raw_velocity_samples(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            tables = root / "tables"
            tables.mkdir()

            def write(name: str, fields: list[str], rows: list[dict[str, str]]) -> None:
                with (tables / name).open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(rows)

            write(
                "run_level_observed.csv",
                ["run_id", "t1_wall_s", "t2_wall_s", "D_response_wall_integral_data_observed_m",
                 "D_debt_requirement_constrained_derived_m"],
                [{"run_id": "run", "t1_wall_s": "1", "t2_wall_s": "3",
                  "D_response_wall_integral_data_observed_m": "20",
                  "D_debt_requirement_constrained_derived_m": "10"}],
            )
            write(
                "velocity_trajectory_observed.csv",
                ["run_id", "sample_index", "t_wall_s", "speed_mps", "availability"],
                [{"run_id": "run", "sample_index": str(index), "t_wall_s": str(index),
                  "speed_mps": "10", "availability": "AVAILABLE"} for index in range(4)],
            )
            write(
                "requirement_registry.csv",
                ["requirement_id", "run_id_or_group", "p_deadline_qualification", "tau_req_center_ms"],
                [{"requirement_id": "REQ.run", "run_id_or_group": "run",
                  "p_deadline_qualification": "QUALIFIED_INDEPENDENT", "tau_req_center_ms": "1000"}],
            )
            result = recompute_analysis(root, tolerance_m=1e-9, write_output=False)[0]
            self.assertEqual(result["recomputation_status"], "PASS")
            self.assertAlmostEqual(float(result["D_response_recomputed_m"]), 20.0)
            self.assertAlmostEqual(float(result["D_debt_recomputed_m"]), 10.0)

    def test_v21_c5_rejects_claimed_debt_not_matching_validator_result(self) -> None:
        c4 = claim("C4.run", "PASS")
        p_clock = claim("P_CLOCK.run", "PASS")
        c5 = claim("C5.run", "PASS", "EV.DEBT|EV.V", "C4.run|P_CLOCK.run")
        evs = [
            evidence(
                "EV.DEBT", "REQUIREMENT_CONSTRAINED_DERIVED", "D_DEBT", "C5.run",
                value="11", unit="m", run_id="run", semantic_role="DEADLINE_EXCESS_DISTANCE_DEBT",
            ),
            evidence(
                "EV.V", "DIRECT_OBSERVED", "VELOCITY_TRAJECTORY", "C5.run",
                value="trajectory", unit="m/s", run_id="run", semantic_role="OBSERVED_VELOCITY_PATH",
            ),
        ]
        l5 = [{
            "run_id": "run", "D_debt_recomputed_m": "10", "tolerance_m": "0.02",
            "recomputation_status": "PASS",
        }]
        issue_rules = rules(validate_argument_rows(
            [c4, p_clock, c5], evs, edges_for([c4, p_clock, c5]), [], l5_rows=l5
        ))
        self.assertIn("V18", issue_rules)

    def test_v21_backward_diagnosis_cannot_use_proves_edge(self) -> None:
        diagnosis = [{
            "hypothesis_id": "H.1", "seed_claim_id": "C6.run",
            "status": "CONSISTENT_BUT_UNRESOLVED", "alternative_hypothesis_ids": "H.2",
        }]
        diagnosis_edges = [{
            "parent_id": "C6.run", "child_id": "H.1", "relation": "PROVES",
            "time_direction": "BACKWARD_DIAGNOSTIC",
        }]
        self.assertIn(
            "V20",
            rules(validate_argument_rows(
                [claim("C6.run", "PARTIAL_PASS")], [], [], [],
                diagnosis_rows=diagnosis, diagnosis_edges=diagnosis_edges,
            )),
        )


if __name__ == "__main__":
    unittest.main()
