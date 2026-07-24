import { mkdirSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";

const renderUrl = String(process.env.RENDER_URL || "").replace(/\/$/, "");
const pagesUrl = String(process.env.PAGES_URL || "").replace(/\/$/, "");
const expectedCommitSha = String(process.env.EXPECTED_COMMIT_SHA || "").trim();
const reportDir = process.env.SMOKE_REPORT_DIR ? resolve(process.env.SMOKE_REPORT_DIR) : "";
const startedAt = new Date();
const checks = [];

if (!renderUrl || !pagesUrl) {
  console.error("Usage: RENDER_URL=https://... PAGES_URL=https://... node deployment/public_smoke_test.mjs");
  process.exit(2);
}

async function fetchOk(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
  return response;
}

async function fetchJson(url, options = {}) {
  const response = await fetchOk(url, options);
  return response.json();
}

function requireEqual(actual, expected, message) {
  if (actual !== expected) {
    throw new Error(`${message}: expected ${JSON.stringify(expected)}, received ${JSON.stringify(actual)}`);
  }
}

function requireMatch(value, pattern, message) {
  if (!pattern.test(String(value))) throw new Error(message);
}

async function check(id, name, action) {
  const checkStartedAt = Date.now();
  try {
    const detail = await action();
    checks.push({
      id,
      name,
      status: "passed",
      duration_ms: Date.now() - checkStartedAt,
      detail: detail || "通过",
    });
    console.log(`PASS ${String(id).padStart(2, "0")} ${name}`);
  } catch (error) {
    checks.push({
      id,
      name,
      status: "failed",
      duration_ms: Date.now() - checkStartedAt,
      detail: error instanceof Error ? error.message : String(error),
    });
    console.error(`FAIL ${String(id).padStart(2, "0")} ${name}: ${checks.at(-1).detail}`);
  }
}

const fallbackCases = [
  { id: "level2_first_fail", expected_scene: "level_2_block" },
  { id: "continuous_failure", expected_scene: "continuous_failure" },
  { id: "android_slow", expected_scene: "android_perf_risk" },
  { id: "cart_no_order", expected_scene: "cart_without_order" },
  { id: "new_user", expected_scene: "new_user_first_game" },
  { id: "no_action", expected_scene: "no_action" },
  { id: "guardrail_block", expected_scene: "level_2_block" },
  { id: "tool_timeout", expected_scene: "level_2_block" },
  { id: "agent_runtime_error", expected_scene: "system_fallback" },
];

let publicCases = fallbackCases;

await check(1, "Render 健康检查与 Mock 边界", async () => {
  const health = await fetchJson(`${renderUrl}/health`);
  requireEqual(health.status, "ok", "health.status");
  requireEqual(health.mock_only, true, "health.mock_only");
  return "status=ok, mock_only=true";
});

await check(2, "九个预设场景目录", async () => {
  const payload = await fetchJson(`${renderUrl}/api/v1/test-cases`);
  requireEqual(payload.test_cases?.length, 9, "test_cases.length");
  publicCases = payload.test_cases;
  return "9 个场景已公开";
});

for (let index = 0; index < fallbackCases.length; index += 1) {
  const fallbackCase = fallbackCases[index];
  const testCase = publicCases.find((item) => item.id === fallbackCase.id) || fallbackCase;
  await check(index + 3, `场景决策：${testCase.id}`, async () => {
    const result = await fetchJson(`${renderUrl}/api/v1/agent/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ test_case: testCase.id }),
    });
    requireEqual(result.mock_only, true, "mock_only");
    requireEqual(result.decision?.scene_type, testCase.expected_scene, "decision.scene_type");
    return `scene_type=${result.decision.scene_type}`;
  });
}

for (const [offset, group] of ["holdout", "fixed_rule", "agent"].entries()) {
  await check(offset + 12, `七阶段 Pipeline：${group}`, async () => {
    const token = `${group}_${Date.now()}`;
    const pipeline = await fetchJson(`${renderUrl}/api/v1/pipeline/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id_hash: `synthetic_public_${token}`,
        session_id: `session_${token}`,
        trace_id: `trace_${token}`,
        force_group: group,
        test_case: "level2_first_fail",
      }),
    });
    requireEqual(pipeline.assignment?.ab_group, group, "assignment.ab_group");
    requireEqual(pipeline.stages?.length, 7, "stages.length");
    requireEqual(pipeline.warehouse_record?.mock_only, true, "warehouse_record.mock_only");
    return `7/7 stages, group=${group}`;
  });
}

