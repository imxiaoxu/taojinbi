#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a transparent offline scenario forecast directly from the five raw CSV tables.

This is not an online causal estimate for the Level 2 Agent. It identifies the historical
Level 2 population and applies separately-estimated PSM-DID intervention effects as
sensitivity scenarios. Outputs are suitable for planning, not launch claims.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from math import ceil, sqrt
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def unique_users(rows: list[dict[str, str]]) -> set[str]:
    return {row["user_id"] for row in rows}


def two_proportion_n(p0: float, absolute_mde: float, alpha_z: float = 2.2414, power_z: float = 0.8416) -> int:
    """Per-arm n, two-sided alpha=.025 and power=.80, equal-size independent groups."""
    p1 = p0 + absolute_mde
    pbar = (p0 + p1) / 2
    numerator = alpha_z * sqrt(2 * pbar * (1 - pbar)) + power_z * sqrt(p0 * (1 - p0) + p1 * (1 - p1))
    return ceil((numerator / absolute_mde) ** 2)


def load_psm_effects(path: Path) -> dict[tuple[str, str], dict[str, float]]:
    effects: dict[tuple[str, str], dict[str, float]] = {}
    for row in read_csv(path):
        effects[(row["intervention_type"], row["outcome"])] = {
            "effect": float(row["psm_did_effect"]),
            "ci_low": float(row["ci_low"]),
            "ci_high": float(row["ci_high"]),
        }
    return effects


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--effects-csv",
        default=str(Path(__file__).resolve().parents[1] / "support" / "intervention_psm_did_results.csv"),
    )
    args = parser.parse_args()
    data_dir = Path(args.data_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    game = read_csv(data_dir / "game_behavior_log.csv")
    # Read all five tables to record dataset availability and project linkage context.
    source_files = [
        "event_log.csv", "game_behavior_log.csv", "intervention_test.csv", "user_profile.csv", "version_exposure.csv",
    ]
    source_counts = {name: len(read_csv(data_dir / name)) for name in source_files}
    effects = load_psm_effects(Path(args.effects_csv))

    l2_starts = [r for r in game if r["event_type"] == "level_start" and r["game_variant"] == "standard" and r["level_id"] == "2"]
    l2_completes = [r for r in game if r["event_type"] == "level_complete" and r["game_variant"] == "standard" and r["level_id"] == "2"]
    l2_first_fails = [r for r in game if r["event_type"] == "level_fail" and r["game_variant"] == "standard" and r["level_id"] == "2"]
    l2_repeat_fails = [r for r in l2_first_fails if int(r["attempt_number"] or 0) >= 2]
    l2_exits = [r for r in game if r["event_type"] == "game_exit" and r["game_variant"] == "standard" and r["exit_point"] == "2"]

    start_users = unique_users(l2_starts)
    complete_users = unique_users(l2_completes)
    first_fail_users = unique_users(l2_first_fails)
    repeat_fail_users = unique_users(l2_repeat_fails)
    exit_users = unique_users(l2_exits)
    baseline = len(complete_users) / len(start_users)

    scenarios = [
        ("tutorial_popup", "game_completion_rate", "首次 Level 2 失败后教程", len(first_fail_users)),
        ("game_difficulty_reduced", "game_completion_rate", "首次 Level 2 失败后降难度", len(first_fail_users)),
        ("tutorial_popup", "game_completion_rate", "第二次及以上失败后教程", len(repeat_fail_users)),
        ("game_difficulty_reduced", "game_completion_rate", "第二次及以上失败后降难度", len(repeat_fail_users)),
    ]

    result_rows: list[dict[str, object]] = []
    for intervention, outcome, population, eligible_n in scenarios:
        effect = effects[(intervention, outcome)]
        result_rows.append({
            "scenario": population,
            "intervention_effect_source": intervention,
            "eligible_users_historical_window": eligible_n,
            "effect_pp": round(effect["effect"] * 100, 2),
            "effect_ci_low_pp": round(effect["ci_low"] * 100, 2),
            "effect_ci_high_pp": round(effect["ci_high"] * 100, 2),
            "expected_incremental_game_completers_low": round(eligible_n * effect["ci_low"], 1),
            "expected_incremental_game_completers_central": round(eligible_n * effect["effect"], 1),
            "expected_incremental_game_completers_high": round(eligible_n * effect["ci_high"], 1),
        })

    # A deliberately separate, indirect translation for the observed immediate exit population.
    difficulty = effects[("game_difficulty_reduced", "game_completion_rate")]
    exit_translation = {
        "scenario": "观察到的 Level 2 立即退出用户（仅作间接换算）",
        "intervention_effect_source": "game_difficulty_reduced",
        "eligible_users_historical_window": len(exit_users),
        "effect_pp": round(difficulty["effect"] * 100, 2),
        "effect_ci_low_pp": round(difficulty["ci_low"] * 100, 2),
        "effect_ci_high_pp": round(difficulty["ci_high"] * 100, 2),
        "expected_incremental_game_completers_low": round(len(exit_users) * difficulty["ci_low"], 1),
        "expected_incremental_game_completers_central": round(len(exit_users) * difficulty["effect"], 1),
        "expected_incremental_game_completers_high": round(len(exit_users) * difficulty["ci_high"], 1),
    }
    result_rows.append(exit_translation)

    forecast_csv = out_dir / "level2_agent_forecast.csv"
    with forecast_csv.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(result_rows[0].keys()))
        writer.writeheader()
        writer.writerows(result_rows)

    sample_rows = []
    for mde in (0.03, 0.05, 0.08):
        per_arm = two_proportion_n(baseline, mde)
        sample_rows.append({"mde_pp": int(mde * 100), "per_arm_n": per_arm, "three_arm_total_n": per_arm * 3})
    sample_csv = out_dir / "level2_sample_size.csv"
    with sample_csv.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(sample_rows[0].keys()))
        writer.writeheader()
        writer.writerows(sample_rows)

    report = f"""# Level 2 Agent 离线挽回预测\n\n## 一、历史目标人群\n\n- 五表原始记录行数：{source_counts}\n- `standard` Level 2 启动用户：{len(start_users)}\n- `standard` Level 2 完成用户：{len(complete_users)}\n- 历史基线通过率：{baseline:.2%}\n- `standard` Level 2 至少一次失败用户：{len(first_fail_users)}\n- `standard` Level 2 第二次及以上失败用户：{len(repeat_fail_users)}\n- `standard` Level 2 退出用户：{len(exit_users)}\n\n## 二、情景估算\n\n预测明细见 `level2_agent_forecast.csv`。以首次 Level 2 失败的 {len(first_fail_users)} 名用户为例：\n\n- 使用 `tutorial_popup` 的历史 PSM-DID 游戏完成效应 `+{effects[('tutorial_popup', 'game_completion_rate')]['effect'] * 100:.2f}pp`，对应预计新增完成约 **{len(first_fail_users) * effects[('tutorial_popup', 'game_completion_rate')]['effect']:.1f} 人**。\n- 使用 `game_difficulty_reduced` 的历史 PSM-DID 游戏完成效应 `+{difficulty['effect'] * 100:.2f}pp`，对应预计新增完成约 **{len(first_fail_users) * difficulty['effect']:.1f} 人**。\n- 对已经发生的 {len(exit_users)} 名 Level 2 退出用户，若仅将降难度效应作间接换算，则同一历史窗口约为 **{len(exit_users) * difficulty['ci_low']:.1f} 至 {len(exit_users) * difficulty['ci_high']:.1f} 名**潜在可挽回完成用户，中心估计 **{len(exit_users) * difficulty['effect']:.1f} 名**。\n\n## 三、解释边界\n\n1. 上述数字是“干预效应 x 历史可触达人群”的**情景规划值**，不是已证明的 Agent 线上收益。\n2. `intervention_test.csv` 的 PSM-DID 对象是历史干预用户，并非 `standard` Level 2 失败用户；外推需要由新 A/B 验证。\n3. 教程、切换 Guided Mode、降难度在 Agent 计划中不可将 uplift 相加，否则会重复计量。首期应把它们作为不同策略臂或由 Agent 选择的联合策略，使用整体 Agent vs Holdout 的 ITT 衡量。\n4. 当前原始游戏表仅代表 treatment 内游戏用户，不能从该表推断版本层的因果效果。\n\n## 四、样本量\n\n见 `level2_sample_size.csv`。按历史基线、双主比较 Bonferroni 校正（双侧 alpha=0.025）和 80% power，检测 5pp 提升约需每组 {sample_rows[1]['per_arm_n']} 名完整用户、三组共 {sample_rows[1]['three_arm_total_n']} 名。\n"""
    (out_dir / "level2_agent_forecast.md").write_text(report, encoding="utf-8")

    print(f"Wrote {forecast_csv}")
    print(f"Wrote {sample_csv}")
    print(f"Wrote {out_dir / 'level2_agent_forecast.md'}")


if __name__ == "__main__":
    main()
