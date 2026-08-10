# Output and report contract

## 1. Minimum artifact set

Write generated files below a dedicated analysis directory:

```text
<analysis-dir>/
├── report/
│   └── six_layer_analysis_report.md
├── tables/
│   ├── run_level_observed.csv
│   ├── run_level_model_predicted.csv
│   ├── layer_evidence_matrix.csv
│   ├── event_timeline.csv
│   ├── stage_timing_and_freshness.csv
│   ├── record_timing_diagnostics.csv
│   ├── group_summary_observed.csv
│   └── exclusions_and_missing.csv
├── record_profiles/
│   └── <run-id>.json
├── figures/
├── validation/
│   ├── input_inventory.json
│   ├── data_quality_audit.md
│   └── validation.json
└── scripts/ or README.md describing reproduction commands
```

If the task is a single-run analysis, keep the same contracts with one observed row. Do not omit unavailable columns merely because one run cannot populate them.

## 2. Required observed table fields

Use explicit names. The following is a minimum, extendable schema:

### Identity and status

- `group_name`
- `run_id`
- `included_main_analysis`
- `analysis_status`
- `outcome_data_observed`
- `collision_event_data_observed`
- `missing_reason`

### Endpoints and time bases

- `t1_wall_s`
- `t2_wall_s`
- `t_deadline_data_derived_s` when available
- `T_e2e_data_observed_ms`
- `time_basis_main`
- `clock_alignment_status`

### Layer 1

- `nominal_injected_delay_ms`
- `bridge_delay_requested_ms`
- `bridge_delay_actual_wall_data_observed_ms`
- `bridge_delay_lifecycle_status`

### Layers 2 and 3

- stage latency fields with `_data_observed_ms` or explicit diagnostic names;
- `data_age_*_data_observed_ms` fields;
- `update_gap_*_data_observed_ms` fields;
- `planning_age_*_data_observed_ms` and reuse fields;
- `reaction_time_message_diagnostic_ms` kept distinct from physical `T_e2e`.

### Layers 4 and 5

- `tau_dynamic_data_derived_ms`
- `timing_slack_data_derived_ms`
- `deadline_miss_data_derived`
- `D1_clear_data_observed_m`
- `D_delay_wall_integral_data_observed_m`
- `D_delay_sim_observed_m` only as a diagnostic when available
- `e2e_sim_frames` only as a diagnostic when available
- `realtime_factor` only as a diagnostic when available
- `D_distance_debt_data_derived_m`
- `D2_clear_data_observed_m`

### Layer 6

- `D_brake_data_observed_m`
- `D_brake_truncated_to_collision_data_observed_m`
- `final_clearance_data_observed_m`
- `M_collision_0m_data_observed_m`
- `M_safety_required_data_observed_m`
- `impact_speed_data_observed_mps`
- `physical_outcome_confidence`

When a field is unavailable, leave it empty/NA and populate `missing_reason` or a dedicated field-level audit table.

## 3. Required model table fields

At minimum:

- `run_id`
- model name/version;
- model inputs and provenance;
- `tau_dynamic_model_predicted_ms`;
- `D_brake_model_predicted_m`;
- `D_distance_debt_model_predicted_m` when applicable;
- `M_safety_model_predicted_m`;
- `collision_model_predicted`;
- `impact_speed_model_predicted_mps`;
- assumptions and scope note;
- compatible observed comparator;
- signed, absolute, and relative error fields when validation is possible.

Never place a model-predicted collision, stopping distance, or margin in the observed table without the model marker.

## 4. Layer evidence matrix

One row per important claim/metric:

| Field | Meaning |
|---|---|
| `layer` | L1-L6 |
| `question` | question being answered |
| `metric` | metric or qualitative finding |
| `run_id_or_group` | scope |
| `value` | result |
| `unit` | unit |
| `evidence_type` | direct observed, data-derived, diagnostic, model-predicted |
| `time_basis` | wall/header/record/monotonic/sim/frame |
| `source_file` | source path |
| `source_locator` | columns, rows, trace ID, sequence, or log lines |
| `availability` | available/unavailable/uncertain |
| `confidence` | high/medium/low with reason |

## 5. Report structure

Use this answer-first structure:

```markdown
# [Experiment] temporal correctness to physical safety analysis

## Executive conclusion
## Scope, architecture, and experiment groups
## Data inventory, clocks, endpoints, and quality limits
## L1 Temporal disturbance
## L2 Temporal degradation
## L3 Cause-effect timing
## L4 Temporal correctness and dynamic deadline
## L5 Temporal-to-physical propagation
## L6 Observed physical safety outcomes
## Cross-run comparison and causal audit
## Model/predicted comparison (separate from observed results)
## Limitations and next experiment recommendations
## Per-run observed results
```

The executive conclusion should state:

1. whether the intervention was verified;
2. whether physical `T_R` and wall-integrated response distance changed;
3. whether a dynamic deadline was available and missed;
4. whether measured margin/outcome changed;
5. the strongest defensible causal claim and its main confounders.

## 6. Figures

Choose figures that expose the chain rather than decorate the report:

- intervention actual-versus-requested delay;
- per-run `T_R`, deadline, and timing slack;
- VT trajectories aligned at `t1`;
- distance budget or ST trajectories aligned at `t1`;
- stage latency/freshness/gap comparison;
- response distance versus observed margin/outcome;
- collision run versus matched safe control.

Label axes with unit and time basis. Mark `t1`, `t2`, `t_deadline`, stop, and collision when available. Do not connect missing values as though observed.

## 7. Statistical reporting

- Show every run before group summaries.
- Report `n total`, `n available`, and `n excluded` for each metric.
- Prefer median/p90/max for timing tails; include mean/SD when useful.
- Do not treat repeated frames within one run as independent experimental replicates.
- Use matched-run or controlled comparisons when initial speed/clearance differ materially.
- State small-sample limits; avoid significance claims without a justified design.

## 8. Validation checks

The final validation must check:

- all required artifact paths;
- observed and model tables are separate;
- the observed table contains a wall-integral response-distance field;
- no observed column is populated from an identically named model column;
- required endpoint/time-basis columns exist;
- every excluded/unavailable run has a reason;
- collision runs do not claim a full observed stop unless supported by an actual post-collision trajectory and declared endpoint;
- report links/figure paths exist;
- source paths in the evidence matrix are present or explicitly external;
- formulas and units are internally consistent.

## 9. Reproducibility note

Include exact commands, configuration paths, dependency versions when material, and a statement that raw experiment directories were not modified. Separate parser execution, table generation, figure generation, and validation so each stage can be rerun and audited.
