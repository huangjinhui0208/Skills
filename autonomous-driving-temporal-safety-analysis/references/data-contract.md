# Data contract and evidence routing

This contract defines source semantics and evidence extraction. Evidence-to-claim eligibility is governed by [inference-contract.md](inference-contract.md); source availability alone never establishes a claim.

## 1. Source priority

Use sources by what they can actually prove, not by convenience.

| Evidence source | Strongest use | Important limitation |
|---|---|---|
| Bridge/SCB logs | requested and applied timing intervention | does not prove physical response or collision |
| Apollo module logs | target decisions, solver/fallback evidence, tagged event times | logging can be incomplete and timestamp semantics vary |
| Trace events/message context | stage timing and causal propagation | monotonic timestamps require an anchor to wall time |
| Localization | wall-time speed/acceleration, response onset, distance integral | spatial displacement is diagnostic, not the canonical `D_response` |
| CARLA collision CSV/JSONL | direct collision event, actor, frame, impulse | no event file alone does not prove a safe stop if collection is incomplete |
| CARLA actor history | final geometry, target association, sim/wall diagnostics | CARLA sim time must not replace the wall-clock main metric |
| Parsed cyber record | channel messages, headers, module timing, freshness, gaps, reuse | only channels/messages written into the record are observable |
| Existing reports/tables | schema examples and prior claims to re-check | never substitute them for raw-data recomputation |

## 1.1 Evidence typing at extraction time

Create an evidence ID when a source fact or derived metric first becomes usable. Assign one primary class from the inference contract and preserve limitation/taint tags.

Examples:

| Item | Primary evidence class | Limitation/taint |
|---|---|---|
| SCB applied wall delay | `DIRECT_OBSERVED` | proves application at logged scope only |
| `T_R=t2-t1` on compatible wall clock | `OBSERVED_DERIVED` | endpoint and lineage assumptions remain |
| `D_response=integral(v dt_wall)` | `OBSERVED_DERIVED` | inherits t1/t2/clock quality |
| same-run stopping-derived deadline | `RETROSPECTIVE_RECONSTRUCTION` | `RETRO_TAINT`; not primary C4 |
| predeclared external response limit | `INDEPENDENT_REQUIREMENT` | must pass P_DEADLINE scenario/uncertainty checks |
| current-sample fitted deadline | `UNVALIDATED_MODEL` | `MODEL_TAINT`; exploratory only |
| collision event | `DIRECT_OBSERVED` | establishes collision, not why |
| nearest-time module match | `WEAK_TEMPORAL_ALIGNMENT` | no strong C3 |
| collision-truncated braking | `DIRECT_OBSERVED` plus `OUTCOME_TRUNCATED` | no full stopping endpoint |

Save the evidence type, clock, source locator, availability, confidence, supported/challenged claims, and limitations in `evidence_ledger.csv`.

## 2. Current experiment directory patterns

Typical run directory:

```text
<group>/<run-id>/
├── collect_time.txt
├── log/
│   ├── localization.log.INFO.*
│   ├── perception.log.INFO.*
│   ├── prediction.log.INFO.*
│   ├── planning.log.INFO.*
│   ├── control.log.INFO.*          # may be absent
│   ├── scb_control_delay_*.csv     # delay injection evidence
│   ├── carla_collision_events_*.csv|jsonl
│   └── carla_collision_actor_history_*.csv
├── trace/
│   ├── trace_anchor/
│   ├── events/
│   ├── message_context/
│   └── fusion_inputs/
└── record/                         # parsed Apollo cyber record export, when present
```

Do not require all files for every run. Inventory them and make availability explicit.

### 2.1 Run-to-record association

Prefer a `record/` directory nested under the same run directory. Otherwise create an explicit association table with `run_id`, `record_dir`, source record filename, collection start/end, and association method. A similar timestamp or directory name is supporting evidence, not a sufficient causal join when runs overlap.

After profiling, left-join `record_timing_diagnostics.csv` to the experiment's run-level table on the audited `run_id` association. Preserve runs without record data and add `record_profile_available=false`; do not restrict group statistics to record-available runs unless the metric itself is record-only.

