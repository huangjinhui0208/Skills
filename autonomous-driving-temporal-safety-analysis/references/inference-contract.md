# TCPS-PA v2 inference contract

## Contents

1. Protocol purpose and execution order
2. Claim taxonomy and dependency graph
3. Evidence type system
4. Evidence admissibility
5. Prerequisite claims
6. Claim inference rules
7. Evidence taint and confidence propagation
8. Defeater mechanism
9. Layer gate contract
10. Special audits
11. Argument-validator rules
12. Forbidden inference patterns

## 1. Protocol purpose and execution order

TCPS-PA v2 is a lightweight scientific inference layer, not a certification or full SACM/GSN assurance-case system. It constrains what may be inferred from experimental evidence.

Execute:

`Raw Data -> Evidence Extraction -> Evidence Typing -> Claim Construction -> Prerequisite Checking -> Inference Rule Evaluation -> Counter-evidence/Defeater Evaluation -> Confidence Propagation -> Six-layer Verdict -> Allowed Claim Strength -> Report`

Metric availability is never sufficient for a claim. Every claim must name evidence, prerequisites, rule, challenges, defeaters, confidence ceiling, residual uncertainty, and allowed language.

## 2. Claim taxonomy and dependency graph

### 2.1 Prerequisite claims

| ID | Proposition | Strong-pass requirement |
|---|---|---|
| `P_CLOCK` | Clocks used by a comparison are compatible and aligned to the claimed precision. | Clock domains, synchronization/anchor method, offset/drift or residual, resolution, and bounded error are documented. |
| `P_TARGET` | Sensor, Fusion, Prediction, Planning, Control response, and collision actor refer to the relevant physical target. | Trace/identity chain is explicit and contradictions are resolved or bounded. |
| `P_FUNC` | Relevant functional behavior has been qualified and does not independently explain the outcome. | Perception, Prediction, Planning, Control, Bridge, and physical-response audit yields `QUALIFIED_PASS`. |
| `P_DEADLINE` | The timing requirement is independent, prospective, scenario-compatible, and qualified. | Requirement provenance and uncertainty are declared; no current-run post-outcome information is critical to the primary requirement. |

`P_FUNC` verdicts are `QUALIFIED_PASS`, `PARTIAL`, `FAIL`, or `NOT_TESTABLE`. Other prerequisite claims use the normal verdict vocabulary.

### 2.2 Core claims

| ID | Layer | Proposition |
|---|---|---|
| `C1` | L1 | A declared temporal disturbance actually entered the SUT/closed loop with known location, timing, magnitude, pattern, and scope. |
| `C2` | L2 | Observable timing behavior degraded relative to an explicitly declared reference, requirement, baseline distribution, or nominal behavior. |
| `C3` | L3 | Timing degradation propagated along the relevant cause-effect chain from environment/sensor cause toward physical vehicle effect. |
| `C4` | L4 | Actual physical Reaction Time exceeded an independently qualified scenario-dependent timing requirement: `T_R > tau_req`. |
| `C5` | L5 | The qualified timing violation produced quantifiable additional physical-space consumption: deadline miss -> deadline-excess debt -> braking-space loss. |
| `C6` | L6 | Physical safety margin and/or observed physical safety outcome degraded. |
| `C7` | Attribution | Physical safety degradation is attributable, at a declared strength, to temporal correctness degradation after competing explanations are evaluated. |

`C7` is not a seventh layer. It is evaluated after C1-C6.

### 2.3 Canonical dependency edges

Use exact scoped claim IDs in `claim_edges.csv` (for example `P_CLOCK.group` -> `C3.group`). The canonical graph is:

```text
P_CLOCK ─┬──────────────> C3 ───────────────┐
P_TARGET ┘                                  │
C1 ─────────> C2 ─────────> C3             │
P_DEADLINE ────────────────> C4             │
C3 ────────────────────────> C4             │
C4 ────────────────────────> C5             ├──> C7
C5 ─────────────────────────────────────────┤
C6 ─────────────────────────────────────────┤
P_FUNC ─────────────────────────────────────┘
```

