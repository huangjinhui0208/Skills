# Six-layer analysis method

## 1. Purpose and logical direction

The framework asks whether an autonomous-driving system can lose temporal correctness, and then physical safety, even when its functional result is correct.

Use this directed chain:

`cause -> manifestation -> system effect -> constraint violation -> physical propagation -> safety outcome`

Dynamic Deadline is an independent input to Layer 4, produced from physical state. It is not a downstream output of the measured cause-effect timing chain.

## 2. Event notation

| Symbol | Meaning | Typical workspace mapping |
|---|---|---|
| `t_c` | external cause/source endpoint | `t1`, stable target source time |
| `t_p` | relevant Perception/Fusion output | stable target output header/publish time |
| `t_pred` | first causally related Prediction output | trace/log/record matched output |
| `t_plan` | first target-related Planning decision/output | STOP/deceleration decision |
| `t_ctrl` | first causally related Control command | Control command or aligned trace event |
| `t_e` | physical effect endpoint | `t2`, sustained effective braking onset |
| `t_d` | latest allowed physical response time | `t_c + tau*` |
| `t_o` | observed outcome endpoint | stop, collision, minimum-speed proxy, or collection end |

Every table must state whether its time is wall epoch, message-source/header time, record receipt time, Trace monotonic time, simulation time, or frame index.

## 3. Layer 1 - Temporal Disturbance

Question: what timing disturbance entered the system?

Examples:

- fixed or random delay;
- jitter and long-tail execution;
- CPU/GPU interference;
- queue backlog;
- message/network delay;
- update loss or gap;
- stale data;
- period or phase mismatch.

Evidence should include nominal configuration and actual execution. For bridge delay injection, retain requested delay, actual wall delay, actual frame delay, activation time, queue depth, and lifecycle status separately.

Layer 1 describes the intervention. It does not by itself establish danger.

## 4. Layer 2 - Temporal Degradation

Question: what observable timing symptoms appeared?

Analyze three parallel dimensions:

### 4.1 Response-time variability

Across frames and runs, report median, p90, p99, maximum, outliers, and variability for relevant stages. Avoid reporting only the mean.

### 4.2 Data freshness

For a causally matched source/effect pair:

`A = t_effect - t_source`

Specify whether `t_effect` is Planning, Control, or physical response. A record receipt timestamp is not automatically the source timestamp.

### 4.3 Update continuity

For consecutive outputs:

`G_k = t_out[k+1] - t_out[k]`

Report the nominal period, p90/p99/max gap, and counts above a declared threshold such as `1.5 x` or `2 x` the nominal/median period. Keep the threshold definition stable across runs.

Useful parsed-record evidence includes topic-rate tables, module timelines, Planning/Control latency, Planning age, reuse count, sensor-to-control reaction/age, and abnormal-frame summaries.

## 5. Layer 3 - Cause-Effect Timing

Question: how did local timing symptoms propagate from environment input to vehicle action?

Nominal chain:

`Sensor -> Perception -> Prediction -> Planning -> Control -> Actuation`

### 5.1 Physical Reaction Time

`T_R = t_e - t_c`

In this workspace's established convention:

`T_e2e_data_observed_ms = (t2_wall_s - t1_wall_s) x 1000`

This includes the physical-response portion after the Control command. Do not replace it with sensor-to-Control timing.

### 5.2 Data Age

`A = t_effect - t_source`

Reaction Time and Data Age answer different questions. A system may respond quickly using old data, or slowly using relatively fresh data. Analyze both when the evidence permits.

### 5.3 Stage decomposition

Report causally matched stages rather than sums of unrelated percentiles:

- sensor/source -> Fusion output;
- Fusion -> Prediction;
- Prediction -> Planning decision;
- Planning -> Control command;
- Control command -> physical response.

Use trace IDs, inherited header timestamps, sequence numbers, Planning references, or validated time alignment. Nearest-time matching alone is weak evidence and must be labeled accordingly.