### 2.2 Fault-to-run association and pre-hazard coverage

For every run, locate nominal configuration and direct fault application. Save requested/actual magnitude, onset/end, scope, affected message count, queue/drop/reorder behavior, and evidence class in `temporal_fault_signature.csv`.

If direct/derived onset precedes `t1`, extract the `[t_fault,t1]` state window when possible. Include position, velocity, acceleration, heading, steering, throttle, brake, Control/Bridge apply, CARLA frame, route progress, and target state. Missing fields stay `MISSING`; do not infer unchanged state.

Classify D1, v1, a1, heading, and route progress as:

- `PRE_EXISTING_CONFOUNDER` only when evidence supports independence from treatment;
- `POSSIBLE_MEDIATOR` when the pre-t1 fault could have produced divergence;
- `POST_TREATMENT_STATE` when treatment causally preceded/measurably changed it;
- `UNKNOWN` when causal role cannot be resolved.

## 3. Parsed record export contract

Start with:

- `extraction_summary.json`: processed files, parse errors, row counts, extraction window, and notes;
- `output_manifest.json`: expected logical tables, including tables that may be absent because the corresponding protobuf field/channel was unavailable;
- `00_meta/record_channels.csv`: channel coverage and record bounds;
- `00_meta/record_topic_rate.csv`: message rate and gap summary;
- `00_meta/record_message_index.csv`: record receipt timeline and message metadata.

### 3.1 Localization and chassis

- `01_localization_chassis/localization_pose.csv`
- `01_localization_chassis/localization_velocity_acc.csv`
- `01_localization_chassis/chassis.csv`
- `01_localization_chassis/chassis_signal.csv`

Useful fields include `record_time_sec`, `header_timestamp_sec`, `measurement_time`, `speed`, velocity/acceleration, pose, chassis speed, and brake/throttle feedback.

Use Localization wall epoch plus interpolated vehicle speed for the main response-distance integral. Treat record receipt time and header/source time as distinct fields.

### 3.2 Planning

- `02_planning/planning_header.csv`
- `02_planning/planning_latency_stats.csv`
- `02_planning/planning_decision.csv`
- `02_planning/planning_obstacle_decision.csv`
- `02_planning/planning_trajectory_summary.csv`
- `02_planning/planning_debug_raw.jsonl`

Use these for Planning publication cadence, total/task execution time, target decisions, trajectory state, and debug evidence. `total_time_ms` may be repeated for every task row; deduplicate by `planning_seq` before computing frame-level statistics.

### 3.3 Control

- `03_control/control_command.csv`
- `03_control/control_latency.csv`
- `03_control/control_planning_reuse.csv`
- `03_control/control_vehicle_state.csv`
- `03_control/control_chassis_feedback.csv`

Use these for command cadence, brake/acceleration command, Control execution latency, Planning age, and trajectory reuse. In the current architecture, the bridge reads Control directly; Guardian must not replace Control in the causal chain.

### 3.4 Perception and Prediction

- `04_prediction_perception/perception_obstacles.csv`
- `04_prediction_perception/prediction_obstacles.csv`
- `04_prediction_perception/perception_raw.jsonl`
- `04_prediction_perception/prediction_raw.jsonl`

Use them for obstacle identity, source/header timestamp propagation, classification, geometry, and output continuity. Obstacle tables contain obstacle rows, not necessarily one row per empty frame; use module/channel timelines for complete publication gaps.

### 3.5 Sensor and diagnostics

- `06_sensor_raw/sensor_timeline.csv`
- `07_diagnostics/module_timeline.csv`
- `07_diagnostics/planning_control_alignment.csv`
- `07_diagnostics/control_reuse_summary.csv`
- `07_diagnostics/sensor_to_control_reaction_age.csv`
- `07_diagnostics/abnormal_frames_summary.csv`
- `07_diagnostics/system_events.csv`

These are the preferred record-derived inputs for Layers 2 and 3.

`sensor_to_control_reaction_age.csv` has message-level `reaction_time_ms` and `data_age_ms`. Preserve its sensor channel and matching semantics. Do not rename its reaction time to physical `T_R` unless the effect endpoint is independently shown to be physical actuation.

