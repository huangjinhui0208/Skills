#!/usr/bin/env python3
"""Flatten per-run record profiles into a cross-run diagnostic CSV."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


CHANNEL_PREFIX = {
    "/apollo/localization/pose": "localization",
    "/apollo/perception/obstacles": "perception",
    "/apollo/prediction": "prediction",
    "/apollo/planning": "planning",
    "/apollo/control": "control",
}


def nested(value: dict[str, Any], *keys: str) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def build_row(profile: dict[str, Any]) -> dict[str, Any]:
    l2 = profile.get("layer_2_temporal_degradation") or {}
    l3 = profile.get("layer_3_cause_effect_timing") or {}
    coverage = profile.get("coverage") or {}
    reaction = nested(l3, "sensor_to_control_message_diagnostics", "all_channels") or {}
    row: dict[str, Any] = {
        "run_id": profile.get("run_id_inferred"),
        "record_dir": profile.get("record_dir"),
        "record_channel_count": coverage.get("channel_count"),
        "record_message_count": coverage.get("message_count"),
        "record_parse_error_count": len(coverage.get("parse_errors") or {}),
        "record_missing_expected_table_count": len(
            coverage.get("missing_expected_tables") or []
        ),
        "record_quality_flags": "|".join(coverage.get("quality_flags") or []),
        "planning_total_time_median_ms": nested(l2, "planning_total_time_ms", "median"),
        "planning_total_time_p90_ms": nested(l2, "planning_total_time_ms", "p90"),
        "planning_total_time_p99_ms": nested(l2, "planning_total_time_ms", "p99"),
        "planning_total_time_max_ms": nested(l2, "planning_total_time_ms", "max"),
        "control_total_time_median_ms": nested(l2, "control_total_time_ms", "median"),
        "control_total_time_p90_ms": nested(l2, "control_total_time_ms", "p90"),
        "control_total_time_p99_ms": nested(l2, "control_total_time_ms", "p99"),
        "control_total_time_max_ms": nested(l2, "control_total_time_ms", "max"),
        "planning_age_median_ms": nested(l2, "planning_age_ms", "median"),
        "planning_age_p90_ms": nested(l2, "planning_age_ms", "p90"),
        "planning_age_p99_ms": nested(l2, "planning_age_ms", "p99"),
        "planning_age_max_ms": nested(l2, "planning_age_ms", "max"),
        "planning_reuse_count_median": nested(l2, "planning_reuse_count", "median"),
        "planning_reuse_count_p90": nested(l2, "planning_reuse_count", "p90"),
        "planning_reuse_count_max": nested(l2, "planning_reuse_count", "max"),
        "sensor_to_control_reaction_median_ms": nested(reaction, "reaction_time_ms", "median"),
        "sensor_to_control_reaction_p90_ms": nested(reaction, "reaction_time_ms", "p90"),
        "sensor_to_control_reaction_p99_ms": nested(reaction, "reaction_time_ms", "p99"),
        "sensor_to_control_data_age_median_ms": nested(reaction, "data_age_ms", "median"),
        "sensor_to_control_data_age_p90_ms": nested(reaction, "data_age_ms", "p90"),
        "sensor_to_control_data_age_p99_ms": nested(reaction, "data_age_ms", "p99"),
    }
    channel_gaps = l2.get("key_channel_update_gaps") or {}
    for channel, prefix in CHANNEL_PREFIX.items():
        stats = channel_gaps.get(channel) or {}
        gap = stats.get("gap_ms") or {}
        row[f"{prefix}_period_median_ms"] = stats.get("estimated_period_ms")
        row[f"{prefix}_gap_p90_ms"] = gap.get("p90")
        row[f"{prefix}_gap_p99_ms"] = gap.get("p99")
        row[f"{prefix}_gap_max_ms"] = gap.get("max")
        row[f"{prefix}_gap_gt_2x_count"] = stats.get("gap_gt_2x_median_count")
    return row


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate record profile JSON files")
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = sorted(args.profiles_dir.glob("*.json"))
    rows = [build_row(json.loads(path.read_text(encoding="utf-8-sig"))) for path in paths]
    if not rows:
        raise SystemExit(f"no profile JSON files found in {args.profiles_dir}")
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(args.output_csv.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