Additional `CHALLENGES`, `QUALIFIES`, and `BOUNDS` edges must be recorded when applicable.

## 3. Evidence type system

Assign exactly one primary evidence class and zero or more taint/limitation tags to every important evidence item.

| Evidence class | Meaning | Default ceiling |
|---|---|---|
| `DIRECT_OBSERVED` | Direct measurement/event evidence such as CollisionSensor, Localization speed, or SCB applied delay. | HIGH for the fact measured, not its cause. |
| `OBSERVED_DERIVED` | Deterministic calculation from compatible direct observations, such as `T_R=t2-t1` or wall-clock speed integration. | Inherit weakest input and formula assumptions. |
| `REQUIREMENT_CONSTRAINED_DERIVED` | Deterministic calculation combining observed data with a qualified independent requirement, such as primary `D_debt`. | Inherit P_DEADLINE and observed-path ceilings. |
| `TRACE_LINEAGE` | Trace ID, sequence, propagated timestamp, or explicit provenance establishing event lineage. | Depends on lineage grade and clocks. |
| `RETROSPECTIVE_RECONSTRUCTION` | Uses same-run post-outcome or full-trajectory information to reconstruct an earlier budget/deadline. | Reconstruction/sensitivity only; not primary C4. |
| `INDEPENDENT_REQUIREMENT` | Predeclared external safety/engineering constraint available before outcome. | Eligible for P_DEADLINE after scenario compatibility and uncertainty checks. |
| `INDEPENDENT_CALIBRATED_MODEL` | Model calibrated on data independent of the current test run and with declared domain. | Eligible for P_DEADLINE only after validation/uncertainty checks. |
| `VALIDATED_MODEL` | Model independently validated for the claimed endpoint/domain but still model output. | Model-supported; may qualify a requirement only when contract conditions hold. |
| `UNVALIDATED_MODEL` | Current-sample fit, unvalidated calibration, or exploratory model. | Exploratory/model-supported only. |
| `WEAK_TEMPORAL_ALIGNMENT` | Event association based only on temporal proximity. | System-level association; no strong C3. |
| `CLOCK_UNVERIFIED` | Cross-domain evidence without reliable alignment to the claimed precision. | LOW/MEDIUM depending on uncertainty; no high-confidence small differences. |
| `OUTCOME_TRUNCATED` | Outcome, usually collision, right-censors full stopping behavior. | Direct outcome/truncated interval only. |
| `CONFLICTED_EVIDENCE` | Direct evidence sources contradict one another. | UNCERTAIN until resolved/bounded. |
| `MISSING` | Evidence unavailable. | No positive inference. |

Recommended limitation/taint tags include `MODEL_TAINT`, `RETRO_TAINT`, `CLOCK_TAINT`, `TARGET_TAINT`, `OUTCOME_TRUNCATED`, `REFERENCE_MISSING`, `SINGLE_MAX_ONLY`, and `POST_TREATMENT_STATE`.

`OUTCOME_TRUNCATED`, `CONFLICTED_EVIDENCE`, and `MISSING` are primary evidence-state classes when an item cannot honestly retain an admissible source class. When a valid direct/derived observation is merely qualified by truncation or conflict, retain its source class and put `OUTCOME_TRUNCATED` or `CONFLICTED_EVIDENCE` in `taint_tags`. Do not encode both meanings ambiguously in `evidence_class`.

## 4. Evidence admissibility

### E1 — Retrospective reconstruction

`RETROSPECTIVE_RECONSTRUCTION` may support accident reconstruction, retrospective physical budgets, or sensitivity analysis. It cannot alone support the primary C4 Temporal Correctness Failure verdict.

### E2 — Unvalidated model

`UNVALIDATED_MODEL` may support exploratory mechanisms and hypotheses. It cannot establish directly observed deadline miss, directly observed distance debt, strong C4, or strong C5.

