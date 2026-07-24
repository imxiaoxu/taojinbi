# 淘金币游戏 Agent 在线测试与部署指南

## 1. 部署目标与边界

本部署用于项目展示、在线评审和规则验收，不接入真实淘金币业务流。

- 前端：Cloudflare Pages 托管实验看板与“在线测试”页面。
- 后端：Render Web Service 托管无状态 Agent Mock API。
- 数据：仅使用 8,100 名合成用户及脱敏回放结果。
- 工具：教程、Guided Mode、降难度、金币补偿等均返回 Mock 结果，不调用真实业务 API。
- 状态：Render 最近 200 条服务端审计保存在进程内存中；看板另将测试者的最近100条记录保存在当前浏览器，可下载为 Markdown 或 JSON。
- 结论：本环境验证决策逻辑、Guardrail、异常兜底和数据展示，不产生真实业务 uplift 或 A/B 因果结论。

## 2. 访问架构

```text
测试者浏览器
    |
    | HTTPS
    v
Cloudflare Pages（实验看板 + 在线测试表单）
    |
    | HTTPS / JSON，CORS 仅允许 Pages 域名
    v
Render Agent Mock API
    |-- 事件接收与去重
    |-- 稳定实验分桶
    |-- 特征标准化
    |-- 场景分类
    |-- Guardrail
    |-- 动作计划
    |-- Mock 工具执行
    |-- 临时审计日志
    |
    v
合成五表汇总与决策树（只读）
```

推荐部署顺序为 Render -> Cloudflare Pages -> 收紧 Render CORS。

## 3. 在线测试方式

测试者打开 <https://coin-game-agent-sandbox.pages.dev> 后，进入：

`Agent 决策测试 -> 在线测试`

测试页支持9个预设场景：

| 场景 | 预期结果 | 验证目的 |
|---|---|---|
| standard Level 2 首次失败 | 教程 -> Guided Mode -> 降难度 | 核心 Level 2 干预路径 |
| 其他关卡连续失败 | 教程/Guided Mode + 金币补偿 | 连续失败识别 |
| Android 加载性能风险 | 性能提示 + 降低动画 | 设备性能场景 |
| 7 日加购未下单 | 淘金币说明 + 优惠券提醒 + 推荐 | 交易辅助场景 |
| 新用户首局 | 新用户教程 | 冷启动引导 |
| 无需干预 | no_action | 不过度干预 |
| 会话频控拦截 | no_action + frequency limit | Guardrail |
| 教程工具超时 | show_static_hint fallback | 异常兜底 |
| Agent 决策引擎异常 | degraded + show_static_hint fallback | 决策服务故障识别与后端兜底 |

测试者还可以修改关卡、失败次数、设备、加载时间、优惠券、加购/下单状态后再次运行。页面会展示：

1. 命中的最终场景；
2. Agent 动作计划；
3. 每个 Mock 工具的执行状态；
4. 规则逐层判断轨迹；
5. 完整 JSON 响应和 `mock_only=true` 标识；
6. Agent、固定规则、Holdout 三组的七阶段端到端 Pipeline 执行轨迹。
7. 当前浏览器中的测试历史、成功/兜底统计及可下载测试报告。

## 4. Render 部署

### 4.1 创建服务

1. 将 `Week6_AB监控预测交付包` 作为独立 GitHub 仓库根目录，或保证该目录完整存在于仓库中。
2. 在 Render 选择 `New -> Blueprint`，连接仓库并读取根目录的 `render.yaml`。
3. 首次部署时将环境变量 `ALLOWED_ORIGINS` 暂设为 `*`。
4. 部署完成后记录服务地址，例如：

```text
https://coin-game-agent-sandbox-api.onrender.com
```

### 4.2 Render 验收

```text
GET  /health
GET  /api/v1/meta
GET  /api/v1/test-cases
POST /api/v1/agent/test
POST /api/v1/pipeline/test
GET  /api/v1/audit?limit=20
GET  /api/v1/pipeline/audit?limit=20
GET  /api/v1/replay/summary
GET  /api/v1/replay/decision-tree
POST /v1/experiments/assign
POST /v1/events/ingest
POST /v1/interventions/delivery
POST /v1/eval/outcomes/backfill
```

`/health` 必须返回 HTTP 200、`status=ok` 和 `mock_only=true`。

Render 官方要求 Web Service 监听 `0.0.0.0` 和平台提供的 `PORT`；本项目的启动命令已按该规则配置，并设置 `/health` 健康检查。

## 5. Cloudflare Pages 部署

1. 在 Cloudflare 选择 `Workers & Pages -> Create application -> Pages -> Connect to Git`。
2. 连接同一 GitHub 仓库。
3. 使用以下构建配置：

| 配置项 | 值 |
|---|---|
| Framework preset | None |
| Build command | `node deployment/build_cloudflare.mjs` |
| Build output directory | `deployment/cloudflare_dist` |
| Environment variable | `RENDER_API_URL=https://coin-game-agent-sandbox-api.onrender.com` |

4. 当前部署地址为 `https://coin-game-agent-sandbox.pages.dev`。
5. Render 的 `ALLOWED_ORIGINS` 已设置为该 Pages 地址。若同时使用自定义域名，使用英文逗号分隔：

```text
https://coin-game-agent-sandbox.pages.dev,https://demo.example.com
```

