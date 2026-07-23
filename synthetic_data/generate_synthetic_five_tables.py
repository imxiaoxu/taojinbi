#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate schema-compatible synthetic five-table data for local Agent/A-B testing.

The generator creates new synthetic users only. Outcome differences are configurable
assumptions for pipeline tests and must never be presented as observed Taobao effects.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path


SEED = 20260716
GROUPS = ("holdout", "fixed_rule", "agent")

# Explicit simulation assumptions, designed to make a three-arm test pipeline observable.
CONFIG = {
    "level_2_start_rate": 0.75,
    "level_2_final_pass_rate": {"holdout": 0.4915, "fixed_rule": 0.5400, "agent": 0.5650},
    "game_completion_rate": {"holdout": 0.2925, "fixed_rule": 0.3600, "agent": 0.4100},
    "order_7d_rate": {"holdout": 0.1100, "fixed_rule": 0.1180, "agent": 0.1250},
    "add_to_cart_7d_rate": {"holdout": 0.2200, "fixed_rule": 0.2240, "agent": 0.2280},
    "retention_7d_rate": {"holdout": 0.3375, "fixed_rule": 0.3700, "agent": 0.3950},
}


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def chance(rng: random.Random, p: float) -> bool:
    return rng.random() < p


def iso_date(base: datetime, offset: int) -> str:
    return (base + timedelta(days=offset)).strftime("%Y-%m-%d")


def event_time(base: datetime, minutes: int) -> str:
    return (base + timedelta(minutes=minutes)).strftime("%Y/%m/%d %H:%M")


def game_time(base: datetime, seconds: int) -> str:
    return (base + timedelta(seconds=seconds)).strftime("%Y-%m-%d %H:%M:%S")


