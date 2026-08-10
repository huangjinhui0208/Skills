#!/usr/bin/env python3
"""Profile one parsed Apollo cyber record export for six-layer analysis.

The script is deliberately read-only and uses only the Python standard library.
It summarizes record coverage and timing diagnostics; it does not claim a
physical response endpoint, dynamic deadline, braking margin, or collision.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


EXPECTED_TABLES = {
    "00_meta/record_channels.csv",
    "00_meta/record_message_index.csv",
    "00_meta/record_topic_rate.csv",
    "01_localization_chassis/localization_pose.csv",
    "01_localization_chassis/localization_velocity_acc.csv",
    "01_localization_chassis/chassis.csv",
    "02_planning/planning_header.csv",
    "02_planning/planning_latency_stats.csv",
    "03_control/control_command.csv",
    "03_control/control_latency.csv",
    "03_control/control_planning_reuse.csv",
    "04_prediction_perception/perception_obstacles.csv",
    "04_prediction_perception/prediction_obstacles.csv",
    "07_diagnostics/module_timeline.csv",
    "07_diagnostics/planning_control_alignment.csv",
    "07_diagnostics/control_reuse_summary.csv",
    "07_diagnostics/sensor_to_control_reaction_age.csv",
    "07_diagnostics/abnormal_frames_summary.csv",
}

KEY_CHANNELS = {
    "/apollo/localization/pose",
    "/apollo/perception/obstacles",
    "/apollo/prediction",
    "/apollo/planning",
    "/apollo/control",
    "/apollo/canbus/chassis",
    "/apollo/guardian",
}


def safe_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def quantile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        return math.nan
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def numeric_summary(values: Iterable[float | None]) -> dict[str, Any]:
    data = sorted(value for value in values if value is not None and math.isfinite(value))
    if not data:
        return {"count": 0}
    return {
        "count": len(data),
        "min": data[0],
        "mean": statistics.fmean(data),
        "median": statistics.median(data),
        "p90": quantile(data, 0.90),
        "p95": quantile(data, 0.95),
        "p99": quantile(data, 0.99),
        "max": data[-1],
    }


def gap_summary(timestamps_s: Iterable[float | None]) -> dict[str, Any]:
    values = [value for value in timestamps_s if value is not None and math.isfinite(value)]
    if len(values) < 2:
        return {"timestamp_count": len(values), "gap_count": 0}
    diffs_ms = [(right - left) * 1000.0 for left, right in zip(values, values[1:])]
    positive = [value for value in diffs_ms if value > 0.0]
    summary = numeric_summary(positive)
    median = safe_float(summary.get("median"))
    result = {
        "timestamp_count": len(values),
        "gap_count": len(diffs_ms),
        "non_positive_gap_count": sum(value <= 0.0 for value in diffs_ms),
        "gap_ms": summary,
    }
    if median and median > 0:
        result.update(
            {
                "estimated_period_ms": median,
                "gap_gt_1_5x_median_count": sum(value > 1.5 * median for value in positive),
                "gap_gt_2x_median_count": sum(value > 2.0 * median for value in positive),
                "gap_gt_3x_median_count": sum(value > 3.0 * median for value in positive),
            }
        )
    return result


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def unique_numeric_summary(
    rows: list[dict[str, str]], key_column: str, value_column: str
) -> dict[str, Any]:
    values: dict[str, float] = {}
    for index, row in enumerate(rows):
        value = safe_float(row.get(value_column))
        if value is None:
            continue
        key = row.get(key_column) or f"row-{index}"
        values.setdefault(key, value)
    result = numeric_summary(values.values())
    result["deduplicated_by"] = key_column
    result["value_column"] = value_column
    return result


def channel_timing(record_dir: Path) -> dict[str, Any]:
    path = record_dir / "07_diagnostics/module_timeline.csv"
    rows = read_csv(path)
    by_channel: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        channel = row.get("channel", "")
        timestamp = safe_float(row.get("record_time_sec"))
        if channel in KEY_CHANNELS and timestamp is not None:
            by_channel[channel].append(timestamp)
    return {channel: gap_summary(values) for channel, values in sorted(by_channel.items())}


def topic_rates(record_dir: Path) -> dict[str, Any]:
    rows = read_csv(record_dir / "00_meta/record_topic_rate.csv")
    result: dict[str, Any] = {}
    for row in rows:
        channel = row.get("channel", "")
        if channel not in KEY_CHANNELS:
            continue
        result[channel] = {
            "message_count": int(safe_float(row.get("message_count")) or 0),
            "duration_sec": safe_float(row.get("duration_sec")),
            "rate_hz": safe_float(row.get("rate_hz")),
            "period_median_ms": safe_float(row.get("period_median_ms")),
            "period_published_max_ms": safe_float(row.get("period_max_ms")),
            "gap_gt_1_5x_median_count": int(
                safe_float(row.get("gap_gt_1_5x_median_count")) or 0
            ),
        }
    return result


def clock_offset_summary(record_dir: Path) -> dict[str, Any]:
    relative_paths = [
        "01_localization_chassis/localization_pose.csv",
        "02_planning/planning_header.csv",
        "03_control/control_command.csv",
        "04_prediction_perception/perception_obstacles.csv",
        "04_prediction_perception/prediction_obstacles.csv",
    ]
    result: dict[str, Any] = {}
    for relative in relative_paths:
        rows = read_csv(record_dir / relative)
        offsets: list[float] = []
        for row in rows:
            record_time = safe_float(row.get("record_time_sec"))
            header_time = safe_float(row.get("header_timestamp_sec"))
            if record_time is not None and header_time is not None and header_time > 0:
                offsets.append((record_time - header_time) * 1000.0)
        summary = numeric_summary(offsets)
        summary["negative_count"] = sum(value < 0 for value in offsets)
        result[relative] = summary
    return result


def reaction_age_summary(record_dir: Path) -> dict[str, Any]:
    rows = read_csv(record_dir / "07_diagnostics/sensor_to_control_reaction_age.csv")
    reaction_by_channel: dict[str, list[float]] = defaultdict(list)
    age_by_channel: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        channel = row.get("sensor_channel", "UNKNOWN")
        reaction = safe_float(row.get("reaction_time_ms"))
        age = safe_float(row.get("data_age_ms"))
        if reaction is not None:
            reaction_by_channel[channel].append(reaction)
        if age is not None:
            age_by_channel[channel].append(age)
    channels = sorted(set(reaction_by_channel) | set(age_by_channel))
    return {
        "semantics_note": (
            "Message-level sensor-to-Control diagnostics from parsed record; "
            "do not substitute for physical Reaction Time t2-t1."
        ),
        "by_sensor_channel": {
            channel: {
                "reaction_time_ms": numeric_summary(reaction_by_channel[channel]),
                "data_age_ms": numeric_summary(age_by_channel[channel]),
            }
            for channel in channels
        },
        "all_channels": {
            "reaction_time_ms": numeric_summary(
                value for values in reaction_by_channel.values() for value in values
            ),
            "data_age_ms": numeric_summary(
                value for values in age_by_channel.values() for value in values
            ),
        },
    }


def abnormal_frames(record_dir: Path) -> dict[str, Any]:
    rows = read_csv(record_dir / "07_diagnostics/abnormal_frames_summary.csv")
    reasons = Counter(row.get("abnormal_reason") or "UNKNOWN" for row in rows)
    modules = Counter(row.get("module") or "UNKNOWN" for row in rows)
    return {
        "row_count": len(rows),
        "reason_counts": dict(sorted(reasons.items())),
        "module_counts": dict(sorted(modules.items())),
    }


def build_profile(record_dir: Path) -> dict[str, Any]:
    summary = read_json(record_dir / "extraction_summary.json")
    if not summary:
        summary = read_json(record_dir / "00_meta/record_summary.json")
    manifest = read_json(record_dir / "output_manifest.json")
    found = {
        str(path.relative_to(record_dir))
        for path in record_dir.rglob("*")
        if path.is_file()
    }

    planning_latency = read_csv(record_dir / "02_planning/planning_latency_stats.csv")
    control_latency = read_csv(record_dir / "03_control/control_latency.csv")
    alignment = read_csv(record_dir / "07_diagnostics/planning_control_alignment.csv")
    reuse = read_csv(record_dir / "07_diagnostics/control_reuse_summary.csv")

    parse_errors = summary.get("parse_errors") or {}
    missing = sorted(EXPECTED_TABLES - found)
    quality_flags: list[str] = []
    if parse_errors:
        quality_flags.append("RECORD_PARSE_ERROR")
    if missing:
        quality_flags.append("MISSING_EXPECTED_RECORD_TABLE")
    if summary.get("last_seconds_requested") is not None:
        quality_flags.append("RECORD_WINDOW_FILTERED")

    return {
        "profile_schema_version": "2.0",
        "run_id_inferred": record_dir.parent.name,
        "record_dir": str(record_dir.resolve()),
        "evidence_class": "OBSERVED_DERIVED",
        "claim_eligibility": {
            "C2": "PARTIAL_ONLY_UNLESS_REFERENCE_OR_REQUIREMENT_IS_PROVIDED",
            "C3": "PARTIAL_ONLY_WITHOUT_TRACE_LINEAGE",
            "C4": "NOT_TESTABLE_FROM_RECORD_PROFILE_ALONE",
            "C5": "NOT_TESTABLE_FROM_RECORD_PROFILE_ALONE",
            "C6": "NOT_TESTABLE_FROM_RECORD_PROFILE_ALONE",
        },
        "scope_warning": (
            "This timing profile does not itself run target-association or physical-endpoint "
            "detection, and therefore does not establish a dynamic deadline, endpoint-compatible "
            "wall-integrated response distance, braking margin, or collision. The underlying "
            "record may support some physical metrics when combined with audited t1/t2, target "
            "geometry, complete vehicle-state coverage, and direct outcome evidence."
        ),
        "coverage": {
            "record_file_count": summary.get("record_file_count"),
            "record_total_size_bytes": summary.get("record_total_size_bytes"),
            "channel_count": summary.get("channel_count"),
            "message_count": summary.get("message_count"),
            "parse_errors": parse_errors,
            "last_seconds_requested": summary.get("last_seconds_requested"),
            "effective_start_time_sec": summary.get("effective_start_time_sec"),
            "effective_end_time_sec": summary.get("effective_end_time_sec"),
            "row_counts": summary.get("row_counts") or {},
            "manifest_sections": sorted(manifest),
            "found_file_count": len(found),
            "missing_expected_tables": missing,
            "quality_flags": quality_flags,
            "notes": summary.get("notes") or [],
        },
        "layer_2_temporal_degradation": {
            "reference_qualification": {
                "status": "MISSING_UNLESS_SUPPLIED_SEPARATELY",
                "rule": (
                    "A maximum gap or slow message is a case-level observation; C2 requires an "
                    "explicit requirement, baseline distribution, or declared nominal reference."
                ),
            },
            "key_topic_rates": topic_rates(record_dir),
            "key_channel_update_gaps": channel_timing(record_dir),
            "planning_total_time_ms": unique_numeric_summary(
                planning_latency, "planning_seq", "total_time_ms"
            ),
            "control_total_time_ms": unique_numeric_summary(
                control_latency, "control_seq", "total_time_ms"
            ),
            "planning_age_ms": numeric_summary(
                safe_float(row.get("planning_age_ms")) for row in alignment
            ),
            "planning_reuse_count": numeric_summary(
                safe_float(row.get("reuse_count")) for row in reuse
            ),
            "planning_max_age_by_reuse_run_ms": numeric_summary(
                safe_float(row.get("max_planning_age_ms")) for row in reuse
            ),
            "abnormal_frames": abnormal_frames(record_dir),
        },
        "layer_3_cause_effect_timing": {
            "causal_lineage_grade": "C",
            "lineage_limitation": (
                "Message timing alignment without an explicit trace ID, propagated sequence, or "
                "validated provenance mapping establishes temporal association only."
            ),
            "sensor_to_control_message_diagnostics": reaction_age_summary(record_dir),
            "record_minus_header_clock_offsets_ms": clock_offset_summary(record_dir),
        },
        "not_established_by_this_profile_alone": {
            "layer_1_temporal_disturbance": [
                "verified bridge/SCB requested and actual wall delay unless explicitly recorded"
            ],
            "layer_4_temporal_correctness": [
                "independently derived dynamic physical deadline",
                "physical timing slack and deadline miss",
            ],
            "layer_5_temporal_to_physical": [
                "endpoint-compatible wall-integrated response distance without audited t1/t2",
                "distance debt without an independently derived deadline",
            ],
            "layer_6_physical_safety": [
                "direct collision truth without collision-event evidence",
                "full observed braking distance without an audited physical endpoint",
                "final clearance and observed safety margin without target geometry",
            ],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Profile a parsed Apollo cyber record export for six-layer analysis"
    )
    parser.add_argument("--record-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    record_dir = args.record_dir.resolve()
    if not record_dir.is_dir():
        raise SystemExit(f"record directory not found: {record_dir}")
    profile = build_profile(record_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
