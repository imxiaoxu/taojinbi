# 合成五表全量 Agent 决策测试报告

- 测试范围：8,100 名合成用户，五表覆盖率 100.0%。
- 场景一致率：8,100/8,100（100.0%）。
- 工具执行：16,708/16,708 成功（100.0%）。
- 非法动作：0；重复动作决策：0。
- 测试结论：通过。

## 场景分布

- `level_2_block`：3,932
- `continuous_failure`：864
- `android_perf_risk`：283
- `cart_without_order`：594
- `new_user_first_game`：989
- `no_action`：1,438

## 说明

本报告验证 Agent V1 的本地决策、Guardrail 与 Mock 工具执行，不用于估计真实业务 uplift。