def build_user_profile(rng: random.Random, user_id: str) -> dict[str, object]:
    birth_year = rng.randint(1970, 2005)
    level = rng.choices(["L1", "L2", "L3", "L4", "L5"], weights=[24, 27, 24, 16, 9])[0]
    city = rng.choices([1, 2, 3, 4, 5], weights=[18, 24, 25, 20, 13])[0]
    order_count = max(0, int(rng.gauss({"L1": 8, "L2": 18, "L3": 32, "L4": 58, "L5": 100}[level], 8)))
    spend = max(0.0, round(order_count * rng.uniform(45, 120), 2))
    return {
        "uid": user_id, "sex": rng.choice(["F", "M", "Unknown"]), "birth_year": birth_year,
        "membership_level": level, "reg_date": iso_date(datetime(2015, 1, 1), rng.randint(0, 3500)),
        "is_88vip": int(level in {"L4", "L5"} and chance(rng, 0.35)), "family_account": int(chance(rng, 0.15)),
        "bindkeep_phone": 1, "bindkeep_alipay": 1, "bindkeep_bank": int(chance(rng, 0.85)),
        "default_payment": rng.choice(["alipay_balance", "credit_card", "debit_card"]),
        "lifetime_order_count": order_count, "lifetime_order_amount": spend,
        "avg_monthly_spend_6m": round(spend / 6, 2), "last_618_order_amount": round(rng.uniform(0, 500), 2),
        "last_double11_order_amount": round(rng.uniform(0, 800), 2),
        "coupon_used_count_90d": rng.randint(0, 6), "coupon_total_count_90d": rng.randint(1, 12),
        "category_preference_1": rng.choice(["美妆", "服饰", "家居", "图书", "数码"]),
        "category_preference_2": rng.choice(["服饰", "食品", "母婴", "运动", "家电"]),
        "city_tier": city, "province": rng.choice(["江苏", "浙江", "广东", "上海", "北京", "其他"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="synthetic_five_tables")
    parser.add_argument("--users-per-group", type=int, default=2700)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    if args.users_per_group < 100:
        raise ValueError("users-per-group must be at least 100")
    rng = random.Random(args.seed)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    base = datetime(2026, 6, 1, 9, 0)
    exposure_rows: list[dict[str, object]] = []
    profile_rows: list[dict[str, object]] = []
    event_rows: list[dict[str, object]] = []
    game_rows: list[dict[str, object]] = []
    intervention_rows: list[dict[str, object]] = []
    audit: Counter[str] = Counter()

    user_index = 0
    for group in GROUPS:
        for _ in range(args.users_per_group):
            user_index += 1
            user_id = f"sim_u_{user_index:08d}"
            session_id = f"sim_s_{user_index:08d}"
            game_session_id = f"sim_gs_{user_index:08d}"
            current = base + timedelta(minutes=user_index * 3)
            is_new = chance(rng, 0.42)
            device_os = rng.choice(["Android", "iOS"])
            device = rng.choice(["iPhone 14", "iPhone 13", "Xiaomi 14", "HUAWEI P60", "OPPO Reno"])
            page_load_ms = rng.randint(3300, 4600) if device_os == "Android" and chance(rng, 0.16) else rng.randint(400, 2600)
            profile_rows.append(build_user_profile(rng, user_id))
            exposure_rows.append({
                "user_id": user_id, "ab_test_group": group, "first_exposure_date": current.strftime("%Y-%m-%d"),
                "total_exposure_days": rng.randint(7, 28), "exposure_sessions": rng.randint(2, 16),
                "version_build": "agent-sim-1.0", "assignment_date": current.strftime("%Y-%m-%d"),
            })
            # Outer app / transaction events retain the original event_log schema.
            event_rows.append({"user_id": user_id, "event_timestamp": event_time(current, 0), "event_type": "app_open", "event_detail": "{}", "device_model": device, "page_load_time_ms": page_load_ms, "session_id": session_id, "network_type": rng.choice(["wifi", "4g", "5g"])})
            event_rows.append({"user_id": user_id, "event_timestamp": event_time(current, 1), "event_type": "coin_page_view", "event_detail": "{\"source\":\"home\"}", "device_model": device, "page_load_time_ms": "", "session_id": session_id, "network_type": "wifi"})
            event_rows.append({"user_id": user_id, "event_timestamp": event_time(current, 2), "event_type": "game_start", "event_detail": "{\"game_type\":\"jump\"}", "device_model": device, "page_load_time_ms": "", "session_id": session_id, "network_type": "wifi"})
            if chance(rng, 0.72):
                event_rows.append({"user_id": user_id, "event_timestamp": event_time(current, 8), "event_type": "product_view", "event_detail": "{\"source\":\"coin_game\"}", "device_model": device, "page_load_time_ms": "", "session_id": session_id, "network_type": "wifi"})
            if chance(rng, CONFIG["add_to_cart_7d_rate"][group]):
                event_rows.append({"user_id": user_id, "event_timestamp": event_time(current, 11), "event_type": "add_to_cart", "event_detail": "{\"item_id\":\"sim_item\"}", "device_model": device, "page_load_time_ms": "", "session_id": session_id, "network_type": "wifi"})
            if chance(rng, CONFIG["order_7d_rate"][group]):
                event_rows.append({"user_id": user_id, "event_timestamp": event_time(current + timedelta(days=rng.randint(0, 6)), 20), "event_type": "order_placed", "event_detail": "{\"order_id\":\"sim_order\"}", "device_model": device, "page_load_time_ms": "", "session_id": session_id, "network_type": "wifi"})

            # Internal game funnel. The treatment effect is intentionally controlled by CONFIG.
            retention_7d = int(chance(rng, CONFIG["retention_7d_rate"][group]))
            retention_14d = int(retention_7d and chance(rng, 0.78))
            intervention_type = "no_intervention" if group == "holdout" else ("tutorial_popup" if group == "fixed_rule" else "game_difficulty_reduced")
            intervention_rows.append({"participant_id": user_id, "intervention_type": intervention_type, "intervention_date": current.strftime("%Y-%m-%d"), "pre_order_rate_7d": 0.08, "post_order_rate_7d": round(CONFIG["order_7d_rate"][group], 4), "pre_game_completion_rate": 0.31, "post_game_completion_rate": round(CONFIG["game_completion_rate"][group], 4), "pre_active_days_7d": 3, "post_active_days_7d": 4 if group != "holdout" else 3, "responded": int(group != "holdout" and chance(rng, 0.65)), "retention_7d": retention_7d, "user_segment": "new" if is_new else "general", "device_os": device_os.lower()})
            game_rows.append({"user_id": user_id, "session_id": game_session_id, "event_timestamp": game_time(current, 0), "event_type": "game_start", "level_id": "", "attempt_number": "", "time_spent_seconds": "", "exit_point": "", "is_new_user": int(is_new), "game_variant": "standard", "retention_7d": retention_7d, "retention_14d": retention_14d})
            rules_viewed = chance(rng, 0.34)
            if rules_viewed:
                game_rows.append({"user_id": user_id, "session_id": game_session_id, "event_timestamp": game_time(current, 8), "event_type": "rule_view", "level_id": "", "attempt_number": "", "time_spent_seconds": 8, "exit_point": "", "is_new_user": int(is_new), "game_variant": "standard", "retention_7d": retention_7d, "retention_14d": retention_14d})
            game_rows.append({"user_id": user_id, "session_id": game_session_id, "event_timestamp": game_time(current, 15), "event_type": "level_start", "level_id": 1, "attempt_number": 1, "time_spent_seconds": "", "exit_point": "", "is_new_user": int(is_new), "game_variant": "standard", "retention_7d": retention_7d, "retention_14d": retention_14d})
            if not chance(rng, 0.75):
                game_rows.append({"user_id": user_id, "session_id": game_session_id, "event_timestamp": game_time(current, 45), "event_type": "level_fail", "level_id": 1, "attempt_number": 1, "time_spent_seconds": 30, "exit_point": "", "is_new_user": int(is_new), "game_variant": "standard", "retention_7d": retention_7d, "retention_14d": retention_14d})
                if chance(rng, 0.42):
                    game_rows.append({"user_id": user_id, "session_id": game_session_id, "event_timestamp": game_time(current, 48), "event_type": "level_start", "level_id": 1, "attempt_number": 2, "time_spent_seconds": "", "exit_point": "", "is_new_user": int(is_new), "game_variant": "standard", "retention_7d": retention_7d, "retention_14d": retention_14d})
                    game_rows.append({"user_id": user_id, "session_id": game_session_id, "event_timestamp": game_time(current, 76), "event_type": "level_fail", "level_id": 1, "attempt_number": 2, "time_spent_seconds": 28, "exit_point": "", "is_new_user": int(is_new), "game_variant": "standard", "retention_7d": retention_7d, "retention_14d": retention_14d})
                game_rows.append({"user_id": user_id, "session_id": game_session_id, "event_timestamp": game_time(current, 80), "event_type": "game_exit", "level_id": "", "attempt_number": "", "time_spent_seconds": "", "exit_point": 1, "is_new_user": int(is_new), "game_variant": "standard", "retention_7d": retention_7d, "retention_14d": retention_14d})
                continue
            game_rows.append({"user_id": user_id, "session_id": game_session_id, "event_timestamp": game_time(current, 45), "event_type": "level_complete", "level_id": 1, "attempt_number": 1, "time_spent_seconds": 30, "exit_point": "", "is_new_user": int(is_new), "game_variant": "standard", "retention_7d": retention_7d, "retention_14d": retention_14d})
            game_rows.append({"user_id": user_id, "session_id": game_session_id, "event_timestamp": game_time(current, 50), "event_type": "level_start", "level_id": 2, "attempt_number": 1, "time_spent_seconds": "", "exit_point": "", "is_new_user": int(is_new), "game_variant": "standard", "retention_7d": retention_7d, "retention_14d": retention_14d})
            audit[f"level2_start_{group}"] += 1
            passed_l2 = chance(rng, CONFIG["level_2_final_pass_rate"][group])
            if passed_l2:
                attempt = 1 if chance(rng, 0.65) else 2
                if attempt == 2:
                    game_rows.append({"user_id": user_id, "session_id": game_session_id, "event_timestamp": game_time(current, 78), "event_type": "level_fail", "level_id": 2, "attempt_number": 1, "time_spent_seconds": 28, "exit_point": "", "is_new_user": int(is_new), "game_variant": "standard", "retention_7d": retention_7d, "retention_14d": retention_14d})
                game_rows.append({"user_id": user_id, "session_id": game_session_id, "event_timestamp": game_time(current, 105), "event_type": "level_complete", "level_id": 2, "attempt_number": attempt, "time_spent_seconds": 27, "exit_point": "", "is_new_user": int(is_new), "game_variant": "standard", "retention_7d": retention_7d, "retention_14d": retention_14d})
                audit[f"level2_pass_{group}"] += 1
                completed_game = chance(rng, CONFIG["game_completion_rate"][group] / CONFIG["level_2_final_pass_rate"][group])
                if completed_game:
                    game_rows.append({"user_id": user_id, "session_id": game_session_id, "event_timestamp": game_time(current, 145), "event_type": "level_complete", "level_id": 3, "attempt_number": 1, "time_spent_seconds": 35, "exit_point": "", "is_new_user": int(is_new), "game_variant": "standard", "retention_7d": retention_7d, "retention_14d": retention_14d})
                    game_rows.append({"user_id": user_id, "session_id": game_session_id, "event_timestamp": game_time(current, 150), "event_type": "game_complete", "level_id": "", "attempt_number": "", "time_spent_seconds": "", "exit_point": "", "is_new_user": int(is_new), "game_variant": "standard", "retention_7d": retention_7d, "retention_14d": retention_14d})
                else:
                    game_rows.append({"user_id": user_id, "session_id": game_session_id, "event_timestamp": game_time(current, 150), "event_type": "game_exit", "level_id": "", "attempt_number": "", "time_spent_seconds": "", "exit_point": 3, "is_new_user": int(is_new), "game_variant": "standard", "retention_7d": retention_7d, "retention_14d": retention_14d})
            else:
                game_rows.append({"user_id": user_id, "session_id": game_session_id, "event_timestamp": game_time(current, 80), "event_type": "level_fail", "level_id": 2, "attempt_number": 1, "time_spent_seconds": 30, "exit_point": "", "is_new_user": int(is_new), "game_variant": "standard", "retention_7d": retention_7d, "retention_14d": retention_14d})
                game_rows.append({"user_id": user_id, "session_id": game_session_id, "event_timestamp": game_time(current, 83), "event_type": "game_exit", "level_id": "", "attempt_number": "", "time_spent_seconds": "", "exit_point": 2, "is_new_user": int(is_new), "game_variant": "standard", "retention_7d": retention_7d, "retention_14d": retention_14d})
                audit[f"level2_exit_{group}"] += 1

    files = {
        "event_log.csv": (["user_id", "event_timestamp", "event_type", "event_detail", "device_model", "page_load_time_ms", "session_id", "network_type"], event_rows),
        "game_behavior_log.csv": (["user_id", "session_id", "event_timestamp", "event_type", "level_id", "attempt_number", "time_spent_seconds", "exit_point", "is_new_user", "game_variant", "retention_7d", "retention_14d"], game_rows),
        "intervention_test.csv": (["participant_id", "intervention_type", "intervention_date", "pre_order_rate_7d", "post_order_rate_7d", "pre_game_completion_rate", "post_game_completion_rate", "pre_active_days_7d", "post_active_days_7d", "responded", "retention_7d", "user_segment", "device_os"], intervention_rows),
        "user_profile.csv": (["uid", "sex", "birth_year", "membership_level", "reg_date", "is_88vip", "family_account", "bindkeep_phone", "bindkeep_alipay", "bindkeep_bank", "default_payment", "lifetime_order_count", "lifetime_order_amount", "avg_monthly_spend_6m", "last_618_order_amount", "last_double11_order_amount", "coupon_used_count_90d", "coupon_total_count_90d", "category_preference_1", "category_preference_2", "city_tier", "province"], profile_rows),
        "version_exposure.csv": (["user_id", "ab_test_group", "first_exposure_date", "total_exposure_days", "exposure_sessions", "version_build", "assignment_date"], exposure_rows),
    }
    for name, (fields, rows) in files.items():
        write_csv(out / name, fields, rows)
    manifest = {
        "purpose": "Synthetic data for local Agent, A/B and dashboard pipeline tests only; not business evidence.",
        "seed": args.seed, "users_per_group": args.users_per_group, "groups": list(GROUPS), "assumptions": CONFIG,
        "row_counts": {name: len(rows) for name, (_, rows) in files.items()}, "audit": dict(audit),
    }
    (out / "synthetic_data_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
