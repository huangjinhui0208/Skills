---
name: autonomous-driving-temporal-safety-analysis
description: Apply TCPS-PA v2, an evidence-constrained Claim–Evidence diagnostic protocol, to CARLA/Apollo autonomous-driving experiments and parsed Apollo cyber records. Use for delay, jitter, backlog, staleness, update gaps, physical reaction time, dynamic deadlines, timing slack, response distance, distance debt, braking margin, near miss, collision attribution, bridge injection, Trace/log/record fusion, six-layer reports, real-time-systems engineering reports, paper-method instantiation, or audits of whether evidence is strong enough to support a timing-safety conclusion. It keeps observed, retrospective, requirement-qualified, and model-supported results separate and rejects methodologically invalid but format-complete six-layer narratives.
---

# TCPS-PA Diagnostic Protocol v2

This skill is not primarily a report-generation workflow. It is an evidence-constrained diagnostic protocol for Temporal Correctness-to-Physical Safety Propagation Analysis.

Use the operational sequence:

`Detect -> Characterize -> Trace -> Judge -> Quantify -> Attribute`

Do not infer a six-layer story merely because every layer has a metric. Build and validate the Claim–Evidence argument before writing prose.

## Read before analysis

Read all five contracts before constructing claims:

1. [references/six-layer-method.md](references/six-layer-method.md) for domain quantities and layer hypotheses.
2. [references/data-contract.md](references/data-contract.md) for source semantics, clocks, record exports, and missing-data rules.
3. [references/inference-contract.md](references/inference-contract.md) for Claim Graph, admissibility, taint, prerequisites, defeaters, and inference gates.
4. [references/claim-strength-contract.md](references/claim-strength-contract.md) for conclusion ceilings and legal language.
5. [references/report-contract.md](references/report-contract.md) for ledgers, audit tables, report structure, and deliverables.

## Non-negotiable rules

1. Keep raw experiment directories read-only and write generated artifacts to a separate analysis directory.
2. Type every important item as evidence before using it in a claim. Preserve `DIRECT_OBSERVED`, `OBSERVED_DERIVED`, `TRACE_LINEAGE`, `RETROSPECTIVE_RECONSTRUCTION`, requirement/model classes, uncertainty classes, and taint.
3. Separate observed/data, retrospective reconstruction, qualified requirement, and model/predicted outputs. Never fill an observed field with a model.
4. Use `D_response_wall_integral_data_observed_m = integral(t1,t2,v dt_wall)` as the canonical response-stage distance. Keep `D_delay_wall_integral_data_observed_m` only as a deprecated compatibility alias.
5. Calculate primary `D_debt` only from a qualified independent `tau_req` plus an observed velocity path. Call retro-derived debt `D_debt_retro_diagnostic`; keep model debt visibly model-tainted.
6. Treat Reaction Time, Data Age, Update Continuity, and strict causal lineage as distinct semantics.
7. Require an explicit reference before claiming temporal degradation. A single maximum gap without a distribution/reference is only a case-level observation.
8. Distinguish physical reaction interval `T_R=t2-t1` from traced cause-effect propagation. Record lineage grade A/B/C/D/UNKNOWN.
9. Do not use a same-run post-outcome stopping process as the primary Temporal Correctness requirement. It is retrospective reconstruction.
10. Do not equate deadline miss with collision or collision with temporal failure.
11. A collision-truncated run cannot contain a fabricated full observed stopping distance or full-stop margin.
12. If fault onset precedes `t1`, run the pre-hazard state divergence audit and classify D1/v1/a1 changes as pre-existing confounder, possible mediator, post-treatment state, or unknown.
13. Apply weakest-link confidence propagation. A downstream claim cannot exceed the weakest critical prerequisite/evidence link.
14. Keep open critical defeaters visible and cap the affected claim at `UNCERTAIN`/`PARTIAL_PASS` unless the inference contract explicitly allows otherwise.
15. Only write “functionally correct, temporally wrong” when `P_FUNC=QUALIFIED_PASS` and `C4` is established with a qualified independent deadline.
16. With one nonzero delay level, describe `Delta T_R / Delta delay` only as an observed incremental end-to-end response ratio, not a stable gain or amplification factor.
17. Preserve the deployed architecture: the Bridge reads Control directly when Guardian commands are not sent to it.
18. Treat a full experiment report as three deliverables at once: a real-time-systems engineering analysis, an explicit six-layer method instantiation, and a reproducible future-paper method record. Keep their completion claims separate.
19. Use the user's requested report language for the main narrative. In a Chinese report, keep headings, explanations, conclusions, limitations, and table descriptions in Chinese; retain English only for canonical IDs, field names, formulas, paths, and standard verdict enums.

