#!/usr/bin/env python3
"""Recompute TCPS-PA L5 integrals from observed wall-clock velocity samples."""

from __future__ import annotations

import argparse
import bisect
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple


VELOCITY_FIELDS = [
    "run_id", "sample_index", "t_wall_s", "speed_mps", "clock_domain",
    "source_file", "source_locator", "availability", "quality_flags",
]

OUTPUT_FIELDS = [
    "run_id", "requirement_id", "t1_wall_s", "t_deadline_wall_s", "te_wall_s",
    "D_response_recomputed_m", "D_debt_recomputed_m", "D_response_reported_m",
    "D_debt_reported_m", "D1_observed_m", "D_brake_observed_m",
    "M0_recomputed_m", "M0_reported_m", "endpoint_coverage", "max_abs_error_m",
    "tolerance_m", "recomputation_status", "notes",
]

LOCALIZATION_PATTERN = re.compile(
    r"header_time=([-+0-9.eE]+).*?ego_vx=([-+0-9.eE]+)\s+ego_vy=([-+0-9.eE]+)\s+ego_vz=([-+0-9.eE]+)"
)


def clean(value: object) -> str:
    return str("" if value is None else value).strip()


def number(value: object) -> float | None:
    try:
        result = float(clean(value))
    except ValueError:
        return None
    return result if math.isfinite(result) else None


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


