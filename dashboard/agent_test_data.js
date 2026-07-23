window.AGENT_TEST_DATA = {
  "meta": {
    "source": "synthetic_full_agent_replay",
    "generated_at": "2026-07-23T20:39:49+08:00",
    "scope": "8,100 synthetic users; Mock tools only"
  },
  "kpis": [
    {
      "label": "全量评估用户",
      "value": "8,100",
      "desc": "每名合成用户一条最终决策",
      "tone": ""
    },
    {
      "label": "五表来源覆盖率",
      "value": "100.0%",
      "desc": "8,100 / 8,100 用户",
      "tone": "positive"
    },
    {
      "label": "场景判定一致率",
      "value": "100.0%",
      "desc": "独立优先级规则 vs Agent",
      "tone": "positive"
    },
    {
      "label": "工具执行成功率",
      "value": "100.0%",
      "desc": "16,708 / 16,708 次工具调用",
      "tone": "positive"
    }
  ],
  "tree": {
    "title": "Agent V1 场景优先级决策树",
    "root_users": 8100,
    "priority_nodes": [
      {
        "id": "level_2_block",
        "label": "standard + Level 2 + 失败/退出",
        "reached": 8100,
        "yes": 3932,
        "no": 4168,
        "action_counts": {
          "show_tutorial": 3932,
          "switch_guided_mode": 3932,
          "reduce_difficulty": 3932
        }
      },
      {
        "id": "continuous_failure",
        "label": "同一会话失败次数 >= 2",
        "reached": 4168,
        "yes": 864,
        "no": 3304,
        "action_counts": {
          "show_tutorial": 864,
          "grant_coin_compensation": 864
        }
      },
      {
        "id": "android_perf_risk",
        "label": "Android 且加载耗时 >= 3000ms",
        "reached": 3304,
        "yes": 283,
        "no": 3021,
        "action_counts": {
          "show_perf_tip": 283,
          "reduce_animation": 283
        }
      },
      {
        "id": "cart_without_order",
        "label": "7 日加购且未下单",
        "reached": 3021,
        "yes": 594,
        "no": 2427,
        "action_counts": {
          "explain_coin_value": 594,
          "coupon_reminder": 441,
          "show_recommendation": 594
        }
      },
      {
        "id": "new_user_first_game",
        "label": "新用户进入首局",
        "reached": 2427,
        "yes": 989,
        "no": 1438,
        "action_counts": {
          "show_tutorial": 989
        }
      },
      {
        "id": "no_action",
        "label": "不触发干预",
        "reached": 1438,
        "yes": 1438,
        "no": 0,
        "action_counts": {
          "no_action": 1438
        }
      }
    ],
    "scene_counts": {
      "level_2_block": 3932,
      "no_action": 1438,
      "new_user_first_game": 989,
      "cart_without_order": 594,
      "android_perf_risk": 283,
      "continuous_failure": 864
    },
    "action_counts": {
      "show_tutorial": 5785,
      "switch_guided_mode": 3932,
      "reduce_difficulty": 3932,
      "no_action": 1438,
      "explain_coin_value": 594,
      "coupon_reminder": 441,
      "show_recommendation": 594,
      "show_perf_tip": 283,
      "reduce_animation": 283,
      "grant_coin_compensation": 864
    }
  },
  "summary": {
    "generated_at": "2026-07-23T20:39:49+08:00",
    "test_type": "full_synthetic_agent_decision_replay",
    "test_boundary": "Mock Agent and Mock tools only; not a business uplift experiment.",
    "source_directory": "synthetic_data/generated",
    "total_users": 8100,
    "all_five_user_count": 8100,
    "all_five_coverage_rate": 1.0,
    "source_row_counts": {
      "event_log": 32906,
      "game_behavior_log": 52437,
      "intervention_test": 8100,
      "user_profile": 8100,
      "version_exposure": 8100
    },
    "group_counts": {
      "holdout": 2700,
      "fixed_rule": 2700,
      "agent": 2700
    },
    "expected_scene_counts": {
      "level_2_block": 3932,
      "no_action": 1438,
      "new_user_first_game": 989,
      "cart_without_order": 594,
      "android_perf_risk": 283,
      "continuous_failure": 864
    },
    "actual_scene_counts": {
      "level_2_block": 3932,
      "no_action": 1438,
      "new_user_first_game": 989,
      "cart_without_order": 594,
      "android_perf_risk": 283,
      "continuous_failure": 864
    },
    "scene_match_count": 8100,
    "scene_match_rate": 1.0,
    "decision_status_counts": {
      "success": 6662,
      "no_action": 1438
    },
    "action_counts": {
      "show_tutorial": 5785,
      "switch_guided_mode": 3932,
      "reduce_difficulty": 3932,
      "no_action": 1438,
      "explain_coin_value": 594,
      "coupon_reminder": 441,
      "show_recommendation": 594,
      "show_perf_tip": 283,
      "reduce_animation": 283,
      "grant_coin_compensation": 864
    },
    "tool_execution_count": 16708,
    "tool_success_count": 16708,
    "tool_success_rate": 1.0,
    "tool_status_counts": {
      "success": 16708
    },
    "invalid_action_count": 0,
    "duplicate_action_decision_count": 0,
    "passed": true
  },
  "group_scene_breakdown": [
    {
      "group": "holdout",
      "scene": "level_2_block",
      "users": 1382
    },
    {
      "group": "holdout",
      "scene": "continuous_failure",
      "users": 291
    },
    {
      "group": "holdout",
      "scene": "android_perf_risk",
      "users": 84
    },
    {
      "group": "holdout",
      "scene": "cart_without_order",
      "users": 192
    },
    {
      "group": "holdout",
      "scene": "new_user_first_game",
      "users": 304
    },
    {
      "group": "holdout",
      "scene": "no_action",
      "users": 447
    },
    {
      "group": "fixed_rule",
      "scene": "level_2_block",
      "users": 1264
    },
    {
      "group": "fixed_rule",
      "scene": "continuous_failure",
      "users": 297
    },
    {
      "group": "fixed_rule",
      "scene": "android_perf_risk",
      "users": 103
    },
    {
      "group": "fixed_rule",
      "scene": "cart_without_order",
      "users": 204
    },
    {
      "group": "fixed_rule",
      "scene": "new_user_first_game",
      "users": 337
    },
    {
      "group": "fixed_rule",
      "scene": "no_action",
      "users": 495
    },
    {
      "group": "agent",
      "scene": "level_2_block",
      "users": 1286
    },
    {
      "group": "agent",
      "scene": "continuous_failure",
      "users": 276
    },
    {
      "group": "agent",
      "scene": "android_perf_risk",
      "users": 96
    },
    {
      "group": "agent",
      "scene": "cart_without_order",
      "users": 198
    },
    {
      "group": "agent",
      "scene": "new_user_first_game",
      "users": 348
    },
    {
      "group": "agent",
      "scene": "no_action",
      "users": 496
    }
  ],
  "sample_decisions": [
    {
      "user_id_hash": "u_00554ae1e01f",
      "group": "holdout",
      "scene": "level_2_block",
      "decision_status": "success",
      "actions": "show_tutorial | switch_guided_mode | reduce_difficulty",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_00c9e1c86dd0",
      "group": "holdout",
      "scene": "level_2_block",
      "decision_status": "success",
      "actions": "show_tutorial | switch_guided_mode | reduce_difficulty",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0121943eaa19",
      "group": "holdout",
      "scene": "level_2_block",
      "decision_status": "success",
      "actions": "show_tutorial | switch_guided_mode | reduce_difficulty",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_014ba5631159",
      "group": "holdout",
      "scene": "level_2_block",
      "decision_status": "success",
      "actions": "show_tutorial | switch_guided_mode | reduce_difficulty",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_014c94be913f",
      "group": "holdout",
      "scene": "level_2_block",
      "decision_status": "success",
      "actions": "show_tutorial | switch_guided_mode | reduce_difficulty",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_01b6018d4dbf",
      "group": "holdout",
      "scene": "level_2_block",
      "decision_status": "success",
      "actions": "show_tutorial | switch_guided_mode | reduce_difficulty",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0090130a46e4",
      "group": "holdout",
      "scene": "continuous_failure",
      "decision_status": "success",
      "actions": "show_tutorial | grant_coin_compensation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0135d4c83ff0",
      "group": "holdout",
      "scene": "continuous_failure",
      "decision_status": "success",
      "actions": "show_tutorial | grant_coin_compensation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_021f1684f2d2",
      "group": "holdout",
      "scene": "continuous_failure",
      "decision_status": "success",
      "actions": "show_tutorial | grant_coin_compensation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_05605de1b845",
      "group": "holdout",
      "scene": "continuous_failure",
      "decision_status": "success",
      "actions": "show_tutorial | grant_coin_compensation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0615beef558d",
      "group": "holdout",
      "scene": "continuous_failure",
      "decision_status": "success",
      "actions": "show_tutorial | grant_coin_compensation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_066a8b217d54",
      "group": "holdout",
      "scene": "continuous_failure",
      "decision_status": "success",
      "actions": "show_tutorial | grant_coin_compensation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_01bcde2c07a1",
      "group": "holdout",
      "scene": "android_perf_risk",
      "decision_status": "success",
      "actions": "show_perf_tip | reduce_animation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_053572b2bdae",
      "group": "holdout",
      "scene": "android_perf_risk",
      "decision_status": "success",
      "actions": "show_perf_tip | reduce_animation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_089c5de5409e",
      "group": "holdout",
      "scene": "android_perf_risk",
      "decision_status": "success",
      "actions": "show_perf_tip | reduce_animation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0a074880a129",
      "group": "holdout",
      "scene": "android_perf_risk",
      "decision_status": "success",
      "actions": "show_perf_tip | reduce_animation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0b05b4af7fba",
      "group": "holdout",
      "scene": "android_perf_risk",
      "decision_status": "success",
      "actions": "show_perf_tip | reduce_animation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0ba412ef97a4",
      "group": "holdout",
      "scene": "android_perf_risk",
      "decision_status": "success",
      "actions": "show_perf_tip | reduce_animation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0086a7648ffa",
      "group": "holdout",
      "scene": "cart_without_order",
      "decision_status": "success",
      "actions": "explain_coin_value | coupon_reminder | show_recommendation",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_00ddaa0702fc",
      "group": "holdout",
      "scene": "cart_without_order",
      "decision_status": "success",
      "actions": "explain_coin_value | show_recommendation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_02b77aab1d14",
      "group": "holdout",
      "scene": "cart_without_order",
      "decision_status": "success",
      "actions": "explain_coin_value | coupon_reminder | show_recommendation",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_05196aabb913",
      "group": "holdout",
      "scene": "cart_without_order",
      "decision_status": "success",
      "actions": "explain_coin_value | coupon_reminder | show_recommendation",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_093694f1caa3",
      "group": "holdout",
      "scene": "cart_without_order",
      "decision_status": "success",
      "actions": "explain_coin_value | show_recommendation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_093f293e4eb4",
      "group": "holdout",
      "scene": "cart_without_order",
      "decision_status": "success",
      "actions": "explain_coin_value | coupon_reminder | show_recommendation",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_018b10e7c0b5",
      "group": "holdout",
      "scene": "new_user_first_game",
      "decision_status": "success",
      "actions": "show_tutorial",
      "tool_execution_count": 1,
      "tool_success_count": 1,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_021b5c3d8b51",
      "group": "holdout",
      "scene": "new_user_first_game",
      "decision_status": "success",
      "actions": "show_tutorial",
      "tool_execution_count": 1,
      "tool_success_count": 1,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_048f68f7fc9b",
      "group": "holdout",
      "scene": "new_user_first_game",
      "decision_status": "success",
      "actions": "show_tutorial",
      "tool_execution_count": 1,
      "tool_success_count": 1,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_054ef331a213",
      "group": "holdout",
      "scene": "new_user_first_game",
      "decision_status": "success",
      "actions": "show_tutorial",
      "tool_execution_count": 1,
      "tool_success_count": 1,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_05ad89e2f716",
      "group": "holdout",
      "scene": "new_user_first_game",
      "decision_status": "success",
      "actions": "show_tutorial",
      "tool_execution_count": 1,
      "tool_success_count": 1,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_05f533680052",
      "group": "holdout",
      "scene": "new_user_first_game",
      "decision_status": "success",
      "actions": "show_tutorial",
      "tool_execution_count": 1,
      "tool_success_count": 1,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0025c6995c07",
      "group": "holdout",
      "scene": "no_action",
      "decision_status": "no_action",
      "actions": "no_action",
      "tool_execution_count": 0,
      "tool_success_count": 0,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_02339c3d9ed3",
      "group": "holdout",
      "scene": "no_action",
      "decision_status": "no_action",
      "actions": "no_action",
      "tool_execution_count": 0,
      "tool_success_count": 0,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_023a41680b29",
      "group": "holdout",
      "scene": "no_action",
      "decision_status": "no_action",
      "actions": "no_action",
      "tool_execution_count": 0,
      "tool_success_count": 0,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_04d6ed6096a3",
      "group": "holdout",
      "scene": "no_action",
      "decision_status": "no_action",
      "actions": "no_action",
      "tool_execution_count": 0,
      "tool_success_count": 0,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0548ba831e76",
      "group": "holdout",
      "scene": "no_action",
      "decision_status": "no_action",
      "actions": "no_action",
      "tool_execution_count": 0,
      "tool_success_count": 0,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0566fc0c51f9",
      "group": "holdout",
      "scene": "no_action",
      "decision_status": "no_action",
      "actions": "no_action",
      "tool_execution_count": 0,
      "tool_success_count": 0,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_00297cf15f21",
      "group": "fixed_rule",
      "scene": "level_2_block",
      "decision_status": "success",
      "actions": "show_tutorial | switch_guided_mode | reduce_difficulty",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0045635ba68a",
      "group": "fixed_rule",
      "scene": "level_2_block",
      "decision_status": "success",
      "actions": "show_tutorial | switch_guided_mode | reduce_difficulty",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_004eb9c5fcb0",
      "group": "fixed_rule",
      "scene": "level_2_block",
      "decision_status": "success",
      "actions": "show_tutorial | switch_guided_mode | reduce_difficulty",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0073d9771e89",
      "group": "fixed_rule",
      "scene": "level_2_block",
      "decision_status": "success",
      "actions": "show_tutorial | switch_guided_mode | reduce_difficulty",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0087ee38caa3",
      "group": "fixed_rule",
      "scene": "level_2_block",
      "decision_status": "success",
      "actions": "show_tutorial | switch_guided_mode | reduce_difficulty",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_015dac8d7077",
      "group": "fixed_rule",
      "scene": "level_2_block",
      "decision_status": "success",
      "actions": "show_tutorial | switch_guided_mode | reduce_difficulty",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_00461a92b982",
      "group": "fixed_rule",
      "scene": "continuous_failure",
      "decision_status": "success",
      "actions": "show_tutorial | grant_coin_compensation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0190f02d670e",
      "group": "fixed_rule",
      "scene": "continuous_failure",
      "decision_status": "success",
      "actions": "show_tutorial | grant_coin_compensation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_02244169dddf",
      "group": "fixed_rule",
      "scene": "continuous_failure",
      "decision_status": "success",
      "actions": "show_tutorial | grant_coin_compensation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_02965ad583b0",
      "group": "fixed_rule",
      "scene": "continuous_failure",
      "decision_status": "success",
      "actions": "show_tutorial | grant_coin_compensation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_037ded4bdb24",
      "group": "fixed_rule",
      "scene": "continuous_failure",
      "decision_status": "success",
      "actions": "show_tutorial | grant_coin_compensation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_042f677075a5",
      "group": "fixed_rule",
      "scene": "continuous_failure",
      "decision_status": "success",
      "actions": "show_tutorial | grant_coin_compensation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0057080937eb",
      "group": "fixed_rule",
      "scene": "android_perf_risk",
      "decision_status": "success",
      "actions": "show_perf_tip | reduce_animation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_02b83430ac4b",
      "group": "fixed_rule",
      "scene": "android_perf_risk",
      "decision_status": "success",
      "actions": "show_perf_tip | reduce_animation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0d587f42c6be",
      "group": "fixed_rule",
      "scene": "android_perf_risk",
      "decision_status": "success",
      "actions": "show_perf_tip | reduce_animation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_110e6bd5ce54",
      "group": "fixed_rule",
      "scene": "android_perf_risk",
      "decision_status": "success",
      "actions": "show_perf_tip | reduce_animation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_1358b6fbff31",
      "group": "fixed_rule",
      "scene": "android_perf_risk",
      "decision_status": "success",
      "actions": "show_perf_tip | reduce_animation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_157d8f71edb9",
      "group": "fixed_rule",
      "scene": "android_perf_risk",
      "decision_status": "success",
      "actions": "show_perf_tip | reduce_animation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_01a2a8137cf8",
      "group": "fixed_rule",
      "scene": "cart_without_order",
      "decision_status": "success",
      "actions": "explain_coin_value | coupon_reminder | show_recommendation",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_01d500656218",
      "group": "fixed_rule",
      "scene": "cart_without_order",
      "decision_status": "success",
      "actions": "explain_coin_value | coupon_reminder | show_recommendation",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0374ae882674",
      "group": "fixed_rule",
      "scene": "cart_without_order",
      "decision_status": "success",
      "actions": "explain_coin_value | show_recommendation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_04d6882cf52a",
      "group": "fixed_rule",
      "scene": "cart_without_order",
      "decision_status": "success",
      "actions": "explain_coin_value | show_recommendation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0508edfe0f83",
      "group": "fixed_rule",
      "scene": "cart_without_order",
      "decision_status": "success",
      "actions": "explain_coin_value | coupon_reminder | show_recommendation",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_05a9c0902377",
      "group": "fixed_rule",
      "scene": "cart_without_order",
      "decision_status": "success",
      "actions": "explain_coin_value | coupon_reminder | show_recommendation",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_003653f2ff56",
      "group": "fixed_rule",
      "scene": "new_user_first_game",
      "decision_status": "success",
      "actions": "show_tutorial",
      "tool_execution_count": 1,
      "tool_success_count": 1,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_01e4c8b67e28",
      "group": "fixed_rule",
      "scene": "new_user_first_game",
      "decision_status": "success",
      "actions": "show_tutorial",
      "tool_execution_count": 1,
      "tool_success_count": 1,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_02042be2a87e",
      "group": "fixed_rule",
      "scene": "new_user_first_game",
      "decision_status": "success",
      "actions": "show_tutorial",
      "tool_execution_count": 1,
      "tool_success_count": 1,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_033022e84be5",
      "group": "fixed_rule",
      "scene": "new_user_first_game",
      "decision_status": "success",
      "actions": "show_tutorial",
      "tool_execution_count": 1,
      "tool_success_count": 1,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_03387751ec01",
      "group": "fixed_rule",
      "scene": "new_user_first_game",
      "decision_status": "success",
      "actions": "show_tutorial",
      "tool_execution_count": 1,
      "tool_success_count": 1,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_05029457ed76",
      "group": "fixed_rule",
      "scene": "new_user_first_game",
      "decision_status": "success",
      "actions": "show_tutorial",
      "tool_execution_count": 1,
      "tool_success_count": 1,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0073f48d388a",
      "group": "fixed_rule",
      "scene": "no_action",
      "decision_status": "no_action",
      "actions": "no_action",
      "tool_execution_count": 0,
      "tool_success_count": 0,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_00dbd660f986",
      "group": "fixed_rule",
      "scene": "no_action",
      "decision_status": "no_action",
      "actions": "no_action",
      "tool_execution_count": 0,
      "tool_success_count": 0,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_018f8bfef1da",
      "group": "fixed_rule",
      "scene": "no_action",
      "decision_status": "no_action",
      "actions": "no_action",
      "tool_execution_count": 0,
      "tool_success_count": 0,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_032713f00e4d",
      "group": "fixed_rule",
      "scene": "no_action",
      "decision_status": "no_action",
      "actions": "no_action",
      "tool_execution_count": 0,
      "tool_success_count": 0,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_03767b22b6c1",
      "group": "fixed_rule",
      "scene": "no_action",
      "decision_status": "no_action",
      "actions": "no_action",
      "tool_execution_count": 0,
      "tool_success_count": 0,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0395e7bfd6e1",
      "group": "fixed_rule",
      "scene": "no_action",
      "decision_status": "no_action",
      "actions": "no_action",
      "tool_execution_count": 0,
      "tool_success_count": 0,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0038144c9a47",
      "group": "agent",
      "scene": "level_2_block",
      "decision_status": "success",
      "actions": "show_tutorial | switch_guided_mode | reduce_difficulty",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_00a37f60d4a5",
      "group": "agent",
      "scene": "level_2_block",
      "decision_status": "success",
      "actions": "show_tutorial | switch_guided_mode | reduce_difficulty",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_011bbf380c74",
      "group": "agent",
      "scene": "level_2_block",
      "decision_status": "success",
      "actions": "show_tutorial | switch_guided_mode | reduce_difficulty",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0122538f8fe3",
      "group": "agent",
      "scene": "level_2_block",
      "decision_status": "success",
      "actions": "show_tutorial | switch_guided_mode | reduce_difficulty",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_013d5ec4d0e9",
      "group": "agent",
      "scene": "level_2_block",
      "decision_status": "success",
      "actions": "show_tutorial | switch_guided_mode | reduce_difficulty",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0153e3a73336",
      "group": "agent",
      "scene": "level_2_block",
      "decision_status": "success",
      "actions": "show_tutorial | switch_guided_mode | reduce_difficulty",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_00047e1427a4",
      "group": "agent",
      "scene": "continuous_failure",
      "decision_status": "success",
      "actions": "show_tutorial | grant_coin_compensation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_00cd2a421dba",
      "group": "agent",
      "scene": "continuous_failure",
      "decision_status": "success",
      "actions": "show_tutorial | grant_coin_compensation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_00f33c266d23",
      "group": "agent",
      "scene": "continuous_failure",
      "decision_status": "success",
      "actions": "show_tutorial | grant_coin_compensation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_01442461e090",
      "group": "agent",
      "scene": "continuous_failure",
      "decision_status": "success",
      "actions": "show_tutorial | grant_coin_compensation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_01556b20a221",
      "group": "agent",
      "scene": "continuous_failure",
      "decision_status": "success",
      "actions": "show_tutorial | grant_coin_compensation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_019b16dce4a9",
      "group": "agent",
      "scene": "continuous_failure",
      "decision_status": "success",
      "actions": "show_tutorial | grant_coin_compensation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_03a43f2eeedc",
      "group": "agent",
      "scene": "android_perf_risk",
      "decision_status": "success",
      "actions": "show_perf_tip | reduce_animation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_040369e44d3e",
      "group": "agent",
      "scene": "android_perf_risk",
      "decision_status": "success",
      "actions": "show_perf_tip | reduce_animation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_041a00fc9029",
      "group": "agent",
      "scene": "android_perf_risk",
      "decision_status": "success",
      "actions": "show_perf_tip | reduce_animation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_08c6b0297ca6",
      "group": "agent",
      "scene": "android_perf_risk",
      "decision_status": "success",
      "actions": "show_perf_tip | reduce_animation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_10c8fd5cecac",
      "group": "agent",
      "scene": "android_perf_risk",
      "decision_status": "success",
      "actions": "show_perf_tip | reduce_animation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_130486041d48",
      "group": "agent",
      "scene": "android_perf_risk",
      "decision_status": "success",
      "actions": "show_perf_tip | reduce_animation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_02251f3dd63f",
      "group": "agent",
      "scene": "cart_without_order",
      "decision_status": "success",
      "actions": "explain_coin_value | coupon_reminder | show_recommendation",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0244f23d5ff2",
      "group": "agent",
      "scene": "cart_without_order",
      "decision_status": "success",
      "actions": "explain_coin_value | coupon_reminder | show_recommendation",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_04ab737c13fa",
      "group": "agent",
      "scene": "cart_without_order",
      "decision_status": "success",
      "actions": "explain_coin_value | coupon_reminder | show_recommendation",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_06490a24e56d",
      "group": "agent",
      "scene": "cart_without_order",
      "decision_status": "success",
      "actions": "explain_coin_value | coupon_reminder | show_recommendation",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_06b2c2a88c4a",
      "group": "agent",
      "scene": "cart_without_order",
      "decision_status": "success",
      "actions": "explain_coin_value | coupon_reminder | show_recommendation",
      "tool_execution_count": 3,
      "tool_success_count": 3,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0735b26e2169",
      "group": "agent",
      "scene": "cart_without_order",
      "decision_status": "success",
      "actions": "explain_coin_value | show_recommendation",
      "tool_execution_count": 2,
      "tool_success_count": 2,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0109cd0c9da1",
      "group": "agent",
      "scene": "new_user_first_game",
      "decision_status": "success",
      "actions": "show_tutorial",
      "tool_execution_count": 1,
      "tool_success_count": 1,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_02bc234600a4",
      "group": "agent",
      "scene": "new_user_first_game",
      "decision_status": "success",
      "actions": "show_tutorial",
      "tool_execution_count": 1,
      "tool_success_count": 1,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_06a20a495464",
      "group": "agent",
      "scene": "new_user_first_game",
      "decision_status": "success",
      "actions": "show_tutorial",
      "tool_execution_count": 1,
      "tool_success_count": 1,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_070bc65399ed",
      "group": "agent",
      "scene": "new_user_first_game",
      "decision_status": "success",
      "actions": "show_tutorial",
      "tool_execution_count": 1,
      "tool_success_count": 1,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0784e20084b0",
      "group": "agent",
      "scene": "new_user_first_game",
      "decision_status": "success",
      "actions": "show_tutorial",
      "tool_execution_count": 1,
      "tool_success_count": 1,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_081acf6e26bc",
      "group": "agent",
      "scene": "new_user_first_game",
      "decision_status": "success",
      "actions": "show_tutorial",
      "tool_execution_count": 1,
      "tool_success_count": 1,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_0001730311c3",
      "group": "agent",
      "scene": "no_action",
      "decision_status": "no_action",
      "actions": "no_action",
      "tool_execution_count": 0,
      "tool_success_count": 0,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_00ac666003e2",
      "group": "agent",
      "scene": "no_action",
      "decision_status": "no_action",
      "actions": "no_action",
      "tool_execution_count": 0,
      "tool_success_count": 0,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_00c241b62a53",
      "group": "agent",
      "scene": "no_action",
      "decision_status": "no_action",
      "actions": "no_action",
      "tool_execution_count": 0,
      "tool_success_count": 0,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_01014572e630",
      "group": "agent",
      "scene": "no_action",
      "decision_status": "no_action",
      "actions": "no_action",
      "tool_execution_count": 0,
      "tool_success_count": 0,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_017edcb9659c",
      "group": "agent",
      "scene": "no_action",
      "decision_status": "no_action",
      "actions": "no_action",
      "tool_execution_count": 0,
      "tool_success_count": 0,
      "source_table_count": 5
    },
    {
      "user_id_hash": "u_01a55a5ba7e8",
      "group": "agent",
      "scene": "no_action",
      "decision_status": "no_action",
      "actions": "no_action",
      "tool_execution_count": 0,
      "tool_success_count": 0,
      "source_table_count": 5
    }
  ]
};