### E3 — Weak alignment

`WEAK_TEMPORAL_ALIGNMENT` cannot establish C3. It supports at most a system-level temporal association and `PARTIAL_PASS`.

### E4 — Unverified clocks

When cross-host alignment uncertainty is comparable with a reported stage difference, confidence is capped LOW. When bounded but non-negligible, cap MEDIUM. Do not label 20–30 ms differences HIGH when alignment uncertainty is of similar magnitude.

### E5 — Outcome truncation

`OUTCOME_TRUNCATED` cannot produce full observed stopping distance, full-stop margin, or same-run observed braking capability beyond the truncation endpoint.

### E6 — Direct collision

`DIRECT_OBSERVED` collision establishes that collision occurred. It does not establish why it occurred.

### E7 — Direct fault evidence

SCB/Bridge actual delay establishes intervention entry only for the logged scope/location. It does not establish downstream timing degradation, deadline miss, distance debt, or collision cause.

### E8 — Single maximum gap

A single maximum gap without a declared reference and distribution supports a case-level timing observation only. It cannot establish group-level temporal degradation.

### E9 — Functional-chain presence

The presence of Perception/Planning/Control outputs does not prove functional correctness. Functional correctness requires P_FUNC audit fields and competing functional explanations.

### E10 — Requirement boundary

A 0 m contact boundary and a 6 m engineering margin have different meanings. A researcher-selected threshold is an analysis margin unless external/pre-registered provenance establishes a safety requirement.

## 5. Prerequisite claims

### 5.1 P_CLOCK

Create `clock_phase_audit.csv`. A claim using only a single compatible wall clock may pass for that interval while cross-host stage decomposition remains partial. Do not grant a global clock pass merely because one metric is single-domain.

### 5.2 P_TARGET

Audit physical identity from sensor/Fusion through Planning and collision actor. Trace/sequence lineage outranks nearest-time matching. Uncertain identity prevents strong C3 and downgrades P_FUNC.

### 5.3 P_FUNC

Create `functional_correctness_audit.csv`. Evaluate target presence/continuity, Prediction semantics, Planning STOP target/location/trajectory/fallback, Control receipt/command continuity, Bridge receive/apply, and physical response. Output:

- `QUALIFIED_PASS`: required links pass and no open functional defeater independently explains the outcome;
- `PARTIAL`: some links pass but payload/semantic evidence or an important alternative remains unresolved;
- `FAIL`: a functional failure is directly supported;
- `NOT_TESTABLE`: required functional evidence is missing/conflicted.

Only `P_FUNC=QUALIFIED_PASS` plus established C4 allows “functionally correct, temporally wrong.”

### 5.4 P_DEADLINE

Maintain requirement provenance:

| Deadline | Source | Primary C4 eligibility |
|---|---|---|
| `tau_retro` | Same-run post-outcome stopping/reconstruction | No; `RETROSPECTIVE_ONLY`. |
| `tau_req` | Predeclared/external requirement or independently calibrated and validated physical envelope using pre-outcome state | Yes after uncertainty/domain checks. |
| `tau_model` | Declared model | Only if independently validated and qualified; otherwise `MODEL_SUPPORTED_ONLY`. |

Record `requirement_id`, name/value, provenance, pre-registration, external/internal status, safety meaning, uncertainty bounds, and validation scope.

## 6. Claim inference rules

### IR-C1 — Temporal Disturbance Verified

Require a complete enough Temporal Fault Signature `F_T={type,location,onset,duration,magnitude,distribution,pattern,scope,affected_messages}` and direct evidence of actual application. Configuration alone yields at most `PARTIAL_PASS`.

### IR-C2 — Temporal Degradation Established

