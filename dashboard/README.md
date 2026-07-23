# 本地实验看板 MVP

打开 `index.html` 即可查看，无需安装依赖或启动服务。

当前页面包含三类明确区分的数据：

- 历史五表基线：来自最初五张原始表的分析结果；
- 离线预测：来自 `offline_simulation/` 的情景测算；
- 本地 Agent 决策测试：来自 8,100 名合成用户的五表全量回放，使用 `agent_test_data.js` 展示规则树和实际命中分布。

页面中的“待线上回流”表示该指标尚未产生真实 Agent/A-B 数据，不应视为已上线结果。合成回放只验证数据流、规则优先级、工具 Mock 和日志闭环，不输出业务 uplift 结论。

刷新本地 Agent 决策测试数据：

```bash
python3 synthetic_data/run_full_agent_replay.py \
  --data-dir synthetic_data/generated \
  --output-dir synthetic_data/agent_full_replay
```

生产接入时：

1. 将 `dashboard_data.js` 替换为 BI/数仓 API 返回的数据。
2. 按 `04_数仓字段与监控看板定义.md` 建立事实表与实验宽表。
3. 每日写入 SRM、主指标 95% CI、p-value 和护栏告警。
4. 只对成熟的 T+7 队列展示 `retention_7d`、`add_to_cart_7d`、`order_7d`。
