# 五表合成数据

本目录用于生成**本地测试数据**，覆盖 Agent 场景回放、三组 A/B 分流、数仓字段和看板验证。所有用户 ID 均以 `sim_u_` 开头，为新生成的合成标识，不包含原始数据用户。

## 生成

```bash
python3 synthetic_data/generate_synthetic_five_tables.py \
  --output-dir synthetic_data/generated \
  --users-per-group 2700 \
  --seed 20260716
```

默认生成 `holdout`、`fixed_rule`、`agent` 三组各 2,700 名用户，共 8,100 名用户。`standard` Level 2 启动率设为 75%，每组约 2,025 名入组用户，可用于验证首期 5pp MDE 的样本量、SRM、漏斗、A/B 指标和看板。

## 已生成样本与 Agent 回放

`generated/` 已按默认参数生成一套可直接使用的数据。其五表用户覆盖均为 8,100 名，全部用户 ID 为合成 ID。

已使用这套数据完成两类本地 Agent 回放：

- 抽样回放：六类场景各抽取 20 条，共 120 条，用于快速排查单条轨迹。结果见 `agent_replay_results/raw_table_replay_audit.json`。
- 全量回放：覆盖全部 8,100 名合成用户，用于验证规则优先级、五表覆盖、动作合法性和看板决策树分布。全量输出位于 `agent_full_replay/`。

再次执行 Agent 回放：

```bash
python3 runtime/build_raw_table_replay.py \
  --data-dir synthetic_data/generated \
  --output-dir synthetic_data/agent_replay_results \
  --max-per-scene 20
```

执行全量回放并同步刷新本地看板数据：

```bash
python3 synthetic_data/run_full_agent_replay.py \
  --data-dir synthetic_data/generated \
  --output-dir synthetic_data/agent_full_replay
```

全量回放会按固定优先级判断 `Level 2 受阻 -> 连续失败 -> Android 性能风险 -> 加购未下单 -> 新用户首局 -> 无动作`，并输出：

| 文件 | 内容 |
|---|---|
| `agent_full_replay/full_agent_replay_results.csv` | 脱敏的逐用户场景、动作和执行状态 |
| `agent_full_replay/full_agent_replay_summary.json` | 场景、动作、工具执行和断言审计汇总 |
| `agent_full_replay/full_agent_decision_tree.json` | 决策树节点及实际命中人数 |
| `agent_full_replay/full_agent_replay_report.md` | 可提交的本地测试报告 |
| `dashboard/agent_test_data.js` | 看板读取的全量回放数据快照 |

若场景一致性、五表覆盖、非法动作或重复动作校验失败，脚本会以非零状态退出。

抽样回放和全量回放均使用`runtime/agent_workflow_mock.py`，交付包可在没有Week5目录的环境中独立运行。

## 五表映射

| 输出文件 | 原始表结构 | 用途 |
|---|---|---|
| `event_log.csv` | `event_log.csv` | 首页、加购、下单行为 |
| `game_behavior_log.csv` | `game_behavior_log.csv` | Level 1-3、失败、退出、完成、留存 |
| `intervention_test.csv` | `intervention_test.csv` | 教程/降难度干预的 pre/post 样例 |
| `user_profile.csv` | `user_profile.csv` | 用户画像与分层 |
| `version_exposure.csv` | `version_exposure.csv` | 三组实验分桶与曝光 |

## 重要限制

- `agent`、`fixed_rule`、`holdout` 的通过率、完成率和下单率差异来自脚本中的**显式假设参数**，不是历史数据估计值。
- 此数据可证明数据链路、实验分析代码和看板是否正确，不能证明 Agent 对真实用户的效果。
- 若要做盲测，可修改脚本中的 `CONFIG` 后重新生成，并在分析前隐藏真实参数。
