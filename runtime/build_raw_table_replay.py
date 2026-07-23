from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from agent_workflow_mock import AgentWorkflow


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


TABLE_SPECS = {
    "event_log": ("event_log.csv", "user_id"),
    "game_behavior_log": ("game_behavior_log.csv", "user_id"),
    "intervention_test": ("intervention_test.csv", "participant_id"),
    "user_profile": ("user_profile.csv", "uid"),
    "version_exposure": ("version_exposure.csv", "user_id"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build anonymized Agent replay cases directly from the five raw CSV tables."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=PACKAGE_ROOT / "synthetic_data" / "generated",
        help="Directory containing the five source CSV files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PACKAGE_ROOT / "synthetic_data" / "agent_replay_results",
        help="Directory for anonymized payloads, results, and audit summary.",
    )
    parser.add_argument(
        "--max-per-scene",
        type=int,
        default=20,
        help="Maximum replay cases retained for each scene.",
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_time(value: str | None) -> datetime:
    if not value:
        return datetime.min
    normalized = value.strip().replace("/", "-")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue
    return datetime.min


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def as_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def normalize_ab_group(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"holdout", "fixed_rule", "agent"}:
        return normalized
    if normalized in {"t", "treatment"}:
        return "treatment"
    if normalized in {"c", "control"}:
        return "control"
    return "Unknown"


def normalize_device_os(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if "ios" in normalized or "iphone" in normalized or "ipad" in normalized:
        return "iOS"
    if normalized == "android" or normalized:
        return "Android"
    return "Unknown"


def anonymize(raw_id: str) -> str:
    return "u_" + hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:12]


def percentile(values: Iterable[float], quantile: float) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * quantile)))
    return ordered[index]


def index_latest(rows: list[dict[str, str]], id_field: str, time_field: str) -> dict[str, dict[str, str]]:
    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        user_id = row.get(id_field, "")
        if not user_id:
            continue
        previous = indexed.get(user_id)
        if previous is None or parse_time(row.get(time_field)) >= parse_time(previous.get(time_field)):
            indexed[user_id] = row
    return indexed