## 4. Timestamp semantics

Common parsed-record columns:

- `record_time_sec`: when the message was written/observed in the record timeline;
- `header_timestamp_sec`: message header timestamp;
- `measurement_time` or obstacle `timestamp`: source/measurement semantics defined by that message type;
- `header_lidar_timestamp`, `header_camera_timestamp`, `header_radar_timestamp`: propagated sensor timestamps, sometimes integer nanoseconds and sometimes zero.

Before using `effect - source`:

1. confirm units;
2. confirm both timestamps refer to the same clock domain or validate alignment;
3. check negative ages and monotonicity;
4. save the matching key/sequence/trace provenance;
5. state whether the result is source age, publication latency, receipt latency, or physical reaction time.

### 4.1 Clock alignment audit

Create `clock_alignment_audit.csv` with clock domain, host, timestamp type, synchronization/anchor method, offset estimate, drift/frequency estimate, alignment residual, timestamp resolution/precision, jitter/dispersion, error budget, and confidence. A single-domain wall interval may remain valid even when cross-host stage decomposition is not.

Do not place phase verdicts in this table. `clock_phase_audit.csv` may remain as a legacy view, but it cannot qualify P_CLOCK or P_PHASE by itself in a new analysis.

### 4.2 Periodic phase audit

Create `phase_audit.csv`. Record CARLA fixed step/tick origin, sensor tick, Apollo module timer periods/origins, injection onset phase, phase-to-tick and phase-to-consumer values, scan design/levels/repeats, and effect/uncertainty. Discrete 300/400/700/800/900 ms clusters without an active phase scan are `PHASE_EFFECT_HYPOTHESIS`, not established phase causation.

### 4.3 Causal-lineage extraction

For each claimed chain, retain source/Fusion/Prediction/Planning/Control/actuation event IDs, matching keys, method, and grade A/B/C/D/UNKNOWN. A physical `T_R` can be valid as a wall-clock interval while strict lineage remains grade C or lower.

## 5. Six-layer evidence routing

| Layer | Primary experiment evidence | Record supplement |
|---|---|---|
| L1 Disturbance | SCB/bridge config and applied rows, resource/load setup | system events and channel coverage only as supporting context |
| L2 Degradation | Trace stage queue/process times, log gaps | topic rates, module timeline, Planning/Control latency, Planning age/reuse, abnormal frames |
| L3 Cause-effect | stable target source, Trace/message context, physical `t2` | propagated headers, Planning-Control alignment, sensor-to-Control reaction/age |
| L4 Correctness | vehicle state, target clearance, measured/calibrated braking envelope | Localization/chassis state can supplement; record alone rarely supplies the entire deadline |
| L5 Propagation | Localization wall-time speed integral | record Localization can cross-check if the required wall-time window and endpoint mapping exist |
| L6 Safety | collision events, actor history, actual stop trajectory/final clearance | command/feedback can support braking execution but not replace direct outcome evidence |

## 5.1 Functional-correctness extraction

Create `functional_correctness_audit.csv`. Extract, without upgrading missing values:

- physical target identity;
- Perception target presence and tracking continuity;
- Prediction presence and semantic validity;
- Planning STOP presence, target correctness, location reasonableness, trajectory validity, fallback/infeasibility;
- Control receipt of relevant trajectory, braking command, and continuity;
- Bridge payload receive/apply;
- physical response.

Each item is `PASS`, `DEGRADED`, `FAIL`, or `UNKNOWN`. The overall P_FUNC verdict is `QUALIFIED_PASS`, `PARTIAL`, `FAIL`, or `NOT_TESTABLE`. Output presence alone does not establish correctness.

## 5.2 Deadline-requirement extraction

Maintain a requirement registry containing requirement ID/name/value, provenance, pre-registration, external/internal origin, safety meaning, calibration/validation domain, uncertainty bounds, and evidence class.

Keep three sources separate:

- `tau_retro`: same-run post-outcome reconstruction;
- `tau_req`: independently qualified prospective requirement;
- `tau_model`: model prediction with validation class.

If `tau_req` is dynamically constructed, also create `dynamic_deadline_construction.csv` under [dynamic-deadline-contract.md](dynamic-deadline-contract.md). The construction row, registry row, and evidence row must share the exact `requirement_id`.