def extract_velocity(observed: Sequence[Mapping[str, str]]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for item in observed:
        run_id = clean(item.get("run_id"))
        source = Path(clean(item.get("source_localization_file")))
        if not run_id or not source.exists():
            continue
        sample_index = 0
        for line_number, line in enumerate(source.open("r", encoding="utf-8", errors="replace"), 1):
            match = LOCALIZATION_PATTERN.search(line)
            if not match:
                continue
            timestamp = float(match.group(1))
            speed = math.sqrt(sum(float(match.group(index)) ** 2 for index in (2, 3, 4)))
            rows.append(
                {
                    "run_id": run_id, "sample_index": sample_index,
                    "t_wall_s": timestamp, "speed_mps": speed,
                    "clock_domain": "wall_epoch_s", "source_file": str(source),
                    "source_locator": "line %d" % line_number, "availability": "AVAILABLE",
                    "quality_flags": "",
                }
            )
            sample_index += 1
    return rows


def valid_series(rows: Sequence[Mapping[str, str]]) -> Tuple[List[float], List[float], str]:
    pairs: List[Tuple[float, float]] = []
    for row in rows:
        if clean(row.get("availability")).upper() not in {"AVAILABLE", "PRESENT"}:
            continue
        t, v = number(row.get("t_wall_s")), number(row.get("speed_mps"))
        if t is not None and v is not None and v >= 0:
            pairs.append((t, v))
    pairs.sort()
    if len(pairs) < 2 or any(b[0] <= a[0] for a, b in zip(pairs, pairs[1:])):
        return [], [], "INVALID_OR_NONMONOTONIC_TRAJECTORY"
    return [p[0] for p in pairs], [p[1] for p in pairs], "OK"


def interpolate(times: Sequence[float], speeds: Sequence[float], endpoint: float) -> float:
    index = bisect.bisect_left(times, endpoint)
    if index < len(times) and times[index] == endpoint:
        return speeds[index]
    if index == 0 or index == len(times):
        raise ValueError("endpoint outside observed trajectory")
    t0, t1 = times[index - 1], times[index]
    v0, v1 = speeds[index - 1], speeds[index]
    return v0 + (v1 - v0) * (endpoint - t0) / (t1 - t0)


def integrate(times: Sequence[float], speeds: Sequence[float], start: float, end: float) -> float:
    if end <= start:
        return 0.0
    points = [(start, interpolate(times, speeds, start))]
    points.extend((t, v) for t, v in zip(times, speeds) if start < t < end)
    points.append((end, interpolate(times, speeds, end)))
    return sum((b[0] - a[0]) * (a[1] + b[1]) / 2.0 for a, b in zip(points, points[1:]))


def qualified_requirements(requirements: Sequence[Mapping[str, str]]) -> Dict[str, Mapping[str, str]]:
    result: Dict[str, Mapping[str, str]] = {}
    for row in requirements:
        qualification = clean(row.get("p_deadline_qualification")).upper()
        if "QUALIFIED" not in qualification or "NOT_QUALIFIED" in qualification:
            continue
        run_id = clean(row.get("run_id_or_group"))
        if run_id and run_id.lower() not in {"all", "all_runs", "group"}:
            result[run_id] = row
    return result


def recompute_analysis(root: Path, tolerance_m: float = 0.02, write_output: bool = True) -> List[Dict[str, object]]:
    tables = root / "tables"
    observed = read_csv(tables / "run_level_observed.csv")
    velocity_path = tables / "velocity_trajectory_observed.csv"
    velocity_rows = read_csv(velocity_path)
    if not velocity_rows:
        extracted = extract_velocity(observed)
        if extracted:
            write_csv(velocity_path, VELOCITY_FIELDS, extracted)
            velocity_rows = [{key: clean(value) for key, value in row.items()} for row in extracted]
    by_run: Dict[str, List[Mapping[str, str]]] = defaultdict(list)
    for row in velocity_rows:
        by_run[clean(row.get("run_id"))].append(row)
    requirements = qualified_requirements(read_csv(tables / "requirement_registry.csv"))
    results: List[Dict[str, object]] = []
    for item in observed:
        run_id = clean(item.get("run_id"))
        t1, te = number(item.get("t1_wall_s")), number(item.get("t2_wall_s"))
        times, speeds, series_status = valid_series(by_run.get(run_id, []))
        row: Dict[str, object] = {field: "" for field in OUTPUT_FIELDS}
        row.update({"run_id": run_id, "t1_wall_s": t1 or "", "te_wall_s": te or "", "tolerance_m": tolerance_m})
        errors: List[float] = []
        notes: List[str] = []
        try:
            if t1 is None or te is None or series_status != "OK":
                raise ValueError(series_status if series_status != "OK" else "missing t1/te")
            d_response = integrate(times, speeds, t1, te)
            reported_response = number(item.get("D_response_wall_integral_data_observed_m") or item.get("D_delay_wall_integral_data_observed_m"))
            row["D_response_recomputed_m"] = d_response
            row["D_response_reported_m"] = reported_response if reported_response is not None else ""
            if reported_response is not None:
                errors.append(abs(d_response - reported_response))
            requirement = requirements.get(run_id)
            if requirement:
                tau_ms = number(requirement.get("tau_req_center_ms") or requirement.get("requirement_value"))
                if tau_ms is None:
                    raise ValueError("qualified requirement lacks center value")
                td = t1 + tau_ms / 1000.0
                d_debt = integrate(times, speeds, max(t1, td), te) if td < te else 0.0
                row["requirement_id"] = clean(requirement.get("requirement_id"))
                row["t_deadline_wall_s"] = td
                row["D_debt_recomputed_m"] = d_debt
                reported_debt = number(item.get("D_debt_requirement_constrained_derived_m"))
                row["D_debt_reported_m"] = reported_debt if reported_debt is not None else ""
                if reported_debt is not None:
                    errors.append(abs(d_debt - reported_debt))
            else:
                notes.append("No qualified per-run tau_req; primary D_debt is not recomputed.")
            d1 = number(item.get("D1_clear_data_observed_m"))
            d_brake = number(item.get("D_brake_data_observed_m"))
            m0_reported = number(item.get("M_collision_0m_data_observed_m"))
            row["D1_observed_m"] = d1 if d1 is not None else ""
            row["D_brake_observed_m"] = d_brake if d_brake is not None else ""
            row["M0_reported_m"] = m0_reported if m0_reported is not None else ""
            if d1 is not None and d_brake is not None:
                m0 = d1 - d_response - d_brake
                row["M0_recomputed_m"] = m0
                if m0_reported is not None:
                    errors.append(abs(m0 - m0_reported))
            row["endpoint_coverage"] = "COVERED_WITH_LINEAR_INTERPOLATION"
            row["max_abs_error_m"] = max(errors) if errors else 0.0
            if errors and max(errors) > tolerance_m:
                row["recomputation_status"] = "FAIL"
            elif requirement:
                row["recomputation_status"] = "PASS"
            else:
                row["recomputation_status"] = "RESPONSE_ONLY"
        except ValueError as exc:
            row["endpoint_coverage"] = "UNAVAILABLE"
            row["recomputation_status"] = "NOT_TESTABLE"
            notes.append(str(exc))
        row["notes"] = "; ".join(notes)
        results.append(row)
    if write_output:
        write_csv(tables / "l5_recomputation.csv", OUTPUT_FIELDS, results)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-dir", type=Path, required=True)
    parser.add_argument("--tolerance-m", type=float, default=0.02)
    args = parser.parse_args()
    rows = recompute_analysis(args.analysis_dir.resolve(), args.tolerance_m, True)
    print(json.dumps({"rows": len(rows), "status_counts": {status: sum(r["recomputation_status"] == status for r in rows) for status in sorted({str(r["recomputation_status"]) for r in rows})}}, ensure_ascii=False))
    return 0 if not any(row["recomputation_status"] == "FAIL" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
