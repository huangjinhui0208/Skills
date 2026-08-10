# TCPS-PA v2 output and report contract

## Contents

1. Generation order
2. Minimum artifact set
3. Ledger schemas
4. Required audit-table schemas
5. Observed/model tables
6. Report structure
7. Inference Status Matrix
8. Executive conclusion
9. Figures/statistics
10. Validation and reproducibility

## 1. Generation order

Do not generate prose directly from metrics. Use:

`Evidence Ledger -> Prerequisite Claims -> Claim Graph -> Defeater Ledger -> Inference Gates -> Claim Strength -> Report`

The report is a view of the validated Claim Ledger, not an independent source of conclusions.

## 2. Minimum artifact set

```text
<analysis-dir>/
├── report/
│   └── six_layer_analysis_report.md
├── tables/
│   ├── run_level_observed.csv
│   ├── run_level_model_predicted.csv
│   ├── evidence_ledger.csv
│   ├── claim_ledger.csv
│   ├── claim_edges.csv
│   ├── defeater_ledger.csv
│   ├── temporal_fault_signature.csv
│   ├── pre_hazard_state_audit.csv
│   ├── functional_correctness_audit.csv
│   ├── clock_phase_audit.csv
│   ├── requirement_registry.csv
│   ├── event_timeline.csv
│   ├── stage_timing_and_freshness.csv
│   ├── record_timing_diagnostics.csv
│   ├── group_summary_observed.csv
│   └── exclusions_and_missing.csv
├── record_profiles/
├── figures/
├── validation/
│   ├── input_inventory.json
│   ├── data_quality_audit.md
│   ├── claim_audit.md
│   ├── validation.json
│   └── v1_to_v2_claim_reassessment.md    # required for a legacy reassessment
└── scripts/ or a reproduction note
```

`layer_evidence_matrix.csv` may remain as a compatibility view of `evidence_ledger.csv`, but it cannot replace the v2 ledger.

For a record-only availability audit, use validator mode `--mode record-only`. The reduced profile requires `record_profiles/*.json` plus `tables/record_timing_diagnostics.csv` and deliberately keeps L4-L6 physical claims `NOT_TESTABLE`; it does not require fabricated empty full-experiment tables.

## 3. Ledger schemas

### 3.1 `evidence_ledger.csv`

Required fields:

- `evidence_id`
- `run_id`
- `layer`
- `metric`
- `value`
- `unit`
- `evidence_class`
- `clock_domain`
- `source_file`
- `source_locator`
- `availability`
- `confidence`
- `supports_claim_ids`
- `challenges_claim_ids`
- `limitations`

Recommended extensions: `taint_tags`, `reference_type`, `distribution_scope`, `causal_lineage_grade`, `endpoint_definition`, `semantic_role`, `requirement_id`, `host`, and `timestamp_type`.

For evidence used by C4 or C6, `semantic_role` is operationally required:

- physical reaction evidence: `PHYSICAL_REACTION_INTERVAL` plus canonical metric `T_R` or `T_e2e_data_observed_ms`;
- physical outcome evidence: `PHYSICAL_OUTCOME` plus a canonical collision, clearance, margin, or impact metric.

A Control command, Planning STOP, chassis message, or metric merely containing the word `reaction` cannot satisfy these roles.

Every deadline evidence row used by C4 must carry `requirement_id` matching a qualified same-scope row in `requirement_registry.csv`; a self-declared evidence class and an unrelated registry row cannot be combined.

Every evidence ID must be unique. Claim links use `|`-separated exact scoped IDs.

### 3.2 `claim_ledger.csv`

Required fields:

- `claim_id`
- `layer`
- `run_id_or_group`
- `proposition`
- `prerequisite_claim_ids`
- `required_evidence_classes`
- `supporting_evidence_ids`
- `challenging_evidence_ids`
- `defeater_ids`
- `inference_rule_id`
- `verdict`
- `confidence`
- `confidence_ceiling`
- `maximum_claim_level`
- `residual_uncertainty`
- `allowed_language`
- `forbidden_language`

Recommended extensions: `causal_lineage_grade`, `deadline_basis`, `gate_criterion`, and `critical_claim`.

Use exact scoped IDs such as `P_CLOCK.group`, `C4.1131`, and `C7.group`. Do not store unscoped prerequisites when multiple scopes exist.

### 3.3 `claim_edges.csv`

Required fields:

