#!/usr/bin/env python3
"""Conservatively migrate a legacy six-layer analysis to TCPS-PA v2 ledgers.

The migration never upgrades retrospective/model values into observed facts.  It
uses only existing generated analysis tables and writes v2 argument artifacts
under the same analysis directory; experiment source directories remain read-only.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence

from inference_core import claim_audit_markdown


EVIDENCE_FIELDS = [
    "evidence_id", "run_id", "layer", "metric", "value", "unit",
    "evidence_class", "clock_domain", "source_file", "source_locator",
    "availability", "confidence", "supports_claim_ids", "challenges_claim_ids",
    "limitations", "taint_tags", "reference_type", "distribution_scope",
    "causal_lineage_grade", "endpoint_definition", "semantic_role", "requirement_id",
    "host", "timestamp_type",
]

CLAIM_FIELDS = [
    "claim_id", "layer", "run_id_or_group", "proposition",
    "prerequisite_claim_ids", "required_evidence_classes",
    "supporting_evidence_ids", "challenging_evidence_ids", "defeater_ids",
    "inference_rule_id", "verdict", "confidence", "confidence_ceiling",
    "maximum_claim_level", "residual_uncertainty", "allowed_language",
    "forbidden_language", "causal_lineage_grade", "deadline_basis",
    "gate_criterion", "critical_claim", "gate_inputs", "gate_metrics",
    "admissible_evidence", "next_gate_condition",
]

EDGE_FIELDS = ["parent_claim_id", "child_claim_id", "relation", "required", "notes"]

DEFEATER_FIELDS = [
    "defeater_id", "claim_id", "description", "type", "evidence_ids",
    "status", "resolution", "residual_risk", "impact_on_claim", "notes",
]

FAULT_FIELDS = [
    "run_id", "fault_type", "injection_location", "requested_magnitude",
    "actual_magnitude", "actual_distribution", "fault_onset_wall",
    "fault_end_wall", "t1_wall", "trigger_relative_t1_s", "duration",
    "persistent_or_transient", "one_shot_or_repeated", "affected_channel",
    "affected_message_count", "queue_behavior", "drop_status", "reorder_status",
    "evidence_class", "confidence",
]

PRE_HAZARD_FIELDS = [
    "run_id", "state_variable", "window_start_wall", "window_end_wall",
    "value_at_fault", "value_at_t1", "delta", "source_file", "availability",
    "causal_role", "evidence_class", "confidence", "notes",
]

FUNCTION_FIELDS = [
    "run_id", "physical_target_identity", "perception_target_present",
    "perception_tracking_continuity", "prediction_target_present",
    "prediction_semantics_valid", "planning_stop_present",
    "planning_stop_target_correct", "planning_stop_location_reasonable",
    "planning_trajectory_valid", "planning_fallback_status",
    "control_received_relevant_trajectory", "control_braking_command_present",
    "control_command_continuity", "bridge_payload_received",
    "bridge_payload_applied", "physical_response_observed", "p_func_verdict",
    "confidence", "source_evidence_ids", "notes",
]

CLOCK_FIELDS = [
    "run_id_or_group", "clock_domain", "host", "timestamp_type", "sync_method",
    "offset_estimate_ms", "drift_estimate", "alignment_residual_ms",
    "timestamp_resolution_ms", "confidence", "phase_scan_performed",
    "phase_effect_verdict", "notes",
]

REQUIREMENT_FIELDS = [
    "requirement_id", "run_id_or_group", "requirement_name", "requirement_value",
    "unit", "requirement_provenance", "pre_registered", "external_or_internal",
    "safety_meaning", "deadline_type", "evidence_class", "tau_req_low_ms",
    "tau_req_center_ms", "tau_req_high_ms", "validation_scope",
    "p_deadline_qualification", "notes",
]

RAG_FIELDS = [
    "dimension", "metric", "source_column", "unit", "semantics",
    "group_name", "n_total_runs", "n_available_runs", "p50", "p90",
    "p95", "p99", "max", "iqr",
]

SPACE_RUN_FIELDS = [
    "run_id", "group_name", "included_main_analysis", "outcome_data_observed",
    "D1_clear_data_observed_m", "D_response_wall_integral_data_observed_m",
    "D_brake_data_observed_m", "M0_recomputed_observed_m",
    "endpoint_compatible_full_stop", "decomposition_scope",
]

SPACE_GROUP_FIELDS = [
    "comparison_group", "n", "D1_mean_m", "D_response_mean_m",
    "D_brake_mean_m", "M0_mean_m",
]

METHOD_FIELDS = ["requirement", "status", "evidence_or_gap"]


def clean(value: object) -> str:
    return str(value or "").strip()


def number(value: object) -> float | None:
    try:
        return float(clean(value))
    except ValueError:
        return None


def truthy(value: object) -> bool:
    return clean(value).lower() in {"true", "1", "yes", "y"}


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def ev(
    evidence_id: str,
    run_id: str,
    layer: str,
    metric: str,
    value: object,
    unit: str,
    evidence_class: str,
    confidence: str,
    supports: str,
    source_file: str = "",
    limitations: str = "",
    **extra: object,
) -> Dict[str, object]:
    row: Dict[str, object] = {
        "evidence_id": evidence_id,
        "run_id": run_id,
        "layer": layer,
        "metric": metric,
        "value": value,
        "unit": unit,
        "evidence_class": evidence_class,
        "clock_domain": "wall_epoch_s",
        "source_file": source_file,
        "source_locator": "legacy generated run-level table",
        "availability": "AVAILABLE" if clean(value) else "MISSING",
        "confidence": confidence,
        "supports_claim_ids": supports,
        "challenges_claim_ids": "",
        "limitations": limitations,
    }
    row.update(extra)
    return row


def claim(
    claim_id: str,
    layer: str,
    proposition: str,
    prerequisites: str,
    required_classes: str,
    support: str,
    defeaters: str,
    rule: str,
    verdict: str,
    confidence: str,
    ceiling: str,
    level: int,
    uncertainty: str,
    allowed: str,
    forbidden: str,
    **extra: object,
) -> Dict[str, object]:
    row: Dict[str, object] = {
        "claim_id": claim_id,
        "layer": layer,
        "run_id_or_group": "all_runs",
        "proposition": proposition,
        "prerequisite_claim_ids": prerequisites,
        "required_evidence_classes": required_classes,
        "supporting_evidence_ids": support,
        "challenging_evidence_ids": "",
        "defeater_ids": defeaters,
        "inference_rule_id": rule,
        "verdict": verdict,
        "confidence": confidence,
        "confidence_ceiling": ceiling,
        "maximum_claim_level": level,
        "residual_uncertainty": uncertainty,
        "allowed_language": allowed,
        "forbidden_language": forbidden,
        "critical_claim": "TRUE",
        "gate_inputs": "Legacy scoped evidence plus canonical prerequisite claims: %s" %
        (prerequisites or "none"),
        "gate_metrics": "Legacy metric mapping retained without new raw-data recomputation.",
        "admissible_evidence": required_classes or "No positive evidence class available.",
        "gate_criterion": "Apply %s conservatively; missing or tainted evidence cannot become PASS." % rule,
        "next_gate_condition": "Enter the next canonical claim only after this gate and its critical prerequisites satisfy the v2 contract.",
    }
    row.update(extra)
    return row


def make_evidence(
    observed: Sequence[Mapping[str, str]], model: Sequence[Mapping[str, str]], observed_path: Path,
    model_path: Path,
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for item in observed:
        run_id = clean(item.get("run_id"))
        if not run_id:
            continue
        rows.extend(
            [
                ev(
                    f"EV.L1.DELAY.{run_id}", run_id, "L1",
                    "bridge_delay_actual_wall_data_observed_ms",
                    item.get("bridge_delay_actual_wall_data_observed_ms")
                    or item.get("scb_actual_wall_delay_ms"), "ms", "DIRECT_OBSERVED", "HIGH",
                    "C1.all_runs|P_CLOCK.fault_signature", str(observed_path),
                    "Establishes injected Bridge/SCB disturbance, not an intrinsic Apollo defect.",
                    endpoint_definition="SCB/Bridge measured application delay",
                    semantic_role="TEMPORAL_DISTURBANCE_APPLICATION", distribution_scope="PER_RUN",
                ),
                ev(
                    f"EV.L2.TR.{run_id}", run_id, "L2", "T_R",
                    item.get("T_e2e_data_observed_ms"), "ms", "OBSERVED_DERIVED", "HIGH",
                    "C2.all_runs|C4.all_runs", str(observed_path),
                    "Wall-clock physical reaction interval; group degradation still requires a declared reference.",
                    endpoint_definition="PHYSICAL_RESPONSE:t2_wall_s-t1_wall_s",
                    semantic_role="PHYSICAL_REACTION_INTERVAL", distribution_scope="PER_RUN",
                ),
                ev(
                    f"EV.L5.D_RESPONSE.{run_id}", run_id, "L5",
                    "D_response_wall_integral_data_observed_m",
                    item.get("D_response_wall_integral_data_observed_m")
                    or item.get("D_delay_wall_integral_data_observed_m"),
                    "m", "OBSERVED_DERIVED", "HIGH", "C5.all_runs", str(observed_path),
                    "Canonical wall-clock speed trapezoid integral; it is not deadline-excess debt by itself.",
                    endpoint_definition="integral v(t) dt_wall over [t1,t2]",
                ),
                ev(
                    f"EV.L6.OUTCOME.{run_id}", run_id, "L6", "physical_outcome",
                    item.get("outcome_data_observed"), "category", "DIRECT_OBSERVED", "HIGH",
                    "C6.all_runs|C7.all_runs", str(observed_path),
                    "Observed outcome cannot by itself establish a temporal failure.",
                    endpoint_definition=item.get("outcome_endpoint_type_data_observed", ""),
                    semantic_role="PHYSICAL_OUTCOME",
                ),
                ev(
                    f"EV.PTARGET.{run_id}", run_id, "P_TARGET", "target_identity_and_presence",
                    item.get("target_id"), "id", "OBSERVED_DERIVED", "MEDIUM",
                    "P_TARGET.all_runs", str(observed_path),
                    "Target identity is present in generated tables but no end-to-end target lineage is archived.",
                    semantic_role="TARGET_ASSOCIATION",
                ),
            ]
        )
        gap = item.get("update_gap_target_response_window_max_data_observed_ms") or item.get(
            "target_gap_max_ms"
        )
        rows.append(
            ev(
                f"EV.L2.GAP_MAX.{run_id}", run_id, "L2", "target_update_gap_max", gap,
                "ms", "OBSERVED_DERIVED", "MEDIUM", "C2.all_runs", str(observed_path),
                "Single maximum without a requirement or nominal distribution is case-level characterization only.",
                reference_type="MISSING", distribution_scope="SINGLE_MAX",
            )
        )
        tau_retro = item.get("tau_dynamic_data_derived_ms")
        rows.append(
            ev(
                f"EV.L4.TAU_RETRO.{run_id}", run_id, "L4", "tau_retro", tau_retro,
                "ms", "RETROSPECTIVE_RECONSTRUCTION", "MEDIUM",
                "P_DEADLINE.all_runs|C4.all_runs", str(observed_path),
                "Same-run physical reconstruction uses post-response/full-trajectory information; not a primary requirement.",
                taint_tags="RETROSPECTIVE", endpoint_definition="legacy tau_dynamic_data_derived_ms reclassified",
                requirement_id=f"REQ.RETRO.COLLISION.{run_id}",
            )
        )
        rows.append(
            ev(
                f"EV.PFUNC.{run_id}", run_id, "P_FUNC", "functional_chain_presence",
                "PARTIAL", "state", "OBSERVED_DERIVED", "MEDIUM", "P_FUNC.all_runs",
                str(observed_path),
                "Planning/output presence is not functional correctness; Control payload is not archived.",
            )
        )

    model_by_run = {clean(row.get("run_id")): row for row in model}
    for run_id, item in model_by_run.items():
        rows.extend(
            [
                ev(
                    f"EV.L4.TAU_MODEL.{run_id}", run_id, "L4", "tau_model",
                    item.get("tau_dynamic_model_predicted_ms"), "ms", "UNVALIDATED_MODEL", "LOW",
                    "P_DEADLINE.all_runs|C4.all_runs", str(model_path),
                    "Baseline-calibrated in-sample model; not an independent validated timing requirement.",
                    taint_tags="MODEL|UNVALIDATED", requirement_id=f"REQ.MODEL.{run_id}",
                ),
                ev(
                    f"EV.L5.DEBT_MODEL.{run_id}", run_id, "L5", "D_debt_model_predicted",
                    item.get("D_distance_debt_model_predicted_m"), "m", "UNVALIDATED_MODEL", "LOW",
                    "C5.all_runs", str(model_path),
                    "Model-derived debt retains MODEL taint and is not observed primary distance debt.",
                    taint_tags="MODEL|UNVALIDATED",
                ),
            ]
        )

    rows.extend(
        [
            ev(
                "EV.CLOCK.FAULT", "all_runs", "P_CLOCK", "fault_signature_clock_compatibility",
                "single_domain", "state", "OBSERVED_DERIVED", "HIGH",
                "P_CLOCK.fault_signature", str(observed_path),
                "Supports the local injected-fault signature only; does not qualify cross-host stages.",
            ),
            ev(
                "EV.CLOCK.CROSS_HOST", "all_runs", "P_CLOCK", "cross_host_clock_alignment",
                "UNVERIFIED", "state", "CLOCK_UNVERIFIED", "MEDIUM",
                "P_CLOCK.cross_host|C3.all_runs", str(observed_path),
                "No dual-clock history/offset-drift estimate; cross-host stage differences are not high-confidence.",
                causal_lineage_grade="C",
            ),
            ev(
                "EV.LINEAGE.ALIGNMENT", "all_runs", "L3", "temporal_alignment_lineage",
                "GRADE_C", "grade", "WEAK_TEMPORAL_ALIGNMENT", "MEDIUM",
                "C3.all_runs", str(observed_path),
                "Validated chronology/alignment without explicit trace ID, sequence propagation, or message provenance.",
                causal_lineage_grade="C", semantic_role="TEMPORAL_ASSOCIATION",
            ),
        ]
    )
    return rows


def make_claims(evidence: Sequence[Mapping[str, object]]) -> List[Dict[str, object]]:
    ids = [clean(row.get("evidence_id")) for row in evidence]
    select = lambda prefix: "|".join(item for item in ids if item.startswith(prefix))
    return [
        claim(
            "P_CLOCK.fault_signature", "P_CLOCK", "Fault-signature timing is comparable in its local clock domain.",
            "", "OBSERVED_DERIVED", "EV.CLOCK.FAULT", "", "IR-P-CLOCK", "PASS", "HIGH", "HIGH", 2,
            "Cross-host stages are outside this scoped prerequisite.",
            "The local Bridge/SCB disturbance timing is usable.",
            "All cross-host stage clocks are globally verified.",
        ),
        claim(
            "P_CLOCK.cross_host", "P_CLOCK", "Cross-host stage timestamps are aligned with bounded offset and drift.",
            "", "TRACE_LINEAGE", "EV.CLOCK.CROSS_HOST", "D_CLOCK.CROSS_HOST", "IR-P-CLOCK",
            "PARTIAL_PASS", "MEDIUM", "MEDIUM", 2,
            "No dual-clock history, offset/drift estimate, or phase scan.",
            "Cross-host timing provides medium-confidence temporal association.",
            "Cross-host stage differences are high-confidence causal delays.",
        ),
        claim(
            "P_TARGET.all_runs", "P_TARGET", "The same relevant physical target is tracked across the chain.",
            "", "TRACE_LINEAGE", select("EV.PTARGET."), "D_TARGET_MISMATCH.CHAIN", "IR-P-TARGET",
            "PARTIAL_PASS", "MEDIUM", "MEDIUM", 2,
            "No explicit end-to-end target lineage.",
            "Target IDs/presence support a qualified target association.",
            "Target identity is proven end to end.",
        ),
        claim(
            "P_FUNC.all_runs", "P_FUNC", "Relevant functional behavior is qualified and does not independently explain outcomes.",
            "P_TARGET.all_runs", "OBSERVED_DERIVED", select("EV.PFUNC."),
            "D_FUNCTIONAL_FAILURE.CHAIN|D_SOLVER_FALLBACK.CHAIN", "IR-P-FUNC", "PARTIAL", "MEDIUM", "MEDIUM", 2,
            "Control payload/command continuity and target-specific Planning correctness are not archived.",
            "Functional-chain presence is observed, but functional correctness remains partial.",
            "functionally correct, temporally wrong|功能正确但时间错误",
        ),
        claim(
            "P_DEADLINE.all_runs", "P_DEADLINE", "An independently qualified scenario-dependent timing requirement is available.",
            "P_TARGET.all_runs", "INDEPENDENT_REQUIREMENT", select("EV.L4.TAU_RETRO.") + "|" + select("EV.L4.TAU_MODEL."),
            "D_DEADLINE.PROVENANCE", "IR-P-DEADLINE", "NOT_TESTABLE", "LOW", "LOW", 1,
            "Available deadlines are retrospective reconstructions or unvalidated model outputs.",
            "A retrospective/model timing budget is available for sensitivity analysis.",
            "The physical safety deadline was independently observed/qualified.",
            deadline_basis="RETROSPECTIVE_AND_UNVALIDATED_MODEL",
        ),
        claim(
            "C1.all_runs", "L1", "A declared temporal disturbance entered the closed loop with characterized scope.",
            "P_CLOCK.fault_signature", "DIRECT_OBSERVED", select("EV.L1.DELAY."), "", "IR-C1", "PASS", "HIGH", "HIGH", 3,
            "The intervention is external Bridge/SCB injection, not an intrinsic Apollo defect.",
            "The injected temporal disturbance is directly verified.",
            "Apollo intrinsically introduced the same disturbance.",
        ),
        claim(
            "C2.all_runs", "L2", "Timing behavior degraded relative to a declared reference or nominal distribution.",
            "C1.all_runs|P_CLOCK.cross_host", "OBSERVED_DERIVED", select("EV.L2.TR.") + "|" + select("EV.L2.GAP_MAX."),
            "D_UPDATE_GAP.REFERENCE|D_PHASE.UNTESTED", "IR-C2", "PARTIAL_PASS", "MEDIUM", "MEDIUM", 2,
            "Physical T_R shifts are observed, but update-gap evidence lacks a qualified reference/distribution and phase was not scanned.",
            "Observed T_R and gap values characterize possible temporal degradation.",
            "A single maximum gap proves group-wide degradation.",
        ),
        claim(
            "C3.all_runs", "L3", "Timing degradation propagated along the relevant cause-effect chain.",
            "C1.all_runs|C2.all_runs|P_CLOCK.cross_host|P_TARGET.all_runs",
            "TRACE_LINEAGE", "EV.LINEAGE.ALIGNMENT|EV.CLOCK.CROSS_HOST",
            "D_CLOCK.CROSS_HOST|D_TARGET_MISMATCH.CHAIN|D_PHASE.UNTESTED", "IR-C3", "PARTIAL_PASS", "MEDIUM", "MEDIUM", 2,
            "Lineage is grade C temporal alignment; explicit trace/provenance lineage is absent.",
            "The evidence supports temporal association across the chain.",
            "Cause-effect temporal propagation is strongly established.",
            causal_lineage_grade="C",
        ),
        claim(
            "C4.all_runs", "L4", "Observed physical Reaction Time exceeded an independently qualified requirement.",
            "C3.all_runs|P_CLOCK.cross_host|P_TARGET.all_runs|P_DEADLINE.all_runs",
            "INDEPENDENT_REQUIREMENT|OBSERVED_DERIVED", select("EV.L2.TR.") + "|" + select("EV.L4.TAU_RETRO.") + "|" + select("EV.L4.TAU_MODEL."),
            "D_DEADLINE.PROVENANCE", "IR-C4", "NOT_TESTABLE", "LOW", "LOW", 1,
            "No independent requirement; retrospective and unvalidated-model comparisons cannot establish primary failure.",
            "Retrospective/model evidence suggests possible deadline misses in sensitivity analysis.",
            "A primary observed temporal correctness failure is established.",
            deadline_basis="RETROSPECTIVE_AND_UNVALIDATED_MODEL",
        ),
        claim(
            "C5.all_runs", "L5", "A qualified timing violation caused quantifiable extra physical-space consumption.",
            "C4.all_runs|P_CLOCK.cross_host", "REQUIREMENT_CONSTRAINED_DERIVED",
            select("EV.L5.D_RESPONSE.") + "|" + select("EV.L5.DEBT_MODEL."),
            "D_BRAKING_CAPABILITY.MODEL|D_GEOMETRY.COMPARABILITY", "IR-C5", "MODEL_SUPPORTED_ONLY", "LOW", "LOW", 2,
            "D_response is observed, but deadline-excess debt is model-tainted and the primary requirement is unavailable.",
            "Observed response distance plus model evidence supports a possible physical propagation mechanism.",
            "Observed primary Distance Debt is established.",
            deadline_basis="UNVALIDATED_MODEL",
        ),
        claim(
            "C6.all_runs", "L6", "Physical safety margin and/or observed outcome degraded across the experiment.",
            "", "DIRECT_OBSERVED", select("EV.L6.OUTCOME."),
            "D_GEOMETRY.COMPARABILITY", "IR-C6", "PASS", "MEDIUM", "MEDIUM", 3,
            "Geometry/initial-state variation limits precise causal attribution, not the directly observed outcomes.",
            "Safe-stop/collision outcomes and physical margins are directly observed.",
            "Observed collision alone proves a temporal failure.",
        ),
        claim(
            "C7.all_runs", "ATTRIBUTION", "Physical degradation is attributable to temporal correctness degradation at a declared strength.",
            "C1.all_runs|C2.all_runs|C3.all_runs|C4.all_runs|C5.all_runs|C6.all_runs|P_FUNC.all_runs",
            "DIRECT_OBSERVED", select("EV.L6.OUTCOME."),
            "D_INITIAL_CLEARANCE.CAUSAL_ROLE|D_FUNCTIONAL_FAILURE.CHAIN|D_DEADLINE.PROVENANCE|D_BRAKING_CAPABILITY.MODEL|D_CLOCK.CROSS_HOST|D_TARGET_MISMATCH.CHAIN",
            "IR-C7", "PARTIAL_PASS", "LOW", "LOW", 2,
            "Strong L1/L6 do not close weak C4/L5; functional, deadline, clock, target, and pre-hazard alternatives remain.",
            "The data support a temporal association and model-supported propagation mechanism.",
            "Timing was the sole or dominant cause; the complete six-layer chain is proven.",
        ),
    ]


def make_edges(claims: Sequence[Mapping[str, object]]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for child in claims:
        for parent in clean(child.get("prerequisite_claim_ids")).split("|"):
            if parent:
                rows.append(
                    {"parent_claim_id": parent, "child_claim_id": child["claim_id"],
                     "relation": "REQUIRES", "required": "TRUE",
                     "notes": "Canonical TCPS-PA v2 prerequisite edge."}
                )
    return rows


def make_defeaters() -> List[Dict[str, str]]:
    specs = [
        ("D_CLOCK.CROSS_HOST", "P_CLOCK.cross_host", "Cross-host offset/drift and phase are unverified.", "CLOCK", "UNKNOWN", "CAPS_AT_PARTIAL"),
        ("D_TARGET_MISMATCH.CHAIN", "P_TARGET.all_runs", "End-to-end target identity lineage is incomplete.", "TARGET_MISMATCH", "UNKNOWN", "CAPS_AT_PARTIAL"),
        ("D_FUNCTIONAL_FAILURE.CHAIN", "P_FUNC.all_runs", "Functional failure remains an alternative explanation.", "FUNCTIONAL_FAILURE", "OPEN", "CRITICAL"),
        ("D_SOLVER_FALLBACK.CHAIN", "P_FUNC.all_runs", "Planning infeasible/fallback counters require target-specific interpretation.", "SOLVER_FALLBACK", "OPEN", "CAPS_AT_PARTIAL"),
        ("D_DEADLINE.PROVENANCE", "P_DEADLINE.all_runs", "No independent pre-registered requirement or validated model.", "DEADLINE", "OPEN", "CRITICAL"),
        ("D_UPDATE_GAP.REFERENCE", "C2.all_runs", "Gap maximum has no reference distribution or requirement.", "UPDATE_GAP", "OPEN", "CAPS_AT_PARTIAL"),
        ("D_PHASE.UNTESTED", "C2.all_runs", "Injection phase was not scanned.", "PHASE", "UNKNOWN", "CAPS_AT_PARTIAL"),
        ("D_CLOCK.CROSS_HOST", "C3.all_runs", "Cross-host clock qualification is incomplete.", "CLOCK", "UNKNOWN", "CAPS_AT_PARTIAL"),
        ("D_TARGET_MISMATCH.CHAIN", "C3.all_runs", "Target lineage is association-grade only.", "TARGET_MISMATCH", "UNKNOWN", "CAPS_AT_PARTIAL"),
        ("D_PHASE.UNTESTED", "C3.all_runs", "Phase sensitivity may alter apparent propagation.", "PHASE", "UNKNOWN", "CAPS_AT_PARTIAL"),
        ("D_DEADLINE.PROVENANCE", "C4.all_runs", "Deadline is retrospective/model-only.", "DEADLINE", "OPEN", "CRITICAL"),
        ("D_BRAKING_CAPABILITY.MODEL", "C5.all_runs", "Braking capability is represented by an in-sample unvalidated model.", "BRAKING_CAPABILITY", "OPEN", "CRITICAL"),
        ("D_GEOMETRY.COMPARABILITY", "C5.all_runs", "Initial clearance/geometry varies and may affect space budgets.", "GEOMETRY", "OPEN", "CAPS_AT_PARTIAL"),
        ("D_GEOMETRY.COMPARABILITY", "C6.all_runs", "Geometry variation limits cross-run effect size.", "GEOMETRY", "BOUNDED", "QUALIFIES"),
        ("D_INITIAL_CLEARANCE", "C7.all_runs", "Initial clearance may differ independently of the intervention.", "INITIAL_CLEARANCE", "OPEN", "CRITICAL"),
        ("D_INITIAL_SPEED", "C7.all_runs", "Initial/approach speed may independently alter the physical outcome.", "INITIAL_SPEED", "OPEN", "CRITICAL"),
        ("D_BRAKING_CAPABILITY", "C7.all_runs", "C5 braking capability is represented by an in-sample model.", "BRAKING_CAPABILITY", "OPEN", "CRITICAL"),
        ("D_FUNCTIONAL_FAILURE", "C7.all_runs", "Functional alternatives are unresolved.", "FUNCTIONAL_FAILURE", "OPEN", "CRITICAL"),
        ("D_TARGET_MISMATCH", "C7.all_runs", "End-to-end target lineage remains partial.", "TARGET_MISMATCH", "UNKNOWN", "CAPS_AT_PARTIAL"),
        ("D_DATA_FRESHNESS", "C7.all_runs", "Freshness degradation is not independently isolated.", "DATA_FRESHNESS", "UNKNOWN", "CAPS_AT_PARTIAL"),
        ("D_UPDATE_GAP", "C7.all_runs", "Update-gap evidence lacks a qualified reference distribution.", "UPDATE_GAP", "OPEN", "CAPS_AT_PARTIAL"),
        ("D_SOLVER_FALLBACK", "C7.all_runs", "Planning fallback/infeasibility may independently contribute.", "SOLVER_FALLBACK", "OPEN", "CRITICAL"),
        ("D_CLOCK", "C7.all_runs", "Cross-host timing remains partially aligned.", "CLOCK", "UNKNOWN", "CAPS_AT_PARTIAL"),
        ("D_PHASE", "C7.all_runs", "Injection phase effects were not scanned.", "PHASE", "UNKNOWN", "CAPS_AT_PARTIAL"),
        ("D_PREHAZARD_STATE", "C7.all_runs", "Fault precedes t1, so D1/v1 may be post-treatment state.", "PREHAZARD_STATE", "OPEN", "CRITICAL"),
        ("D_GEOMETRY", "C7.all_runs", "Geometry and target clearance vary across runs.", "GEOMETRY", "OPEN", "CAPS_AT_PARTIAL"),
        ("D_OUTCOME_CONFLICT", "C7.all_runs", "Outcome sources have not been exhaustively reconciled.", "OUTCOME_CONFLICT", "UNKNOWN", "CAPS_AT_PARTIAL"),
        ("D_DEADLINE", "C7.all_runs", "C4 has no independently qualified timing requirement.", "DEADLINE", "OPEN", "CRITICAL"),
    ]
    rows: List[Dict[str, str]] = []
    for index, (defeater_id, claim_id, description, kind, status, impact) in enumerate(specs, 1):
        scoped_defeater_id = (
            f"{defeater_id}.{claim_id}" if claim_id.startswith("C7.")
            else f"{defeater_id}.{index}"
        )
        rows.append(
            {
                "defeater_id": scoped_defeater_id, "claim_id": claim_id,
                "description": description, "type": kind, "evidence_ids": "",
                "status": status, "resolution": "Requires new independent evidence/audit.",
                "residual_risk": description, "impact_on_claim": impact,
                "notes": "Not hidden or auto-resolved during v1 migration.",
            }
        )
    return rows


def make_fault_and_prehazard(observed: Sequence[Mapping[str, str]]) -> tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    faults: List[Dict[str, object]] = []
    pre: List[Dict[str, object]] = []
    for row in observed:
        run_id = clean(row.get("run_id"))
        t1 = number(row.get("t1_wall_s"))
        relative = number(row.get("scb_trigger_relative_t1_s"))
        onset = t1 + relative if t1 is not None and relative is not None else ""
        faults.append(
            {
                "run_id": run_id, "fault_type": "ADDED_CONTROL_CHANNEL_DELAY",
                "injection_location": "Bridge/SCB control path",
                "requested_magnitude": row.get("bridge_delay_requested_ms") or row.get("scb_requested_delay_ms"),
                "actual_magnitude": row.get("bridge_delay_actual_wall_data_observed_ms") or row.get("scb_actual_wall_delay_ms"),
                "actual_distribution": "PER_RUN_ACTUAL_WALL_DELAY",
                "fault_onset_wall": onset, "fault_end_wall": "", "t1_wall": row.get("t1_wall_s"),
                "trigger_relative_t1_s": row.get("scb_trigger_relative_t1_s"),
                "duration": "UNKNOWN_UNTIL_RUN_END", "persistent_or_transient": "PERSISTENT_SETTING",
                "one_shot_or_repeated": "REPEATED_PER_AFFECTED_MESSAGE", "affected_channel": "Control",
                "affected_message_count": "UNKNOWN", "queue_behavior": "ADDED_DELAY",
                "drop_status": "NOT_ESTABLISHED", "reorder_status": "NOT_ESTABLISHED",
                "evidence_class": "DIRECT_OBSERVED", "confidence": "HIGH",
            }
        )
        if relative is not None and relative < 0:
            for variable, at_t1, source in [
                ("D1", row.get("D1_clear_data_observed_m"), row.get("source_localization_file")),
                ("V1", row.get("v1_data_observed_mps"), row.get("source_localization_file")),
                ("A1", "", row.get("source_localization_file")),
                ("HEADING", "", row.get("source_localization_file")),
                ("ROUTE_PROGRESS", "", row.get("source_localization_file")),
            ]:
                pre.append(
                    {
                        "run_id": run_id, "state_variable": variable,
                        "window_start_wall": onset, "window_end_wall": row.get("t1_wall_s"),
                        "value_at_fault": "", "value_at_t1": at_t1, "delta": "",
                        "source_file": source or "", "availability": "PARTIAL" if clean(at_t1) else "MISSING",
                        "causal_role": "POSSIBLE_MEDIATOR" if variable in {"D1", "V1"} else "UNKNOWN",
                        "evidence_class": "MISSING", "confidence": "LOW",
                        "notes": "Fault precedes t1; value_at_fault is unavailable, so change is not assumed independent.",
                    }
                )
    return faults, pre


def item_state(condition: bool, present: bool = True) -> str:
    if not present:
        return "UNKNOWN"
    return "PASS" if condition else "DEGRADED"


def make_functional(observed: Sequence[Mapping[str, str]]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for row in observed:
        run_id = clean(row.get("run_id"))
        target_count = number(row.get("target_output_count_response_window"))
        planning_stops = number(row.get("planning_stop_count"))
        empty = number(row.get("planning_empty_trajectory_count"))
        infeasible = number(row.get("planning_primal_infeasible_count"))
        fallback = number(row.get("planning_speed_fallback_count"))
        archived = truthy(row.get("control_payload_archived"))
        rows.append(
            {
                "run_id": run_id,
                "physical_target_identity": "PARTIAL" if clean(row.get("target_id")) else "UNKNOWN",
                "perception_target_present": item_state(bool(target_count and target_count > 0), target_count is not None),
                "perception_tracking_continuity": "UNKNOWN",
                "prediction_target_present": "UNKNOWN", "prediction_semantics_valid": "UNKNOWN",
                "planning_stop_present": item_state(bool(planning_stops and planning_stops > 0), planning_stops is not None),
                "planning_stop_target_correct": "UNKNOWN", "planning_stop_location_reasonable": "UNKNOWN",
                "planning_trajectory_valid": "DEGRADED" if (empty or infeasible) else "UNKNOWN",
                "planning_fallback_status": "DEGRADED" if fallback else "UNKNOWN",
                "control_received_relevant_trajectory": "UNKNOWN",
                "control_braking_command_present": "UNKNOWN" if not archived else "PASS",
                "control_command_continuity": "UNKNOWN", "bridge_payload_received": "PASS",
                "bridge_payload_applied": "UNKNOWN",
                "physical_response_observed": "PASS" if clean(row.get("T_e2e_data_observed_ms")) else "UNKNOWN",
                "p_func_verdict": "PARTIAL", "confidence": "MEDIUM",
                "source_evidence_ids": f"EV.PFUNC.{run_id}",
                "notes": "Apollo Guardian is not in this path; Bridge reads Control directly. Presence is not correctness.",
            }
        )
    return rows


def make_clock_rows(observed: Sequence[Mapping[str, str]]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for row in observed:
        rows.append(
            {
                "run_id_or_group": row.get("run_id"), "clock_domain": "wall_epoch_s",
                "host": "Orin+CARLA_server", "timestamp_type": "wall",
                "sync_method": row.get("clock_alignment_status") or "UNKNOWN",
                "offset_estimate_ms": "", "drift_estimate": "",
                "alignment_residual_ms": row.get("clock_alignment_p95_residual_ms"),
                "timestamp_resolution_ms": "", "confidence": "MEDIUM",
                "phase_scan_performed": "FALSE", "phase_effect_verdict": "NOT_TESTABLE",
                "notes": "Main wall interval is retained; cross-host stage decomposition has no dual-clock history.",
            }
        )
    return rows


def make_requirements(observed: Sequence[Mapping[str, str]], model: Sequence[Mapping[str, str]]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for row in observed:
        run_id = clean(row.get("run_id"))
        for suffix, name, value, meaning in [
            ("COLLISION", "same-run reconstructed collision-avoidance budget", row.get("tau_dynamic_data_derived_ms"), "zero-clearance reconstructed budget"),
            ("SAFETY6M", "same-run reconstructed 6 m budget", row.get("tau_dynamic_safety_6m_data_derived_ms"), "internal 6 m analysis margin"),
        ]:
            rows.append(
                {
                    "requirement_id": f"REQ.RETRO.{suffix}.{run_id}", "run_id_or_group": run_id,
                    "requirement_name": name, "requirement_value": value, "unit": "ms",
                    "requirement_provenance": "same-run post-outcome/full-trajectory reconstruction",
                    "pre_registered": "FALSE", "external_or_internal": "INTERNAL_ANALYSIS",
                    "safety_meaning": meaning, "deadline_type": "RETROSPECTIVE_PHYSICAL",
                    "evidence_class": "RETROSPECTIVE_RECONSTRUCTION", "tau_req_low_ms": "",
                    "tau_req_center_ms": value, "tau_req_high_ms": "", "validation_scope": "SAME_RUN_ONLY",
                    "p_deadline_qualification": "NOT_QUALIFIED_PRIMARY",
                    "notes": "Sensitivity/reconstruction only; cannot establish primary C4.",
                }
            )
    for row in model:
        run_id = clean(row.get("run_id"))
        value = row.get("tau_dynamic_model_predicted_ms")
        rows.append(
            {
                "requirement_id": f"REQ.MODEL.{run_id}", "run_id_or_group": run_id,
                "requirement_name": "baseline-calibrated model timing budget", "requirement_value": value,
                "unit": "ms", "requirement_provenance": row.get("model_inputs_and_provenance"),
                "pre_registered": "FALSE", "external_or_internal": "INTERNAL_MODEL",
                "safety_meaning": "predicted zero-clearance timing budget", "deadline_type": "MODEL",
                "evidence_class": "UNVALIDATED_MODEL", "tau_req_low_ms": "",
                "tau_req_center_ms": value, "tau_req_high_ms": "", "validation_scope": "IN_SAMPLE_BASELINE_CALIBRATED",
                "p_deadline_qualification": "NOT_QUALIFIED_PRIMARY",
                "notes": "Not cross-validated or independent; model-supported only.",
            }
        )
    return rows


def make_realtime_rag_placeholders(
    observed: Sequence[Mapping[str, str]],
) -> List[Dict[str, object]]:
    """Keep R/A/G explicit without inventing unavailable legacy tail statistics."""

    total = len(observed)
    reaction_available = sum(
        1 for row in observed if clean(row.get("T_e2e_data_observed_ms"))
    )
    return [
        {
            "dimension": "R", "metric": "physical T_R",
            "source_column": "T_e2e_data_observed_ms", "unit": "ms",
            "semantics": "Legacy observed physical interval; regenerate tail statistics from run data.",
            "group_name": "all_runs", "n_total_runs": total,
            "n_available_runs": reaction_available, "p50": "", "p90": "",
            "p95": "", "p99": "", "max": "", "iqr": "",
        },
        {
            "dimension": "A", "metric": "data age", "source_column": "",
            "unit": "ms", "semantics": "UNAVAILABLE_IN_LEGACY_BOOTSTRAP",
            "group_name": "all_runs", "n_total_runs": total,
            "n_available_runs": 0, "p50": "", "p90": "", "p95": "",
            "p99": "", "max": "", "iqr": "",
        },
        {
            "dimension": "G", "metric": "update gap", "source_column": "",
            "unit": "ms", "semantics": "UNAVAILABLE_IN_LEGACY_BOOTSTRAP",
            "group_name": "all_runs", "n_total_runs": total,
            "n_available_runs": 0, "p50": "", "p90": "", "p95": "",
            "p99": "", "max": "", "iqr": "",
        },
    ]


def make_space_budget_placeholders(
    observed: Sequence[Mapping[str, str]],
) -> List[Dict[str, object]]:
    """Create per-run availability rows without qualifying legacy endpoints."""

    rows: List[Dict[str, object]] = []
    for item in observed:
        response = item.get("D_response_wall_integral_data_observed_m") or item.get(
            "D_delay_wall_integral_data_observed_m"
        )
        rows.append(
            {
                "run_id": item.get("run_id"),
                "group_name": item.get("group_name") or item.get("group") or "",
                "included_main_analysis": item.get("included_main_analysis") or "",
                "outcome_data_observed": item.get("outcome_data_observed") or item.get("outcome") or "",
                "D1_clear_data_observed_m": item.get("D1_clear_data_observed_m") or "",
                "D_response_wall_integral_data_observed_m": response or "",
                "D_brake_data_observed_m": item.get("D_brake_data_observed_m") or "",
                "M0_recomputed_observed_m": "",
                "endpoint_compatible_full_stop": "UNKNOWN",
                "decomposition_scope": "LEGACY_REASSESSMENT_REQUIRES_ENDPOINT_AUDIT",
            }
        )
    return rows


def make_method_completeness_rows() -> List[Dict[str, str]]:
    items = [
        ("Evidence/model separation", "STRUCTURALLY_COMPLETED", "v2 evidence classes and taint are emitted."),
        ("Claim Graph and six-layer gates", "STRUCTURALLY_COMPLETED", "Canonical claims and edges are bootstrapped conservatively."),
        ("Executable I-M-E-C-O-N gates", "PARTIAL", "Fields exist; raw-data-specific criteria require regeneration."),
        ("Temporal Fault Signature", "PARTIAL", "End/duration/message/drop/reorder fields may remain missing."),
        ("R/A/G tail latency", "NOT_ESTABLISHED", "Bootstrap does not invent unavailable distributions."),
        ("Strict cause-effect lineage", "NOT_ESTABLISHED", "Explicit event/sequence/provenance lineage is still required."),
        ("Independent tau_req", "NOT_ESTABLISHED", "Retrospective/model deadlines remain ineligible for primary C4."),
        ("Observed primary Distance Debt", "NOT_ESTABLISHED", "Requires qualified tau_req plus observed velocity ancestry."),
        ("Observed space budget", "PARTIAL", "Endpoint compatibility requires a raw-data audit."),
        ("Continuous physical safety scale", "PARTIAL", "Threshold provenance still requires review."),
        ("Functional correctness", "PARTIAL", "P_FUNC remains conservative until semantic links are qualified."),
        ("Clock/phase uncertainty", "NOT_ESTABLISHED", "Offset/drift/resolution and an active phase scan remain required."),
        ("Pre-hazard state divergence", "PARTIAL", "Missing pre-fault history remains missing."),
        ("Paper-level method validity", "NOT_ESTABLISHED", "Requires controls, multiple levels, independent and cross-system validation."),
    ]
    return [
        {"requirement": requirement, "status": status, "evidence_or_gap": evidence_or_gap}
        for requirement, status, evidence_or_gap in items
    ]


def reassessment_markdown() -> str:
    items = [
        ("1. ‘300 ms在闭环物理响应端被放大’", "REFRAMED", "Only one non-zero intervention level exists. Use an observed incremental response ratio, not amplification/gain."),
        ("2. ‘300 ms → 449.543 ms’", "UNCHANGED", "The descriptive observed delta may remain if endpoint and uncertainty are stated; it is not a stable transfer coefficient."),
        ("3. L2 Fusion degradation", "REFRAMED", "A Fusion maximum is case-level characterization. No reference distribution/requirement supports group degradation."),
        ("4. L3 Cause-Effect Timing", "DOWNGRADED", "Lineage is grade C temporal alignment, not explicit trace/provenance lineage."),
        ("5. tau_data_derived evidence qualification", "DOWNGRADED", "Reclassified as tau_retro: useful for reconstruction, ineligible as primary independent deadline."),
        ("6. 1202/1211 model deadline miss", "MODEL_ONLY", "The deadline and miss are unvalidated-model outputs, not observed temporal failures."),
        ("7. 1131 Distance Debt 5.018 m", "MODEL_ONLY", "Debt inherits the model deadline taint; D_response remains separately observed."),
        ("8. 1643 Distance Debt 10.309 m", "MODEL_ONLY", "Debt inherits the model deadline taint; it cannot enter the observed primary chain."),
        ("9. 1131 timing-dominated candidate", "DOWNGRADED", "At most a candidate: C4 is not testable, P_FUNC is partial, and critical defeaters remain open."),
        ("10. 1643 multi-factor", "REFRAMED", "Multi-factor is the conservative class, but individual contributions are not quantified."),
        ("11. ‘functionally correct, temporally wrong’", "NOT_TESTABLE", "P_FUNC is not QUALIFIED_PASS and C4 is not established."),
        ("12. Current six-layer overall claim", "DOWNGRADED", "L1 PASS, L2 PARTIAL, L3 PARTIAL, L4 NOT_TESTABLE, L5 MODEL_SUPPORTED_ONLY, L6 PASS. Strong ends do not close weak middle claims."),
    ]
    lines = [
        "# Legacy report v1 -> TCPS-PA v2 claim reassessment", "",
        "## Six-Layer Inference Status Matrix", "",
        "| Layer | v2 verdict | Evidence ceiling | Main reason |", "|---|---|---|---|",
        "| L1 / C1 | PASS | HIGH | Bridge/SCB disturbance is directly observed. |",
        "| L2 / C2 | PARTIAL_PASS | MEDIUM | T_R is observed; gap reference/distribution and phase scan are incomplete. |",
        "| L3 / C3 | PARTIAL_PASS | MEDIUM | Causal lineage grade C and clocks are partial. |",
        "| L4 / C4 | NOT_TESTABLE | LOW | No independently qualified deadline. |",
        "| L5 / C5 | MODEL_SUPPORTED_ONLY | LOW | D_response is observed; deadline-excess debt is model-tainted. |",
        "| L6 / C6 | PASS | MEDIUM | Physical outcomes are directly observed; attribution remains separate. |",
        "| Attribution / C7 | PARTIAL_PASS (Level 2 max) | LOW | Weak C4/C5 and open functional/pre-hazard defeaters cap attribution. |",
        "", "## Claim-by-claim decisions", "",
    ]
    for title, status, reason in items:
        lines.extend([f"### {title}", "", f"**{status}** — {reason}", ""])
    lines.extend(
        [
            "## Diagnostic conclusion", "",
            "The experiment directly establishes the injected disturbance and physical outcomes. It supports temporal association and an unvalidated-model propagation mechanism, but it does not establish a primary temporal deadline failure or qualified observed Distance Debt. The most important missing evidence is an independent scenario deadline and requirement-constrained L5 debt, followed by end-to-end lineage, cross-host clock qualification, functional-chain qualification, and pre-hazard state history.", "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap TCPS-PA v2 ledgers from legacy generated outputs")
    parser.add_argument("--analysis-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    root = parse_args().analysis_dir.resolve()
    tables = root / "tables"
    observed_path = tables / "run_level_observed.csv"
    model_path = tables / "run_level_model_predicted.csv"
    observed = read_csv(observed_path)
    model = read_csv(model_path)
    if not observed:
        raise SystemExit(f"No observed run table found or table is empty: {observed_path}")

    evidence = make_evidence(observed, model, observed_path, model_path)
    claims = make_claims(evidence)
    edges = make_edges(claims)
    defeaters = make_defeaters()
    defeater_ids_by_claim: Dict[str, List[str]] = {}
    for row in defeaters:
        defeater_ids_by_claim.setdefault(clean(row.get("claim_id")), []).append(
            clean(row.get("defeater_id"))
        )
    for row in claims:
        row["defeater_ids"] = "|".join(
            defeater_ids_by_claim.get(clean(row.get("claim_id")), [])
        )
    faults, pre_hazard = make_fault_and_prehazard(observed)

    write_csv(tables / "evidence_ledger.csv", EVIDENCE_FIELDS, evidence)
    write_csv(tables / "claim_ledger.csv", CLAIM_FIELDS, claims)
    write_csv(tables / "claim_edges.csv", EDGE_FIELDS, edges)
    write_csv(tables / "defeater_ledger.csv", DEFEATER_FIELDS, defeaters)
    write_csv(tables / "temporal_fault_signature.csv", FAULT_FIELDS, faults)
    write_csv(tables / "pre_hazard_state_audit.csv", PRE_HAZARD_FIELDS, pre_hazard)
    write_csv(tables / "functional_correctness_audit.csv", FUNCTION_FIELDS, make_functional(observed))
    write_csv(tables / "clock_phase_audit.csv", CLOCK_FIELDS, make_clock_rows(observed))
    write_csv(tables / "requirement_registry.csv", REQUIREMENT_FIELDS, make_requirements(observed, model))
    write_csv(tables / "realtime_rag_summary.csv", RAG_FIELDS, make_realtime_rag_placeholders(observed))
    write_csv(tables / "space_budget_decomposition_observed.csv", SPACE_RUN_FIELDS, make_space_budget_placeholders(observed))
    write_csv(tables / "space_budget_group_decomposition.csv", SPACE_GROUP_FIELDS, [])
    write_csv(tables / "method_completeness_matrix.csv", METHOD_FIELDS, make_method_completeness_rows())

    validation_dir = root / "validation"
    validation_dir.mkdir(parents=True, exist_ok=True)
    (validation_dir / "claim_audit.md").write_text(
        claim_audit_markdown(claims, evidence, defeaters), encoding="utf-8"
    )
    (validation_dir / "v1_to_v2_claim_reassessment.md").write_text(
        reassessment_markdown(), encoding="utf-8"
    )
    print(f"Wrote TCPS-PA v2 ledgers for {len(observed)} runs under {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
