import assert from "node:assert/strict";

const renderUrl = String(process.env.RENDER_URL || "").replace(/\/$/, "");
const pagesUrl = String(process.env.PAGES_URL || "").replace(/\/$/, "");

if (!renderUrl || !pagesUrl) {
  console.error("Usage: RENDER_URL=https://... PAGES_URL=https://... node deployment/public_smoke_test.mjs");
  process.exit(2);
}

async function json(url, options = {}) {
  const response = await fetch(url, options);
  assert.ok(response.ok, `${url}: HTTP ${response.status}`);
  return response.json();
}

const health = await json(`${renderUrl}/health`);
assert.equal(health.status, "ok");
assert.equal(health.mock_only, true);

const casePayload = await json(`${renderUrl}/api/v1/test-cases`);
assert.equal(casePayload.test_cases.length, 9, "Public API must expose nine test cases");

for (const testCase of casePayload.test_cases) {
  const result = await json(`${renderUrl}/api/v1/agent/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ test_case: testCase.id }),
  });
  assert.equal(result.mock_only, true, `${testCase.id}: mock boundary missing`);
  assert.equal(result.decision.scene_type, testCase.expected_scene, `${testCase.id}: scene mismatch`);
}

for (const group of ["holdout", "fixed_rule", "agent"]) {
  const token = `${group}_${Date.now()}`;
  const pipeline = await json(`${renderUrl}/api/v1/pipeline/test`, {
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
  assert.equal(pipeline.assignment.ab_group, group, `${group}: assignment mismatch`);
  assert.equal(pipeline.stages.length, 7, `${group}: incomplete pipeline`);
  assert.equal(pipeline.warehouse_record.mock_only, true, `${group}: warehouse boundary missing`);
}

const pageResponse = await fetch(`${pagesUrl}/`);
assert.ok(pageResponse.ok, `Pages root: HTTP ${pageResponse.status}`);
const pageHtml = await pageResponse.text();
assert.match(pageHtml, /淘金币跳一跳/);
assert.match(pageHtml, /端到端 Pipeline Mock/);

const runtimeResponse = await fetch(`${pagesUrl}/runtime-config.js`);
assert.ok(runtimeResponse.ok, `runtime-config.js: HTTP ${runtimeResponse.status}`);
const runtimeConfig = await runtimeResponse.text();
assert.ok(runtimeConfig.includes(renderUrl), "Cloudflare runtime-config does not reference the final Render URL");

const csvResponse = await fetch(`${pagesUrl}/synthetic_data/agent_full_replay/full_agent_replay_results.csv`);
assert.ok(csvResponse.ok, `Public CSV: HTTP ${csvResponse.status}`);
assert.match(csvResponse.headers.get("content-type") || "", /text\/csv/);

console.log("Public deployment smoke tests: 18/18 passed");
console.log(`Frontend: ${pagesUrl}`);
console.log(`Backend:  ${renderUrl}`);