Require a named reference: `BASELINE_DISTRIBUTION`, `NOMINAL_PERIOD`, `ENGINEERING_REQUIREMENT`, `SAME_CONDITION_CONTROL`, `PRE_FAULT_WITHIN_RUN`, or `DECLARED_EXTERNAL_REFERENCE`. Report R/A/G distributional summaries and treat runs, not repeated frames, as experimental replicates. No reference -> descriptive observation only.

### IR-C3 — Cause-Effect Temporal Propagation

Require P_CLOCK and P_TARGET appropriate to the claimed chain plus lineage grade:

| Grade | Basis | Maximum verdict |
|---|---|---|
| A | Explicit trace ID/sequence/provenance lineage | PASS if prerequisites pass. |
| B | Propagated source/header timestamp plus validated downstream mapping | PASS if prerequisites pass. |
| C | Validated temporal alignment only | PARTIAL_PASS / temporal association. |
| D | Nearest-time heuristic | UNCERTAIN. |
| UNKNOWN | Insufficient evidence | NOT_TESTABLE. |

`T_R=t2-t1` remains a physical reaction interval even when strict lineage is only C/D.

### IR-C4 — Temporal Correctness Failure

Require observed `T_R`, P_DEADLINE, compatible clocks, and uncertainty-aware comparison:

The evidence ledger must mark this interval `semantic_role=PHYSICAL_REACTION_INTERVAL` and use canonical metric `T_R` or `T_e2e_data_observed_ms`. A record/message metric such as `sensor_to_control_reaction_age` is ineligible even if its name contains “reaction.” The validator recomputes the comparison from same-scope millisecond values in `requirement_registry.csv`; an evidence-class label alone is insufficient.

- `T_R <= tau_req_low` -> `CLEARLY_WITHIN_REQUIREMENT` (C4 hypothesis FAIL: no failure established);
- `tau_req_low < T_R <= tau_req_high` -> `BOUNDARY_UNCERTAIN`;
- `T_R > tau_req_high` -> `CLEARLY_MISSED` (C4 PASS);
- only `tau_retro` -> `RETROSPECTIVE_ONLY` / C4 NOT_TESTABLE;
- only unvalidated `tau_model` -> `MODEL_SUPPORTED_ONLY` / primary C4 NOT_TESTABLE.

Do not derive the requirement from `T_R` or choose it after observing labels.

### IR-C5 — Temporal-to-Physical Propagation

Canonical quantities:

`D_response = integral(t_c,t_e,v(t)dt_wall)`

`D_debt = max(0, integral(t_c+tau_req,t_e,v(t)dt_wall))`

Primary C5 requires established/qualified C4, observed compatible-clock velocity path, and `REQUIREMENT_CONSTRAINED_DERIVED` debt. Model deadline -> `D_debt_model` with model taint. Retrospective deadline -> `D_debt_retro_diagnostic`. Neither may be relabeled observed primary debt.

Decompose:

`M_D = D1 - D_response - D_brake - D_safe`

`Delta M_D = Delta D1 - Delta D_response - Delta D_brake`

When fault onset precedes t1, distinguish total closed-loop effect from post-t1 response effect.

### IR-C6 — Physical Safety Degradation

Use continuous outcomes where available: final/minimum clearance, margin, minimum speed, impact speed/impulse, truncated braking distance, strict/near stop, and outcome severity. Direct collision establishes collision; threshold-based critical/near-miss categories require threshold provenance.

C6 strong evidence must be `DIRECT_OBSERVED`, carry `semantic_role=PHYSICAL_OUTCOME`, and use a canonical collision/clearance/margin/impact metric. Planning/Control commands and chassis messages are functional or state evidence, not direct physical outcome evidence.

### IR-C7 — Temporal Safety Attribution

Require the strongest available chain across C1-C6, P_FUNC, and defeater resolution. Attribution strength is capped by weak C4/C5, unresolved functional alternatives, post-treatment initial state, or physical/geometry differences. An injected Bridge fault cannot establish an SUT-intrinsic defect.

## 7. Evidence taint and confidence propagation

### 7.1 Taint propagation

