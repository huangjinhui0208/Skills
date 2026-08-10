# Data contract and evidence routing

## 1. Source priority

Use sources by what they can actually prove, not by convenience.

| Evidence source | Strongest use | Important limitation |
|---|---|---|
| Bridge/SCB logs | requested and applied timing intervention | does not prove physical response or collision |
| Apollo module logs | target decisions, solver/fallback evidence, tagged event times | logging can be incomplete and timestamp semantics vary |
| Trace events/message context | stage timing and causal propagation | monotonic timestamps require an anchor to wall time |
| Localization | wall-time speed/acceleration, response onset, distance integral | spatial displacement is diagnostic, not the main `D_delay` |
| CARLA collision CSV/JSONL | direct collision event, actor, frame, impulse | no event file alone does not prove a safe stop if collection is incomplete |
| CARLA actor history | final geometry, target association, sim/wall diagnostics | CARLA sim time must not replace the wall-clock main metric |
| Parsed cyber record | channel messages, headers, module timing, freshness, gaps, reuse | only channels/messages written into the record are observable |
| Existing reports/tables | schema examples and prior claims to re-check | never substitute them for raw-data recomputation |

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

## 5. Six-layer evidence routing

| Layer | Primary experiment evidence | Record supplement |
|---|---|---|
| L1 Disturbance | SCB/bridge config and applied rows, resource/load setup | system events and channel coverage only as supporting context |
| L2 Degradation | Trace stage queue/process times, log gaps | topic rates, module timeline, Planning/Control latency, Planning age/reuse, abnormal frames |
| L3 Cause-effect | stable target source, Trace/message context, physical `t2` | propagated headers, Planning-Control alignment, sensor-to-Control reaction/age |
| L4 Correctness | vehicle state, target clearance, measured/calibrated braking envelope | Localization/chassis state can supplement; record alone rarely supplies the entire deadline |
| L5 Propagation | Localization wall-time speed integral | record Localization can cross-check if the required wall-time window and endpoint mapping exist |
| L6 Safety | collision events, actor history, actual stop trajectory/final clearance | command/feedback can support braking execution but not replace direct outcome evidence |

## 6. Current second-experiment schema example

The current workspace's raw-data-first analysis already establishes useful field conventions:

- `t1_wall_s`, `t2_wall_s`;
- `T_e2e_data_observed_ms`;
- `D1_clear_data_observed_m`;
- `D_delay_wall_integral_data_observed_m`;
- `D2_clear_data_observed_m`;
- `D_brake_data_observed_m`;
- `M_collision_0m_data_observed_m` and `M_safety_6m_data_observed_m`;
- stage latency and continuity diagnostics;
- separately stored counterfactual model fields.

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

Each flag should name affected outputs and source evidence.