let pageHtml = "";
await check(15, "Cloudflare Pages 首页可访问", async () => {
  const response = await fetchOk(`${pagesUrl}/`);
  pageHtml = await response.text();
  return `HTTP ${response.status}`;
});

await check(16, "首页关键功能内容完整", async () => {
  if (!pageHtml) pageHtml = await (await fetchOk(`${pagesUrl}/`)).text();
  requireMatch(pageHtml, /淘金币跳一跳/, "页面缺少项目标题");
  requireMatch(pageHtml, /端到端 Pipeline Mock/, "页面缺少 Pipeline 测试入口");
  requireMatch(pageHtml, /测试记录与报告/, "页面缺少测试记录与报告区");
  return "标题、Pipeline、测试记录区均存在";
});

await check(17, "运行配置与部署版本一致", async () => {
  const runtimeConfig = await (await fetchOk(`${pagesUrl}/runtime-config.js`)).text();
  if (!runtimeConfig.includes(renderUrl)) {
    throw new Error("runtime-config.js 未引用最终 Render URL");
  }
  const buildMeta = await fetchJson(`${pagesUrl}/build-meta.json`);
  if (expectedCommitSha && buildMeta.commit_sha !== expectedCommitSha) {
    throw new Error(`Cloudflare 尚未发布当前提交：expected ${expectedCommitSha}, received ${buildMeta.commit_sha}`);
  }
  return `commit=${buildMeta.commit_sha}`;
});

await check(18, "脱敏全量回放 CSV 可下载", async () => {
  const response = await fetchOk(`${pagesUrl}/synthetic_data/agent_full_replay/full_agent_replay_results.csv`);
  requireMatch(response.headers.get("content-type") || "", /text\/csv/, "CSV Content-Type 不正确");
  return `content-type=${response.headers.get("content-type")}`;
});

const passedCount = checks.filter((item) => item.status === "passed").length;
const failedCount = checks.length - passedCount;
const finishedAt = new Date();
const report = {
  report_type: "public_deployment_acceptance",
  status: failedCount === 0 ? "passed" : "failed",
  generated_at: finishedAt.toISOString(),
  started_at: startedAt.toISOString(),
  duration_ms: finishedAt.getTime() - startedAt.getTime(),
  attempt: Number(process.env.SMOKE_ATTEMPT || 1),
  commit_sha: expectedCommitSha || null,
  frontend_url: pagesUrl,
  backend_url: renderUrl,
  passed_count: passedCount,
  failed_count: failedCount,
  total_count: checks.length,
  checks,
};

const markdownRows = checks.map((item) => {
  const detail = String(item.detail).replaceAll("|", "\\|").replaceAll("\n", " ");
  return `| ${item.id} | ${item.name} | ${item.status === "passed" ? "通过" : "失败"} | ${item.duration_ms} | ${detail} |`;
}).join("\n");
const markdown = `# 公网部署 18 项验收报告

- 验收状态：**${report.status === "passed" ? "通过" : "失败"}**
- 通过项：${passedCount}/${checks.length}
- 前端：${pagesUrl}
- 后端：${renderUrl}
- 提交版本：${expectedCommitSha || "未指定"}
- 执行时间：${report.generated_at}
- 重试轮次：${report.attempt}

| # | 验收项 | 结果 | 耗时（ms） | 说明 |
|---:|---|---|---:|---|
${markdownRows}
`;

if (reportDir) {
  mkdirSync(reportDir, { recursive: true });
  writeFileSync(join(reportDir, "public-smoke-report.json"), `${JSON.stringify(report, null, 2)}\n`, "utf8");
  writeFileSync(join(reportDir, "public-smoke-report.md"), markdown, "utf8");
}

console.log(`Public deployment smoke tests: ${passedCount}/${checks.length} passed`);
console.log(`Frontend: ${pagesUrl}`);
console.log(`Backend:  ${renderUrl}`);

if (failedCount > 0) process.exitCode = 1;
