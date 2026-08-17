#!/usr/bin/env python3
"""Construct prospective RSS-like longitudinal physical response deadlines."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence


REQUIRED_PARAMETERS = (
    "d_clear_m", "v_ego_mps", "v_front_mps", "d_safe_m",
    "a_ego_response_max_mps2", "b_ego_min_mps2", "b_front_max_mps2",
)

OUTPUT_FIELDS = [
    "construction_id", "requirement_id", "run_id_or_group", "method", "method_version",
    "state_time", "state_time_basis", "state_available_by_t1", "d_clear_m",
    "input_cutoff_time", "latest_input_time", "input_provenance_json",
    "parameter_selection_time", "parameter_selection_locked_by_t1",
    "current_run_post_t1_data_used", "current_run_outcome_used",
    "v_ego_mps", "v_front_mps", "d_safe_m", "a_ego_response_max_mps2",
    "b_ego_min_mps2", "b_front_max_mps2", "parameter_bounds_json",
    "uncertainty_method", "uncertainty_sample_count", "braking_envelope_id",
    "braking_envelope_provenance", "braking_envelope_status",
    "validation_dataset_independent", "validation_scope", "target_motion_assumption",
    "calibration_run_ids", "evaluation_run_ids",
    "road_condition_assumption", "tau_req_low_ms", "tau_req_center_ms",
    "tau_req_high_ms", "parameter_bounds_complete", "construction_status",
    "qualification", "source_evidence_ids", "notes",
]


def clean(value: object) -> str:
    return str("" if value is None else value).strip()


def truthy(value: object) -> bool:
    return clean(value).lower() in {"true", "1", "yes", "y"}


def number(value: object) -> float:
    result = float(clean(value))
    if not math.isfinite(result):
        raise ValueError("non-finite parameter")
    return result


def solve_tau_seconds(params: Mapping[str, float]) -> tuple[float, str]:
    d = params["d_clear_m"]
    ve = params["v_ego_mps"]
    vf = params["v_front_mps"]
    ds = params["d_safe_m"]
    ar = params["a_ego_response_max_mps2"]
    be = params["b_ego_min_mps2"]
    bf = params["b_front_max_mps2"]
    if d < 0 or ve < 0 or vf < 0 or ds < 0 or ar < 0 or be <= 0 or bf <= 0:
        raise ValueError("invalid sign or non-positive braking magnitude")
    a = 0.5 * ar + ar * ar / (2.0 * be)
    b = ve + ve * ar / be
    c = ve * ve / (2.0 * be) - vf * vf / (2.0 * bf) + ds - d
    if c > 0:
        return 0.0, "ALREADY_UNSAFE_AT_STATE_EPOCH"
    if abs(a) < 1e-15:
        if b <= 0:
            return math.inf, "UNBOUNDED_WITH_ZERO_APPROACH_SPEED"
        return max(0.0, -c / b), "SOLVED"
    disc = b * b - 4.0 * a * c
    if disc < 0:
        raise ValueError("negative discriminant")
    return max(0.0, (-b + math.sqrt(disc)) / (2.0 * a)), "SOLVED"


def parse_bounds(row: Mapping[str, str]) -> tuple[Dict[str, tuple[float, float]], bool]:
    raw = clean(row.get("parameter_bounds_json"))
    if not raw:
        return {}, False
    data = json.loads(raw)
    bounds: Dict[str, tuple[float, float]] = {}
    for name in REQUIRED_PARAMETERS:
        values = data.get(name)
        if not isinstance(values, list) or len(values) != 2:
            return {}, False
        low, high = number(values[0]), number(values[1])
        if low > high:
            return {}, False
        bounds[name] = (low, high)
    return bounds, True


def parse_provenance(row: Mapping[str, str]) -> bool:
    raw = clean(row.get("input_provenance_json"))
    if not raw:
        return False
    data = json.loads(raw)
    return isinstance(data, dict) and all(clean(data.get(name)) for name in REQUIRED_PARAMETERS)


def id_set(value: object) -> set[str]:
    return {
        item.strip() for item in clean(value).replace(",", "|").split("|")
        if item.strip()
    }


def construct_row(row: Mapping[str, str]) -> Dict[str, object]:
    output: Dict[str, object] = {field: row.get(field, "") for field in OUTPUT_FIELDS}
    output["method"] = clean(row.get("method")) or "RSS_LIKE_LONGITUDINAL"
    output["method_version"] = clean(row.get("method_version")) or "TCPS-PA-2.1"
    notes: List[str] = []
    try:
        center_params = {name: number(row.get(name)) for name in REQUIRED_PARAMETERS}
        center, center_state = solve_tau_seconds(center_params)
        bounds, complete = parse_bounds(row)
        provenance_complete = parse_provenance(row)
        cutoff = number(row.get("input_cutoff_time"))
        latest_input = number(row.get("latest_input_time"))
        calibration_ids = id_set(row.get("calibration_run_ids"))
        evaluation_ids = id_set(row.get("evaluation_run_ids"))
        datasets_disjoint = bool(calibration_ids and evaluation_ids) and not (
            calibration_ids & evaluation_ids
        )
        output["parameter_bounds_complete"] = str(complete).upper()
        values: List[float] = []
        if complete:
            for corner in itertools.product(*[(bounds[name][0], bounds[name][1]) for name in REQUIRED_PARAMETERS]):
                params = dict(zip(REQUIRED_PARAMETERS, corner))
                tau, _state = solve_tau_seconds(params)
                if math.isfinite(tau):
                    values.append(tau)
        if not math.isfinite(center) or not values:
            raise ValueError("deadline is unbounded or uncertainty bounds yield no finite result")
        output["tau_req_low_ms"] = min(values) * 1000.0
        output["tau_req_center_ms"] = center * 1000.0
        output["tau_req_high_ms"] = max(values) * 1000.0
        output["uncertainty_method"] = clean(row.get("uncertainty_method")) or "EXHAUSTIVE_PARAMETER_BOX_CORNERS"
        output["uncertainty_sample_count"] = len(values)
        qualified = all(
            [
                truthy(row.get("state_available_by_t1")),
                latest_input <= cutoff,
                provenance_complete,
                truthy(row.get("parameter_selection_locked_by_t1")),
                not truthy(row.get("current_run_post_t1_data_used")),
                not truthy(row.get("current_run_outcome_used")),
                truthy(row.get("validation_dataset_independent")),
                datasets_disjoint,
                complete,
                clean(row.get("braking_envelope_status")).upper() == "QUALIFIED",
                bool(clean(row.get("braking_envelope_id"))),
                bool(clean(row.get("braking_envelope_provenance"))),
                bool(clean(row.get("validation_scope"))),
                bool(clean(row.get("target_motion_assumption"))),
                bool(clean(row.get("road_condition_assumption"))),
            ]
        )
        output["construction_status"] = center_state
        output["qualification"] = "QUALIFIED_DYNAMIC_PHYSICAL" if qualified else "NOT_QUALIFIED_PRIMARY"
        if not qualified:
            notes.append("Construction is numerically available but prospective provenance, dataset independence, or domain qualification is incomplete.")
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        output["tau_req_low_ms"] = ""
        output["tau_req_center_ms"] = ""
        output["tau_req_high_ms"] = ""
        output["construction_status"] = "CONSTRUCTION_INVALID"
        output["qualification"] = "NOT_QUALIFIED_PRIMARY"
        output["parameter_bounds_complete"] = "FALSE"
        notes.append(str(exc))
    output["notes"] = "; ".join(filter(None, [clean(row.get("notes")), *notes]))
    return output


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()
    rows = [construct_row(row) for row in read_csv(args.input_csv)]
    write_csv(args.output_csv, rows)
    invalid = sum(row["qualification"] != "QUALIFIED_DYNAMIC_PHYSICAL" for row in rows)
    print(json.dumps({"rows": len(rows), "not_qualified": invalid, "output": str(args.output_csv)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
