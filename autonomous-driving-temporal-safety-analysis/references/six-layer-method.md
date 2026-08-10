# TCPS-PA v2 six-layer domain method

## Contents

1. Purpose and event notation
2. Common layer-gate structure
3. L1 Temporal Fault Signature
4. L2 Temporal Degradation
5. L3 Cause-Effect Temporal Propagation
6. L4 Temporal Correctness
7. L5 Temporal-to-Physical Propagation
8. L6 Physical Safety Degradation
9. C7 Temporal Safety Attribution
10. Cross-run and feedback rules

## 1. Purpose and event notation

The domain chain is:

`temporal disturbance -> timing degradation -> physical reaction interval/lineage -> qualified requirement comparison -> physical-space propagation -> safety degradation`

The inference chain is governed separately by [inference-contract.md](inference-contract.md). A quantity in a layer does not imply the layer claim passes.

| Symbol | Meaning | Typical workspace mapping |
|---|---|---|
| `t_f` | fault onset | first applied Bridge/SCB delay or internal anomaly onset |
| `t_c` / `t1` | environment/source cause endpoint | first source timestamp in continuous three-frame stable Fusion sequence |
| `t_p` | relevant Perception/Fusion output | stable target output header/publish time |
| `t_pred` | causally related Prediction output | trace/sequence/header-matched output |
| `t_plan` | relevant Planning output | target-related STOP/deceleration decision |
| `t_ctrl` | relevant Control command | Control command/trace event; Bridge reads Control in the current deployment |
| `t_e` / `t2` | physical response endpoint | sustained effective braking onset |
| `t_d` | qualified deadline endpoint | `t_c + tau_req` |
| `t_o` | observed outcome endpoint | stop, collision, minimum-speed proxy, or collection end |

Every timestamp must state clock domain, host, type, resolution, and alignment status. Do not subtract incompatible clocks.

## 2. Common layer-gate structure

Evaluate every layer with:

- Hypothesis
- Inputs
- Required Preconditions
- Metrics
- Admissible Evidence
- Criterion
- Supporting Evidence
- Challenging Evidence
- Defeaters
- Verdict (`PASS`, `PARTIAL_PASS`, `FAIL`, `UNCERTAIN`, `NOT_TESTABLE`, `RETROSPECTIVE_ONLY`, or `MODEL_SUPPORTED_ONLY`)
- Confidence and ceiling
- Maximum Claim Strength
- Gate result and residual uncertainty

`NOT_TESTABLE` is a valid completed analysis result.

## 3. L1 — Temporal Fault Signature

### Hypothesis C1

A declared temporal disturbance actually entered the SUT/closed loop with known location, timing, magnitude, pattern, and scope.

### Fault signature

Define:

```text
F_T = {
  fault_type, location, onset, duration, magnitude, distribution,
  pattern, scope, affected_messages
}
```

Examples: fixed/random delay, jitter, CPU/GPU interference, queue backlog, network delay, loss/gap, staleness, phase/period mismatch.

For Bridge injection retain requested magnitude, actual wall delay, actual frame/sim delay, activation/apply time, queue behavior, lifecycle, affected message count, drop/reorder status, and payload scope separately.

Configuration proves intent. Applied rows/direct instrumentation prove actual entry. L1 does not prove degradation, propagation, danger, or cause of collision.

### Pre-hazard trigger

If `t_f < t1`, create `pre_hazard_state_audit.csv`. Do not automatically treat D1/v1 differences as pre-existing confounders; they may be treatment-induced mediators or post-treatment state.

## 4. L2 — Temporal Degradation

### Hypothesis C2

Observable timing behavior degraded relative to an explicitly declared reference.

### Required reference

Use one or more:

- `BASELINE_DISTRIBUTION`
- `NOMINAL_PERIOD`
- `ENGINEERING_REQUIREMENT`
- `SAME_CONDITION_CONTROL`
- `PRE_FAULT_WITHIN_RUN`
- `DECLARED_EXTERNAL_REFERENCE`

No reference -> temporal observation only, not established degradation.

### Three-dimensional degradation vector

Define:

`T_deg = {R, A, G}`

- `R`: response-time variability;
- `A`: data freshness/age;
- `G`: update continuity/gap.

For each relevant distribution save P50, P90, P95, P99, MAX, and IQR/MAD or another declared variability statistic.

Data age for a causally matched pair is:

`A = t_effect - t_source`

State whether the effect is Planning, Control, or physical response and whether source time is measurement/header/record time.

For consecutive outputs:

`G_k = t_out[k+1] - t_out[k]`

Save nominal period, threshold, threshold provenance, count above threshold, and maximum gap. A single MAX outlier without reference/distribution is only a case-level anomaly. Repeated frames within a run are not independent experimental replicates.

Record-derived Planning age/reuse, sensor-to-Control reaction/age, module latency, and topic gaps supplement L2. A record profile alone does not prove physical L3-L6 claims.

## 5. L3 — Cause-Effect Temporal Propagation

### Hypothesis C3

Timing degradation propagated along the relevant cause-effect chain from environment/sensor cause toward physical vehicle effect.

Nominal chain:

`Sensor -> Perception/Fusion -> Prediction -> Planning -> Control -> Bridge/Actuation -> Physical response`

Guardian is excluded from the executed command chain when the Bridge reads Control directly.

### Physical reaction interval

`T_R = t_e - t_c`

For the established second-experiment endpoints:

`T_e2e_data_observed_ms = (t2_wall_s - t1_wall_s) * 1000`

This is a system-level physical reaction interval and includes Control-to-physical-response time. Do not replace it with message-level sensor-to-Control latency.

### Strict lineage

Store event IDs and method:

- `source_event_id`
- `perception_event_id`
- `fusion_event_id`
- `prediction_event_id`
- `planning_event_id`
- `control_event_id`
- `actuation_event_id`
- `causal_lineage_method`
- `causal_lineage_grade`

Grades:

| Grade | Method | Claim ceiling |
|---|---|---|
| A | explicit trace ID/sequence/provenance lineage | C3 PASS eligible |
| B | propagated source/header timestamp plus validated downstream mapping | C3 PASS eligible |
| C | validated temporal alignment only | temporal association / PARTIAL_PASS |
| D | nearest-time heuristic | UNCERTAIN |
| UNKNOWN | insufficient evidence | NOT_TESTABLE |

P_CLOCK and P_TARGET are strong-C3 prerequisites. Stage decomposition must use causally matched events, not sums of unrelated percentiles.

## 6. L4 — Temporal Correctness

### Hypothesis C4

Observed physical Reaction Time exceeded an independently qualified scenario-dependent timing requirement.

### Deadline classes

#### A. Retrospective physical deadline `tau_retro`

Uses same-run post-outcome information such as full stopping behavior. It supports reconstruction/sensitivity only and cannot establish primary C4.

#### B. Independent safety/engineering deadline `tau_req`

Uses state available before response/outcome plus a predeclared external requirement or independently calibrated/validated physical envelope. This is the only primary C4 deadline.

#### C. Model-predicted deadline `tau_model`

Mark `VALIDATED_MODEL` or `UNVALIDATED_MODEL`. An unvalidated/current-sample model yields `MODEL_SUPPORTED_ONLY`, not primary C4.

### Requirement registry

For every requirement save:

- requirement ID/name/value;
- provenance and derivation;
- pre-registered status;
- external/internal origin;
- safety meaning (contact avoidance, engineering margin, etc.);
- calibration/validation domain;
- `tau_req_low`, center, high.

A 6 m researcher-selected threshold is an engineering analysis margin unless external/pre-registered evidence makes it a safety requirement.

### Comparison

`S_T = tau_req - T_R`

- `T_R <= tau_req_low`: `CLEARLY_WITHIN_REQUIREMENT` (C4 failure hypothesis FAIL);
- `tau_req_low < T_R <= tau_req_high`: `BOUNDARY_UNCERTAIN`;
- `T_R > tau_req_high`: `CLEARLY_MISSED` (C4 PASS);
- retro only: `RETROSPECTIVE_ONLY / NOT_TESTABLE`;
- unvalidated model only: `MODEL_SUPPORTED_ONLY / NOT_TESTABLE`.

