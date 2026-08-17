#!/usr/bin/env python3
"""Build conservative backward temporal-defect hypotheses from C4/L6 seeds."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence


HYPOTHESIS_FIELDS = [
    "hypothesis_id", "run_id_or_group", "seed_claim_id", "seed_evidence_ids",
    "candidate_layer", "candidate_component", "candidate_fault_type", "hypothesis",
    "path_claim_ids", "supporting_evidence_ids", "challenging_evidence_ids",
    "alternative_hypothesis_ids", "required_prerequisite_claim_ids",
    "diagnosability_class", "equivalence_class_id", "status", "rank_score",
    "rank_method", "maximum_diagnosis_strength", "discriminating_test",
    "residual_uncertainty", "allowed_language", "forbidden_language",
]

EDGE_FIELDS = ["parent_id", "child_id", "relation", "time_direction", "required", "notes"]

CANDIDATES = [
    ("L1", "external_injection", "EXTERNAL_TEMPORAL_INTERVENTION", ("DELAY", "FAULT_SIGNATURE"), "Verify actual applied rows and repeat without injection."),
    ("L2", "data_freshness", "STALE_OR_REUSED_DATA", ("AGE", "STALE", "REUSE"), "Collect source/header/receipt lineage and compare data-age distributions."),
    ("L2", "update_continuity", "MESSAGE_GAP_OR_LOSS", ("GAP", "DROP", "CONTINUITY"), "Capture per-message sequence/gap/loss evidence under matched phase."),
    ("L2", "compute_runtime", "EXECUTION_OR_QUEUE_TAIL", ("LATENCY", "QUEUE", "PROCESS", "WCET"), "Collect executor/queue/trace spans and test node deadline budgets."),
    ("L3", "network_bridge", "NETWORK_OR_BRIDGE_DELAY", ("BRIDGE", "NETWORK", "CONTROL_TO_T2"), "Timestamp Control receive, Bridge apply, and physical actuation on qualified clocks."),
    ("L3", "actuation", "ACTUATION_RESPONSE_DELAY", ("ACTUATION", "BRAKE", "CONTROL_TO_T2"), "Measure command-to-actuator and actuator-to-deceleration response independently."),
    ("P_CLOCK", "clock", "CLOCK_ALIGNMENT_ARTIFACT", ("CLOCK", "OFFSET", "DRIFT"), "Collect offset/drift/dispersion history and recompute the interval error budget."),
    ("P_PHASE", "phase", "PERIODIC_PHASE_EFFECT", ("PHASE", "TICK", "PERIOD"), "Run an active injection/sampling phase scan with repeats."),
    ("P_FUNC", "functional_chain", "FUNCTIONAL_FAILURE", ("FALLBACK", "INFEASIBLE", "TARGET", "FUNCTION"), "Audit target-specific Planning/Control semantics and payload continuity."),
    ("L5", "vehicle_geometry", "PHYSICAL_OR_GEOMETRY_ALTERNATIVE", ("D1", "BRAKING", "GEOMETRY", "MARGIN"), "Match initial state and independently calibrate braking/geometry envelopes."),
]


def clean(value: object) -> str:
    return str("" if value is None else value).strip()


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def base(claim_id: str) -> str:
    return claim_id.split(".", 1)[0].upper()


def build(root: Path) -> tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    tables = root / "tables"
    claims = read_csv(tables / "claim_ledger.csv")
    evidence = read_csv(tables / "evidence_ledger.csv")
    seeds = [
        row for row in claims
        if (base(clean(row.get("claim_id"))) == "C4" and clean(row.get("verdict")).upper() == "PASS")
        or (base(clean(row.get("claim_id"))) == "C6" and clean(row.get("verdict")).upper() in {"PASS", "PARTIAL_PASS"})
    ]
    hypotheses: List[Dict[str, object]] = []
    edges: List[Dict[str, object]] = []
    for seed in seeds:
        seed_id = clean(seed.get("claim_id"))
        scope = clean(seed.get("run_id_or_group"))
        seed_evidence = clean(seed.get("supporting_evidence_ids"))
        ids: List[str] = []
        for index, (layer, component, fault_type, keywords, discriminator) in enumerate(CANDIDATES, 1):
            hypothesis_id = "H.%s.%02d" % (seed_id, index)
            ids.append(hypothesis_id)
            matching = [
                row for row in evidence
                if any(keyword in (clean(row.get("metric")) + " " + clean(row.get("semantic_role"))).upper() for keyword in keywords)
                and clean(row.get("availability")).upper() in {"AVAILABLE", "PRESENT"}
            ]
            supporting = "|".join(clean(row.get("evidence_id")) for row in matching[:20])
            status = "CONSISTENT_BUT_UNRESOLVED" if supporting else "NOT_TESTABLE"
            score = 1.0 if supporting else 0.0
            hypotheses.append(
                {
                    "hypothesis_id": hypothesis_id, "run_id_or_group": scope,
                    "seed_claim_id": seed_id, "seed_evidence_ids": seed_evidence,
                    "candidate_layer": layer, "candidate_component": component,
                    "candidate_fault_type": fault_type,
                    "hypothesis": "%s is temporally/physically consistent with seed %s but is not proven by reverse traversal." % (fault_type, seed_id),
                    "path_claim_ids": "C6|C5|C4|C3|C2|C1" if base(seed_id) == "C6" else "C4|C3|C2|C1",
                    "supporting_evidence_ids": supporting, "challenging_evidence_ids": "",
                    "alternative_hypothesis_ids": "", "required_prerequisite_claim_ids": "P_CLOCK|P_TARGET",
                    "diagnosability_class": "OBSERVATIONALLY_EQUIVALENT_CANDIDATE_SET",
                    "equivalence_class_id": "EQ.%s" % seed_id, "status": status,
                    "rank_score": score, "rank_method": "EVIDENCE_AVAILABILITY_ONLY_NO_CAUSAL_PROBABILITY",
                    "maximum_diagnosis_strength": "DETECTED" if status == "NOT_TESTABLE" else "LOCALIZED_TO_SEGMENT",
                    "discriminating_test": discriminator,
                    "residual_uncertainty": "Competing candidates remain observationally equivalent until the discriminating test is run.",
                    "allowed_language": "This remains a candidate consistent with the observed seed.",
                    "forbidden_language": "proven root cause|unique root cause|intrinsic Apollo defect",
                }
            )
            edges.append(
                {"parent_id": seed_id, "child_id": hypothesis_id, "relation": "SEEDS_DIAGNOSIS",
                 "time_direction": "BACKWARD_DIAGNOSTIC", "required": "TRUE",
                 "notes": "Downstream observation seeds, but does not prove, an upstream candidate."}
            )
            for row in matching[:20]:
                edges.append(
                    {"parent_id": clean(row.get("evidence_id")), "child_id": hypothesis_id,
                     "relation": "CONSISTENT_WITH", "time_direction": "BACKWARD_DIAGNOSTIC",
                     "required": "FALSE", "notes": "Available evidence is consistent, not uniquely identifying."}
                )
        alternatives = "|".join(ids)
        for row in hypotheses[-len(ids):]:
            row["alternative_hypothesis_ids"] = "|".join(item for item in ids if item != row["hypothesis_id"])
    return hypotheses, edges


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.analysis_dir.resolve()
    hypotheses, edges = build(root)
    write_csv(root / "tables/diagnosis_hypothesis_ledger.csv", HYPOTHESIS_FIELDS, hypotheses)
    write_csv(root / "tables/diagnosis_edges.csv", EDGE_FIELDS, edges)
    print(json.dumps({"hypotheses": len(hypotheses), "edges": len(edges)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