## 6. Layer 4 - Temporal Correctness

Question: did actual timing violate the maximum physically allowed response time?

Let the current vehicle/scene state be:

`x(t) = [v, clearance, acceleration, braking capability, friction, safety margin, ...]`

Derive:

`tau* = f(x(t_c))`

Then compare:

`S_T = tau* - T_R`

- `S_T >= 0`: temporal requirement satisfied under the declared physical model/data-derived envelope;
- `S_T < 0`: deadline miss;
- `T_R > tau*`: equivalent miss condition.

### 6.1 Deadline provenance classes

Keep these distinct:

- `tau_data_derived`: derived from measured vehicle state and an observed/calibrated braking envelope; unavailable when the needed observed braking endpoint is missing.
- `tau_model_predicted`: derived from a declared physical or empirical prediction model.
- `tau_requirement`: externally specified safety or engineering requirement.

Do not calculate `tau*` from `T_R` or choose it merely to separate safe and collision runs. When the measured braking capability came from the same delayed run, acknowledge the closed-loop dependence and add a sensitivity or baseline-calibrated deadline.

## 7. Layer 5 - Temporal-to-Physical Propagation

Question: how much physical space did the timing behavior consume?

### 7.1 Response distance

`D_response = integral(t_c, t_e, v(t) dt_wall)`

In the current workspace, the main field is:

`D_delay_wall_integral_data_observed_m`

Compute with trapezoidal integration after interpolating the endpoints. Save Localization path/displacement and CARLA simulation diagnostics under distinct names.

### 7.2 Distance debt

`t_d = t_c + tau*`

`D_debt = max(0, integral(t_d, t_e, v(t) dt_wall))`

This is the incremental distance traveled after the time budget was exhausted. It is not automatically equal to the entire response distance.

### 7.3 Total versus incremental space loss

- Total remaining space at response: `D_brake_available = D_available - D_response`.
- Incremental loss relative to an on-time deadline baseline: `D_debt`.

State which quantity is being plotted or compared. Do not subtract both from the same baseline unless the baseline definition explicitly calls for it.

## 8. Layer 6 - Physical Safety

Question: what actual or predicted safety outcome followed?

For an observed full stop:

`M_collision_0m_data = D1_clear_data - D_response_data - D_brake_data`

For a required final safety clearance `D_safe`:

`M_safety_data = M_collision_0m_data - D_safe`

Interpretation:

- positive margin: stopping is physically possible under the measured endpoint, though it may be near-critical;
- near zero: safety-margin depletion;
- negative: minimum-clearance violation is predicted/derived, but direct event evidence still determines whether an observed collision occurred.

For collision runs:

- record collision occurrence, target association, impact speed, impulse, and braking distance truncated to collision as observed fields;
- leave full observed stopping distance and full-stop margin unavailable;
- place any reconstructed stopping distance, restored-response outcome, or impact prediction in the model table.

## 9. Cyber-physical feedback

Timing degradation can change state and tighten the next deadline:

`Reaction Time up -> D_response up -> clearance down -> tau*(x) down`

This feedback is a reason to evaluate deadlines from a clearly specified state and to avoid treating a run-specific, post-delay braking state as an entirely independent requirement without qualification.

## 10. Cross-run comparison rules

Use identical definitions across every compared run:

- same clock basis;
- same `t1` and `t2` detection rules;
- same speed interpolation and trapezoidal integration;
- same target geometry convention;
- same safety-clearance convention;
- same missing-value rules;
- same observed/model separation.

Report run-level rows before group aggregates. Group counts must include unavailable and excluded runs transparently, not only successfully parsed cases.

## 11. Minimum causal conclusion chain

A strong conclusion names evidence for all links:

1. the temporal intervention actually occurred;
2. internal timing symptoms changed;
3. end-to-end physical response changed;
4. the response exceeded or approached an independently defined deadline;
5. additional response time became measured distance consumption;
6. braking margin and the observed outcome changed;
7. important competing explanations were checked.