6. 重新测试 Pages 页面中的“检查连接”和9个预设场景。

Cloudflare Pages 支持无框架静态 HTML 和 Git 自动部署；本项目构建脚本只打包看板、运行配置和脱敏结果，不包含原始五张 CSV。

## 6. 公共链接交付格式

对外测试说明可直接使用：

```text
项目测试地址：https://coin-game-agent-sandbox.pages.dev

测试入口：Agent 决策测试 -> 在线测试
建议依次测试：
1. standard Level 2 首次失败；
2. 会话频控拦截；
3. 教程工具超时；
4. Agent 决策引擎异常；
5. 自行修改失败次数、设备或加载时间。

说明：该环境只使用合成数据和 Mock 工具，不接入真实淘金币业务，也不代表线上 A/B 效果。
```

## 7. 验收标准

| 验收项 | 标准 |
|---|---|
| 页面访问 | Cloudflare Pages HTTPS 正常打开 |
| API 健康度 | `/health` 返回 200 |
| 场景准确性 | 9个预设场景均命中预期 scene 或系统兜底状态 |
| 核心动作 | Level 2 返回教程、Guided Mode、降难度 |
| Guardrail | 达到会话频控后不执行工具 |
| 失败兜底 | 教程超时后返回 `show_static_hint` |
| 服务故障兜底 | Agent 决策异常被识别，返回 `degraded` 和 `show_static_hint` |
| 客户端超时 | 请求超过10秒后停止等待，展示静态兜底和重新测试入口 |
| 端到端 Pipeline | Agent、固定规则、Holdout 均完成七阶段 Mock 链路并返回数仓回流记录 |
| 数据边界 | 响应包含 `mock_only=true`，无真实用户 ID |
| 全量回放 | 8,100/8,100 场景一致，五表覆盖率 100% |
| 页面兼容 | 桌面和移动端无全页横向溢出 |

## 8. 部署后自动验收

仓库中的 `.github/workflows/public-deployment-acceptance.yml` 会在以下情况下运行：

1. `main` 分支收到新提交；
2. 在 GitHub Actions 页面手动运行；
3. 每日定时巡检。

工作流最多重试20次、每次间隔30秒，以覆盖 Render 冷启动和 Cloudflare Pages 发布延迟。18项验收包括：

- Render 健康状态与 `mock_only` 边界；
- 9个预设场景的预期决策；
- Agent、固定规则、Holdout 的七阶段 Pipeline；
- Cloudflare 首页、关键功能区、运行配置和脱敏 CSV；
- Cloudflare `build-meta.json` 中的 commit SHA 必须与触发工作流的提交一致。

每次执行都会生成：

```text
public-smoke-report.json
public-smoke-report.md
```

报告会显示在 GitHub Actions 的 Job Summary，并作为 Artifact 保存90天。即使验收失败，已执行的检查结果仍会归档，便于定位部署延迟、CORS、API或静态资源问题。

## 9. 测试记录持久化

### 浏览器测试记录

看板的 `Agent 决策测试 -> 在线测试 -> 测试记录与报告` 会保存最近100条 Agent 与 Pipeline 测试。记录包括测试时间、场景/分组、决策状态、请求标识和完整 Mock 响应。

- 持久化介质：当前浏览器 `localStorage`；
- 导出格式：Markdown 汇总报告、JSON 完整记录；
- 隐私边界：只记录合成测试输入和脱敏标识；
- 生命周期：关闭页面后仍保留，清除浏览器数据或点击“清空记录”后删除；
- 适用范围：单个评审者的测试留痕，不用于跨设备协作或生产审计。

GitHub Actions Artifact 负责保存自动化公网验收记录；浏览器 `localStorage` 负责保存人工交互测试记录。两者用途分离。

### 生产化扩展

如果后续需要多人共享、服务端检索、长期留存或审计追溯，应新增 Postgres（或正式日志平台），以 `request_id` / `pipeline_id` 为幂等键写入测试事实表，并设置访问控制、数据保留期和删除机制。不得依赖 Render 临时文件系统。

## 10. 部署建议

### 答辩或集中测试

Render Free Web Service 空闲 15 分钟后会休眠，首次唤醒可能需要约一分钟。若使用免费实例，应在测试前 2 分钟打开 `/health` 预热，并提前告知测试者首次连接可能较慢。

若需要在固定时间稳定测试，建议测试期间临时升级为不会休眠的付费实例，测试结束后再降级。

### 安全与成本

- Cloudflare 页面中不保存 Render 密钥；API 本身不需要业务密钥。
- Render CORS 最终只允许 Pages 域名。
- API 请求体限制为 64KB，审计日志最多 200 条且随进程重启清空。
- 不上传原始五表；Cloudflare 只包含合成汇总和脱敏回放 CSV。
- 公网环境保持 Mock 工具，不开放任何真实发券、发金币或修改难度接口。

## 11. 官方参考

- Cloudflare Pages 静态 HTML：<https://developers.cloudflare.com/pages/framework-guides/deploy-anything/>
- Cloudflare Pages Git 集成：<https://developers.cloudflare.com/pages/get-started/git-integration/>
- Render Web Service：<https://render.com/docs/web-services>
- Render Health Checks：<https://render.com/docs/health-checks>
- Render Free 限制：<https://render.com/docs/free>