## Mandatory workflow

### 1. Freeze scope and extract evidence

Inventory runs, groups, fault settings, logs, Trace, Control/Bridge evidence, Localization, collision/actor evidence, configuration, and same-run parsed `record/` exports. Profile every record export with:

```bash
python3 <skill-dir>/scripts/profile_record_export.py \
  --record-dir <run>/record \
  --output <analysis-dir>/record_profiles/<run-id>.json
```

Aggregate profiles with:

```bash
python3 <skill-dir>/scripts/aggregate_record_profiles.py \
  --profiles-dir <analysis-dir>/record_profiles \
  --output-csv <analysis-dir>/tables/record_timing_diagnostics.csv
```

Record association must be audited and left-joined. Do not attach another experiment's record by a similar directory timestamp.

### 2. Build event, clock, target, and fault dictionaries

Define `t_c/t1`, module events, `t_e/t2`, requirements, deadlines, stops/collisions, clock domains, target identity, and the Temporal Fault Signature `F_T`. If `fault_onset < t1`, create `pre_hazard_state_audit.csv` before treating D1 or v1 as a confounder.

### 3. Build ledgers before claims

Create:

- `evidence_ledger.csv` with evidence class, source, clock, confidence, limitations, and claim links;
- `temporal_fault_signature.csv`;
- `clock_phase_audit.csv`, `functional_correctness_audit.csv`, and target/deadline qualification evidence;
- `defeater_ledger.csv` with default and experiment-specific defeaters.

Do not draft layer conclusions yet.

### 4. Build prerequisite claims and Claim Graph

Evaluate `P_CLOCK`, `P_TARGET`, `P_FUNC`, and `P_DEADLINE`. Then evaluate `C1` through `C6`; evaluate attribution `C7` only after the six layer claims. Store exact dependencies in `claim_edges.csv` and full gate records in `claim_ledger.csv`.

Each gate must contain an executable `I-M-E-C-O-N` record:

- `I / Inputs`: scoped data and prerequisite claims;
- `M / Metrics`: exact metric names, units, clocks, endpoints, and aggregation scope;
- `E / Evidence`: admissible evidence classes and linked evidence IDs;
- `C / Criterion`: a falsifiable decision rule, including uncertainty and missing-data behavior;
- `O / Output`: verdict, confidence/ceiling, maximum claim level, allowed language, and residual uncertainty;
- `N / Next`: the exact condition for entering the next canonical claim.

Store `gate_inputs`, `gate_metrics`, `admissible_evidence`, `gate_criterion`, and `next_gate_condition` in `claim_ledger.csv` for C1-C7. Support/challenge evidence, prerequisites, defeaters, and `O` fields remain the canonical ledger columns.

### 5. Evaluate inference rules and taint

Use [references/inference-contract.md](references/inference-contract.md). In particular:

- retrospective deadline -> reconstruction only, never primary C4;
- unvalidated model deadline -> `MODEL_SUPPORTED_ONLY`, not direct deadline miss;
- weak alignment/uncertain target -> C3 cannot strong-pass;
- model/retro deadline taint propagates into downstream debt and attribution;
- critical open defeater -> cap claim strength;
- `P_FUNC != QUALIFIED_PASS` -> forbid timing-only functional-correctness language.

### 6. Analyze six layers under gates

