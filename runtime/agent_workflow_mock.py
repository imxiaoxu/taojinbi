from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def parse_key_features(raw: str) -> dict[str, Any]:
    features: dict[str, Any] = {}
    if not raw:
        return features
    for part in raw.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value.lower() in {"true", "false"}:
            features[key] = parse_bool(value)
        else:
            try:
                if "." in value:
                    features[key] = float(value)
                else:
                    features[key] = int(value)
            except ValueError:
                features[key] = value
    return features


@dataclass
class MemoryStore:
    records: dict[str, dict[str, Any]] = field(default_factory=dict)

    def read(self, user_id: str, session_id: str) -> dict[str, Any]:
        user_memory = self.records.get(user_id, {}).copy()
        user_memory.setdefault("intervention_history", [])
        user_memory.setdefault("preferred_game_variant", None)
        user_memory.setdefault("historical_fail_level", [])
        user_memory.setdefault("last_intervention_feedback", None)
        user_memory.setdefault("intervention_cooldown_until", None)
        user_memory["session_id"] = session_id
        return user_memory

    def write(self, user_id: str, update: dict[str, Any]) -> dict[str, Any]:
        current = self.records.setdefault(user_id, {})
        for key, value in update.items():
            if key == "intervention_history":
                current.setdefault(key, [])
                current[key].extend(value if isinstance(value, list) else [value])
            else:
                current[key] = value
        current["updated_at"] = now_iso()
        return {"status": "success", "updated_keys": sorted(update.keys())}


