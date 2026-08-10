---
name: autonomous-driving-temporal-safety-analysis
description: Analyze CARLA/Apollo autonomous-driving experiments and Apollo cyber record parsed exports with the six-layer temporal-correctness-to-physical-safety framework. Use this skill whenever a user asks about autonomous-driving delay, jitter, backlog, stale data, update gaps, end-to-end reaction time, dynamic deadline, timing slack, distance debt, braking margin, near miss, collision causality, bridge delay injection, Trace/log/record fusion, or wants a per-run or cross-run timing-safety report—even if they do not explicitly mention the six layers. It is specialized for raw-data-first, evidence-traceable analysis that keeps observed/data results separate from model/predicted results.
compatibility: Requires Python 3.9+ for bundled profiling and validation scripts. Optional analysis dependencies may include numpy, pandas, PyYAML, and matplotlib when the workspace's existing analysis code uses them.
---

# Autonomous-driving temporal correctness to physical safety analysis

Use this workflow to turn experiment artifacts into an auditable six-layer argument:

`temporal disturbance -> temporal symptoms -> cause-effect timing -> temporal correctness -> distance debt -> physical safety outcome`

The point is not merely to show that a module became slower. Establish whether a timing disturbance propagated through the closed loop, exceeded a deadline independently determined from vehicle physics, consumed physical distance, and changed an observed safety outcome.

## Read the relevant references first

- Read [references/six-layer-method.md](references/six-layer-method.md) before defining metrics or writing conclusions.
- Read [references/data-contract.md](references/data-contract.md) when locating experiment logs, Trace files, bridge/SCB evidence, collision evidence, or `record/` parsed exports.
- Read [references/report-contract.md](references/report-contract.md) before creating final tables, figures, or reports.

## Non-negotiable analysis rules

1. Treat raw experiment directories as read-only. Write all generated artifacts to a separate analysis workspace.
2. Define every event endpoint and clock before calculating a duration or distance. Do not silently rename an existing endpoint.
3. Use wall-clock vehicle speed trapezoidal integration for the main response-stage distance:

   `D_delay_wall_integral_m = integral(t1, t2, v(t) dt_wall)`

   CARLA frames, simulation time, realtime factor, and Localization spatial displacement are diagnostics, not substitutes.
4. Save observed/data and model/predicted results separately. Never fill a missing observed value with a model estimate.
5. Derive the dynamic physical deadline from vehicle state and braking/safety assumptions independently of the measured reaction time. Compare afterward.
6. Do not equate a deadline miss with a collision. Preserve the chain `deadline miss -> distance debt -> margin loss -> outcome`.
7. Keep Reaction Time, Data Age, and Update Continuity as separate timing semantics.
8. Do not use Guardian as the commanded-actuation source when the experiment architecture states that the bridge reads Control directly.

## Workflow

### 1. Inventory and freeze the scope

Identify:

- experiment root, run directories, groups, nominal injected delays, and expected run count;
- log, Trace, bridge/SCB, collision, actor-history, collection-window, and configuration files;
- parsed `record/` directories and their `extraction_summary.json`/`output_manifest.json`;
- existing analysis scripts and previously generated tables, which are references rather than ground truth;
- the requested deliverables and output directory.

Run the bundled record profiler for every parsed record directory:

```bash
python3 <skill-dir>/scripts/profile_record_export.py \
  --record-dir <run>/record \
  --output <analysis-workspace>/record_profiles/<run-id>.json
```

After profiling all runs, create the cross-run record diagnostic table:

```bash
python3 <skill-dir>/scripts/aggregate_record_profiles.py \
  --profiles-dir <analysis-workspace>/record_profiles \
  --output-csv <analysis-workspace>/tables/record_timing_diagnostics.csv
```

Start with `extraction_summary.json`. Record parse errors, missing expected tables, time windows, and row counts. A successfully parsed record only proves what was written to its channels.

### 2. Establish the event and clock dictionary

Create a per-run event table with at least:

- `t_cause` / `t1`: the agreed environment-cause or stable target-source endpoint;
- `t_perception_output`, `t_prediction`, `t_planning`, `t_control_command`;
- `t_physical_response` / `t2`: the first sustained physical response endpoint;
- `t_deadline = t_cause + tau_dynamic`;
- `t_stop`, `t_collision`, and/or another actual outcome endpoint.

For this workspace's established second-experiment convention, `t1` is the source timestamp of the first frame in a continuous three-frame stable Fusion sequence. `t2` is the end of the first interval satisfying the sustained-deceleration rule. Preserve those definitions when comparing its runs.

Track each timestamp's time basis: wall epoch, record receipt time, message header/source time, Trace monotonic time, CARLA simulation time, or CARLA frame. Align clocks explicitly and report alignment residuals. Do not subtract timestamps from different bases without demonstrated alignment.

### 3. Build a source-provenance matrix

For every metric, save:

- layer;
- metric name and unit;
- endpoint definition;
- clock basis;
- source file and source columns or lines;
- observed/derived/model status;
- availability and missing reason;
- confidence or data-quality note.

Prefer direct experiment evidence for physical outcomes. Use record-derived timing diagnostics to enrich the timing layers; do not let them overwrite collision truth or actual vehicle motion.

### 4. Analyze all six layers

Follow [references/six-layer-method.md](references/six-layer-method.md). Minimum per-layer outputs:

- **L1 Temporal Disturbance:** requested and actual bridge delay, jitter/load/backlog/gap/staleness/phase conditions, activation time, and intervention verification.
- **L2 Temporal Degradation:** response variability, tail latency, data freshness, message/update gaps, Planning reuse/age, queueing, and anomalous frames.
- **L3 Cause-Effect Timing:** event timeline, stage latency decomposition, physical Reaction Time, Data Age at effect, and update continuity. Treat record `sensor_to_control_reaction_age.csv` as a message-level diagnostic, not automatically as physical `T_R`.
- **L4 Temporal Correctness:** dynamic deadline, timing slack, deadline-miss flag, deadline provenance, and sensitivity to safety margin/braking assumptions.
- **L5 Temporal-to-Physical Propagation:** wall-integrated response distance, deadline-exceedance distance debt, remaining distance at response, and an explicit total-loss versus incremental-loss distinction.
- **L6 Physical Safety:** actual braking process, actual endpoint, actual clearance/collision/impact evidence, observed safety margin when calculable, and model predictions in a separate section/table.

### 5. Separate observed and predicted datasets

Create at least two run-level outputs:

- `run_level_observed.csv`: direct or data-derived quantities with `_data_observed_` or an equally explicit marker;
- `run_level_model_predicted.csv`: empirical-model, counterfactual, or predicted quantities with `_model_predicted_`/`_model_` markers.

Collision runs often lack a full observed stopping distance. Save truncated braking-to-collision separately, keep full stopping distance and stopping-margin fields unavailable, and report the collision itself as the observed outcome.

When evaluating a model, compare it only with endpoint-, clock-, and distance-compatible observed results. Report signed error, absolute error, relative error when the denominator is valid, and error direction.

### 6. Perform quality and causal audits

At minimum audit:

- expected versus found runs and files;
- parse errors and empty/high-volume tables;
- target identity across Perception, Prediction, Planning, and CARLA actor evidence;
- timestamp monotonicity, negative ages, clock alignment, and record-window coverage;
- `D_delay` integral versus independent spatial-displacement diagnostic;
- stopping endpoint quality and collision/geometry contradictions;
- intervention fidelity and actual versus requested bridge delay;
- confounders such as initial clearance, initial speed, perception gaps, braking capability, and solver fallback.

Use `UNKNOWN`/`UNAVAILABLE` with a reason when evidence conflicts. Do not remove a run merely because it is inconvenient; state the exclusion criterion and retain its diagnostic rows.

### 7. Produce the deliverables

Use the exact minimum artifact set in [references/report-contract.md](references/report-contract.md). The report's main results and conclusions must use observed/data results. Put prediction, counterfactual restoration, and fitted braking models in a clearly separated model section.

Run validation after generating outputs:

```bash
python3 <skill-dir>/scripts/validate_analysis_outputs.py \
  --analysis-dir <analysis-workspace>
```

Resolve validation errors before presenting conclusions. Warnings may remain only when they are explained in the data-quality report.

## Interpretation discipline

Use claim strength that matches the evidence:

- **Observed association:** timing and outcome moved together under the measured run conditions.
- **Supported propagation:** measured timing increase produced measured response-distance increase and margin reduction.
- **Causal contribution:** intervention fidelity and competing explanations have been checked.
- **Sole cause:** reserve for designs that isolate other relevant changes; ordinary run comparisons rarely justify it.

Prefer language such as “the primary supported contributor under this run's measured state” when initial clearance, freshness, solver behavior, or braking ability also differ.

## Existing workspace integration

When operating in the current CARLA 0.9.15/Apollo 10 workspace:

- inspect `report_workspace/README.md` and reuse its raw-data-first parser functions where appropriate;
- treat `report_workspace/tables/run_level_metrics.csv` as a useful schema example, not a replacement for rerunning the source analysis;
- use each run's parsed `record/07_diagnostics/` tables to add freshness, gap, reuse, and message-level reaction/age evidence;
- preserve the architecture fact that the bridge reads Control directly because Guardian commands are not currently sent to the bridge.

## Completion criteria

The task is complete only when:

- every included run has a traceable evidence row or an explicit unavailable reason;
- the six layers are connected without skipping the deadline comparison or distance propagation;
- wall-clock response distance is used consistently across runs;
- observed and model results are physically and visibly separated;
- collision claims agree with direct event evidence or are marked uncertain;
- validation passes, and the report names remaining limitations.
