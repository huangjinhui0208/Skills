# Dynamic Physical Deadline Construction Contract

## Contents

1. Purpose and eligibility
2. Longitudinal construction model
3. Input and uncertainty contract
4. Construction algorithm
5. Qualification and anti-leakage rules
6. Required output schema

## 1. Purpose and eligibility

This contract constructs a prospective state-dependent response deadline `tau_req(x)` when no externally declared scalar deadline exists. It is an engineering safety envelope, not an observed runtime and not a substitute for a legal or certified requirement.

A constructed deadline is primary-C4 eligible only when:

- all state inputs were observable no later than `t1`;
- vehicle/target dynamics and braking limits were declared before the current outcome;
- the braking envelope came from an external specification or an independently calibrated and validated dataset;
- the operational domain, road/grade/friction assumptions, geometry, and uncertainty bounds are explicit;
- no current-run post-`t1` stopping distance, collision label, `t2`, or fitted outcome information enters the construction;
- construction is reproducible and returns a nonempty conservative interval.

Otherwise classify it as `UNVALIDATED_MODEL`, `RETROSPECTIVE_RECONSTRUCTION`, or `NOT_QUALIFIED_PRIMARY`.

## 2. Longitudinal construction model

For same-lane longitudinal following, the default interpretable envelope is RSS-like:

```text
d_required(tau) =
    v_e * tau
  + 0.5 * a_resp * tau^2
  + (v_e + a_resp * tau)^2 / (2 * b_e)
  - v_f^2 / (2 * b_f)
  + d_safe
```

where:

- `d_clear` is the longitudinal bumper-to-obstacle/vehicle clearance available at the state epoch;
- `v_e`, `v_f` are ego/front longitudinal speeds;
- `a_resp >= 0` bounds ego acceleration during response;
- `b_e > 0` is the guaranteed minimum ego braking magnitude;
- `b_f > 0` is the assumed maximum front-vehicle braking magnitude;
- `d_safe` is a declared contact or engineering residual margin.

The maximum admissible response delay is the largest nonnegative `tau` satisfying:

`d_required(tau) <= d_clear`.

For a stationary obstacle set `v_f=0`; do not invent target braking credit. For curved roads or non-longitudinal conflict geometry, use a validated reachability/dynamics model and identify it instead of forcing this closed form.

This model is grounded in the interpretable RSS longitudinal safe-distance construction. RSS does not make the resulting parameters universally valid; each parameter still requires scenario/domain provenance.

## 3. Input and uncertainty contract

Create one construction row per run/scenario with:

- state epoch and clock: `state_time`, `state_time_basis`, `state_available_by_t1`;
- prospective cut-off: `input_cutoff_time`, `latest_input_time`, `parameter_selection_time`, `parameter_selection_locked_by_t1`;
- parameter-level lineage in `input_provenance_json`, with a source/time locator for every critical parameter;
- geometry: `d_clear_m`, `d_safe_m`, target type and target-motion assumption;
- dynamics: `v_ego_mps`, `v_front_mps`, `a_ego_response_max_mps2`, `b_ego_min_mps2`, `b_front_max_mps2`;
- lower/center/upper bounds for every uncertain critical parameter;
- `braking_envelope_id`, source, calibration dataset, independence from current test, validation domain, and validation error;
- explicit disjoint `calibration_run_ids` and `evaluation_run_ids`;
- road grade/friction/actuation-build-up assumptions when relevant;
- construction method/version and units.

Bounds must be physically ordered and sign-convention safe. Do not encode a negative deceleration in a field defined as braking magnitude.

## 4. Construction algorithm

For the closed-form envelope define:

```text
A = 0.5*a_resp + a_resp^2/(2*b_e)
B = v_e + v_e*a_resp/b_e
C = v_e^2/(2*b_e) - v_f^2/(2*b_f) + d_safe - d_clear
```

Solve `A*tau^2 + B*tau + C = 0` for the largest nonnegative feasible root. If `C > 0`, the state is already outside the declared envelope and `tau=0` with `ALREADY_UNSAFE_AT_STATE_EPOCH`. Reject invalid dynamics or a negative discriminant as `CONSTRUCTION_INVALID`.

Compute:

- `tau_req_center_ms` from center parameters;
- `tau_req_low_ms` as the minimum admissible deadline over the declared parameter box;
- `tau_req_high_ms` as the maximum over that box.

Use exhaustive corners only when the parameter box is small and its dependence assumptions are defensible. Otherwise use a declared interval, reachability, polynomial-zonotope, Monte Carlo with coverage guarantees, or another independently reviewed uncertainty method. Save the method and sample/corner count.

## 5. Qualification and anti-leakage rules

`QUALIFIED_DYNAMIC_PHYSICAL` requires:

- `state_available_by_t1=TRUE`;
- `latest_input_time <= input_cutoff_time`, `parameter_selection_locked_by_t1=TRUE`, and complete parameter-level provenance;
- `current_run_post_t1_data_used=FALSE` and `current_run_outcome_used=FALSE`;
- `validation_dataset_independent=TRUE`;
- nonempty, disjoint calibration/evaluation run sets;
- `parameter_bounds_complete=TRUE`;
- braking envelope status `QUALIFIED`;
- low/center/high finite and ordered;
- construction status `SOLVED` or `ALREADY_UNSAFE_AT_STATE_EPOCH`;
- exact reciprocal link to `requirement_registry.requirement_id`.

The following force `NOT_QUALIFIED_PRIMARY`:

- same-run post-outcome braking or full-stop distance;
- calibration on any current evaluated run;
- parameter selection after observing collision labels;
- missing target-motion or braking assumptions;
- unbounded road/friction/grade conditions relevant to the claim;
- applying the longitudinal formula to incompatible geometry.

## 6. Required output schema

Write `dynamic_deadline_construction.csv` with at least:

- `construction_id`, `requirement_id`, `run_id_or_group`, `method`, `method_version`;
- `state_time`, `state_time_basis`, `state_available_by_t1`;
- `input_cutoff_time`, `latest_input_time`, `input_provenance_json`, `parameter_selection_time`, `parameter_selection_locked_by_t1`;
- `current_run_post_t1_data_used`, `current_run_outcome_used`;
- `d_clear_m`, `v_ego_mps`, `v_front_mps`, `d_safe_m`;
- `a_ego_response_max_mps2`, `b_ego_min_mps2`, `b_front_max_mps2`;
- `parameter_bounds_json`, `uncertainty_method`, `uncertainty_sample_count`;
- `braking_envelope_id`, `braking_envelope_provenance`, `validation_dataset_independent`, `validation_scope`;
- `calibration_run_ids`, `evaluation_run_ids`;
- `target_motion_assumption`, `road_condition_assumption`;
- `tau_req_low_ms`, `tau_req_center_ms`, `tau_req_high_ms`;
- `parameter_bounds_complete`, `construction_status`, `qualification`, `source_evidence_ids`, `notes`.

Use `construct_dynamic_deadline.py` for the default RSS-like longitudinal model. A custom model must emit the same audit fields.
