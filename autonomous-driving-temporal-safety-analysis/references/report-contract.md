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
11. Real-time engineering and paper-method completeness

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
│   ├── clock_alignment_audit.csv
│   ├── phase_audit.csv
│   ├── requirement_registry.csv
│   ├── dynamic_deadline_construction.csv
│   ├── velocity_trajectory_observed.csv
│   ├── l5_recomputation.csv
│   ├── diagnosis_hypothesis_ledger.csv
│   ├── diagnosis_edges.csv
│   ├── event_timeline.csv
│   ├── stage_timing_and_freshness.csv
│   ├── record_timing_diagnostics.csv
│   ├── group_summary_observed.csv
│   ├── realtime_rag_summary.csv
│   ├── space_budget_decomposition_observed.csv
│   ├── space_budget_group_decomposition.csv
│   ├── method_completeness_matrix.csv
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

The four real-time engineering tables above are required for a full experiment analysis. They may contain explicitly unavailable rows when source evidence is missing; do not omit the artifact or fabricate values. They are not required in `--mode record-only`, where L4-L6 are deliberately unavailable.

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

Operationally required C1-C7 gate extensions for a full experiment analysis:

- `gate_inputs`
- `gate_metrics`
- `admissible_evidence`
- `gate_criterion`
- `next_gate_condition`

Recommended additional extensions: `causal_lineage_grade`, `deadline_basis`, and `critical_claim`.

These five gate fields encode I/M/E/C/N. The canonical verdict, confidence/ceiling, maximum claim level, allowed/forbidden language, and residual uncertainty encode O. Empty gate text is not a completed gate.

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

Legacy compatibility only. New full analyses must also emit the separated schemas below.

### 4.4a `clock_alignment_audit.csv`

Minimum:

- `run_id_or_group`, `comparison_id`, `clock_domain_a`, `clock_domain_b`;
- `host_a`, `host_b`, `timestamp_type_a`, `timestamp_type_b`;
- `sync_method`, `anchor_method`, `offset_estimate_ms`, `drift_ppm`;
- `alignment_residual_ms`, `timestamp_resolution_ms`, `jitter_ms`, `dispersion_ms`, `error_budget_ms`;
- `comparison_tolerance_ms`, `p_clock_verdict`, `confidence`, `source_evidence_ids`, `notes`.

### 4.4b `phase_audit.csv`

Minimum:

- `run_id_or_group`, `phase_pair_id`, `producer`, `consumer`;
- `producer_period_ms`, `consumer_period_ms`, `phase_origin`, `phase_offset_ms`;
- `carla_fixed_delta_ms`, `injection_phase_ms`, `phase_to_tick_ms`;
- `phase_scan_performed`, `scan_levels`, `repeats_per_level`;
- `effect_metric`, `effect_estimate`, `effect_uncertainty`, `phase_effect_verdict`;
- `p_phase_verdict`, `confidence`, `source_evidence_ids`, `notes`.

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

### 4.5a `dynamic_deadline_construction.csv`

Use the complete schema in [dynamic-deadline-contract.md](dynamic-deadline-contract.md). A constructed deadline used by P_DEADLINE/C4 must be `QUALIFIED_DYNAMIC_PHYSICAL` and linked by exact `requirement_id`.

### 4.6 `realtime_rag_summary.csv`

Minimum:

- `dimension` (`R`, `A`, or `G`)
- `metric`
- `source_column`
- `unit`
- `semantics`
- `group_name`
- `n_total_runs`
- `n_available_runs`
- `p50`, `p90`, `p95`, `p99`, `max`
- `iqr` or another explicitly named robust spread field

R/A/G rows must preserve semantic identity. Message reaction, physical `T_R`, data age, and output gap are not interchangeable.

### 4.7 Observed space-budget tables

`space_budget_decomposition_observed.csv` minimum:

- `run_id`, `group_name`, `included_main_analysis`, `outcome_data_observed`
- `D1_clear_data_observed_m`
- `D_response_wall_integral_data_observed_m`
- `D_brake_data_observed_m`
- `M0_recomputed_observed_m`
- `endpoint_compatible_full_stop`
- `decomposition_scope`

`space_budget_group_decomposition.csv` minimum:

- `comparison_group`, `n`
- `D1_mean_m`, `D_response_mean_m`, `D_brake_mean_m`, `M0_mean_m`

Only endpoint-compatible observed full stops enter full-stop group decompositions. Collision/right-censored runs remain explicit but unavailable.

### 4.8 `method_completeness_matrix.csv`

Minimum:

- `requirement`
- `status`
- `evidence_or_gap`