## 5.3 Observed velocity trajectory for L5 recomputation

Create `velocity_trajectory_observed.csv` from Localization/Chassis samples with at least:

- `run_id`, `sample_index`, `t_wall_s`, `speed_mps`;
- `clock_domain`, `source_file`, `source_locator`;
- `availability`, `quality_flags`.

Use wall epoch and speed magnitude (or a declared signed longitudinal speed when the geometry requires it). Sort by time, reject duplicate/nonmonotonic samples unless explicitly resolved, and preserve samples bracketing `t1`, `t_d`, and `t_e`. Endpoint interpolation is linear; integration is trapezoidal.

The validator writes `l5_recomputation.csv`. Do not manually mark its status PASS.

## 5.4 Backward diagnosis inputs

Create `diagnosis_hypothesis_ledger.csv` and `diagnosis_edges.csv`. Candidate hypotheses may point to raw/derived evidence and forward claims but cannot alter them. Preserve candidates with missing evidence as `NOT_TESTABLE`; do not discard them merely to force unique diagnosis.

## 6. Current second-experiment schema example

The current workspace's raw-data-first analysis already establishes useful field conventions:

- `t1_wall_s`, `t2_wall_s`;
- `T_e2e_data_observed_ms`;
- `D1_clear_data_observed_m`;
- `D_delay_wall_integral_data_observed_m`;
- `D_response_wall_integral_data_observed_m` as the canonical v2 name; keep `D_delay_wall_integral_data_observed_m` as a deprecated alias;
- `D2_clear_data_observed_m`;
- `D_brake_data_observed_m`;
- `M_collision_0m_data_observed_m` and `M_safety_6m_data_observed_m`;
- stage latency and continuity diagnostics;
- separately stored counterfactual model fields.

Legacy fields named `tau_dynamic_data_derived_ms` require provenance reassessment. If they use same-run full-stop braking, reclassify them as `tau_retro`, not qualified `tau_req`. Legacy `D_distance_debt_model_predicted_m` retains model taint.

Inspect `report_workspace/README.md` and `report_workspace/tables/run_level_metrics.csv` for the current schema. Re-run raw parsing for new results; do not copy old values into a new analysis.

## 7. Missing-data rules

- Missing input -> unavailable result with a reason.
- Parse error -> preserve the error and affected metric list.
- Collision truncates the physical trajectory -> full observed stopping distance and full-stop margins unavailable.
- No actor history -> realtime factor and some final-geometry diagnostics unavailable; wall-clock main timing/distance may remain valid.
- No Control payload -> Control command semantics unavailable even if a Trace timing event exists.
- No target identity chain -> do not attribute a Planning/Control response to the collision target with high confidence.
- Conflicting collision and geometry evidence -> mark outcome uncertain and retain the run for diagnostics while excluding it from outcome aggregates under an explicit rule.

## 8. Data-quality flags

Use stable flag names where possible:

- `MISSING_REQUIRED_SOURCE`
- `RECORD_PARSE_ERROR`
- `RECORD_WINDOW_INCOMPLETE`
- `CLOCK_ALIGNMENT_UNVERIFIED`
- `NEGATIVE_DATA_AGE`
- `TARGET_IDENTITY_UNCERTAIN`
- `BRAKING_ENDPOINT_TRUNCATED_BY_COLLISION`
- `STRICT_STOP_NOT_OBSERVED`
- `COLLISION_GEOMETRY_CONFLICT`
- `OBSERVED_VALUE_UNAVAILABLE`
- `MODEL_ONLY_NOT_OBSERVED`
- `RETROSPECTIVE_ONLY_NOT_REQUIREMENT`
- `REFERENCE_MISSING`
- `SINGLE_MAX_ONLY`
- `PRE_HAZARD_AUDIT_REQUIRED`
- `POST_TREATMENT_STATE_UNCLASSIFIED`
- `FUNCTIONAL_CORRECTNESS_NOT_QUALIFIED`
- `OPEN_CRITICAL_DEFEATER`

Each flag should name affected outputs and source evidence.
