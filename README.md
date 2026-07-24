# Week6：Level 2 Agent A/B、监控与离线预测交付包

## 目标

验证淘金币跳一跳小游戏 Agent 是否能在 `standard` 模式 Level 2 受阻时，优于固定规则和无新增干预流程，提升关卡通过与游戏完成，并在不突破成本、稳定性和体验护栏的前提下观察后续留存、加购和下单。

## 文件清单

| 文件 | 说明 |
|---|---|
| `01_AB测试方案.md` | 三组实验、样本量、指标、成功/停止规则和分析口径 |
| `02_前端埋点事件规范.csv` | 首页及游戏链路事件、上报字段和实时聚合规则 |
| `03_端到端数据流与后端执行设计.md` | 前端、Backend、Dify、业务工具和失败兜底 |
| `04_数仓字段与监控看板定义.md` | 执行事实表、实验宽表、指标 SQL 口径和看板需求 |
| `offline_simulation/build_level2_forecast.py` | 直接读取五张原始 CSV，生成样本量与离线预测 |
| `offline_simulation/level2_agent_forecast.md` | 脚本生成的挽回、订单与 ROI 情景预测说明 |
| `offline_simulation/level2_agent_forecast.csv` | 脚本生成的预测明细 |
| `offline_simulation/level2_agent_roi_scenarios.csv` | 保守/基准/积极三档 ROI 敏感性明细 |
| `synthetic_data/run_full_agent_replay.py` | 对 8,100 名合成用户执行全量 Agent Mock 回放并刷新看板数据 |
| `synthetic_data/agent_full_replay/` | 逐用户结果、规则树节点分布、审计 JSON 和本地测试报告 |
| `runtime/` | 包内 Agent Mock 运行时和脱敏抽样回放脚本 |
| `support/intervention_psm_did_results.csv` | 离线预测使用的包内 PSM-DID 效应输入 |
| `dashboard/index.html` | 本地实验看板，含 Agent 决策树、全量回放分布和七阶段 Pipeline 测试 |
| `deployment/render_backend/` | 可部署到 Render 的 Agent 与端到端 Pipeline Mock API |
| `deployment/build_cloudflare.mjs` | 生成 Cloudflare Pages 静态发布目录 |
| `deployment/在线测试与Cloudflare_Render部署指南.md` | 在线测试方法、部署步骤、边界和验收标准 |
| `deployment/public_smoke_test.mjs` | 对最终 Render 与 Cloudflare 地址执行 18 项公网验收 |
| `.github/workflows/public-deployment-acceptance.yml` | 主分支部署后自动重试公网验收，并归档 JSON/Markdown 报告 |
| `08_独立复现验证.md` | 在无Week5相邻目录环境中的隔离复现记录 |
| `09_公网部署执行清单.md` | GitHub、Render、Cloudflare 的一次性发布和最终链接验收 |

## 运行

使用最初五张原始表重新生成历史预测：

```bash
python3 offline_simulation/build_level2_forecast.py \
  --data-dir /path/to/five-source-csv \
  --output-dir offline_simulation
```

原始业务CSV因隐私边界不重复打包。脚本使用包内`support/intervention_psm_did_results.csv`，不再依赖上级目录。若只验证交付包可运行性，可将`--data-dir`设为`synthetic_data/generated`并将输出写入临时目录。

运行全量合成五表 Agent 回放：

```bash
python3 synthetic_data/run_full_agent_replay.py \
  --data-dir synthetic_data/generated \
  --output-dir synthetic_data/agent_full_replay
```

该脚本使用 `holdout`、`fixed_rule`、`agent` 三组各 2,700 名合成用户，但本轮仅验证 Agent 的场景判定、动作计划、Mock 执行和数据回流，不比较组间业务效果。

运行脱敏抽样回放：

```bash
python3 runtime/build_raw_table_replay.py
```

以上回放脚本均使用包内`runtime/agent_workflow_mock.py`，不依赖Week5目录。

## 在线测试沙盒

本交付包已增加 Cloudflare Pages + Render 可部署沙盒。测试者可在看板的 `Agent 决策测试 -> 在线测试` 中选择9个预设场景、修改特征并运行 Agent Mock，也可选择 Agent、固定规则或 Holdout，运行“前端埋点 -> Backend 监听 -> 实验分桶 -> 特征构建 -> 策略决策 -> Mock 动作 -> 数据回流”的完整链路。

在线测试请求的客户端超时为10秒。若Render、网络或Agent服务未在时限内响应，页面会停止等待、标记服务不可用并展示`show_static_hint`静态兜底，可直接点击“重新测试”。

每次 Agent 决策测试和完整 Pipeline 测试都会保存在当前浏览器的 `localStorage` 中，最多保留100条，包含成功、无动作、超时、兜底和失败记录。页面可直接下载 Markdown 测试报告或包含完整响应的 JSON 记录。该记录仅在当前浏览器内持久化，不是跨设备的生产审计库。

本地运行：

```bash
cd deployment/render_backend
npm run dev
```

浏览器打开 `http://127.0.0.1:8787/demo/`。公网地址为 <https://coin-game-agent-sandbox.pages.dev>，部署与验收按 `deployment/在线测试与Cloudflare_Render部署指南.md` 执行。

完整 Pipeline 测试接口为 `POST /api/v1/pipeline/test`，最近 200 条临时链路审计可通过 `GET /api/v1/pipeline/audit` 查看。四个实验扩展接口也已提供内存 Mock；生产接入仍需替换为真实实验平台、业务工具和数仓服务。

推送到 `main` 后，GitHub Actions 会等待 Cloudflare Pages 和 Render 发布完成，再执行18项公网验收。工作流通过 Cloudflare `build-meta.json` 核对当前 commit SHA，避免对旧版本误判；JSON与Markdown报告作为 Actions Artifact 保存90天，也会写入该次工作流的 Job Summary。工作流还支持手动执行和每日定时巡检。

## 重要边界

1. 预测是**离线情景估算**，借用 `intervention_test.csv` 中 `tutorial_popup` 与 `game_difficulty_reduced` 的 PSM-DID 效应；它不等价于 Level 2 Agent 的线上因果结论。
2. Agent、固定规则、Holdout 必须在首次满足入组条件时随机分配，并对用户固定分桶。
3. `game_behavior_log.csv` 只覆盖 treatment 内游戏用户，不能用于直接估计 control 与 treatment 的游戏差异。
4. 现有版本实验存在 SRM 与事件采集范围差异风险；本次新实验必须独立完成分流审计、事件完整性核验和日志回流。