@dataclass
class EvalLogger:
    logs: list[dict[str, Any]] = field(default_factory=list)

    def write(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.logs.append(payload)
        return {"status": "success", "log_index": len(self.logs) - 1}

    def dump_jsonl(self, path: Path) -> None:
        with path.open("w", encoding="utf-8") as f:
            for row in self.logs:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")


class FeatureBuilder:
    def build(self, event: dict[str, Any], key_features: dict[str, Any]) -> dict[str, Any]:
        trigger_event_name = event.get("event_name", "unknown")
        level_id = key_features.get("level_id", key_features.get("current_level_id"))
        game_variant = key_features.get("game_variant", key_features.get("current_game_variant", "unknown"))

        realtime = {
            "trigger_event_name": trigger_event_name,
            "current_level_id": level_id,
            "current_game_variant": game_variant,
            "current_fail_reason": key_features.get("fail_reason", "unknown"),
            "current_exit_point": key_features.get("current_exit_point"),
            "page_load_time_ms": key_features.get("page_load_time_ms"),
            "tool_timeout_flag": parse_bool(key_features.get("tool_timeout_flag")),
        }
        session = {
            "fail_count_session": int(key_features.get("fail_count_session", 0) or 0),
            "level_2_fail_count_session": int(key_features.get("level_2_fail_count_session", 0) or 0),
            "intervention_count_session": int(key_features.get("intervention_count_session", 0) or 0),
            "last_intervention_type": key_features.get("last_intervention_type"),
            "tutorial_shown_session": parse_bool(key_features.get("tutorial_shown_session")),
            "guided_mode_switched_session": parse_bool(key_features.get("guided_mode_switched_session")),
            "session_duration_ms": int(key_features.get("session_duration_ms", 0) or 0),
        }
        profile = {
            "membership_level": key_features.get("membership_level", "Unknown"),
            "is_88vip": parse_bool(key_features.get("is_88vip")),
            "device_os": key_features.get("device_os", "Unknown"),
            "province": key_features.get("province", "Unknown"),
            "category_preference_1": key_features.get("category_preference_1", "Unknown"),
        }
        history = {
            "is_new_game_user": parse_bool(key_features.get("is_new_game_user")),
            "historical_game_completion_rate_30d": key_features.get("historical_game_completion_rate_30d"),
            "historical_exit_rate_30d": key_features.get("historical_exit_rate_30d"),
            "historical_level_2_fail_count_30d": key_features.get("historical_level_2_fail_count_30d", 0),
        }
        transaction = {
            "has_add_to_cart_7d": parse_bool(key_features.get("has_add_to_cart_7d")),
            "has_order_7d": parse_bool(key_features.get("has_order_7d")),
            "coupon_available_count": int(key_features.get("coupon_available_count", 0) or 0),
            "coin_balance": int(key_features.get("coin_balance", 0) or 0),
        }
        transaction["add_to_cart_without_order_flag"] = (
            transaction["has_add_to_cart_7d"] and not transaction["has_order_7d"]
        )
        guardrails = {
            "max_intervention_per_session": int(key_features.get("max_intervention_per_session", 1) or 1),
            "allow_coin_compensation": parse_bool(key_features.get("allow_coin_compensation", True)),
            "allow_coupon": parse_bool(key_features.get("allow_coupon", True)),
            "risk_level": key_features.get("risk_level", "low"),
            "push_frequency_limit_reached": parse_bool(key_features.get("push_frequency_limit_reached")),
        }
        return {
            "realtime_features": realtime,
            "session_features": session,
            "user_profile_features": profile,
            "history_features": history,
            "transaction_features": transaction,
            "guardrails": guardrails,
        }


class SceneClassifier:
    def classify(self, features: dict[str, Any], memory: dict[str, Any]) -> str:
        r = features["realtime_features"]
        s = features["session_features"]
        p = features["user_profile_features"]
        h = features["history_features"]
        t = features["transaction_features"]

        level_id = r.get("current_level_id")
        if str(r.get("current_game_variant")) == "standard" and str(level_id) == "2" and (
            s["fail_count_session"] >= 1 or str(r.get("current_exit_point")) == "2"
        ):
            return "level_2_block"
        if s["fail_count_session"] >= 2:
            return "continuous_failure"
        if r.get("tool_timeout_flag") or (
            p.get("device_os") == "Android"
            and r.get("page_load_time_ms") is not None
            and int(r["page_load_time_ms"]) >= 3000
        ):
            return "android_perf_risk"
        if t.get("add_to_cart_without_order_flag"):
            return "cart_without_order"
        if h.get("is_new_game_user") and r.get("trigger_event_name") == "game_start":
            return "new_user_first_game"
        return "no_action"


class Guardrail:
    def check(self, features: dict[str, Any], memory: dict[str, Any]) -> dict[str, Any]:
        session = features["session_features"]
        guardrails = features["guardrails"]
        if session["intervention_count_session"] >= guardrails["max_intervention_per_session"]:
            return {"allowed": False, "reason": "session_frequency_limit", "allowed_actions": []}
        cooldown_until = memory.get("intervention_cooldown_until")
        if cooldown_until == "future":
            return {"allowed": False, "reason": "memory_cooldown", "allowed_actions": []}
        if guardrails.get("risk_level") == "high":
            return {"allowed": False, "reason": "high_risk", "allowed_actions": ["show_static_hint"]}

        allowed_actions = [
            "show_tutorial",
            "switch_guided_mode",
            "reduce_difficulty",
            "show_static_hint",
            "show_perf_tip",
            "reduce_animation",
            "explain_coin_value",
            "show_recommendation",
        ]
        if guardrails.get("allow_coin_compensation"):
            allowed_actions.append("grant_coin_compensation")
        if guardrails.get("allow_coupon"):
            allowed_actions.extend(["issue_coupon", "coupon_reminder"])
        if not guardrails.get("push_frequency_limit_reached"):
            allowed_actions.append("send_push")
        return {"allowed": True, "reason": "ok", "allowed_actions": allowed_actions}


class Planner:
    def plan(self, scene_type: str, features: dict[str, Any], memory: dict[str, Any], guardrail: dict[str, Any]) -> dict[str, Any]:
        decision_id = f"dec_{uuid.uuid4().hex[:12]}"
        if not guardrail["allowed"]:
            return {
                "decision_id": decision_id,
                "scene_type": scene_type,
                "decision_status": "no_action",
                "confidence": 0.0,
                "plan": [],
                "fallback_action": "show_static_hint",
                "memory_update": {},
                "eval_tags": [guardrail["reason"]],
            }

        session = features["session_features"]
        realtime = features["realtime_features"]
        plan: list[dict[str, Any]] = []
        memory_update: dict[str, Any] = {}
        confidence = 0.85

        def add(step: int, action_type: str, tool_name: str, params: dict[str, Any]) -> None:
            if action_type in guardrail["allowed_actions"]:
                plan.append({"step": step, "action_type": action_type, "tool_name": tool_name, "params": params})

        if scene_type == "level_2_block":
            if not session["tutorial_shown_session"]:
                add(1, "show_tutorial", "tutorial_service.show", {"level_id": 2, "tutorial_type": "level_hint"})
            if not session["guided_mode_switched_session"]:
                add(len(plan) + 1, "switch_guided_mode", "guided_mode_service.switch", {"target_game_variant": "guided_mode"})
            add(len(plan) + 1, "reduce_difficulty", "difficulty_service.reduce", {"level_id": 2, "difficulty_delta": -1})
            memory_update = {"historical_fail_level": [2], "preferred_game_variant": "guided_mode"}
        elif scene_type == "continuous_failure":
            if not session["tutorial_shown_session"]:
                add(1, "show_tutorial", "tutorial_service.show", {"level_id": realtime.get("current_level_id"), "tutorial_type": "level_hint"})
            else:
                add(1, "switch_guided_mode", "guided_mode_service.switch", {"target_game_variant": "guided_mode"})
            if "grant_coin_compensation" in guardrail["allowed_actions"]:
                add(len(plan) + 1, "grant_coin_compensation", "coin_service.grant", {"coin_amount": 10, "reason": "continuous_failure"})
            memory_update = {"historical_fail_level": [realtime.get("current_level_id")]}
        elif scene_type == "android_perf_risk":
            add(1, "show_perf_tip", "content_service.render_perf_tip", {"device_os": "Android"})
            add(2, "reduce_animation", "performance_service.reduce_animation", {"level": "safe"})
            memory_update = {"last_intervention_feedback": "android_perf_risk_detected"}
        elif scene_type == "cart_without_order":
            add(1, "explain_coin_value", "content_service.render_coin_value", {"source": "cart"})
            if features["transaction_features"]["coupon_available_count"] > 0:
                add(2, "coupon_reminder", "coupon_service.remind", {"coupon_count": features["transaction_features"]["coupon_available_count"]})
            add(len(plan) + 1, "show_recommendation", "recommendation_service.show", {"strategy": "cart_related"})
            memory_update = {"last_intervention_feedback": "cart_without_order"}
        elif scene_type == "new_user_first_game":
            add(1, "show_tutorial", "tutorial_service.show", {"tutorial_type": "new_user"})
            memory_update = {"preferred_game_variant": "guided_mode"}
        else:
            confidence = 0.2

        decision_status = "success" if plan else "no_action"
        return {
            "decision_id": decision_id,
            "scene_type": scene_type,
            "decision_status": decision_status,
            "confidence": confidence,
            "plan": plan[:5],
            "fallback_action": "show_static_hint",
            "memory_update": memory_update,
            "eval_tags": [scene_type],
        }


class PlanValidator:
    REGISTERED_TOOLS = {
        "tutorial_service.show",
        "guided_mode_service.switch",
        "difficulty_service.reduce",
        "coin_service.grant",
        "content_service.render_perf_tip",
        "performance_service.reduce_animation",
        "content_service.render_coin_value",
        "coupon_service.remind",
        "recommendation_service.show",
    }

    def validate(self, decision: dict[str, Any], guardrail: dict[str, Any]) -> dict[str, Any]:
        if len(decision.get("plan", [])) > 5:
            decision["plan"] = decision["plan"][:5]
        for action in decision.get("plan", []):
            if action.get("tool_name") not in self.REGISTERED_TOOLS:
                return self._fallback(decision, "unregistered_tool")
            if action.get("action_type") not in guardrail.get("allowed_actions", []):
                return self._fallback(decision, "guardrail_rejected_action")
        return decision

    def _fallback(self, decision: dict[str, Any], reason: str) -> dict[str, Any]:
        decision = decision.copy()
        decision.update(
            {
                "decision_status": "fallback",
                "plan": [],
                "fallback_action": "show_static_hint",
                "error_code": reason,
            }
        )
        return decision


class ToolExecutor:
    def execute(self, request_id: str, decision: dict[str, Any], key_features: dict[str, Any]) -> list[dict[str, Any]]:
        results = []
        forced_timeout = parse_bool(key_features.get("tutorial_service_timeout")) or parse_bool(key_features.get("tool_timeout_flag"))
        for action in decision.get("plan", []):
            started = time.perf_counter()
            status = "success"
            error_code = None
            if forced_timeout and action["tool_name"] == "tutorial_service.show":
                status = "timeout"
                error_code = "mock_timeout"
            latency_ms = int((time.perf_counter() - started) * 1000)
            results.append(
                {
                    "request_id": request_id,
                    "decision_id": decision["decision_id"],
                    "tool_name": action["tool_name"],
                    "action_type": action["action_type"],
                    "status": status,
                    "latency_ms": latency_ms,
                    "retry_count": 1 if status == "timeout" else 0,
                    "error_code": error_code,
                }
            )
        return results


class AgentWorkflow:
    def __init__(self) -> None:
        self.feature_builder = FeatureBuilder()
        self.memory_store = MemoryStore()
        self.eval_logger = EvalLogger()
        self.guardrail = Guardrail()
        self.classifier = SceneClassifier()
        self.planner = Planner()
        self.validator = PlanValidator()
        self.tool_executor = ToolExecutor()

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_id = payload.get("request_id") or f"req_{uuid.uuid4().hex[:12]}"
        user_id = payload.get("user_id", "mock_user")
        session_id = payload.get("session_id", "mock_session")
        trigger_event = payload.get("trigger_event", {})
        key_features = payload.get("key_features", {})

        features = self.feature_builder.build(trigger_event, key_features)
        memory = self.memory_store.read(user_id, session_id)
        guardrail_result = self.guardrail.check(features, memory)
        scene_type = self.classifier.classify(features, memory)
        decision = self.planner.plan(scene_type, features, memory, guardrail_result)
        decision = self.validator.validate(decision, guardrail_result)
        if parse_bool(key_features.get("tool_timeout_flag")):
            decision["decision_status"] = "fallback"
            decision["plan"] = []
            decision["fallback_action"] = "show_static_hint"
            decision["error_code"] = "upstream_tool_timeout"
        tool_results = self.tool_executor.execute(request_id, decision, key_features)

        if any(row["status"] in {"timeout", "failed"} for row in tool_results):
            decision["decision_status"] = "fallback"
            decision["fallback_action"] = "show_static_hint"
            decision.setdefault("error_code", "tool_execution_failed")

        memory_result = self.memory_store.write(user_id, decision.get("memory_update", {}))
        response = {
            "request_id": request_id,
            "user_id": user_id,
            "session_id": session_id,
            "features": features,
            "guardrail_result": guardrail_result,
            "decision": decision,
            "tool_results": tool_results,
            "memory_write_result": memory_result,
            "created_at": now_iso(),
        }
        self.eval_logger.write(response)
        return response
