#!/usr/bin/env python3
"""Synthetic regression tests A-J from the TCPS-PA v2 contract."""

from __future__ import annotations

import sys
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


if __name__ == "__main__":
    unittest.main()