- `parent_claim_id`
- `child_claim_id`
- `relation`
- `required`
- `notes`

Relations: `REQUIRES`, `SUPPORTS`, `CHALLENGES`, `QUALIFIES`, or `BOUNDS`.

### 3.4 `defeater_ledger.csv`

Required fields:

- `defeater_id`
- `claim_id`
- `description`
- `type`
- `evidence_ids`
- `status`
- `resolution`
- `residual_risk`
- `impact_on_claim`
- `notes`

States: `OPEN`, `BOUNDED`, `RESOLVED`, `REFUTED`, `NOT_APPLICABLE`, `UNKNOWN`. Mark critical impact explicitly, for example `CRITICAL`, `INVALIDATES`, or `CAPS_AT_PARTIAL`.

## 4. Required audit-table schemas

### 4.1 `temporal_fault_signature.csv`

Minimum:

- `run_id`
- `fault_type`
- `injection_location`
- `requested_magnitude`
- `actual_magnitude`
- `actual_distribution`
- `fault_onset_wall`
- `fault_end_wall`
- `t1_wall`
- `trigger_relative_t1_s`
- `duration`
- `persistent_or_transient`
- `one_shot_or_repeated`
- `affected_channel`
- `affected_message_count`
- `queue_behavior`
- `drop_status`
- `reorder_status`
- `evidence_class`
- `confidence`

### 4.2 `pre_hazard_state_audit.csv`

Minimum:

- `run_id`
- `state_variable`
- `window_start_wall`
- `window_end_wall`
- `value_at_fault`
- `value_at_t1`
- `delta`
- `source_file`
- `availability`
- `causal_role`
- `evidence_class`
- `confidence`
- `notes`

Include D1, v1, a1, heading, and route progress rows when fault onset precedes t1. `causal_role` must be `PRE_EXISTING_CONFOUNDER`, `POSSIBLE_MEDIATOR`, `POST_TREATMENT_STATE`, or `UNKNOWN`.

### 4.3 `functional_correctness_audit.csv`

Minimum functional fields:

- `run_id`
- `physical_target_identity`
- `perception_target_present`
- `perception_tracking_continuity`
- `prediction_target_present`
- `prediction_semantics_valid`
- `planning_stop_present`
- `planning_stop_target_correct`
- `planning_stop_location_reasonable`
- `planning_trajectory_valid`
- `planning_fallback_status`
- `control_received_relevant_trajectory`
- `control_braking_command_present`
- `control_command_continuity`
- `bridge_payload_received`
- `bridge_payload_applied`
- `physical_response_observed`
- `p_func_verdict`
- `confidence`
- `source_evidence_ids`
- `notes`

Item states are `PASS`, `DEGRADED`, `FAIL`, or `UNKNOWN`; P_FUNC is `QUALIFIED_PASS`, `PARTIAL`, `FAIL`, or `NOT_TESTABLE`.

### 4.4 `clock_phase_audit.csv`

Minimum:

- `run_id_or_group`
- `clock_domain`
- `host`
- `timestamp_type`
- `sync_method`
- `offset_estimate_ms`
- `drift_estimate`
- `alignment_residual_ms`
- `timestamp_resolution_ms`
- `confidence`
- `phase_scan_performed`
- `phase_effect_verdict`
- `notes`

### 4.5 `requirement_registry.csv`

Minimum:

- `requirement_id`
- `run_id_or_group`
- `requirement_name`
- `requirement_value`
- `unit`
- `requirement_provenance`
- `pre_registered`
- `external_or_internal`
- `safety_meaning`
- `deadline_type`
- `evidence_class`
- `tau_req_low_ms`
- `tau_req_center_ms`
- `tau_req_high_ms`
- `validation_scope`
- `p_deadline_qualification`
- `notes`

## 5. Observed/model tables

### 5.1 Observed table

Keep identity/status, endpoints, L1 fields, timing/freshness, physical outcomes, and missing reasons. Required core fields include:

- `run_id`, `analysis_status`, `included_main_analysis`, `missing_reason`;
- `t1_wall_s`, `t2_wall_s`, `T_e2e_data_observed_ms`, `time_basis_main`, `clock_alignment_status`;
- `D_response_wall_integral_data_observed_m`;
- deprecated alias `D_delay_wall_integral_data_observed_m` when legacy consumers need it;
- D1/D2, collision, full/truncated braking, final/minimum clearance, margins, impact, strict/near-stop fields when available.