At minimum audit: evidence/model separation, Claim Graph/gates, Temporal Fault Signature, R/A/G tails, strict lineage, independent `tau_req`, observed primary Distance Debt, space budget, continuous safety scale, P_FUNC, clock/phase, pre-hazard divergence, and paper-level validation design. Distinguish structural completion from empirical completion.

### 4.9 `velocity_trajectory_observed.csv` and `l5_recomputation.csv`

Velocity input minimum:

- `run_id`, `sample_index`, `t_wall_s`, `speed_mps`, `clock_domain`;
- `source_file`, `source_locator`, `availability`, `quality_flags`.

Recomputation output minimum:

- `run_id`, `requirement_id`, `t1_wall_s`, `t_deadline_wall_s`, `te_wall_s`;
- `D_response_recomputed_m`, `D_debt_recomputed_m`;
- `D_response_reported_m`, `D_debt_reported_m`;
- `D1_observed_m`, `D_brake_observed_m`, `M0_recomputed_m`, `M0_reported_m`;
- `endpoint_coverage`, `max_abs_error_m`, `tolerance_m`, `recomputation_status`, `notes`.

### 4.10 Backward diagnosis tables

`diagnosis_hypothesis_ledger.csv` minimum:

- `hypothesis_id`, `run_id_or_group`, `seed_claim_id`, `seed_evidence_ids`;
- `candidate_layer`, `candidate_component`, `candidate_fault_type`, `hypothesis`;
- `path_claim_ids`, `supporting_evidence_ids`, `challenging_evidence_ids`, `alternative_hypothesis_ids`;
- `required_prerequisite_claim_ids`, `diagnosability_class`, `equivalence_class_id`;
- `status`, `rank_score`, `rank_method`, `maximum_diagnosis_strength`;
- `discriminating_test`, `residual_uncertainty`, `allowed_language`, `forbidden_language`.

`diagnosis_edges.csv` minimum:

- `parent_id`, `child_id`, `relation`, `time_direction`, `required`, `notes`.

Allowed relations are `SEEDS_DIAGNOSIS`, `CONSISTENT_WITH`, `CHALLENGED_BY`, and `DISCRIMINATES`; `time_direction` must be `BACKWARD_DIAGNOSTIC`.

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
## Report positioning and method-completeness matrix
## Scope, architecture, intervention, and references
## Event semantics and executable gate definitions
## Evidence, clocks/phase, targets, functionality, pre-hazard state, and deadline qualification
## Forward fault-injection analysis and backward temporal-defect diagnosis
## L1 Temporal Fault Signature
## L2 Temporal Degradation and R/A/G tails
## L3 Cause-Effect Temporal Propagation
## L4 Temporal Correctness
## L5 Temporal-to-Physical Propagation and observed space budget
## L6 Continuous Physical Safety Degradation
## C7 Temporal Safety Attribution
## Model/retrospective analyses (separate)
## Open defeaters and residual uncertainty
## Per-run observed results
## Method limitations and future experiment requirements
## Reproducibility
```

For each L1-L6 section and C7 use:

- Scientific Claim
- I / Inputs and Required Preconditions
- M / Metrics, units, clocks, endpoints, and aggregation scope
- E / Admissible Evidence, support, counter-evidence, and Open Defeaters
- C / Falsifiable criterion and Inference Rule
- O / Verdict, Confidence, ceiling, Allowed Conclusion, and residual uncertainty
- N / Next Gate Condition
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

Use the user's requested language for the main narrative. For a Chinese deliverable, write headings, explanations, conclusions, caveats, and table descriptions in Chinese; retain canonical IDs, formulas, schema fields, file paths, and verdict enums as needed. Do not let a renderer fall back to English halfway through the report.

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

## 11. Real-time engineering and paper-method completeness

Treat a full report as three separately auditable products:

1. **Real-time-systems engineering report:** architecture and executed chain, event/clock semantics, complete fault signature, R/A/G tails, P_FUNC, clock/phase, pre-hazard state, space budget, continuous physical outcome, and small-n/availability limits.
2. **Six-layer method instantiation:** scoped prerequisite claims, canonical Claim Graph, I-M-E-C-O-N gates, evidence/defeater reciprocity, weakest-link ceilings, and allowed language.
3. **Future-paper method record:** formulas/algorithm, data selection and missingness rules, observed/model error analysis, reproducibility, validity threats, and the next experiment needed to close each empirical bridge.

The report must state whether each product is structurally instantiated, empirically supported, partially supported, or not established. In particular, do not call the method empirically complete when independent requirements, record-enabled lineage, active phase scans, functional qualification, multiple nonzero fault levels, negative controls, or cross-system validation are absent.
