#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run a full, anonymized Agent decision replay over synthetic five-table data.

This runner intentionally computes an expected scene outside AgentWorkflow, then compares
it with the current SceneClassifier. It validates decision behavior and data plumbing only.
No real business tools or production users are invoked.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve()
WEEK6_DIR = HERE.parents[1]
LOCAL_RUNTIME = WEEK6_DIR / "runtime"
sys.path.insert(0, str(LOCAL_RUNTIME))
from agent_workflow_mock import AgentWorkflow  # noqa: E402


TABLE_SPECS = {
    "event_log": ("event_log.csv", "user_id"),
    "game_behavior_log": ("game_behavior_log.csv", "user_id"),
    "intervention_test": ("intervention_test.csv", "participant_id"),
    "user_profile": ("user_profile.csv", "uid"),
    "version_exposure": ("version_exposure.csv", "user_id"),
}
SCENE_ORDER = (
    "level_2_block",
    "continuous_failure",
    "android_perf_risk",
    "cart_without_order",
    "new_user_first_game",
    "no_action",
)
REGISTERED_ACTIONS = {
    "show_tutorial",
    "switch_guided_mode",
    "reduce_difficulty",
    "show_static_hint",
    "show_perf_tip",
    "reduce_animation",
    "explain_coin_value",
    "show_recommendation",
    "grant_coin_compensation",
    "coupon_reminder",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run full Agent replay over synthetic five-table data.")
    parser.add_argument("--data-dir", type=Path, default=HERE.parent / "generated")
    parser.add_argument("--output-dir", type=Path, default=HERE.parent / "agent_full_replay")
    parser.add_argument("--dashboard-data", type=Path, default=WEEK6_DIR / "dashboard" / "agent_test_data.js")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


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


def normalize_device_os(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if "ios" in normalized or "iphone" in normalized or "ipad" in normalized:
        return "iOS"
    if normalized == "android":
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
        key = row.get(id_field, "")
        if not key:
            continue
        prior = indexed.get(key)
        if prior is None or parse_time(row.get(time_field)) >= parse_time(prior.get(time_field)):
            indexed[key] = row
    return indexed


def build_event_summary(rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    by_user: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("user_id"):
            by_user[row["user_id"]].append(row)
    summary: dict[str, dict[str, Any]] = {}
    for user_id, events in by_user.items():
        ordered = sorted(events, key=lambda row: parse_time(row.get("event_timestamp")))
        load_times = [value for value in (as_float(row.get("page_load_time_ms")) for row in ordered) if value is not None]
        summary[user_id] = {
            "counts": Counter(row.get("event_type", "") for row in ordered),
            "page_load_time_p95": percentile(load_times, 0.95),
            "last_event": ordered[-1],
        }
    return summary


def build_game_sessions(rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    by_user: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("user_id"):
            by_user[row["user_id"]].append(row)
    sessions: dict[str, dict[str, Any]] = {}
    for user_id, game_rows in by_user.items():
        ordered = sorted(game_rows, key=lambda row: parse_time(row.get("event_timestamp")))
        failures = [row for row in ordered if row.get("event_type") == "level_fail"]
        l2_failures = [row for row in failures if as_int(row.get("level_id"), -1) == 2]
        exits = [row for row in ordered if row.get("event_type") == "game_exit"]
        l2_exits = [row for row in exits if str(row.get("exit_point", "")).strip() in {"2", "2.0"}]
        starts = [row for row in ordered if row.get("event_type") == "game_start"]
        trigger = l2_failures[-1] if l2_failures else (l2_exits[-1] if l2_exits else (failures[-1] if failures else starts[0]))
        sessions[user_id] = {
            "session_id": trigger.get("session_id") or f"session_{user_id}",
            "variant": next((row.get("game_variant") for row in ordered if row.get("game_variant")), "unknown"),
            "failures": failures,
            "l2_failures": l2_failures,
            "l2_exits": l2_exits,
            "is_new_user": any(as_bool(row.get("is_new_user")) for row in starts),
            "trigger": trigger,
        }
    return sessions


def expected_scene(features: dict[str, Any]) -> str:
    """Independent oracle mirroring the approved priority order, not the Agent implementation."""
    if features["current_game_variant"] == "standard" and features["current_level_id"] == 2 and (
        features["level_2_fail_count_session"] >= 1 or str(features.get("current_exit_point")) == "2"
    ):
        return "level_2_block"
    if features["fail_count_session"] >= 2:
        return "continuous_failure"
    if features["device_os"] == "Android" and (features.get("page_load_time_ms") or 0) >= 3000:
        return "android_perf_risk"
    if features["has_add_to_cart_7d"] and not features["has_order_7d"]:
        return "cart_without_order"
    if features["is_new_game_user"]:
        return "new_user_first_game"
    return "no_action"


def trigger_name_for(scene: str, trigger: dict[str, str]) -> str:
    if scene == "new_user_first_game":
        return "game_start"
    if scene == "android_perf_risk":
        return "app_open"
    if scene == "cart_without_order":
        return "add_to_cart"
    if scene == "no_action":
        return "app_open"
    return trigger.get("event_type") or "level_fail"


def action_summary(response: dict[str, Any]) -> tuple[list[str], str]:
    actions = [step["action_type"] for step in response["decision"].get("plan", [])]
    fallback = response["decision"].get("fallback_action", "") if response["decision"].get("decision_status") == "fallback" else ""
    return actions, fallback


def build_dashboard_payload(summary: dict[str, Any], tree: dict[str, Any], results: list[dict[str, Any]]) -> str:
    """Build a compact, auditable data snapshot for the static local dashboard.

    The dashboard gets full group-by-scene counts plus a deterministic, anonymized
    decision sample. The complete 8,100-row record remains in the CSV output.
    """
    scene_group_counts: dict[tuple[str, str], int] = Counter(
        (row["ab_group"], row["actual_scene"]) for row in results
    )
    group_scene_breakdown = [
        {
            "group": group,
            "scene": scene,
            "users": scene_group_counts[(group, scene)],
        }
        for group in ("holdout", "fixed_rule", "agent")
        for scene in SCENE_ORDER
    ]
    sample_decisions: list[dict[str, Any]] = []
    for group in ("holdout", "fixed_rule", "agent"):
        for scene in SCENE_ORDER:
            candidates = sorted(
                (row for row in results if row["ab_group"] == group and row["actual_scene"] == scene),
                key=lambda row: row["user_id_hash"],
            )
            for row in candidates[:6]:
                sample_decisions.append({
                    "user_id_hash": row["user_id_hash"],
                    "group": row["ab_group"],
                    "scene": row["actual_scene"],
                    "decision_status": row["decision_status"],
                    "actions": row["actions"] or "no_action",
                    "tool_execution_count": row["tool_execution_count"],
                    "tool_success_count": row["tool_success_count"],
                    "source_table_count": row["source_table_count"],
                })
    data = {
        "meta": {"source": "synthetic_full_agent_replay", "generated_at": summary["generated_at"], "scope": "8,100 synthetic users; Mock tools only"},
        "kpis": [
            {"label": "全量评估用户", "value": f"{summary['total_users']:,}", "desc": "每名合成用户一条最终决策", "tone": ""},
            {"label": "五表来源覆盖率", "value": f"{summary['all_five_coverage_rate']:.1%}", "desc": f"{summary['all_five_user_count']:,} / {summary['total_users']:,} 用户", "tone": "positive"},
            {"label": "场景判定一致率", "value": f"{summary['scene_match_rate']:.1%}", "desc": "独立优先级规则 vs Agent", "tone": "positive" if summary["scene_match_rate"] == 1 else "negative"},
            {"label": "工具执行成功率", "value": f"{summary['tool_success_rate']:.1%}", "desc": f"{summary['tool_success_count']:,} / {summary['tool_execution_count']:,} 次工具调用", "tone": "positive"},
        ],
        "tree": tree,
        "summary": summary,
        "group_scene_breakdown": group_scene_breakdown,
        "sample_decisions": sample_decisions,
    }
    return "window.AGENT_TEST_DATA = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n"


def main() -> int:
    args = parse_args()
    paths = {name: args.data_dir / filename for name, (filename, _) in TABLE_SPECS.items()}
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing source files: " + ", ".join(missing))
    raw = {name: read_csv(path) for name, path in paths.items()}
    profiles = {row["uid"]: row for row in raw["user_profile"] if row.get("uid")}
    exposures = index_latest(raw["version_exposure"], "user_id", "first_exposure_date")
    interventions = index_latest(raw["intervention_test"], "participant_id", "intervention_date")
    event_summary = build_event_summary(raw["event_log"])
    sessions = build_game_sessions(raw["game_behavior_log"])
    source_sets = {name: {row[id_field] for row in raw[name] if row.get(id_field)} for name, (_, id_field) in TABLE_SPECS.items()}
    user_ids = sorted(set.intersection(*source_sets.values()))
    if not user_ids:
        raise RuntimeError("No five-table user overlap found")

    workflow = AgentWorkflow()
    results: list[dict[str, Any]] = []
    condition_reach = Counter()
    condition_yes = Counter()
    group_counts = Counter()
    action_counts = Counter()
    scene_action_counts: dict[str, Counter[str]] = defaultdict(Counter)
    status_counts = Counter()
    tool_status_counts = Counter()
    mismatch_count = 0
    invalid_action_count = 0
    duplicate_action_count = 0

    for raw_user_id in user_ids:
        profile = profiles[raw_user_id]
        exposure = exposures[raw_user_id]
        intervention = interventions[raw_user_id]
        events = event_summary[raw_user_id]
        session = sessions[raw_user_id]
        coupon_total = as_int(profile.get("coupon_total_count_90d"))
        coupon_used = as_int(profile.get("coupon_used_count_90d"))
        trigger = session["trigger"]
        features = {
            "membership_level": profile.get("membership_level") or "Unknown",
            "is_88vip": as_bool(profile.get("is_88vip")),
            "device_os": normalize_device_os(intervention.get("device_os")),
            "province": profile.get("province") or "Unknown",
            "category_preference_1": profile.get("category_preference_1") or "Unknown",
            "coupon_available_count": max(0, coupon_total - coupon_used),
            "ab_test_group": exposure.get("ab_test_group") or "Unknown",
            "current_game_variant": session["variant"],
            "current_level_id": as_int(trigger.get("level_id"), 0) or None,
            "current_exit_point": trigger.get("exit_point") or None,
            "fail_count_session": len(session["failures"]),
            "level_2_fail_count_session": len(session["l2_failures"]),
            "is_new_game_user": session["is_new_user"],
            "has_add_to_cart_7d": events["counts"].get("add_to_cart", 0) > 0,
            "has_order_7d": events["counts"].get("order_placed", 0) > 0,
            "page_load_time_ms": events["page_load_time_p95"],
            "max_intervention_per_session": 1,
            "allow_coin_compensation": True,
            "allow_coupon": True,
            "risk_level": "low",
            "push_frequency_limit_reached": False,
        }
        # Set explicit Level 2 context before applying the priority oracle.
        if session["variant"] == "standard" and (session["l2_failures"] or session["l2_exits"]):
            features["current_level_id"] = 2
            features["current_exit_point"] = "2" if session["l2_exits"] else features["current_exit_point"]
            features["fail_count_session"] = max(1, features["fail_count_session"])
        expected = expected_scene(features)
        for scene in SCENE_ORDER:
            condition_reach[scene] += 1
            if expected == scene:
                condition_yes[scene] += 1
                break
        payload = {
            "request_id": f"synthetic_{expected}_{anonymize(raw_user_id)}",
            "user_id": anonymize(raw_user_id),
            "session_id": "s_" + hashlib.sha256(session["session_id"].encode("utf-8")).hexdigest()[:10],
            "trigger_event": {"event_name": trigger_name_for(expected, trigger), "event_time": trigger.get("event_timestamp")},
            "key_features": features,
        }
        response = workflow.run(payload)
        actual = response["decision"]["scene_type"]
        actions, fallback = action_summary(response)
        tool_results = response["tool_results"]
        group_counts[features["ab_test_group"]] += 1
        status_counts[response["decision"]["decision_status"]] += 1
        action_counts.update(actions or ([fallback] if fallback else ["no_action"]))
        scene_action_counts[actual].update(actions or ([fallback] if fallback else ["no_action"]))
        tool_status_counts.update(result["status"] for result in tool_results)
        scene_match = expected == actual
        mismatch_count += int(not scene_match)
        invalid_actions = [action for action in actions if action not in REGISTERED_ACTIONS]
        invalid_action_count += len(invalid_actions)
        duplicate_action_count += int(len(actions) != len(set(actions)))
        results.append({
            "user_id_hash": payload["user_id"], "ab_group": features["ab_test_group"], "expected_scene": expected,
            "actual_scene": actual, "scene_match": scene_match, "decision_status": response["decision"]["decision_status"],
            "actions": " | ".join(actions), "fallback_action": fallback, "tool_execution_count": len(tool_results),
            "tool_success_count": sum(result["status"] == "success" for result in tool_results),
            "source_table_count": 5, "source_coverage": "event_log | game_behavior_log | intervention_test | user_profile | version_exposure",
            "feature_version": "synthetic-five-table-v1", "workflow_version": "agent-v1-mock",
        })

    tool_execution_count = sum(row["tool_execution_count"] for row in results)
    tool_success_count = sum(row["tool_success_count"] for row in results)
    scene_counts = Counter(row["actual_scene"] for row in results)
    summary = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "test_type": "full_synthetic_agent_decision_replay",
        "test_boundary": "Mock Agent and Mock tools only; not a business uplift experiment.",
        "source_directory": str(args.data_dir),
        "total_users": len(results),
        "all_five_user_count": len(results),
        "all_five_coverage_rate": 1.0,
        "source_row_counts": {name: len(rows) for name, rows in raw.items()},
        "group_counts": dict(group_counts),
        "expected_scene_counts": dict(Counter(row["expected_scene"] for row in results)),
        "actual_scene_counts": dict(scene_counts),
        "scene_match_count": len(results) - mismatch_count,
        "scene_match_rate": (len(results) - mismatch_count) / len(results),
        "decision_status_counts": dict(status_counts),
        "action_counts": dict(action_counts),
        "tool_execution_count": tool_execution_count,
        "tool_success_count": tool_success_count,
        "tool_success_rate": tool_success_count / tool_execution_count if tool_execution_count else 1.0,
        "tool_status_counts": dict(tool_status_counts),
        "invalid_action_count": invalid_action_count,
        "duplicate_action_decision_count": duplicate_action_count,
        "passed": mismatch_count == 0 and invalid_action_count == 0 and duplicate_action_count == 0,
    }
    tree = {
        "title": "Agent V1 场景优先级决策树",
        "root_users": len(results),
        "priority_nodes": [
            {"id": "level_2_block", "label": "standard + Level 2 + 失败/退出", "reached": condition_reach["level_2_block"], "yes": condition_yes["level_2_block"], "no": condition_reach["level_2_block"] - condition_yes["level_2_block"], "action_counts": dict(scene_action_counts["level_2_block"])},
            {"id": "continuous_failure", "label": "同一会话失败次数 >= 2", "reached": condition_reach["continuous_failure"], "yes": condition_yes["continuous_failure"], "no": condition_reach["continuous_failure"] - condition_yes["continuous_failure"], "action_counts": dict(scene_action_counts["continuous_failure"])},
            {"id": "android_perf_risk", "label": "Android 且加载耗时 >= 3000ms", "reached": condition_reach["android_perf_risk"], "yes": condition_yes["android_perf_risk"], "no": condition_reach["android_perf_risk"] - condition_yes["android_perf_risk"], "action_counts": dict(scene_action_counts["android_perf_risk"])},
            {"id": "cart_without_order", "label": "7 日加购且未下单", "reached": condition_reach["cart_without_order"], "yes": condition_yes["cart_without_order"], "no": condition_reach["cart_without_order"] - condition_yes["cart_without_order"], "action_counts": dict(scene_action_counts["cart_without_order"])},
            {"id": "new_user_first_game", "label": "新用户进入首局", "reached": condition_reach["new_user_first_game"], "yes": condition_yes["new_user_first_game"], "no": condition_reach["new_user_first_game"] - condition_yes["new_user_first_game"], "action_counts": dict(scene_action_counts["new_user_first_game"])},
            {"id": "no_action", "label": "不触发干预", "reached": condition_reach["no_action"], "yes": condition_yes["no_action"], "no": 0, "action_counts": dict(scene_action_counts["no_action"])},
        ],
        "scene_counts": dict(scene_counts),
        "action_counts": dict(action_counts),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    result_path = args.output_dir / "full_agent_replay_results.csv"
    summary_path = args.output_dir / "full_agent_replay_summary.json"
    tree_path = args.output_dir / "full_agent_decision_tree.json"
    report_path = args.output_dir / "full_agent_replay_report.md"
    write_csv(result_path, list(results[0].keys()), results)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    tree_path.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")
    scene_lines = "\n".join(f"- `{name}`：{scene_counts.get(name, 0):,}" for name in SCENE_ORDER)
    report = (
        "# 合成五表全量 Agent 决策测试报告\n\n"
        f"- 测试范围：{summary['total_users']:,} 名合成用户，五表覆盖率 {summary['all_five_coverage_rate']:.1%}。\n"
        f"- 场景一致率：{summary['scene_match_count']:,}/{summary['total_users']:,}（{summary['scene_match_rate']:.1%}）。\n"
        f"- 工具执行：{summary['tool_success_count']:,}/{summary['tool_execution_count']:,} 成功（{summary['tool_success_rate']:.1%}）。\n"
        f"- 非法动作：{summary['invalid_action_count']}；重复动作决策：{summary['duplicate_action_decision_count']}。\n"
        f"- 测试结论：{'通过' if summary['passed'] else '失败'}。\n\n"
        f"## 场景分布\n\n{scene_lines}\n"
        "\n## 说明\n\n本报告验证 Agent V1 的本地决策、Guardrail 与 Mock 工具执行，不用于估计真实业务 uplift。\n"
    )
    report_path.write_text(report, encoding="utf-8")
    args.dashboard_data.parent.mkdir(parents=True, exist_ok=True)
    args.dashboard_data.write_text(build_dashboard_payload(summary, tree, results), encoding="utf-8")
    print(f"Full replay users: {summary['total_users']}")
    print(f"Scene match: {summary['scene_match_count']}/{summary['total_users']}")
    print(f"All-five coverage: {summary['all_five_user_count']}/{summary['total_users']}")
    print(f"Tool success: {summary['tool_success_count']}/{summary['tool_execution_count']}")
    print(f"Passed: {summary['passed']}")
    print(f"Results: {result_path}")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
