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


ROI_ASSUMPTIONS = (
    {
        "scenario": "保守",
        "contribution_margin_per_incremental_order": 5.0,
        "variable_cost_per_eligible_user": 0.8,
    },
    {
        "scenario": "基准",
        "contribution_margin_per_incremental_order": 8.0,
        "variable_cost_per_eligible_user": 0.5,
    },
    {
        "scenario": "积极",
        "contribution_margin_per_incremental_order": 12.0,
        "variable_cost_per_eligible_user": 0.3,
    },
)


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

    roi_rows: list[dict[str, object]] = []
    roi_interventions = (
        ("tutorial_popup", "首次 Level 2 失败后教程"),
        ("game_difficulty_reduced", "首次 Level 2 失败后降难度"),
    )
    for intervention, label in roi_interventions:
        order_effect = effects[(intervention, "order_rate_7d")]
        incremental_orders = len(first_fail_users) * order_effect["effect"]
        for assumption in ROI_ASSUMPTIONS:
            gross_contribution = incremental_orders * assumption["contribution_margin_per_incremental_order"]
            variable_cost = len(first_fail_users) * assumption["variable_cost_per_eligible_user"]
            net_contribution_before_fixed = gross_contribution - variable_cost
            operating_roi = net_contribution_before_fixed / variable_cost if variable_cost else 0.0
            roi_rows.append({
                "strategy": label,
                "intervention_effect_source": intervention,
                "assumption_scenario": assumption["scenario"],
                "eligible_users_historical_window": len(first_fail_users),
                "order_effect_pp": round(order_effect["effect"] * 100, 2),
                "expected_incremental_orders": round(incremental_orders, 1),
                "contribution_margin_per_incremental_order_cny": assumption["contribution_margin_per_incremental_order"],
                "variable_cost_per_eligible_user_cny": assumption["variable_cost_per_eligible_user"],
                "expected_gross_contribution_cny": round(gross_contribution, 1),
                "variable_cost_cny": round(variable_cost, 1),
                "net_contribution_before_fixed_cost_cny": round(net_contribution_before_fixed, 1),
                "operating_roi_before_fixed_cost_pct": round(operating_roi * 100, 1),
                "max_affordable_one_time_fixed_cost_cny": round(max(net_contribution_before_fixed, 0.0), 1),
            })

    roi_csv = out_dir / "level2_agent_roi_scenarios.csv"
    with roi_csv.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(roi_rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(roi_rows)

    roi_base = {
        row["intervention_effect_source"]: row
        for row in roi_rows
        if row["assumption_scenario"] == "基准"
    }
    tutorial_roi = roi_base["tutorial_popup"]
    difficulty_roi = roi_base["game_difficulty_reduced"]

    report = f"""# Level 2 Agent 离线挽回与 ROI 情景预测

## 一、历史目标人群

- 五表原始记录行数：{source_counts}
- `standard` Level 2 启动用户：{len(start_users)}
- `standard` Level 2 完成用户：{len(complete_users)}
- 历史基线通过率：{baseline:.2%}
- `standard` Level 2 至少一次失败用户：{len(first_fail_users)}
- `standard` Level 2 第二次及以上失败用户：{len(repeat_fail_users)}
- `standard` Level 2 退出用户：{len(exit_users)}

## 二、游戏完成挽回情景

预测明细见 `level2_agent_forecast.csv`。以首次 Level 2 失败的 {len(first_fail_users)} 名用户为例：

- 使用 `tutorial_popup` 的历史 PSM-DID 游戏完成效应 `+{effects[('tutorial_popup', 'game_completion_rate')]['effect'] * 100:.2f}pp`，对应预计新增完成约 **{len(first_fail_users) * effects[('tutorial_popup', 'game_completion_rate')]['effect']:.1f} 人**。
- 使用 `game_difficulty_reduced` 的历史 PSM-DID 游戏完成效应 `+{difficulty['effect'] * 100:.2f}pp`，对应预计新增完成约 **{len(first_fail_users) * difficulty['effect']:.1f} 人**。
- 对已经发生的 {len(exit_users)} 名 Level 2 退出用户，若仅将降难度效应作间接换算，则同一历史窗口约为 **{len(exit_users) * difficulty['ci_low']:.1f} 至 {len(exit_users) * difficulty['ci_high']:.1f} 名**潜在可挽回完成用户，中心估计 **{len(exit_users) * difficulty['effect']:.1f} 名**。

## 三、订单与 ROI 情景

订单增量采用 `intervention_test.csv` 的 PSM-DID `order_rate_7d` 效应；金额参数不是原始数据字段，因此使用明确的规划假设并进行敏感性分析。完整明细见 `level2_agent_roi_scenarios.csv`。

计算口径：

```text
预计增量订单 = 历史可触达用户 × PSM-DID order_rate_7d 效应
预计毛贡献 = 预计增量订单 × 单笔增量订单贡献毛利
变动成本 = 历史可触达用户 × 单用户 Agent/工具变动成本
运营 ROI（不含一次性建设成本）=（预计毛贡献 - 变动成本）/ 变动成本
可承受一次性建设成本上限 = max(预计毛贡献 - 变动成本, 0)
```

| 策略 | 历史可触达用户 | 订单效应 | 预计增量订单 | 基准毛贡献 | 基准变动成本 | 基准运营 ROI | 一次性成本盈亏平衡上限 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 首次失败后教程 | {tutorial_roi['eligible_users_historical_window']} | +{tutorial_roi['order_effect_pp']:.2f}pp | {tutorial_roi['expected_incremental_orders']:.1f} | ¥{tutorial_roi['expected_gross_contribution_cny']:.1f} | ¥{tutorial_roi['variable_cost_cny']:.1f} | {tutorial_roi['operating_roi_before_fixed_cost_pct']:.1f}% | ¥{tutorial_roi['max_affordable_one_time_fixed_cost_cny']:.1f} |
| 首次失败后降难度 | {difficulty_roi['eligible_users_historical_window']} | +{difficulty_roi['order_effect_pp']:.2f}pp | {difficulty_roi['expected_incremental_orders']:.1f} | ¥{difficulty_roi['expected_gross_contribution_cny']:.1f} | ¥{difficulty_roi['variable_cost_cny']:.1f} | {difficulty_roi['operating_roi_before_fixed_cost_pct']:.1f}% | ¥{difficulty_roi['max_affordable_one_time_fixed_cost_cny']:.1f} |

基准假设为单笔增量订单贡献毛利 **¥8.00**、单可触达用户 Agent/工具变动成本 **¥0.50**。保守、基准、积极三档分别采用 `¥5.00/¥0.80`、`¥8.00/¥0.50`、`¥12.00/¥0.30`。正式立项时必须用财务确认的贡献毛利、Dify 调用、云资源、运维和业务工具成本替换。

## 四、解释边界

1. 上述数字是“历史干预效应 × 历史可触达人群”的情景规划值，不是已证明的 Agent 线上收益。
2. `intervention_test.csv` 的 PSM-DID 对象是历史干预用户，并非 `standard` Level 2 失败用户；外推需要由新 A/B 验证。
3. 教程、切换 Guided Mode、降难度在 Agent 计划中不可将 uplift 相加，否则会重复计量。
4. 当前 ROI 是不含一次性建设成本的运营 ROI；是否值得建设应比较实际一次性成本与表中的盈亏平衡上限。
5. 当前原始游戏表仅代表 treatment 内游戏用户，不能从该表推断版本层的因果效果。

## 五、样本量

见 `level2_sample_size.csv`。按历史基线、双主比较 Bonferroni 校正（双侧 alpha=0.025）和 80% power，检测 5pp 提升约需每组 {sample_rows[1]['per_arm_n']} 名完整用户、三组共 {sample_rows[1]['three_arm_total_n']} 名。
"""
    (out_dir / "level2_agent_forecast.md").write_text(report, encoding="utf-8")

    print(f"Wrote {forecast_csv}")
    print(f"Wrote {roi_csv}")
    print(f"Wrote {sample_csv}")
    print(f"Wrote {out_dir / 'level2_agent_forecast.md'}")


if __name__ == "__main__":
    main()
