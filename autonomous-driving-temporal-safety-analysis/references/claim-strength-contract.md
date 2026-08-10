# TCPS-PA v2 claim-strength contract

## Contents

1. Purpose
2. Claim levels
3. Evidence and prerequisite ceilings
4. Allowed and forbidden language
5. Executive-conclusion algorithm
6. Special language guards

## 1. Purpose

This contract maps validated claims to the strongest legal conclusion. Claim strength is not a writing preference. It is an output of prerequisite closure, admissible evidence, defeaters, and weakest-link confidence.

Save the ceiling in `claim_ledger.csv.maximum_claim_level`. Prose must not exceed it.

## 2. Claim levels

### LEVEL 0 — Descriptive observation

Meaning: a quantity/event was measured or calculated under declared semantics.

Minimum support: direct or observed-derived evidence with source provenance.

Allowed examples:

- “SCB logged 300.1 ms actual delay.”
- “The physical reaction interval was 799.6 ms.”
- “A 507 ms maximum Fusion gap was observed in run 1131.”

Not allowed: degradation, propagation, requirement failure, causal contribution, or intrinsic defect.

### LEVEL 1 — Temporal anomaly/degradation observed

Meaning: timing behavior degraded against a declared reference/requirement/distribution.

Minimum support: C2 PASS/PARTIAL_PASS with reference provenance and adequate distributional scope.

Allowed: “Temporal degradation was observed relative to the baseline distribution.”

Not allowed: the degradation propagated to physical effect unless C3 supports it.

### LEVEL 2 — Cause-effect temporal propagation supported

Meaning: a timing change is supported along the relevant chain or, for grade C, a bounded system-level temporal association is supported.

Minimum support: C3, P_CLOCK, and P_TARGET under the inference contract.

Allowed:

- Grade A/B: “Cause-effect temporal propagation is supported.”
- Grade C: “A system-level temporal association is supported; strict lineage is incomplete.”

Not allowed: temporal correctness failure without qualified C4.

### LEVEL 3 — Temporal correctness failure supported

Meaning: observed T_R exceeded a qualified independent timing requirement.

Minimum support: P_DEADLINE qualified, compatible observed T_R, C4 PASS, uncertainty-aware miss.

Allowed: “A temporal correctness failure is supported under requirement R1.”

Not allowed when deadline is only retrospective or unvalidated model-derived.

### LEVEL 4 — Temporal contribution to physical safety degradation supported

Meaning: timing violation materially contributed to space/margin/outcome degradation.

Minimum support: qualified C4, C5, C6, adequate P_FUNC, and bounded critical defeaters.

Allowed: “Timing materially contributed to physical safety degradation under the measured scenario.”

Not allowed: timing dominated or was the sole cause unless Level 5 conditions hold.

### LEVEL 5 — Timing-dominated safety failure candidate

Meaning: timing is the primary supported candidate after functional, initial-state, braking, freshness, phase, geometry, and outcome alternatives have been evaluated.

Minimum support: strong C1-C6 chain, C7, P_FUNC qualified, important defeaters resolved/bounded, repeatability or strong matched evidence.

Allowed: “This run is a timing-dominated safety-failure candidate.”

The word “candidate” is required unless a stronger experimental design isolates alternatives.

### LEVEL 6 — SUT-intrinsic temporal defect

Meaning: the SUT itself exhibits an internal timing defect rather than merely responding to an injected external delay.

Minimum support:

- internal queueing/resource/scheduling/message-staleness/WCET-tail mechanism or experimentally isolated internal source;
- reproducibility across relevant conditions;
- qualified C1-C7 chain and resolved external-injection alternatives;
- domain/uncertainty limits.

Allowed: “The SUT exhibits an intrinsic temporal defect under the tested conditions.”

An artificial Bridge injection cannot directly establish Level 6.

## 3. Evidence and prerequisite ceilings

Apply all applicable ceilings and select the minimum:

| Condition | Maximum level |
|---|---:|
| Only descriptive direct/derived evidence | 0 |
| C2 has no reference or only single max | 0 |
| C2 established but C3 unavailable | 1 |
| C3 lineage C | 2 |
| C3 lineage D/UNKNOWN | 1 |
| P_CLOCK or P_TARGET uncertain for critical chain | 2 |
| C4 retrospective only | 2 |
| C4 unvalidated-model only | 2 |
| C4 qualified but C5 unavailable | 3 |
| C5 model/retro only | 3 at most; attribution wording must remain model/retro-supported |
| P_FUNC PARTIAL | 4 at most, normally lower if functional defeater is critical/open |
| P_FUNC FAIL/NOT_TESTABLE | no timing-only attribution; 2 unless contract-specific evidence supports a bounded multifactor contribution |
| Critical defeater OPEN/UNKNOWN | affected claim PARTIAL/UNCERTAIN; normally <=3 |
| One nonzero injected delay level | no stable gain/amplification claim |
| External Bridge injection is fault source | <=5; never Level 6 from injection alone |
| Strong C1/C6 but C4 NOT_TESTABLE and C5 MODEL_ONLY | overall <=2 |

## 4. Allowed and forbidden language

### 4.1 Default allowed phrases

| Level | Preferred language |
|---|---|
| 0 | observed, measured, calculated, recorded, descriptive |
| 1 | temporal anomaly/degradation was observed relative to [reference] |
| 2 | propagation is supported; system-level association is supported |
| 3 | temporal correctness failure is supported under [qualified requirement] |
| 4 | timing materially contributed under the measured conditions |
| 5 | timing-dominated safety-failure candidate |
| 6 | SUT exhibits an intrinsic temporal defect under [domain] |

### 4.2 Globally guarded phrases

Do not use without explicit rule satisfaction:

- “sole cause”;
- “proves Apollo is non-real-time”;
- “fixed 700 ms deadline” or “700 ms is a universal deadline”;
- “stable 1.5x amplification”, “amplification factor”, “propagation gain”, or “system gain” from a single nonzero delay level;
- “functionally correct, temporally wrong” without P_FUNC QUALIFIED_PASS and qualified C4;
- “directly observed distance debt” when deadline is model/retrospective;
- “complete six-layer proof” when an intermediate claim is model-only/not-testable;
- “SUT-intrinsic defect” when the only fault source is external injection.

Populate each claim's `allowed_language` and `forbidden_language`; the validator scans the report and claim audit.

## 5. Executive-conclusion algorithm

1. Select the scoped C1-C6 and C7 records used by the report.
2. Calculate `overall_level = min(critical claim/prerequisite ceilings)`; do not average.
3. State direct observations first.
4. Name not-testable/model-only intermediate claims explicitly.
5. State open critical defeaters and residual uncertainty.
6. Use only phrases permitted by `overall_level`.

Example:

```text
C1 PASS/HIGH
C2 PARTIAL_PASS/MEDIUM
C3 PARTIAL_PASS/lineage C/MEDIUM
C4 NOT_TESTABLE/retrospective or model only
C5 MODEL_SUPPORTED_ONLY
C6 PASS/HIGH
```

Allowed conclusion:

> Direct observations establish a temporal disturbance, delayed physical response, and degraded physical outcome. A system-level temporal association is supported. The intermediate deadline-miss-to-distance-debt mechanism remains model-supported rather than directly established.

Forbidden conclusion:

> The experiment completely proves temporal correctness failure propagated into collision.

## 6. Special language guards

### 6.1 One nonzero delay level

With baseline plus one nonzero delay level:

`Delta T_R / Delta delay`

is an `observed incremental end-to-end response ratio`. Do not call it gain, propagation gain, system gain, amplification, or amplification factor.

A stable gain requires multiple nonzero levels, repeats, controlled initial state, uncertainty/error estimates, and an approximately stable dose-response relationship.

### 6.2 Single maximum gap

Say “a case-level maximum gap of X was observed.” Only say “continuity degraded” when a reference/distribution and replicate scope satisfy C2.

### 6.3 Retrospective and model deadlines

- `tau_retro`: “Retrospective reconstruction indicates...”
- unvalidated `tau_model`: “Model evidence supports a possible deadline miss...”
- qualified `tau_req`: “Observed T_R [met/missed] requirement R under stated uncertainty.”

### 6.4 Attribution

When initial clearance may be post-treatment, say “pre-hazard state divergence may mediate part of the total closed-loop effect,” not “initial clearance is an independent confounder,” until causal role is classified.