def build_event_summary(rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    by_user: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("user_id"):
            by_user[row["user_id"]].append(row)

    result: dict[str, dict[str, Any]] = {}
    for user_id, user_rows in by_user.items():
        ordered = sorted(user_rows, key=lambda row: parse_time(row.get("event_timestamp")))
        counts = Counter(row.get("event_type", "") for row in ordered)
        load_times = [
            number
            for number in (as_float(row.get("page_load_time_ms")) for row in ordered)
            if number is not None
        ]
        device_os = "Unknown"
        for row in reversed(ordered):
            if row.get("device_model"):
                device_os = normalize_device_os(row["device_model"])
                break
        result[user_id] = {
            "counts": counts,
            "last_event": ordered[-1],
            "page_load_time_p95": percentile(load_times, 0.95),
            "device_os": device_os,
        }
    return result


def build_game_sessions(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("user_id") and row.get("session_id"):
            grouped[(row["user_id"], row["session_id"])].append(row)

    sessions: list[dict[str, Any]] = []
    for (user_id, session_id), session_rows in grouped.items():
        ordered = sorted(session_rows, key=lambda row: parse_time(row.get("event_timestamp")))
        starts = [row for row in ordered if row.get("event_type") == "game_start"]
        failures = [row for row in ordered if row.get("event_type") == "level_fail"]
        exits = [row for row in ordered if row.get("event_type") == "game_exit"]
        level_2_failures = [row for row in failures if as_int(row.get("level_id"), -1) == 2]
        level_2_exits = [row for row in exits if str(row.get("exit_point", "")).strip() in {"2", "2.0"}]
        variant = next((row.get("game_variant") for row in ordered if row.get("game_variant")), "unknown")
        trigger = level_2_failures[-1] if level_2_failures else (
            level_2_exits[-1] if level_2_exits else (failures[-1] if failures else (starts[0] if starts else ordered[-1]))
        )
        sessions.append(
            {
                "user_id": user_id,
                "session_id": session_id,
                "variant": variant,
                "failures": failures,
                "level_2_failures": level_2_failures,
                "level_2_exits": level_2_exits,
                "trigger": trigger,
                "is_new_user": any(as_bool(row.get("is_new_user")) for row in starts),
                "has_game_complete": any(row.get("event_type") == "game_complete" for row in ordered),
                "event_count": len(ordered),
            }
        )
    return sessions


def main() -> None:
    args = parse_args()
    paths = {name: args.data_dir / file_name for name, (file_name, _) in TABLE_SPECS.items()}
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing source files: " + ", ".join(missing))

    raw = {name: read_csv(path) for name, path in paths.items()}
    profiles = {row["uid"]: row for row in raw["user_profile"] if row.get("uid")}
    exposures = index_latest(raw["version_exposure"], "user_id", "first_exposure_date")
    interventions = index_latest(raw["intervention_test"], "participant_id", "intervention_date")
    event_summary = build_event_summary(raw["event_log"])
    game_sessions = build_game_sessions(raw["game_behavior_log"])

    source_sets = {
        name: {row[id_field] for row in raw[name] if row.get(id_field)}
        for name, (_, id_field) in TABLE_SPECS.items()
    }

    def coverage(user_id: str) -> list[str]:
        return sorted(name for name, user_ids in source_sets.items() if user_id in user_ids)

    def base_features(user_id: str) -> dict[str, Any]:
        profile = profiles.get(user_id, {})
        exposure = exposures.get(user_id, {})
        intervention = interventions.get(user_id, {})
        events = event_summary.get(user_id, {})
        coupon_total = as_int(profile.get("coupon_total_count_90d"))
        coupon_used = as_int(profile.get("coupon_used_count_90d"))
        return {
            "membership_level": profile.get("membership_level") or "Unknown",
            "is_88vip": as_bool(profile.get("is_88vip")),
            "device_os": normalize_device_os(intervention.get("device_os"))
            if intervention.get("device_os")
            else events.get("device_os", "Unknown"),
            "province": profile.get("province") or "Unknown",
            "category_preference_1": profile.get("category_preference_1") or "Unknown",
            "coupon_available_count": max(0, coupon_total - coupon_used),
            "last_intervention_type": intervention.get("intervention_type") or "none",
            "ab_test_group": normalize_ab_group(exposure.get("ab_test_group")),
            "total_exposure_days": as_int(exposure.get("total_exposure_days")),
            "allow_coin_compensation": True,
            "allow_coupon": True,
            "max_intervention_per_session": 1,
        }

    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for session in game_sessions:
        user_id = session["user_id"]
        common = base_features(user_id)
        trigger = session["trigger"]
        trigger_level = as_int(trigger.get("level_id"), 0) or None
        exit_point = trigger.get("exit_point") or None
        common.update(
            {
                "current_game_variant": session["variant"],
                "current_level_id": trigger_level,
                "current_exit_point": exit_point,
                "fail_count_session": len(session["failures"]),
                "level_2_fail_count_session": len(session["level_2_failures"]),
                "is_new_game_user": session["is_new_user"],
            }
        )

        if session["variant"] == "standard" and (session["level_2_failures"] or session["level_2_exits"]):
            scene = "level_2_block"
            common["current_level_id"] = 2
            common["current_exit_point"] = "2" if session["level_2_exits"] else exit_point
            common["fail_count_session"] = max(1, common["fail_count_session"])
        elif len(session["failures"]) >= 2:
            scene = "continuous_failure"
            if session["variant"] == "standard" and common["current_level_id"] == 2:
                common["current_level_id"] = 3
        elif session["is_new_user"]:
            scene = "new_user_first_game"
            common["fail_count_session"] = 0
            common["current_level_id"] = None
        else:
            continue

        event_name = "game_start" if scene == "new_user_first_game" else trigger.get("event_type", "game_event")
        candidates[scene].append(
            {
                "raw_user_id": user_id,
                "payload": {
                    "request_id": (
                        f"raw_{scene}_{anonymize(user_id)}_"
                        + hashlib.sha256(session["session_id"].encode("utf-8")).hexdigest()[:8]
                    ),
                    "user_id": anonymize(user_id),
                    "session_id": "s_" + hashlib.sha256(session["session_id"].encode("utf-8")).hexdigest()[:10],
                    "trigger_event": {
                        "event_name": event_name,
                        "event_time": trigger.get("event_timestamp"),
                    },
                    "key_features": common,
                    "source_context": {
                        "expected_scene": scene,
                        "source_coverage": coverage(user_id),
                        "source_table_count": len(coverage(user_id)),
                    },
                },
            }
        )

    for user_id, summary in event_summary.items():
        counts: Counter[str] = summary["counts"]
        common = base_features(user_id)
        common.update(
            {
                "has_add_to_cart_7d": counts.get("add_to_cart", 0) > 0,
                "has_order_7d": counts.get("order_placed", 0) > 0,
                "page_load_time_ms": summary.get("page_load_time_p95"),
                "fail_count_session": 0,
                "is_new_game_user": False,
            }
        )

        if common["device_os"] == "Android" and (common["page_load_time_ms"] or 0) >= 3000:
            scene = "android_perf_risk"
        elif common["has_add_to_cart_7d"] and not common["has_order_7d"]:
            scene = "cart_without_order"
        elif counts.get("app_open", 0) > 0:
            scene = "no_action"
        else:
            continue

        trigger = summary["last_event"]
        candidates[scene].append(
            {
                "raw_user_id": user_id,
                "payload": {
                    "request_id": f"raw_{scene}_{anonymize(user_id)}",
                    "user_id": anonymize(user_id),
                    "session_id": "s_" + hashlib.sha256((trigger.get("session_id") or user_id).encode("utf-8")).hexdigest()[:10],
                    "trigger_event": {
                        "event_name": trigger.get("event_type") or "historical_replay",
                        "event_time": trigger.get("event_timestamp"),
                    },
                    "key_features": common,
                    "source_context": {
                        "expected_scene": scene,
                        "source_coverage": coverage(user_id),
                        "source_table_count": len(coverage(user_id)),
                    },
                },
            }
        )

    selected: list[dict[str, Any]] = []
    for scene in (
        "level_2_block",
        "continuous_failure",
        "android_perf_risk",
        "cart_without_order",
        "new_user_first_game",
        "no_action",
    ):
        rows = sorted(
            candidates.get(scene, []),
            key=lambda row: (
                -row["payload"]["source_context"]["source_table_count"],
                row["payload"]["user_id"],
                row["payload"]["request_id"],
            ),
        )
        selected.extend(rows[: args.max_per_scene])

    workflow = AgentWorkflow()
    results: list[dict[str, Any]] = []
    for item in selected:
        payload = item["payload"]
        response = workflow.run(payload)
        expected = payload["source_context"]["expected_scene"]
        actual = response["decision"]["scene_type"]
        results.append(
            {
                "request_id": payload["request_id"],
                "user_id": payload["user_id"],
                "expected_scene": expected,
                "actual_scene": actual,
                "scene_match": expected == actual,
                "decision_status": response["decision"]["decision_status"],
                "actions": [step["action_type"] for step in response["decision"].get("plan", [])],
                "source_coverage": payload["source_context"]["source_coverage"],
                "source_table_count": payload["source_context"]["source_table_count"],
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    payload_path = args.output_dir / "raw_table_replay_payloads.json"
    result_path = args.output_dir / "raw_table_replay_results.json"
    summary_path = args.output_dir / "raw_table_replay_summary.csv"
    audit_path = args.output_dir / "raw_table_replay_audit.json"

    payload_path.write_text(
        json.dumps([item["payload"] for item in selected], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    result_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    with summary_path.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = [
            "request_id",
            "user_id",
            "expected_scene",
            "actual_scene",
            "scene_match",
            "decision_status",
            "actions",
            "source_table_count",
            "source_coverage",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in results:
            writer.writerow(
                {
                    **row,
                    "actions": " | ".join(row["actions"]),
                    "source_coverage": " | ".join(row["source_coverage"]),
                }
            )

    scene_counts = Counter(row["expected_scene"] for row in results)
    matched = sum(row["scene_match"] for row in results)
    all_five_count = sum(row["source_table_count"] == 5 for row in results)
    try:
        source_directory = str(args.data_dir.resolve().relative_to(PACKAGE_ROOT))
    except ValueError:
        source_directory = "external_source"
    audit = {
        "source_directory": source_directory,
        "source_row_counts": {name: len(rows) for name, rows in raw.items()},
        "source_user_counts": {name: len(user_ids) for name, user_ids in source_sets.items()},
        "all_five_user_overlap": len(set.intersection(*source_sets.values())),
        "selected_replay_cases": len(results),
        "selected_all_five_table_cases": all_five_count,
        "scene_counts": dict(scene_counts),
        "scene_match_count": matched,
        "scene_match_rate": matched / len(results) if results else 0.0,
        "privacy": "Raw user identifiers are SHA-256 hashed in all generated outputs.",
    }
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Replay cases: {len(results)}")
    print(f"Scene matches: {matched}/{len(results)}")
    print(f"All-five-table cases: {all_five_count}")
    print(f"Payloads: {payload_path}")
    print(f"Results: {result_path}")
    print(f"Audit: {audit_path}")


if __name__ == "__main__":
    main()
