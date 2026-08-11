#!/usr/bin/env python3
"""Semantic inference checks for TCPS-PA Diagnostic Protocol v2.

This module is deliberately standard-library only.  It validates whether an
evidence/claim graph is methodologically admissible; it does not compute the
experiment's physical metrics and never upgrades missing evidence.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple


EVIDENCE_CLASSES: Set[str] = {
    "DIRECT_OBSERVED",
    "OBSERVED_DERIVED",
    "REQUIREMENT_CONSTRAINED_DERIVED",
    "TRACE_LINEAGE",
    "RETROSPECTIVE_RECONSTRUCTION",
    "INDEPENDENT_REQUIREMENT",
    "INDEPENDENT_CALIBRATED_MODEL",
    "VALIDATED_MODEL",
    "UNVALIDATED_MODEL",
    "WEAK_TEMPORAL_ALIGNMENT",
    "CLOCK_UNVERIFIED",
    "OUTCOME_TRUNCATED",
    "CONFLICTED_EVIDENCE",
    "MISSING",
}

VERDICTS: Set[str] = {
    "PASS",
    "PARTIAL_PASS",
    "FAIL",
    "UNCERTAIN",
    "NOT_TESTABLE",
    "RETROSPECTIVE_ONLY",
    "MODEL_SUPPORTED_ONLY",
    "QUALIFIED_PASS",  # P_FUNC
    "PARTIAL",  # P_FUNC
}

DEFEATER_STATES: Set[str] = {
    "OPEN",
    "BOUNDED",
    "RESOLVED",
    "REFUTED",
    "NOT_APPLICABLE",
    "UNKNOWN",
}

CONFIDENCE_ORDER = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
CRITICAL_DEFEATER_IMPACTS = {"CRITICAL", "INVALIDATES", "CAPS_AT_PARTIAL"}
WEAK_VERDICTS = {
    "PARTIAL_PASS",
    "PARTIAL",
    "UNCERTAIN",
    "NOT_TESTABLE",
    "RETROSPECTIVE_ONLY",
    "MODEL_SUPPORTED_ONLY",
}

REQUIRED_CLAIM_BASES = {
    "P_CLOCK", "P_TARGET", "P_FUNC", "P_DEADLINE",
    "C1", "C2", "C3", "C4", "C5", "C6", "C7",
}

EXPECTED_LAYERS = {
    "C1": "L1", "C2": "L2", "C3": "L3", "C4": "L4",
    "C5": "L5", "C6": "L6", "C7": "ATTRIBUTION",
}

EXPECTED_RULES = {base: "IR-%s" % base for base in EXPECTED_LAYERS}

CANONICAL_PARENT_BASES = {
    "C2": {"C1"},
    "C3": {"C1", "C2", "P_CLOCK", "P_TARGET"},
    "C4": {"C3", "P_DEADLINE"},
    "C5": {"C4"},
    "C7": {"C4", "C5", "C6", "P_FUNC"},
}

MANDATORY_STRONG_EVIDENCE = {
    "C1": {"DIRECT_OBSERVED"},
    "C3": {"TRACE_LINEAGE"},
    "C4": {"OBSERVED_DERIVED"},
    "C5": {"REQUIREMENT_CONSTRAINED_DERIVED"},
    "C6": {"DIRECT_OBSERVED"},
    "P_TARGET": {"TRACE_LINEAGE"},
    "P_DEADLINE": {"INDEPENDENT_REQUIREMENT"},
}

C7_DEFAULT_DEFEATER_TYPES = {
    "D_INITIAL_CLEARANCE": "INITIAL_CLEARANCE",
    "D_INITIAL_SPEED": "INITIAL_SPEED",
    "D_BRAKING_CAPABILITY": "BRAKING_CAPABILITY",
    "D_FUNCTIONAL_FAILURE": "FUNCTIONAL_FAILURE",
    "D_TARGET_MISMATCH": "TARGET_MISMATCH",
    "D_DATA_FRESHNESS": "DATA_FRESHNESS",
    "D_UPDATE_GAP": "UPDATE_GAP",
    "D_SOLVER_FALLBACK": "SOLVER_FALLBACK",
    "D_CLOCK": "CLOCK",
    "D_PHASE": "PHASE",
    "D_PREHAZARD_STATE": "PREHAZARD_STATE",
    "D_GEOMETRY": "GEOMETRY",
    "D_OUTCOME_CONFLICT": "OUTCOME_CONFLICT",
}

GLOBAL_FORBIDDEN_PATTERNS: Sequence[Tuple[str, str]] = (
    (r"\bsole cause\b", "sole-cause language"),
    (r"proves?\s+Apollo\s+is\s+non[- ]real[- ]time", "unqualified Apollo defect claim"),
    (r"fixed\s+700\s*ms\s+deadline", "fixed 700 ms deadline"),
    (r"700\s*ms.{0,30}(universal|普适|固定).{0,15}(deadline|阈值)", "universal 700 ms deadline"),
    (r"stable\s+1\.5\s*[x×].{0,20}(gain|amplification)", "stable 1.5x gain"),
    (r"1\.5\s*倍.{0,10}放大", "1.5x amplification"),
    (r"放大系数", "amplification-factor language"),
    (r"\bamplification factor\b", "amplification-factor language"),
    (r"\bpropagation gain\b", "propagation-gain language"),
    (r"\bsystem gain\b", "system-gain language"),
    (r"放大效应", "amplification-effect language"),
    (r"延迟乘数", "delay-multiplier language"),
    (r"\bdelay multiplier\b", "delay-multiplier language"),
    (r"(?:闭环|物理响应端).{0,30}被放大", "closed-loop amplification language"),
    (r"complete six[- ]layer proof", "complete-proof language"),
    (r"完整(六层|传播).{0,12}(证明|证据链已经成立)", "complete-proof language"),
)

V11_ONLY_LABELS = {
    "stable 1.5x gain", "1.5x amplification", "amplification-factor language",
    "propagation-gain language", "system-gain language", "amplification-effect language",
    "delay-multiplier language",
    "closed-loop amplification language",
}


def clean(value: Any) -> str:
    return str(value or "").strip()


def upper(value: Any) -> str:
    return clean(value).upper()


def split_ids(value: Any) -> List[str]:
    text = clean(value)
    if not text:
        return []
    return [item.strip() for item in text.replace(",", "|").split("|") if item.strip()]


def safe_float(value: Any) -> Optional[float]:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def boolish(value: Any) -> bool:
    return upper(value) in {"TRUE", "1", "YES", "Y", "PASS"}


def first_markdown_table_after(text_value: str, marker: str) -> str:
    """Return the first visible Markdown table following marker."""

    marker_index = text_value.lower().find(marker.lower())
    if marker_index < 0:
        return ""
    lines = text_value[marker_index:].splitlines()
    table_lines: List[str] = []
    started = False
    for line in lines[1:]:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            table_lines.append(stripped)
            started = True
        elif started and stripped:
            break
    return "\n".join(table_lines)


def has_unnegated_match(pattern: str, text_value: str) -> bool:
    """Conservative phrase guard that does not punish explicit prohibitions."""

    negations = (
        "不能", "不可", "不得", "禁止", "阻止", "不应", "并非", "不是",
        "cannot", "can't", "must not", "do not", "does not", "not a", "forbid",
    )
    for match in re.finditer(pattern, text_value, flags=re.IGNORECASE | re.DOTALL):
        prefix = text_value[max(0, match.start() - 45):match.start()].lower()
        if any(token in prefix for token in negations):
            continue
        return True
    return False


def base_claim_id(claim_id: str) -> str:
    return claim_id.split(".", 1)[0].upper()


def claim_scope(claim: Mapping[str, Any]) -> str:
    declared = clean(claim.get("run_id_or_group"))
    if declared:
        return declared
    claim_id = clean(claim.get("claim_id"))
    return claim_id.split(".", 1)[1] if "." in claim_id else ""


def confidence_value(value: Any) -> int:
    return CONFIDENCE_ORDER.get(upper(value), -1)


def issue(
    severity: str,
    rule: str,
    message: str,
    claim_id: str = "",
    evidence_id: str = "",
) -> Dict[str, str]:
    return {
        "severity": severity,
        "rule": rule,
        "claim_id": claim_id,
        "evidence_id": evidence_id,
        "message": message,
    }


def claim_index(claims: Sequence[Mapping[str, Any]]) -> Dict[str, Mapping[str, Any]]:
    return {clean(row.get("claim_id")): row for row in claims if clean(row.get("claim_id"))}


def evidence_index(evidence: Sequence[Mapping[str, Any]]) -> Dict[str, Mapping[str, Any]]:
    return {
        clean(row.get("evidence_id")): row
        for row in evidence
        if clean(row.get("evidence_id"))
    }


def supporting_rows(
    claim: Mapping[str, Any], evidence_by_id: Mapping[str, Mapping[str, Any]]
) -> List[Mapping[str, Any]]:
    return [
        evidence_by_id[evidence_id]
        for evidence_id in split_ids(claim.get("supporting_evidence_ids"))
        if evidence_id in evidence_by_id
    ]


def prerequisite_rows(
    claim: Mapping[str, Any], claims_by_id: Mapping[str, Mapping[str, Any]]
) -> List[Mapping[str, Any]]:
    return [
        claims_by_id[claim_id]
        for claim_id in split_ids(claim.get("prerequisite_claim_ids"))
        if claim_id in claims_by_id
    ]


def weakest_confidence_ceiling(
    claim: Mapping[str, Any],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    claims_by_id: Mapping[str, Mapping[str, Any]],
    defeaters_by_claim: Mapping[str, Sequence[Mapping[str, Any]]],
) -> str:
    values: List[int] = []
    for row in supporting_rows(claim, evidence_by_id):
        value = confidence_value(row.get("confidence"))
        if value >= 0:
            values.append(value)
    for row in prerequisite_rows(claim, claims_by_id):
        value = confidence_value(row.get("confidence_ceiling") or row.get("confidence"))
        if value >= 0:
            values.append(value)
    for row in defeaters_by_claim.get(clean(claim.get("claim_id")), []):
        if upper(row.get("status")) in {"OPEN", "UNKNOWN"} and upper(
            row.get("impact_on_claim")
        ) in CRITICAL_DEFEATER_IMPACTS:
            values.append(CONFIDENCE_ORDER["MEDIUM"])
    if not values:
        return "NONE"
    ceiling = min(values)
    return next(name for name, rank in CONFIDENCE_ORDER.items() if rank == ceiling)


def has_qualified_deadline(
    claim: Mapping[str, Any],
    support: Sequence[Mapping[str, Any]],
    claims_by_id: Mapping[str, Mapping[str, Any]],
) -> bool:
    classes = {upper(row.get("evidence_class")) for row in support}
    deadline_prereqs = [
        claims_by_id[item]
        for item in split_ids(claim.get("prerequisite_claim_ids"))
        if item in claims_by_id and base_claim_id(item) == "P_DEADLINE"
    ]
    prerequisite_pass = any(
        upper(row.get("verdict")) in {"PASS", "QUALIFIED_PASS"}
        for row in deadline_prereqs
    )
    eligible_class = bool(
        classes
        & {
            "INDEPENDENT_REQUIREMENT",
            "INDEPENDENT_CALIBRATED_MODEL",
            "VALIDATED_MODEL",
        }
    )
    return prerequisite_pass and eligible_class


def has_observed_reaction(support: Sequence[Mapping[str, Any]]) -> bool:
    for row in support:
        metric = upper(row.get("metric"))
        klass = upper(row.get("evidence_class"))
        endpoint = upper(row.get("endpoint_definition"))
        semantic_role = upper(row.get("semantic_role"))
        if (
            klass in {"DIRECT_OBSERVED", "OBSERVED_DERIVED"}
            and metric in {"T_R", "T_E2E_DATA_OBSERVED_MS"}
            and (
                semantic_role == "PHYSICAL_REACTION_INTERVAL"
                or endpoint.startswith("PHYSICAL_RESPONSE")
            )
        ):
            return True
    return False


def has_direct_physical_outcome(support: Sequence[Mapping[str, Any]]) -> bool:
    for row in support:
        if upper(row.get("evidence_class")) != "DIRECT_OBSERVED":
            continue
        if upper(row.get("semantic_role")) != "PHYSICAL_OUTCOME":
            continue
        metric = upper(row.get("metric"))
        if metric in {
            "PHYSICAL_OUTCOME",
            "COLLISION_EVENT_DATA_OBSERVED",
            "FINAL_CLEARANCE_PROJECTED_DATA_OBSERVED_M",
            "M_COLLISION_0M_DATA_OBSERVED_M",
            "M_SAFETY_6M_DATA_OBSERVED_M",
            "IMPACT_SPEED_DATA_OBSERVED_MPS",
        }:
            return True
    return False


def has_observed_velocity_path(support: Sequence[Mapping[str, Any]]) -> bool:
    for row in support:
        metric = upper(row.get("metric"))
        klass = upper(row.get("evidence_class"))
        if klass in {"DIRECT_OBSERVED", "OBSERVED_DERIVED", "REQUIREMENT_CONSTRAINED_DERIVED"} and (
            "VELOCITY" in metric
            or "D_RESPONSE" in metric
            or "WALL_INTEGRAL" in metric
            or upper(row.get("semantic_role")) == "OBSERVED_VELOCITY_PATH"
        ):
            return True
    return False


def qualified_deadline_comparisons(
    claim: Mapping[str, Any],
    support: Sequence[Mapping[str, Any]],
    requirement_rows: Sequence[Mapping[str, Any]],
) -> List[Tuple[float, float, float]]:
    """Return compatible (T_R, tau_low, tau_high) tuples in milliseconds."""

    reaction_by_run: Dict[str, List[float]] = defaultdict(list)
    for row in support:
        if not has_observed_reaction([row]):
            continue
        value = safe_float(row.get("value"))
        if value is not None and upper(row.get("unit")) in {"MS", "MILLISECOND", "MILLISECONDS"}:
            reaction_by_run[clean(row.get("run_id"))].append(value)

    scope = claim_scope(claim)
    result: List[Tuple[float, float, float]] = []
    eligible_classes = {
        "INDEPENDENT_REQUIREMENT", "INDEPENDENT_CALIBRATED_MODEL", "VALIDATED_MODEL",
    }
    linked_requirement_ids = {
        clean(row.get("requirement_id")) for row in support
        if upper(row.get("evidence_class")) in eligible_classes
        and clean(row.get("requirement_id"))
    }
    if not linked_requirement_ids:
        return []
    for requirement in requirement_rows:
        if clean(requirement.get("requirement_id")) not in linked_requirement_ids:
            continue
        if upper(requirement.get("evidence_class")) not in eligible_classes:
            continue
        if "QUALIFIED" not in upper(requirement.get("p_deadline_qualification")) or (
            "NOT_QUALIFIED" in upper(requirement.get("p_deadline_qualification"))
        ):
            continue
        if upper(requirement.get("unit")) not in {"MS", "MILLISECOND", "MILLISECONDS"}:
            continue
        req_scope = clean(requirement.get("run_id_or_group"))
        center = safe_float(requirement.get("tau_req_center_ms") or requirement.get("requirement_value"))
        low = safe_float(requirement.get("tau_req_low_ms"))
        high = safe_float(requirement.get("tau_req_high_ms"))
        if center is None and (low is None or high is None):
            continue
        low = center if low is None else low
        high = center if high is None else high
        if low is None or high is None or low > high:
            continue
        compatible_runs = [req_scope] if req_scope in reaction_by_run else []
        if req_scope == scope or req_scope.lower() in {"all", "all_runs", "group"}:
            compatible_runs = list(reaction_by_run)
        for run_id in compatible_runs:
            for reaction in reaction_by_run.get(run_id, []):
                result.append((reaction, low, high))
    return result


def validate_argument_rows(
    claims: Sequence[Mapping[str, Any]],
    evidence: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
    defeaters: Sequence[Mapping[str, Any]],
    fault_signatures: Sequence[Mapping[str, Any]] = (),
    pre_hazard_rows: Sequence[Mapping[str, Any]] = (),
    functional_rows: Sequence[Mapping[str, Any]] = (),
    clock_rows: Sequence[Mapping[str, Any]] = (),
    requirement_rows: Sequence[Mapping[str, Any]] = (),
    observed_rows: Sequence[Mapping[str, Any]] = (),
    report_text: str = "",
) -> List[Dict[str, str]]:
    """Return semantic issues. Errors are methodological contract violations."""

    issues: List[Dict[str, str]] = []
    visible_report = re.sub(r"<!--.*?-->", "", report_text, flags=re.DOTALL)
    claims_by_id = claim_index(claims)
    evidence_by_id = evidence_index(evidence)
    defeaters_by_claim: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    defeaters_by_id: Dict[str, Mapping[str, Any]] = {}
    for row in defeaters:
        defeaters_by_claim[clean(row.get("claim_id"))].append(row)
        defeater_id = clean(row.get("defeater_id"))
        if defeater_id:
            if defeater_id in defeaters_by_id:
                issues.append(issue("ERROR", "S6", "defeater_id values must be unique"))
            defeaters_by_id[defeater_id] = row

    if not claims:
        issues.append(issue("ERROR", "GRAPH_COMPLETENESS", "claim_ledger.csv is empty"))
    else:
        present_bases = {base_claim_id(clean(row.get("claim_id"))) for row in claims}
        missing_bases = sorted(REQUIRED_CLAIM_BASES - present_bases)
        if missing_bases:
            issues.append(
                issue(
                    "ERROR", "GRAPH_COMPLETENESS",
                    "Claim Graph lacks required bases: %s" % ", ".join(missing_bases),
                )
            )

    for row in claims:
        claim_id = clean(row.get("claim_id"))
        base = base_claim_id(claim_id)
        if not claim_id or "." not in claim_id:
            issues.append(
                issue("ERROR", "GRAPH_COMPLETENESS", "claim_id must be explicitly scoped", claim_id)
            )
        if not clean(row.get("proposition")):
            issues.append(
                issue("ERROR", "GRAPH_COMPLETENESS", "claim proposition is empty", claim_id)
            )
        expected_layer = EXPECTED_LAYERS.get(base)
        if expected_layer and upper(row.get("layer")) != expected_layer:
            issues.append(
                issue(
                    "ERROR", "GRAPH_COMPLETENESS",
                    "%s must use layer %s" % (base, expected_layer), claim_id,
                )
            )
        expected_rule = EXPECTED_RULES.get(base)
        if expected_rule and upper(row.get("inference_rule_id")) != expected_rule:
            issues.append(
                issue(
                    "ERROR", "GRAPH_COMPLETENESS",
                    "%s must use inference_rule_id %s" % (base, expected_rule), claim_id,
                )
            )
        if base in EXPECTED_LAYERS:
            gate_fields = (
                "gate_inputs", "gate_metrics", "admissible_evidence",
                "gate_criterion", "next_gate_condition",
            )
            missing_gate_fields = [
                field for field in gate_fields if not clean(row.get(field))
            ]
            if missing_gate_fields:
                issues.append(
                    issue(
                        "ERROR", "GATE_COMPLETENESS",
                        "I-M-E-C-O-N gate fields are empty: %s" %
                        ", ".join(missing_gate_fields),
                        claim_id,
                    )
                )

    # Core enum, ID, and link integrity.
    if len(claims_by_id) != len([row for row in claims if clean(row.get("claim_id"))]):
        issues.append(issue("ERROR", "S1", "claim_id values must be unique"))
    if len(evidence_by_id) != len([row for row in evidence if clean(row.get("evidence_id"))]):
        issues.append(issue("ERROR", "S2", "evidence_id values must be unique"))

    for row in evidence:
        evidence_id = clean(row.get("evidence_id"))
        klass = upper(row.get("evidence_class"))
        if klass not in EVIDENCE_CLASSES:
            issues.append(
                issue(
                    "ERROR",
                    "S3",
                    "unknown evidence class: %s" % (klass or "<empty>"),
                    evidence_id=evidence_id,
                )
            )
        if upper(row.get("confidence")) not in CONFIDENCE_ORDER:
            issues.append(
                issue(
                    "ERROR", "S7", "unknown evidence confidence: %s" % upper(row.get("confidence")),
                    evidence_id=evidence_id,
                )
            )

    for row in defeaters:
        status = upper(row.get("status"))
        if status not in DEFEATER_STATES:
            issues.append(
                issue(
                    "ERROR",
                    "S4",
                    "unknown defeater status: %s" % (status or "<empty>"),
                    claim_id=clean(row.get("claim_id")),
                )
            )

    edge_pairs = {
        (clean(row.get("parent_claim_id")), clean(row.get("child_claim_id")))
        for row in edges
    }
    for row in edges:
        parent = clean(row.get("parent_claim_id"))
        child = clean(row.get("child_claim_id"))
        if parent not in claims_by_id or child not in claims_by_id:
            issues.append(
                issue(
                    "ERROR",
                    "V0",
                    "claim edge references unknown node %s -> %s" % (parent, child),
                    child,
                )
            )
        if (parent, child) in edge_pairs and (
            upper(row.get("relation")) != "REQUIRES" or not boolish(row.get("required"))
        ):
            # Non-REQUIRES edges are allowed, but they cannot satisfy a declared prerequisite.
            if child in claims_by_id and parent in split_ids(
                claims_by_id[child].get("prerequisite_claim_ids")
            ):
                issues.append(
                    issue(
                        "ERROR", "V0",
                        "declared prerequisite edge must be relation=REQUIRES and required=true",
                        child,
                    )
                )

    # Required edges must form a DAG.
    required_graph: Dict[str, Set[str]] = defaultdict(set)
    for row in edges:
        if upper(row.get("relation")) == "REQUIRES" and boolish(row.get("required")):
            required_graph[clean(row.get("parent_claim_id"))].add(
                clean(row.get("child_claim_id"))
            )

    visiting: Set[str] = set()
    visited: Set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(child) for child in required_graph.get(node, set())):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    if any(visit(node) for node in list(required_graph) if node not in visited):
        issues.append(issue("ERROR", "V0", "REQUIRES Claim Graph contains a cycle"))

    for row in evidence:
        evidence_id = clean(row.get("evidence_id"))
        for linked_claim in split_ids(row.get("supports_claim_ids")) + split_ids(
            row.get("challenges_claim_ids")
        ):
            if linked_claim not in claims_by_id:
                issues.append(
                    issue(
                        "ERROR", "V0", "evidence references unknown claim %s" % linked_claim,
                        linked_claim, evidence_id,
                    )
                )

    for row in defeaters:
        linked_claim = clean(row.get("claim_id"))
        if linked_claim not in claims_by_id:
            issues.append(
                issue("ERROR", "V0", "defeater references unknown claim", linked_claim)
            )

    for claim in claims:
        claim_id = clean(claim.get("claim_id"))
        base = base_claim_id(claim_id)
        verdict = upper(claim.get("verdict"))
        if verdict not in VERDICTS:
            issues.append(issue("ERROR", "S5", "unknown verdict: %s" % verdict, claim_id))
        for field in ("confidence", "confidence_ceiling"):
            if upper(claim.get(field)) not in CONFIDENCE_ORDER:
                issues.append(
                    issue(
                        "ERROR", "S7", "unknown %s: %s" % (field, upper(claim.get(field))),
                        claim_id,
                    )
                )
        level = safe_float(claim.get("maximum_claim_level"))
        if level is None or level < 0 or level > 6 or not float(level).is_integer():
            issues.append(
                issue("ERROR", "S8", "maximum_claim_level must be an integer from 0 to 6", claim_id)
            )

        prereq_ids = split_ids(claim.get("prerequisite_claim_ids"))
        prereq_bases = {
            base_claim_id(item) for item in prereq_ids if item in claims_by_id
        }
        missing_canonical = sorted(CANONICAL_PARENT_BASES.get(base, set()) - prereq_bases)
        if missing_canonical:
            issues.append(
                issue(
                    "ERROR", "V0",
                    "%s lacks canonical prerequisites: %s"
                    % (base, ", ".join(missing_canonical)), claim_id,
                )
            )
        for prereq_id in prereq_ids:
            if prereq_id not in claims_by_id:
                issues.append(
                    issue("ERROR", "V0", "missing prerequisite claim %s" % prereq_id, claim_id)
                )
                continue
            if (prereq_id, claim_id) not in edge_pairs:
                issues.append(
                    issue(
                        "ERROR",
                        "V0",
                        "prerequisite %s is not represented in claim_edges.csv" % prereq_id,
                        claim_id,
                    )
                )
            elif claim_scope(claims_by_id[prereq_id]) != claim_scope(claim):
                issues.append(
                    issue(
                        "ERROR", "V0", "prerequisite is from a different scope",
                        claim_id,
                    )
                )

        support_ids = split_ids(claim.get("supporting_evidence_ids"))
        for evidence_id in support_ids:
            if evidence_id not in evidence_by_id:
                issues.append(
                    issue(
                        "ERROR",
                        "V0",
                        "missing supporting evidence %s" % evidence_id,
                        claim_id,
                        evidence_id,
                    )
                )
                continue
            evidence_row = evidence_by_id[evidence_id]
            if claim_id not in split_ids(evidence_row.get("supports_claim_ids")):
                issues.append(
                    issue(
                        "ERROR", "V0", "claim/evidence support link is not reciprocal",
                        claim_id, evidence_id,
                    )
                )
            if verdict in {"PASS", "QUALIFIED_PASS"}:
                availability = upper(evidence_row.get("availability"))
                if availability not in {"AVAILABLE", "PRESENT"}:
                    issues.append(
                        issue(
                            "ERROR", "E_ADMISSIBILITY",
                            "strong claim uses unavailable evidence", claim_id, evidence_id,
                        )
                    )
                for field in ("value", "unit", "source_file", "source_locator"):
                    if not clean(evidence_row.get(field)):
                        issues.append(
                            issue(
                                "ERROR", "E_ADMISSIBILITY",
                                "strong evidence lacks %s" % field, claim_id, evidence_id,
                            )
                        )
                if upper(evidence_row.get("evidence_class")) in {
                    "MISSING", "CONFLICTED_EVIDENCE", "CLOCK_UNVERIFIED",
                    "WEAK_TEMPORAL_ALIGNMENT",
                }:
                    issues.append(
                        issue(
                            "ERROR", "E_ADMISSIBILITY",
                            "strong claim uses evidence class that cannot strong-pass",
                            claim_id, evidence_id,
                        )
                    )

        for evidence_id in split_ids(claim.get("challenging_evidence_ids")):
            if evidence_id not in evidence_by_id:
                issues.append(
                    issue(
                        "ERROR", "V0", "missing challenging evidence %s" % evidence_id,
                        claim_id, evidence_id,
                    )
                )
                continue
            challenge_row = evidence_by_id[evidence_id]
            if claim_id not in split_ids(challenge_row.get("challenges_claim_ids")):
                issues.append(
                    issue(
                        "ERROR", "V0", "claim/evidence challenge link is not reciprocal",
                        claim_id, evidence_id,
                    )
                )
            if verdict in {"PASS", "QUALIFIED_PASS"} and upper(
                challenge_row.get("availability")
            ) in {"AVAILABLE", "PRESENT"}:
                issues.append(
                    issue(
                        "ERROR", "V16",
                        "unresolved available challenging evidence forbids a strong verdict",
                        claim_id, evidence_id,
                    )
                )
        for defeater_id in split_ids(claim.get("defeater_ids")):
            defeater = defeaters_by_id.get(defeater_id)
            if not defeater:
                issues.append(
                    issue("ERROR", "V0", "missing defeater %s" % defeater_id, claim_id)
                )
            elif clean(defeater.get("claim_id")) != claim_id:
                issues.append(
                    issue(
                        "ERROR", "V0", "defeater %s belongs to a different claim" % defeater_id,
                        claim_id,
                    )
                )

        support = supporting_rows(claim, evidence_by_id)
        support_classes = {upper(row.get("evidence_class")) for row in support}
        if verdict in {"PARTIAL_PASS", "PARTIAL"} and not any(
            upper(row.get("availability")) in {"AVAILABLE", "PRESENT"}
            and upper(row.get("evidence_class")) not in {"MISSING", "CONFLICTED_EVIDENCE"}
            for row in support
        ):
            issues.append(
                issue(
                    "ERROR", "E_ADMISSIBILITY",
                    "partial positive verdict has no available supporting evidence", claim_id,
                )
            )
        required_classes = {upper(item) for item in split_ids(claim.get("required_evidence_classes"))}
        missing_required = sorted(required_classes - support_classes)
        if missing_required and verdict in {"PASS", "QUALIFIED_PASS"}:
            issues.append(
                issue(
                    "ERROR",
                    "E_ADMISSIBILITY",
                    "PASS claim lacks required evidence classes: %s"
                    % ", ".join(missing_required),
                    claim_id,
                )
            )
        mandatory = MANDATORY_STRONG_EVIDENCE.get(base, set())
        if verdict in {"PASS", "QUALIFIED_PASS"} and mandatory:
            if base == "P_DEADLINE":
                eligible = {
                    "INDEPENDENT_REQUIREMENT", "INDEPENDENT_CALIBRATED_MODEL", "VALIDATED_MODEL",
                }
                mandatory_missing = not bool(support_classes & eligible)
            else:
                mandatory_missing = not mandatory.issubset(support_classes)
            if mandatory_missing:
                issues.append(
                    issue(
                        "ERROR", "E_ADMISSIBILITY",
                        "%s strong verdict lacks contract-mandated evidence role/class" % base,
                        claim_id,
                    )
                )

        mandatory_semantic_roles = {
            "C1": "TEMPORAL_DISTURBANCE_APPLICATION",
            "P_TARGET": "TARGET_LINEAGE",
            "C3": "CAUSE_EFFECT_LINEAGE",
        }
        required_role = mandatory_semantic_roles.get(base)
        if verdict in {"PASS", "QUALIFIED_PASS"} and required_role and not any(
            upper(row.get("semantic_role")) == required_role for row in support
        ):
            issues.append(
                issue(
                    "ERROR", "E_ADMISSIBILITY",
                    "%s strong verdict lacks semantic_role=%s" % (base, required_role),
                    claim_id,
                )
            )

        # Prerequisite closure for strong claims.
        for prereq in prerequisite_rows(claim, claims_by_id):
            prereq_verdict = upper(prereq.get("verdict"))
            if verdict in {"PASS", "QUALIFIED_PASS"} and prereq_verdict not in {
                "PASS", "QUALIFIED_PASS",
            }:
                issues.append(
                    issue(
                        "ERROR",
                        "V0",
                        "strong claim depends on non-passing prerequisite %s=%s"
                        % (clean(prereq.get("claim_id")), prereq_verdict),
                        claim_id,
                    )
                )

        declared_ceiling = upper(claim.get("confidence_ceiling"))
        confidence = upper(claim.get("confidence"))
        computed_ceiling = weakest_confidence_ceiling(
            claim, evidence_by_id, claims_by_id, defeaters_by_claim
        )
        if confidence_value(confidence) > confidence_value(declared_ceiling):
            issues.append(
                issue(
                    "ERROR",
                    "TAINT_CONFIDENCE",
                    "claim confidence %s exceeds declared ceiling %s"
                    % (confidence, declared_ceiling),
                    claim_id,
                )
            )
        if confidence_value(declared_ceiling) > confidence_value(computed_ceiling) >= 0:
            issues.append(
                issue(
                    "ERROR",
                    "TAINT_CONFIDENCE",
                    "declared ceiling %s exceeds weakest-link ceiling %s"
                    % (declared_ceiling, computed_ceiling),
                    claim_id,
                )
            )

        open_critical = [
            row
            for row in defeaters_by_claim.get(claim_id, [])
            if upper(row.get("status")) in {"OPEN", "UNKNOWN"}
            and upper(row.get("impact_on_claim")) in CRITICAL_DEFEATER_IMPACTS
        ]
        if open_critical and verdict in {"PASS", "FAIL", "QUALIFIED_PASS"}:
            issues.append(
                issue(
                    "ERROR",
                    "V16",
                    "critical OPEN/UNKNOWN defeater requires UNCERTAIN/PARTIAL verdict",
                    claim_id,
                )
            )

        # V1-V5: deadline and distance-debt eligibility/taint.
        if base == "C4":
            qualified = has_qualified_deadline(claim, support, claims_by_id)
            observed_reaction = has_observed_reaction(support)
            comparisons = qualified_deadline_comparisons(
                claim, support, requirement_rows
            )
            numeric_verdict_supported = (
                all(reaction > high for reaction, _low, high in comparisons)
                if verdict == "PASS"
                else all(reaction <= low for reaction, low, _high in comparisons)
            )
            if verdict in {"PASS", "FAIL"} and not (
                qualified and observed_reaction and comparisons and numeric_verdict_supported
            ):
                issues.append(
                    issue(
                        "ERROR",
                        "V1",
                        "C4 PASS/FAIL requires a same-scope qualified requirement and a numerically consistent observed physical T_R comparison",
                        claim_id,
                    )
                )
            if "RETROSPECTIVE_RECONSTRUCTION" in support_classes and not qualified:
                if verdict not in {"RETROSPECTIVE_ONLY", "NOT_TESTABLE"}:
                    issues.append(
                        issue(
                            "ERROR",
                            "V2",
                            "retrospective-only deadline cannot establish C4",
                            claim_id,
                        )
                    )
            if "UNVALIDATED_MODEL" in support_classes and not qualified:
                if verdict not in {"MODEL_SUPPORTED_ONLY", "NOT_TESTABLE"}:
                    issues.append(
                        issue(
                            "ERROR",
                            "V3",
                            "unvalidated-model deadline caps C4 at MODEL_SUPPORTED_ONLY",
                            claim_id,
                        )
                    )
            if verdict in {"PASS", "FAIL"} and support_classes == {"DIRECT_OBSERVED"}:
                issues.append(
                    issue("ERROR", "V14", "observed outcome alone cannot establish C4", claim_id)
                )

        if base == "C5":
            if verdict == "PASS":
                prereq_c4_pass = any(
                    base_claim_id(clean(row.get("claim_id"))) == "C4"
                    and upper(row.get("verdict")) == "PASS"
                    for row in prerequisite_rows(claim, claims_by_id)
                )
                compatible_clock = any(
                    base_claim_id(clean(row.get("claim_id"))) == "P_CLOCK"
                    and upper(row.get("verdict")) == "PASS"
                    for row in prerequisite_rows(claim, claims_by_id)
                )
                debt_rows = [
                    row for row in support
                    if upper(row.get("evidence_class")) == "REQUIREMENT_CONSTRAINED_DERIVED"
                    and (
                        "DEBT" in upper(row.get("metric"))
                        or upper(row.get("semantic_role")) == "DEADLINE_EXCESS_DISTANCE_DEBT"
                    )
                ]
                debt_tainted = any(
                    {"MODEL_TAINT", "RETRO_TAINT"}
                    & set(split_ids(row.get("taint_tags")))
                    for row in debt_rows
                )
                if not (
                    prereq_c4_pass
                    and compatible_clock
                    and debt_rows
                    and not debt_tainted
                    and has_observed_velocity_path(support)
                ):
                    issues.append(
                        issue(
                            "ERROR",
                            "V4",
                            "C5 PASS requires C4 PASS, compatible P_CLOCK, observed velocity path, and requirement-constrained debt",
                            claim_id,
                        )
                    )
            model_debt = any(
                upper(row.get("evidence_class")) in {"UNVALIDATED_MODEL", "VALIDATED_MODEL"}
                and (
                    "DEBT" in upper(row.get("metric"))
                    or upper(row.get("semantic_role")) == "DEADLINE_EXCESS_DISTANCE_DEBT"
                )
                for row in support
            )
            if model_debt and verdict == "PASS":
                issues.append(
                    issue(
                        "ERROR",
                        "V5",
                        "model-derived debt retains MODEL taint and cannot be direct C5 PASS",
                        claim_id,
                    )
                )
            if "RETROSPECTIVE_RECONSTRUCTION" in support_classes and verdict == "PASS":
                issues.append(
                    issue(
                        "ERROR",
                        "V5",
                        "retrospective debt cannot be primary C5 PASS",
                        claim_id,
                    )
                )

        if base == "C2" and verdict == "PASS":
            qualified_reference = any(
                upper(row.get("reference_type"))
                not in {"", "NONE", "MISSING", "UNKNOWN", "SAME_RUN_POST_OUTCOME"}
                and upper(row.get("distribution_scope")) != "SINGLE_MAX"
                for row in support
            )
            if not qualified_reference:
                issues.append(
                    issue(
                        "ERROR", "V12",
                        "C2 PASS requires an explicit admissible reference and non-single-max distribution",
                        claim_id,
                    )
                )

        # V7/V8 and target/clock taint on C3.
        if base == "C3":
            grade = upper(claim.get("causal_lineage_grade")) or "UNKNOWN"
            if grade in {"C", "D", "UNKNOWN"} and verdict == "PASS":
                issues.append(
                    issue(
                        "ERROR",
                        "V7",
                        "causal lineage grade %s cannot support C3 PASS" % grade,
                        claim_id,
                    )
                )
            clock_unverified = "CLOCK_UNVERIFIED" in support_classes or any(
                base_claim_id(clean(row.get("claim_id"))) == "P_CLOCK"
                and upper(row.get("verdict")) != "PASS"
                for row in prerequisite_rows(claim, claims_by_id)
            )
            if clock_unverified and confidence == "HIGH":
                issues.append(
                    issue(
                        "ERROR",
                        "V8",
                        "unverified/partial clocks forbid HIGH-confidence C3 timing",
                        claim_id,
                    )
                )

        if base == "P_FUNC" and verdict == "QUALIFIED_PASS":
            scope = claim_scope(claim)
            applicable_functional_rows = [
                row for row in functional_rows
                if scope.lower() in {"all", "all_runs", "group"}
                or clean(row.get("run_id")) == scope
            ]
            audit_verdicts = {
                upper(row.get("p_func_verdict")) for row in applicable_functional_rows
                if clean(row.get("p_func_verdict"))
            }
            if not audit_verdicts or audit_verdicts - {"QUALIFIED_PASS"}:
                issues.append(
                    issue(
                        "ERROR", "V6",
                        "P_FUNC QUALIFIED_PASS conflicts with incomplete/absent functional audit",
                        claim_id,
                    )
                )

        local_clock_only = bool(support) and all(
            "FAULT_SIGNATURE" in upper(row.get("metric"))
            or upper(row.get("semantic_role")) == "LOCAL_FAULT_CLOCK"
            for row in support
        )
        if base == "P_CLOCK" and verdict == "PASS" and not local_clock_only:
            clock_confidence = {upper(row.get("confidence")) for row in clock_rows}
            phase_states = {upper(row.get("phase_effect_verdict")) for row in clock_rows}
            if not clock_rows or clock_confidence - {"HIGH"} or phase_states & {"NOT_TESTABLE", "UNKNOWN", ""}:
                issues.append(
                    issue(
                        "ERROR", "V8",
                        "cross-host P_CLOCK PASS conflicts with incomplete clock/phase audit",
                        claim_id,
                    )
                )

        # V13: a deadline miss cannot manufacture a physical outcome.
        if base == "C6" and verdict == "PASS":
            if not has_direct_physical_outcome(support):
                issues.append(
                    issue(
                        "ERROR",
                        "V13",
                        "C6 PASS requires DIRECT_OBSERVED evidence with semantic_role=PHYSICAL_OUTCOME and a canonical physical metric",
                        claim_id,
                    )
                )

        # Evidence-specific language in claim ledger.
        forbidden = split_ids(claim.get("forbidden_language"))
        for phrase in forbidden:
            if phrase and phrase.lower() in visible_report.lower():
                issues.append(
                    issue(
                        "ERROR",
                        "LANGUAGE",
                        "report uses phrase forbidden by claim: %s" % phrase,
                        claim_id,
                    )
                )

    # V9/V10: pre-hazard state divergence.
    pre_hazard_by_run: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in pre_hazard_rows:
        pre_hazard_by_run[clean(row.get("run_id"))].append(row)
    for fault in fault_signatures:
        run_id = clean(fault.get("run_id"))
        onset = safe_float(fault.get("fault_onset_wall"))
        t1 = safe_float(fault.get("t1_wall"))
        relative = safe_float(fault.get("trigger_relative_t1_s"))
        if onset is None and t1 is not None and relative is not None:
            onset = t1 + relative
        if onset is None or t1 is None or onset >= t1:
            continue
        rows = pre_hazard_by_run.get(run_id, [])
        if not rows:
            issues.append(
                issue(
                    "ERROR",
                    "V9",
                    "fault onset precedes t1 but pre_hazard_state_audit has no run row",
                    claim_id="C7.%s" % run_id,
                )
            )
            continue
        required_variables = {"D1", "V1"}
        classified = {
            upper(row.get("state_variable"))
            for row in rows
            if upper(row.get("causal_role"))
            in {
                "PRE_EXISTING_CONFOUNDER",
                "POSSIBLE_MEDIATOR",
                "POST_TREATMENT_STATE",
            }
            and upper(row.get("availability")) not in {"MISSING", "UNAVAILABLE"}
        }
        if not required_variables.issubset(classified):
            issues.append(
                issue(
                    "ERROR",
                    "V10",
                    "pre-t1 fault requires D1 and v1 causal-role classification",
                    claim_id="C7.%s" % run_id,
                )
            )

    # V11: one nonzero level cannot support stable gain/amplification language.
    nonzero_levels = {
        round(value, 9)
        for value in (safe_float(row.get("requested_magnitude")) for row in fault_signatures)
        if value is not None and value > 0
    }
    if len(nonzero_levels) == 1:
        for pattern, label in GLOBAL_FORBIDDEN_PATTERNS:
            if label in V11_ONLY_LABELS and has_unnegated_match(pattern, visible_report):
                issues.append(
                    issue(
                        "ERROR",
                        "V11",
                        "single nonzero delay level forbids %s" % label,
                    )
                )

    # V12: a single max with no reference cannot strong-pass group C2.
    for evidence_row in evidence:
        metric = upper(evidence_row.get("metric"))
        if "GAP" not in metric or "MAX" not in metric:
            continue
        reference = upper(evidence_row.get("reference_type"))
        distribution = upper(evidence_row.get("distribution_scope"))
        if reference not in {"", "NONE", "MISSING"} and distribution != "SINGLE_MAX":
            continue
        for claim_id in split_ids(evidence_row.get("supports_claim_ids")):
            claim = claims_by_id.get(claim_id)
            if not claim or base_claim_id(claim_id) != "C2":
                continue
            scope = upper(claim.get("run_id_or_group"))
            if upper(claim.get("verdict")) == "PASS" and (
                "GROUP" in scope or "ALL" in scope
            ):
                issues.append(
                    issue(
                        "ERROR",
                        "V12",
                        "single max gap without reference/distribution cannot establish group C2",
                        claim_id,
                        clean(evidence_row.get("evidence_id")),
                    )
                )

    # V15: collision right-censoring.
    for row in observed_rows:
        if not boolish(row.get("collision_event_data_observed")):
            continue
        full_brake_fields = [
            key for key in row
            if (
                ("D_BRAKE" in upper(key) or "BRAKING_DISTANCE" in upper(key))
                and "OBSERVED" in upper(key)
                and not any(
                    tag in upper(key)
                    for tag in {"TRUNCATED", "NEAR_STOP", "STRICT_STOP", "DIAGNOSTIC", "COMPARATOR"}
                )
            )
        ]
        populated = [
            key for key in full_brake_fields
            if clean(row.get(key)).lower() not in {"", "na", "nan", "none", "null"}
        ]
        if populated:
            issues.append(
                issue(
                    "ERROR",
                    "V15",
                    "collision run %s has full observed braking distance fields: %s"
                    % (clean(row.get("run_id")), ", ".join(populated)),
                )
            )

    # V6 and global language guards.
    normalized_report = visible_report.lower()
    p_func_rows = [
        row for row in claims
        if base_claim_id(clean(row.get("claim_id"))) == "P_FUNC"
    ]
    c4_rows = [
        row for row in claims
        if base_claim_id(clean(row.get("claim_id"))) == "C4"
    ]
    p_func_qualified = bool(p_func_rows) and all(
        base_claim_id(clean(row.get("claim_id"))) == "P_FUNC"
        and upper(row.get("verdict")) == "QUALIFIED_PASS"
        for row in p_func_rows
    )
    c4_qualified = bool(c4_rows) and all(
        base_claim_id(clean(row.get("claim_id"))) == "C4"
        and upper(row.get("verdict")) == "PASS"
        for row in c4_rows
    )
    if (
        "functionally correct, temporally wrong" in normalized_report
        or "功能正确但时间错误" in visible_report
    ) and not (p_func_qualified and c4_qualified):
        issues.append(
            issue(
                "ERROR",
                "V6",
                "functional-correctness language requires P_FUNC QUALIFIED_PASS and C4 PASS",
            )
        )

    for pattern, label in GLOBAL_FORBIDDEN_PATTERNS:
        if label in V11_ONLY_LABELS:
            continue
        if has_unnegated_match(pattern, visible_report):
            issues.append(issue("ERROR", "LANGUAGE", "forbidden inference language: %s" % label))

    # Scope-specific attribution ceiling and default defeater completeness.
    for c7 in [row for row in claims if base_claim_id(clean(row.get("claim_id"))) == "C7"]:
        c7_id = clean(c7.get("claim_id"))
        prereqs = {
            base_claim_id(clean(row.get("claim_id"))): row
            for row in prerequisite_rows(c7, claims_by_id)
        }
        c4_verdict = upper(prereqs.get("C4", {}).get("verdict"))
        c5_verdict = upper(prereqs.get("C5", {}).get("verdict"))
        c6_verdict = upper(prereqs.get("C6", {}).get("verdict"))
        p_func_verdict = upper(prereqs.get("P_FUNC", {}).get("verdict"))
        c7_defeaters = defeaters_by_claim.get(c7_id, [])
        critical_open = any(
            upper(row.get("status")) in {"OPEN", "UNKNOWN"}
            and upper(row.get("impact_on_claim")) in CRITICAL_DEFEATER_IMPACTS
            for row in c7_defeaters
        )
        _label, computed_level = allowed_attribution_label(
            p_func_verdict, c4_verdict, c5_verdict, c6_verdict, critical_open
        )
        verdict_level_caps = {
            "NOT_TESTABLE": 0,
            "FAIL": 0,
            "UNCERTAIN": 2,
            "RETROSPECTIVE_ONLY": 2,
            "MODEL_SUPPORTED_ONLY": 2,
            "PARTIAL_PASS": 2,
            "PARTIAL": 2,
        }
        computed_level = min(
            computed_level,
            verdict_level_caps.get(upper(c7.get("verdict")), computed_level),
        )
        declared_level = safe_float(c7.get("maximum_claim_level"))
        if declared_level is None or declared_level > computed_level:
            issues.append(
                issue(
                    "ERROR", "WEAKEST_LINK",
                    "C7 declared level exceeds scope-specific computed ceiling %s" % computed_level,
                    c7_id,
                )
            )
        declared_defeater_ids = set(split_ids(c7.get("defeater_ids")))
        expected_ids = {
            "%s.%s" % (prefix, c7_id) for prefix in C7_DEFAULT_DEFEATER_TYPES
        }
        ledger_ids = {clean(row.get("defeater_id")) for row in c7_defeaters}
        missing_defaults = sorted(expected_ids - ledger_ids)
        if missing_defaults:
            issues.append(
                issue(
                    "ERROR", "V16",
                    "C7 lacks default defeaters: %s" % ", ".join(missing_defaults),
                    c7_id,
                )
            )
        for prefix, expected_type in C7_DEFAULT_DEFEATER_TYPES.items():
            expected_id = "%s.%s" % (prefix, c7_id)
            if expected_id not in ledger_ids:
                continue
            row = defeaters_by_id[expected_id]
            if expected_id not in declared_defeater_ids:
                issues.append(
                    issue(
                        "ERROR", "V16", "C7 default defeater is not linked reciprocally",
                        c7_id,
                    )
                )
            if upper(row.get("type")) != expected_type:
                issues.append(
                    issue(
                        "ERROR", "V16", "C7 default defeater has wrong type", c7_id,
                    )
                )
            if not clean(row.get("description")) or not clean(row.get("resolution")):
                issues.append(
                    issue(
                        "ERROR", "V16", "C7 default defeater lacks description/resolution",
                        c7_id,
                    )
                )
            if upper(row.get("status")) in {"RESOLVED", "REFUTED", "NOT_APPLICABLE", "BOUNDED"} and not split_ids(row.get("evidence_ids")):
                issues.append(
                    issue(
                        "ERROR", "V16",
                        "closed/bounded C7 default defeater requires supporting evidence_ids",
                        c7_id,
                    )
                )
        if computed_level < 5 and re.search(
            r"(delay|timing|延迟|时间).{0,30}(caused|led to|导致|造成).{0,20}(collision|碰撞)",
            visible_report, flags=re.IGNORECASE | re.DOTALL,
        ):
            issues.append(
                issue(
                    "ERROR", "LANGUAGE",
                    "timing-caused-collision language exceeds the C7 ceiling", c7_id,
                )
            )
        if computed_level < 4 and has_unnegated_match(
            r"(?:timing|delay|时序|时间|延迟).{0,80}(?:material(?:ly)? contribut|重要贡献因素|主要贡献因素)",
            visible_report,
        ):
            issues.append(
                issue(
                    "ERROR", "LANGUAGE",
                    "material-contribution language exceeds the C7 ceiling", c7_id,
                )
            )

    if visible_report:
        title_index = normalized_report.find("six-layer inference status matrix")
        if title_index < 0:
            issues.append(
                issue(
                    "ERROR", "REPORT_GATE",
                    "report must begin analysis with a Six-Layer Inference Status Matrix",
                )
            )
        else:
            first_layer_heading = re.search(r"^#{1,4}\s+L[1-6]\b", visible_report, re.MULTILINE)
            if first_layer_heading and title_index > first_layer_heading.start():
                issues.append(
                    issue("ERROR", "REPORT_GATE", "status matrix appears after layer analysis")
                )
            matrix_text = first_markdown_table_after(
                visible_report, "six-layer inference status matrix"
            )
            if not matrix_text:
                issues.append(issue("ERROR", "REPORT_GATE", "status matrix table is missing"))
            for claim in claims:
                base = base_claim_id(clean(claim.get("claim_id")))
                if base not in EXPECTED_LAYERS:
                    continue
                label = "Attribution" if base == "C7" else EXPECTED_LAYERS[base]
                verdict = upper(claim.get("verdict"))
                row_pattern = r"\|\s*%s(?:\s*/\s*%s)?\s*\|\s*%s\b" % (
                    re.escape(label), base, re.escape(verdict)
                )
                if not re.search(row_pattern, matrix_text, flags=re.IGNORECASE):
                    issues.append(
                        issue(
                            "ERROR", "REPORT_GATE",
                            "status matrix lacks ledger-consistent row %s=%s" % (base, verdict),
                            clean(claim.get("claim_id")),
                        )
                    )

    return issues


def allowed_attribution_label(
    p_func: str,
    c4: str,
    c5: str,
    c6: str,
    critical_defeater_open: bool = False,
) -> Tuple[str, int]:
    """Return a conservative attribution label and claim-strength ceiling.

    This helper is used by synthetic tests and migration tooling.  It is not a
    substitute for the full ledger validator.
    """

    p_func_u, c4_u, c5_u, c6_u = map(upper, (p_func, c4, c5, c6))
    if c6_u not in {"PASS", "PARTIAL_PASS"}:
        return "NO_PHYSICAL_DEGRADATION_CLAIM", 2
    if p_func_u == "FAIL":
        return "FUNCTIONAL_OR_MULTI_FACTOR_FAILURE", 2
    if c4_u == "FAIL":
        return "NO_TEMPORAL_FAILURE_ESTABLISHED", 2
    if c4_u in {"NOT_TESTABLE", "RETROSPECTIVE_ONLY", "MODEL_SUPPORTED_ONLY"}:
        return "TEMPORAL_ASSOCIATION_WITH_UNQUALIFIED_MECHANISM", 2
    if c5_u in {"NOT_TESTABLE", "RETROSPECTIVE_ONLY", "MODEL_SUPPORTED_ONLY"}:
        return "TEMPORAL_FAILURE_WITH_MODEL_OR_RETRO_PHYSICAL_SUPPORT", 3
    if critical_defeater_open or p_func_u not in {"QUALIFIED_PASS", "PASS"}:
        return "MULTI_FACTOR_TEMPORAL_CONTRIBUTION", 4
    return "TIMING_DOMINATED_FAILURE_CANDIDATE", 5


def temporal_correctness_classification(
    reaction_ms: float, tau_req_low_ms: float, tau_req_high_ms: float
) -> Tuple[str, str]:
    """Classify C4 without conflating system correctness with claim truth.

    The second element is the verdict on the C4 *failure proposition*: ``FAIL``
    therefore means the run is clearly within the qualified requirement, not
    that the system failed.  This distinction prevents the overloaded word
    "PASS" from reversing the claim's meaning in reports.
    """

    if tau_req_low_ms > tau_req_high_ms:
        raise ValueError("tau_req_low_ms must be <= tau_req_high_ms")
    if reaction_ms <= tau_req_low_ms:
        return "CLEARLY_WITHIN_REQUIREMENT", "FAIL"
    if reaction_ms > tau_req_high_ms:
        return "CLEARLY_MISSED", "PASS"
    return "REQUIREMENT_INTERVAL_OVERLAP", "UNCERTAIN"


def claim_audit_markdown(
    claims: Sequence[Mapping[str, Any]],
    evidence: Sequence[Mapping[str, Any]],
    defeaters: Sequence[Mapping[str, Any]],
) -> str:
    evidence_by_id = evidence_index(evidence)
    defeaters_by_claim: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in defeaters:
        defeaters_by_claim[clean(row.get("claim_id"))].append(row)
    blocks = ["# TCPS-PA v2 claim audit", ""]
    for claim in claims:
        claim_id = clean(claim.get("claim_id"))
        support = [
            "%s (%s)" % (evidence_id, upper(evidence_by_id[evidence_id].get("evidence_class")))
            for evidence_id in split_ids(claim.get("supporting_evidence_ids"))
            if evidence_id in evidence_by_id
        ]
        challenge = split_ids(claim.get("challenging_evidence_ids"))
        defeater_lines = [
            "%s=%s: %s"
            % (
                clean(row.get("defeater_id")),
                upper(row.get("status")),
                clean(row.get("impact_on_claim")),
            )
            for row in defeaters_by_claim.get(claim_id, [])
        ]
        blocks.extend(
            [
                "## CLAIM: %s" % claim_id,
                "",
                "**PROPOSITION:** %s" % clean(claim.get("proposition")),
                "",
                "**PREREQUISITES:** %s"
                % (", ".join(split_ids(claim.get("prerequisite_claim_ids"))) or "None"),
                "",
                "**SUPPORT:** %s" % (", ".join(support) or "None"),
                "",
                "**CHALLENGES:** %s" % (", ".join(challenge) or "None"),
                "",
                "**DEFEATERS:** %s" % ("; ".join(defeater_lines) or "None"),
                "",
                "**VERDICT:** %s" % upper(claim.get("verdict")),
                "",
                "**CONFIDENCE / CEILING:** %s / %s"
                % (upper(claim.get("confidence")), upper(claim.get("confidence_ceiling"))),
                "",
                "**WHY NOT STRONGER:** %s" % clean(claim.get("residual_uncertainty")),
                "",
                "**ALLOWED LANGUAGE:** %s" % clean(claim.get("allowed_language")),
                "",
                "**FORBIDDEN LANGUAGE:** %s" % clean(claim.get("forbidden_language")),
                "",
            ]
        )
    return "\n".join(blocks).rstrip() + "\n"