Critical-input taint propagates downstream:

```text
UNVALIDATED_MODEL deadline -> MODEL_TAINT debt -> MODEL_SUPPORTED propagation
RETROSPECTIVE deadline -> RETRO_TAINT debt -> retrospective reconstruction only
CLOCK_UNVERIFIED stage -> CLOCK_TAINT C3 -> C3 confidence ceiling
TARGET uncertainty -> TARGET_TAINT lineage -> no strong C3/P_FUNC
OUTCOME_TRUNCATED braking -> no full-stop observed margin/deadline
```

Do not remove taint because a downstream arithmetic operation is deterministic.

### 7.2 Weakest-link ceiling

Use ordinal confidence `NONE < LOW < MEDIUM < HIGH`. The downstream confidence ceiling is the minimum of:

- each critical prerequisite confidence/ceiling;
- each critical supporting evidence confidence;
- inference-rule ceiling for its evidence class;
- unresolved critical-defeater ceiling.

Do not average confidence scores.

### 7.3 Verdict vocabulary

Use `PASS`, `PARTIAL_PASS`, `FAIL`, `UNCERTAIN`, `NOT_TESTABLE`, `RETROSPECTIVE_ONLY`, or `MODEL_SUPPORTED_ONLY`. Specialized physical classification may be saved separately, but must map to one of these gate verdicts.

## 8. Defeater mechanism

A defeater is a condition that, if true, invalidates or downgrades a claim. It is not merely a limitation.

Use states `OPEN`, `BOUNDED`, `RESOLVED`, `REFUTED`, `NOT_APPLICABLE`, or `UNKNOWN`. Critical `OPEN`/`UNKNOWN` defeaters cap the affected claim at `UNCERTAIN` or `PARTIAL_PASS`.

Default defeaters:

| ID | Description |
|---|---|
| `D_INITIAL_CLEARANCE` | Initial clearance differs. |
| `D_INITIAL_SPEED` | Initial speed differs. |
| `D_BRAKING_CAPABILITY` | Braking capability/vehicle dynamics differ. |
| `D_FUNCTIONAL_FAILURE` | Perception/Planning/Control/Bridge functional failure may explain outcome. |
| `D_TARGET_MISMATCH` | Wrong target association. |
| `D_DATA_FRESHNESS` | Stale state may independently alter decisions. |
| `D_UPDATE_GAP` | Long target update gap. |
| `D_SOLVER_FALLBACK` | Planner fallback/infeasibility. |
| `D_CLOCK` | Clock alignment uncertainty. |
| `D_PHASE` | CARLA/Control/Localization phase quantization. |
| `D_PREHAZARD_STATE` | Fault changed state before t1. |
| `D_GEOMETRY` | Vehicle boundary/clearance uncertainty. |
| `D_OUTCOME_CONFLICT` | CollisionSensor/geometry/collection evidence conflict. |

Extend with experiment-specific defeaters. Record evidence, resolution, residual risk, and exact claim impact.

## 9. Layer gate contract

Every C1-C6 gate and C7 attribution record must state:

- Hypothesis/proposition
- `I / gate_inputs`: scoped inputs and Required Preconditions
- `M / gate_metrics`: exact metrics, units, clocks, endpoints, and aggregation scope
- `E / admissible_evidence`: allowed evidence classes plus supporting/challenging evidence and defeaters
- `C / gate_criterion`: falsifiable criterion/inference rule, uncertainty, reference, and missing-data behavior
- `O`: verdict, confidence and confidence ceiling, maximum claim strength, allowed/forbidden language, and residual uncertainty
- `N / next_gate_condition`: exact conditions for entering the next canonical claim
- Supporting Evidence
- Challenging Evidence
- Defeaters

Layer completeness means the gate was evaluated, including `NOT_TESTABLE`; it does not mean PASS.

## 10. Special audits

### 10.1 Temporal Fault Signature