Do not place model or retrospective requirement values into observed primary-deadline/debt fields. A same-run full-stop deadline must be named `tau_retro_*`, and its debt `D_debt_retro_diagnostic_*`.

### 5.2 Model table

Keep model name/version, inputs/provenance, validation class, deadlines, braking/impact predictions, model-tainted debt, assumptions, comparator compatibility, signed/absolute/relative error, and scope. Model values never fill observed fields.

### 5.3 Distance naming

Canonical v2:

- `D_response_wall_integral_data_observed_m`: total t1-to-t2 response distance;
- `D_debt_requirement_constrained_derived_m`: primary debt from qualified tau_req;
- `D_debt_retro_diagnostic_m`: retrospective diagnostic;
- `D_debt_model_predicted_m`: model-tainted debt.

## 6. Report structure

```markdown
# [Experiment] TCPS-PA v2 analysis

## Six-Layer Inference Status Matrix
## Executive conclusion constrained by Claim Ledger
## Scope, architecture, intervention, and references
## Evidence, clocks, targets, functionality, and deadline qualification
## L1 Temporal Fault Signature
## L2 Temporal Degradation
## L3 Cause-Effect Temporal Propagation
## L4 Temporal Correctness
## L5 Temporal-to-Physical Propagation
## L6 Physical Safety Degradation
## C7 Temporal Safety Attribution
## Model/retrospective analyses (separate)
## Open defeaters and residual uncertainty
## Per-run observed results
## Reproducibility
```

For each L1-L6 section use:

- Scientific Claim
- Required Preconditions
- Evidence
- Counter-evidence
- Open Defeaters
- Inference Rule
- Verdict
- Confidence
- Allowed Conclusion
- What Remains Unproven

Do not use “this layer's results are...” as a substitute for the gate.

## 7. Six-Layer Inference Status Matrix

The first analytical table must show, at minimum:

| Layer/claim | Verdict | Evidence basis | Confidence | Ceiling | Open critical defeaters | Allowed claim |
|---|---|---|---|---|---|---|

Example:

```text
L1/C1 PASS / DIRECT_OBSERVED / HIGH
L2/C2 PARTIAL_PASS / OBSERVED_DERIVED / MEDIUM
L3/C3 PARTIAL_PASS / LINEAGE C / MEDIUM
L4/C4 NOT_TESTABLE / RETROSPECTIVE+UNVALIDATED_MODEL / LOW
L5/C5 MODEL_SUPPORTED_ONLY / MODEL_TAINT / LOW
L6/C6 PASS / DIRECT_OBSERVED / HIGH
```

All six gates must appear even when NOT_TESTABLE.

## 8. Executive conclusion

Generate from Claim Ledger after semantic validation. It must:

1. state direct observed facts;
2. state C2/C3 qualification and lineage grade;
3. state whether a qualified independent deadline exists;
4. distinguish primary, retrospective, and model distance debt;
5. state C6 outcome evidence;
6. name open critical defeaters;
7. use language at or below the overall weakest-link ceiling.

Strong C1 and C6 cannot hide weak C4/C5. When C4 is not testable and C5 is model-supported, say so explicitly and do not claim a complete propagation proof.

## 9. Figures and statistics

Figures should expose evidence and claim boundaries:

- actual versus requested fault signature;
- T_R and qualified/retro/model deadlines using distinct encodings;
- R/A/G distributions and declared references;
- VT/ST trajectories with clock/endpoints;
- canonical response distance versus requirement/retro/model debt;
- space-budget decomposition into D1, D_response, D_brake;
- continuous safety severity/outcome;
- claim graph/status matrix when useful.

Show every run, total/available/excluded counts, and small-n limits. Repeated frames are not experimental replicates. Do not connect missing values.

## 10. Validation and reproducibility

Validation must cover:

- required files and schemas;
- source paths and formulas;
- observed/model/right-censoring rules;
- Claim Graph prerequisite closure;
- evidence-class admissibility;
- retrospective/model taint propagation;
- P_CLOCK/P_TARGET/P_FUNC/P_DEADLINE gates;
- open critical defeaters;
- confidence ceilings;
- pre-hazard causal-role audit;
- claim-language legality and forbidden patterns;
- complete `validation/claim_audit.md`.

Include exact parser, ledger-generation, report-generation, and validation commands. State that raw data were not modified.