Never derive `tau_req` from `T_R` or choose it to separate collision labels.

## 7. L5 — Temporal-to-Physical Propagation

### Hypothesis C5

A qualified timing violation produced quantifiable additional physical-space consumption.

### Canonical response distance

`D_response = integral(t_c,t_e,v(t)dt_wall)`

Canonical field:

`D_response_wall_integral_data_observed_m`

Compatibility alias:

`D_delay_wall_integral_data_observed_m` (deprecated)

Interpolate endpoints and use trapezoidal wall-clock integration. CARLA frame/sim time, realtime factor, and Localization displacement/path are independent diagnostics, not substitutes.

### Qualified distance debt

`t_d = t_c + tau_req`

`D_debt = max(0, integral(t_d,t_e,v(t)dt_wall))`

Primary debt is `REQUIREMENT_CONSTRAINED_DERIVED`: qualified `tau_req` plus observed compatible-clock velocity.

- model deadline -> `D_debt_model_predicted_m` with `MODEL_TAINT`;
- retrospective deadline -> `D_debt_retro_diagnostic_m` with `RETRO_TAINT`;
- neither may be named directly observed primary debt.

### Space-budget decomposition

`M_D = D1 - D_response - D_brake - D_safe`

Across runs:

`Delta M_D = Delta D1 - Delta D_response - Delta D_brake`

Decompose initial-space, response-distance, and braking-distance contributions when endpoint-compatible. If fault onset is before t1, separate:

- Total Closed-loop Effect, which may include treatment-induced D1/v1 change;
- Post-t1 Response Effect, based on t1-to-t2 behavior.

Do not subtract total response distance and deadline-excess debt twice from the same baseline.

## 8. L6 — Physical Safety Degradation

### Hypothesis C6

Physical safety margin and/or observed physical safety outcome degraded.

### Continuous outcomes

Preserve where available:

- final/minimum clearance;
- physical/contact/engineering margin;
- minimum speed;
- impact speed and impulse;
- truncated braking distance/time;
- strict stop and near stop;
- outcome severity.

For a full observed stop:

`M_collision_0m_data = D1 - D_response - D_brake`

`M_safety_data = M_collision_0m_data - D_safe`

For collision runs, record direct collision, actor association, impact, and braking truncated to collision. Leave full observed stopping distance/full-stop margins unavailable.

### Outcome taxonomy

Use `SAFE_STOP`, `LOW_MARGIN_STOP`, `CRITICAL_STOP`, `NEAR_MISS`, `CONTACT`, `COLLISION`, `HIGH_SEVERITY_COLLISION`, or `UNCERTAIN`. Any low/critical/near/high-severity threshold requires provenance. Do not invent a threshold after seeing outcomes.

Direct collision proves outcome, not temporal cause.

## 9. C7 — Temporal Safety Attribution

C7 is evaluated after C1-C6, not displayed as a seventh layer. Consider:

- intervention fidelity and location;
- P_CLOCK/P_TARGET/P_FUNC/P_DEADLINE;
- initial clearance/speed causal role;
- braking capability and dynamics;
- freshness/update gap/solver fallback;
- phase quantization;
- geometry and outcome conflict;
- model/retrospective taint;
- dose-response design and repeatability.

Use the Claim Strength Contract. A Bridge injection can demonstrate response to an imposed fault but does not establish an intrinsic Apollo defect.

## 10. Cross-run and feedback rules

Use identical clocks, endpoints, integration, geometry, safety-margin semantics, and missing-value rules across compared runs. Show every run before aggregates and keep excluded/unavailable counts.

Cyber-physical feedback can tighten later requirements:

`Reaction Time up -> D_response up -> clearance down -> tau_req(x) down`

If the fault began before t1, D1/v1 can be part of that feedback. Classify their causal role before calling them confounders.

With baseline plus one nonzero delay level, report only an observed incremental end-to-end response ratio. Stable propagation gain requires multiple nonzero levels, repeats, controlled state, uncertainty estimates, and an approximately stable dose response.