Create `temporal_fault_signature.csv`. If `fault_onset_wall < t1_wall`, trigger the pre-hazard audit.

### 10.2 Pre-hazard state divergence

Create `pre_hazard_state_audit.csv` over `[t_fault,t1]` using position, velocity, acceleration, steering, throttle, brake, Control/Bridge, CARLA frame, route progress, and target state when available. Classify D1/v1/a1/heading/route progress as `PRE_EXISTING_CONFOUNDER`, `POSSIBLE_MEDIATOR`, `POST_TREATMENT_STATE`, or `UNKNOWN`.

### 10.3 Functional correctness

Presence is not correctness. Use the P_FUNC audit and preserve fallback/infeasibility as potential functional defeaters.

### 10.4 Clock and phase

Record clock domain/host/timestamp type/sync/offset/drift/residual/resolution. Phase clusters without an active phase scan remain `PHASE_EFFECT_HYPOTHESIS`, never `PHASE_EFFECT_ESTABLISHED`.

## 11. Argument-validator rules

The semantic validator must enforce:

- nonempty scoped P/C claims, canonical layer/rule mappings, same-scope required Claim Graph edges, `REQUIRES|required=true`, and an acyclic graph;
- available, nonempty, source-traceable evidence with reciprocal Evidence–Claim links for strong verdicts;
- code-defined evidence-role minima rather than trusting `required_evidence_classes` declared by the report;
- numerical C4 recomputation from the requirement registry and scope-specific C7 ceiling/default-defeater checks;
- status-matrix rows consistent with the Claim Ledger, not merely the presence of a matrix heading;
- nonempty I-M-E-C-O-N gate fields for every C1-C7 record in a full experiment analysis;
- full-report engineering artifacts for R/A/G tail statistics, endpoint-compatible observed space budgets, and method-completeness status;

- `V1`: C4 PASS requires qualified P_DEADLINE and observed T_R.
- `V2`: only `tau_retro` -> C4 cannot PASS/FAIL; use RETROSPECTIVE_ONLY/NOT_TESTABLE.
- `V3`: only unvalidated `tau_model` -> C4 maximum MODEL_SUPPORTED_ONLY.
- `V4`: C5 PASS requires qualified tau_req, observed velocity path, compatible clocks, and requirement-constrained debt.
- `V5`: model deadline taint propagates to D_debt and C5.
- `V6`: P_FUNC not QUALIFIED_PASS forbids “functionally correct, temporally wrong.”
- `V7`: lineage C/D/UNKNOWN forbids strong C3 PASS.
- `V8`: unverified cross-host clocks forbid HIGH-confidence small stage differences.
- `V9`: fault onset before t1 without pre-hazard audit is an error.
- `V10`: onset before t1 plus D1/v1 changes without causal-role classification is an error.
- `V11`: one nonzero delay level forbids stable gain/amplification-factor claims.
- `V12`: single maximum gap without reference/distribution forbids group-level C2 PASS.
- `V13`: deadline miss does not imply collision.
- `V14`: observed collision does not imply temporal failure.
- `V15`: collision run cannot claim fabricated full observed braking distance.
- `V16`: critical OPEN/UNKNOWN defeater caps claim at UNCERTAIN/PARTIAL_PASS.

## 12. Forbidden inference patterns

Reject or downgrade:

- metric exists -> layer PASS;
- all six layers populated -> complete propagation proven;
- same-run post-outcome braking -> prospective deadline;
- model debt -> directly observed debt;
- function output exists -> function correct;
- one maximum gap -> group degradation;
- unverified cross-host clocks -> precise high-confidence stage difference;
- D1/v1 difference after pre-t1 fault -> automatically independent confounder;
- one nonzero delay level -> stable propagation gain/amplification factor;
- direct collision -> temporal cause;
- deadline miss -> collision;
- Bridge-injected fault -> SUT-intrinsic defect;
- UNKNOWN -> PASS;
- strong C1+C6 -> conceal weak/not-testable C4+C5.