- **L1 / C1:** verify the fault signature and actual entry into the SUT/closed loop.
- **L2 / C2:** establish degradation only against a declared reference and distribution; summarize Reaction, Age, and Gap with per-run availability plus P50/P90/P95/P99/MAX and IQR/MAD.
- **L3 / C3:** separate physical reaction interval from strict causal lineage and apply P_CLOCK/P_TARGET ceilings.
- **L4 / C4:** compare observed `T_R` only with a qualified prospective `tau_req`; keep `tau_retro` and `tau_model` separate.
- **L5 / C5:** separate total response distance, qualified deadline-excess debt, retro/model diagnostics, and endpoint-compatible space-budget contributions. Keep collision-truncated runs out of full-stop decompositions.
- **L6 / C6:** report continuous safety degradation and direct outcome evidence with threshold provenance.
- **Attribution / C7:** evaluate functional, initial-state, physical, freshness, phase, geometry, and outcome-conflict alternatives.

### 7. Generate prose from Claim Ledger

The report is downstream of:

`Evidence Ledger -> Claim Ledger -> Defeater Ledger -> Claim Graph -> Report`

Begin with the Six-Layer Inference Status Matrix. For each layer render the `I-M-E-C-O-N` gate plus support, counter-evidence, open defeaters, allowed conclusion, and what remains unproven. Executive language must obey the weakest intermediate claim; strong C1/C6 cannot conceal weak C4/C5.

For a full experiment analysis, also render and link:

- a report-positioning and method-completeness matrix that distinguishes `completed`, `partial`, and `not established`;
- architecture, event semantics, clock/phase audit, functional-correctness audit, and pre-hazard state divergence;
- the full Temporal Fault Signature, including explicit missing end/duration/message/drop/reorder fields;
- `realtime_rag_summary.csv` and an R/A/G tail-distribution figure or equivalent table;
- observed per-run and group space-budget decompositions, with endpoint compatibility and right-censoring visible;
- continuous physical-safety outcomes and threshold provenance;
- model-versus-observed error analysis in a separate section;
- per-run observed results, exclusions, small-n limits, exact reproduction commands, and future evidence/experiment requirements.

Do not label the method empirically complete merely because the Claim Graph and six layer sections exist. Missing independent `tau_req`, record-enabled lineage, phase scan, functional qualification, multiple nonzero fault levels, negative controls, or cross-system validation must remain visible in the method-completeness matrix.

### 8. Validate the argument

Run:

```bash
python3 <skill-dir>/scripts/validate_analysis_outputs.py \
  --analysis-dir <analysis-dir>
```

The validator checks schemas and the argument: prerequisite closure, evidence admissibility, taint, deadline qualification, open defeaters, confidence ceilings, lineage/clock restrictions, pre-hazard audit, claim language, and forbidden inference patterns. Resolve errors rather than weakening rules.

For record-only inputs, run the reduced availability audit after profiling:

```bash
python3 <skill-dir>/scripts/validate_analysis_outputs.py \
  --analysis-dir <analysis-dir> \
  --mode record-only
```

This mode validates that record evidence stays diagnostic and that C4-C6 remain `NOT_TESTABLE`; it does not demand empty physical-outcome tables.

For legacy v1 outputs, create conservative v2 ledgers and reassessment with:

```bash
python3 <skill-dir>/scripts/bootstrap_inference_ledgers.py \
  --analysis-dir <analysis-dir>
```

Bootstrap output is an audit/migration aid. UNKNOWN remains UNKNOWN and does not become PASS.

## Completion criteria

Complete the task only when:

- every important metric is typed in the evidence ledger;
- prerequisite claims, C1-C7, edges, and defeaters are explicit;
- layer gates reflect evidence eligibility rather than metric presence;
- C1-C7 have nonempty `I-M-E-C-O-N` gate fields and an explicit next-gate condition;
- response distance uses wall-clock integration and distance debt carries its requirement/model/retro provenance;
- collision right-censoring and observed/model separation hold;
- a full experiment report includes R/A/G tail statistics, endpoint-compatible space-budget tables, and a method-completeness matrix;
- the report explicitly separates structural method instantiation from empirically unclosed evidence bridges;
- open critical defeaters and residual uncertainty remain visible;
- the report language does not exceed the Claim Ledger ceiling;
- semantic validation passes, or a legacy report's failure is explicitly retained as a v2 reassessment finding.
