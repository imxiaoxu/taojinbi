import { createServer } from "node:http";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { createHash, randomUUID } from "node:crypto";

const HERE = dirname(fileURLToPath(import.meta.url));
const PACKAGE_ROOT = resolve(HERE, "../..");
const STATIC_ROOT = resolve(HERE, "../cloudflare_dist");
const PORT = Number(process.env.PORT || 8787);
const HOST = process.env.HOST || "0.0.0.0";
const MAX_BODY_BYTES = 64 * 1024;
const AUDIT_LIMIT = 200;
const startedAt = new Date().toISOString();
const auditLog = [];
const pipelineAudit = [];
const assignmentStore = new Map();
const ingestedEventIds = new Set();
const deliveryLog = [];
const outcomeLog = [];

const SCENE_ORDER = [
  "level_2_block",
  "continuous_failure",
  "android_perf_risk",
  "cart_without_order",
  "new_user_first_game",
  "no_action",
];

export const TEST_CASES = {
  level2_first_fail: {
    label: "standard Level 2 首次失败",
    expected_scene: "level_2_block",
    features: { trigger_event_name: "level_fail", game_variant: "standard", level_id: 2, fail_count_session: 1 },
  },
  continuous_failure: {
    label: "其他关卡连续失败",
    expected_scene: "continuous_failure",
    features: { trigger_event_name: "level_fail", game_variant: "easy_mode", level_id: 3, fail_count_session: 2 },
  },
  android_slow: {
    label: "Android 加载性能风险",
    expected_scene: "android_perf_risk",
    features: { trigger_event_name: "app_open", device_os: "Android", page_load_time_ms: 3600 },
  },
  cart_no_order: {
    label: "7 日加购未下单",
    expected_scene: "cart_without_order",
    features: { trigger_event_name: "add_to_cart", has_add_to_cart_7d: true, has_order_7d: false, coupon_available_count: 2 },
  },
  new_user: {
    label: "新用户首局",
    expected_scene: "new_user_first_game",
    features: { trigger_event_name: "game_start", game_variant: "guided_mode", level_id: 1, is_new_game_user: true },
  },
  no_action: {
    label: "无需干预",
    expected_scene: "no_action",
    features: { trigger_event_name: "app_open", game_variant: "easy_mode", level_id: 1 },
  },
  guardrail_block: {
    label: "会话频控拦截",
    expected_scene: "level_2_block",
    features: { trigger_event_name: "level_fail", game_variant: "standard", level_id: 2, fail_count_session: 1, intervention_count_session: 1, max_intervention_per_session: 1 },
  },
  tool_timeout: {
    label: "教程工具超时",
    expected_scene: "level_2_block",
    features: { trigger_event_name: "level_fail", game_variant: "standard", level_id: 2, fail_count_session: 1, tutorial_service_timeout: true },
  },
  agent_runtime_error: {
    label: "Agent 决策引擎异常",
    expected_scene: "system_fallback",
    features: { trigger_event_name: "level_fail", game_variant: "standard", level_id: 2, fail_count_session: 1, simulate_agent_crash: true },
  },
};

function bool(value, fallback = false) {
  if (value === undefined || value === null || value === "") return fallback;
  if (typeof value === "boolean") return value;
  return ["1", "true", "yes", "y"].includes(String(value).trim().toLowerCase());
}

function number(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizeFeatures(raw = {}) {
  return {
    trigger_event_name: raw.trigger_event_name || "unknown",
    game_variant: raw.game_variant || "unknown",
    level_id: raw.level_id === "" || raw.level_id === null || raw.level_id === undefined ? null : number(raw.level_id),
    current_exit_point: raw.current_exit_point ?? null,
    fail_count_session: Math.max(0, number(raw.fail_count_session)),
    level_2_fail_count_session: Math.max(0, number(raw.level_2_fail_count_session)),
    intervention_count_session: Math.max(0, number(raw.intervention_count_session)),
    max_intervention_per_session: Math.max(1, number(raw.max_intervention_per_session, 1)),
    tutorial_shown_session: bool(raw.tutorial_shown_session),
    guided_mode_switched_session: bool(raw.guided_mode_switched_session),
    device_os: raw.device_os || "Unknown",
    page_load_time_ms: raw.page_load_time_ms === "" || raw.page_load_time_ms === null || raw.page_load_time_ms === undefined ? null : number(raw.page_load_time_ms),
    has_add_to_cart_7d: bool(raw.has_add_to_cart_7d),
    has_order_7d: bool(raw.has_order_7d),
    coupon_available_count: Math.max(0, number(raw.coupon_available_count)),
    is_new_game_user: bool(raw.is_new_game_user),
    allow_coin_compensation: bool(raw.allow_coin_compensation, true),
    allow_coupon: bool(raw.allow_coupon, true),
    push_frequency_limit_reached: bool(raw.push_frequency_limit_reached),
    risk_level: raw.risk_level || "low",
    tutorial_service_timeout: bool(raw.tutorial_service_timeout),
    simulate_agent_crash: bool(raw.simulate_agent_crash),
  };
}

function classify(features) {
  const rules = [
    {
      scene: "level_2_block",
      label: "standard + Level 2 + 失败/退出",
      matched: features.game_variant === "standard" && String(features.level_id) === "2" && (features.fail_count_session >= 1 || String(features.current_exit_point) === "2"),
    },
    { scene: "continuous_failure", label: "同一会话失败次数 >= 2", matched: features.fail_count_session >= 2 },
    { scene: "android_perf_risk", label: "Android 且加载耗时 >= 3000ms", matched: features.device_os === "Android" && features.page_load_time_ms !== null && features.page_load_time_ms >= 3000 },
    { scene: "cart_without_order", label: "7 日加购且未下单", matched: features.has_add_to_cart_7d && !features.has_order_7d },
    { scene: "new_user_first_game", label: "新用户进入首局", matched: features.is_new_game_user && features.trigger_event_name === "game_start" },
    { scene: "no_action", label: "不触发干预", matched: true },
  ];
  const selectedIndex = rules.findIndex((rule) => rule.matched);
  return {
    scene: rules[selectedIndex].scene,
    trace: rules.map((rule, index) => ({ ...rule, evaluated: index <= selectedIndex, selected: index === selectedIndex })),
  };
}

function guardrail(features) {
  if (features.intervention_count_session >= features.max_intervention_per_session) {
    return { allowed: false, reason: "session_frequency_limit" };
  }
  if (features.risk_level === "high") return { allowed: false, reason: "high_risk" };
  return { allowed: true, reason: "ok" };
}

function plan(scene, features, gate) {
  if (!gate.allowed) return { status: "no_action", actions: [], fallback_action: "show_static_hint", reason: gate.reason };
  const actions = [];
  const add = (action_type, tool_name, params = {}) => actions.push({ step: actions.length + 1, action_type, tool_name, params });
  if (scene === "level_2_block") {
    if (!features.tutorial_shown_session) add("show_tutorial", "tutorial_service.show", { level_id: 2 });
    if (!features.guided_mode_switched_session) add("switch_guided_mode", "guided_mode_service.switch", { target_game_variant: "guided_mode" });
    add("reduce_difficulty", "difficulty_service.reduce", { level_id: 2, difficulty_delta: -1 });
  } else if (scene === "continuous_failure") {
    if (!features.tutorial_shown_session) add("show_tutorial", "tutorial_service.show", { level_id: features.level_id });
    else add("switch_guided_mode", "guided_mode_service.switch", { target_game_variant: "guided_mode" });
    if (features.allow_coin_compensation) add("grant_coin_compensation", "coin_service.grant", { coin_amount: 10 });
  } else if (scene === "android_perf_risk") {
    add("show_perf_tip", "content_service.render_perf_tip", { device_os: "Android" });
    add("reduce_animation", "performance_service.reduce_animation", { level: "safe" });
  } else if (scene === "cart_without_order") {
    add("explain_coin_value", "content_service.render_coin_value", { source: "cart" });
    if (features.allow_coupon && features.coupon_available_count > 0) add("coupon_reminder", "coupon_service.remind", { coupon_count: features.coupon_available_count });
    add("show_recommendation", "recommendation_service.show", { strategy: "cart_related" });
  } else if (scene === "new_user_first_game") {
    add("show_tutorial", "tutorial_service.show", { tutorial_type: "new_user" });
  }
  return { status: actions.length ? "success" : "no_action", actions, fallback_action: "show_static_hint", reason: actions.length ? "scene_plan_generated" : "no_scene_action" };
}

function executeTools(actions, features) {
  return actions.map((action, index) => {
    const timeout = features.tutorial_service_timeout && action.tool_name === "tutorial_service.show";
    return {
      step: action.step,
      action_type: action.action_type,
      tool_name: action.tool_name,
      status: timeout ? "timeout" : "success",
      latency_ms: timeout ? 500 : 18 + index * 7,
      retry_count: timeout ? 1 : 0,
      error_code: timeout ? "mock_timeout" : null,
      mock_only: true,
    };
  });
}

export function runDecision(rawFeatures = {}, testCase = "custom") {
  const features = normalizeFeatures(rawFeatures);
  const classification = classify(features);
  const gate = guardrail(features);
  const generatedPlan = plan(classification.scene, features, gate);
  const toolResults = executeTools(generatedPlan.actions, features);
  const failedTool = toolResults.find((item) => item.status !== "success");
  const decisionStatus = failedTool ? "fallback" : generatedPlan.status;
  const response = {
    request_id: `demo_req_${randomUUID().slice(0, 8)}`,
    decision_id: `demo_dec_${randomUUID().slice(0, 8)}`,
    test_case: testCase,
    mock_only: true,
    created_at: new Date().toISOString(),
    normalized_features: features,
    decision_trace: classification.trace,
    guardrail: gate,
    decision: {
      scene_type: classification.scene,
      decision_status: decisionStatus,
      actions: failedTool ? [] : generatedPlan.actions,
      planned_actions: generatedPlan.actions,
      fallback_action: failedTool ? "show_static_hint" : generatedPlan.fallback_action,
      reason: failedTool ? "mock_tool_execution_failed" : generatedPlan.reason,
    },
    tool_results: toolResults,
  };
  auditLog.unshift({ request_id: response.request_id, decision_id: response.decision_id, test_case: testCase, scene_type: classification.scene, decision_status: decisionStatus, action_count: generatedPlan.actions.length, created_at: response.created_at });
  if (auditLog.length > AUDIT_LIMIT) auditLog.length = AUDIT_LIMIT;
  return response;
}

export function runAgentRequest(rawFeatures = {}, testCase = "custom") {
  try {
    if (bool(rawFeatures.simulate_agent_crash)) throw new Error("mock_agent_runtime_crash");
    return runDecision(rawFeatures, testCase);
  } catch (error) {
    const createdAt = new Date().toISOString();
    const response = {
      request_id: `demo_req_${randomUUID().slice(0, 8)}`,
      decision_id: null,
      test_case: testCase,
      mock_only: true,
      created_at: createdAt,
      system_status: "degraded",
      normalized_features: normalizeFeatures(rawFeatures),
      decision_trace: [],
      guardrail: { allowed: false, reason: "agent_runtime_unavailable" },
      decision: {
        scene_type: "system_fallback",
        decision_status: "fallback",
        actions: [],
        planned_actions: [],
        fallback_action: "show_static_hint",
        reason: "agent_runtime_error_caught_by_backend",
      },
      tool_results: [],
      failure_event: {
        component: "agent_decision_engine",
        error_code: error.message,
        detected: true,
        service_process_alive: true,
      },
    };
    auditLog.unshift({ request_id: response.request_id, decision_id: null, test_case: testCase, scene_type: "system_fallback", decision_status: "fallback", failure_component: "agent_decision_engine", action_count: 0, created_at: createdAt });
    if (auditLog.length > AUDIT_LIMIT) auditLog.length = AUDIT_LIMIT;
    return response;
  }
}

function pushBounded(list, record) {
  list.unshift(record);
  if (list.length > AUDIT_LIMIT) list.length = AUDIT_LIMIT;
}

function stableGroup(experimentId, userIdHash) {
  const groups = ["holdout", "fixed_rule", "agent"];
  const digest = createHash("sha256").update(`${experimentId}:${userIdHash}`).digest();
  return groups[digest.readUInt32BE(0) % groups.length];
}

function assignExperiment(body = {}) {
  const userIdHash = String(body.user_id_hash || "").trim();
  const experimentId = String(body.experiment_id || "coin_game_level2_agent_v1").trim();
  if (!userIdHash) throw new Error("user_id_hash_required");
  const assignmentKey = `${experimentId}:${userIdHash}`;
  const allowedGroups = new Set(["holdout", "fixed_rule", "agent"]);
  const forcedGroup = allowedGroups.has(body.force_group) ? body.force_group : null;
  const storedGroup = assignmentStore.get(assignmentKey);
  const abGroup = forcedGroup || storedGroup || stableGroup(experimentId, userIdHash);
  assignmentStore.set(assignmentKey, abGroup);
  return {
    experiment_id: experimentId,
    ab_group: abGroup,
    enrolled: true,
    assignment_version: "mock-1.0.0",
    assignment_source: forcedGroup ? "test_override" : storedGroup ? "stable_store" : "deterministic_hash",
    mock_only: true,
  };
}

function ingestEvent(body = {}) {
  const required = ["event_id", "event_name", "event_time", "trace_id", "user_id_hash", "session_id"];
  const missing = required.filter((field) => !body[field]);
  if (missing.length) throw new Error(`missing_event_fields:${missing.join(",")}`);
  const duplicate = ingestedEventIds.has(body.event_id);
  ingestedEventIds.add(body.event_id);
  return {
    accepted: true,
    duplicate,
    event_id: body.event_id,
    trace_id: body.trace_id,
    handling: duplicate ? "deduplicated" : "accepted_for_realtime_and_warehouse",
    mock_only: true,
  };
}

function runFixedRule(rawFeatures = {}) {
  const features = normalizeFeatures(rawFeatures);
  const gate = guardrail(features);
  const actions = [];
  if (gate.allowed && features.trigger_event_name === "level_fail") {
    if (features.fail_count_session >= 2) {
      actions.push({ step: 1, action_type: "switch_guided_mode", tool_name: "guided_mode_service.switch", params: { target_game_variant: "guided_mode" } });
      actions.push({ step: 2, action_type: "reduce_difficulty", tool_name: "difficulty_service.reduce", params: { level_id: features.level_id, difficulty_delta: -1 } });
    } else {
      actions.push({ step: 1, action_type: "show_tutorial", tool_name: "tutorial_service.show", params: { level_id: features.level_id } });
    }
  }
  const toolResults = executeTools(actions, features);
  const failedTool = toolResults.find((item) => item.status !== "success");
  return {
    request_id: `rule_req_${randomUUID().slice(0, 8)}`,
    decision_id: `rule_dec_${randomUUID().slice(0, 8)}`,
    mock_only: true,
    normalized_features: features,
    decision_trace: [{ label: "固定阈值：level_fail 后按失败次数执行", evaluated: true, selected: actions.length > 0 }],
    guardrail: gate,
    decision: {
      scene_type: actions.length ? "fixed_rule_level_fail" : "no_action",
      decision_status: failedTool ? "fallback" : actions.length ? "success" : "no_action",
      actions: failedTool ? [] : actions,
      planned_actions: actions,
      fallback_action: "show_static_hint",
      reason: failedTool ? "mock_tool_execution_failed" : actions.length ? "fixed_rule_triggered" : "fixed_rule_not_triggered",
    },
    tool_results: toolResults,
  };
}

function runHoldout(rawFeatures = {}) {
  return {
    request_id: `holdout_req_${randomUUID().slice(0, 8)}`,
    decision_id: null,
    mock_only: true,
    normalized_features: normalizeFeatures(rawFeatures),
    decision_trace: [{ label: "Holdout 不执行产品干预", evaluated: true, selected: true }],
    guardrail: { allowed: false, reason: "experiment_holdout" },
    decision: {
      scene_type: "holdout",
      decision_status: "no_action",
      actions: [],
      planned_actions: [],
      fallback_action: null,
      reason: "experiment_holdout",
    },
    tool_results: [],
  };
}

function recordDelivery(body = {}) {
  const required = ["decision_id", "trace_id", "action_type", "delivery_status", "event_time"];
  const missing = required.filter((field) => !body[field]);
  if (missing.length) throw new Error(`missing_delivery_fields:${missing.join(",")}`);
  const record = { ...body, persisted_at: new Date().toISOString(), mock_only: true };
  pushBounded(deliveryLog, record);
  return { persisted: true, record, mock_only: true };
}

function recordOutcome(body = {}) {
  const required = ["user_id_hash", "experiment_id", "outcome_date", "metrics"];
  const missing = required.filter((field) => !body[field]);
  if (missing.length) throw new Error(`missing_outcome_fields:${missing.join(",")}`);
  const record = { ...body, accepted_at: new Date().toISOString(), mock_only: true };
  pushBounded(outcomeLog, record);
  return { accepted: true, record, mock_only: true };
}

export function runPipelineRequest(body = {}) {
  const pipelineId = `pipe_${randomUUID().slice(0, 8)}`;
  const traceId = body.trace_id || `trace_${randomUUID().slice(0, 8)}`;
  const userIdHash = body.user_id_hash || `synthetic_${randomUUID().slice(0, 8)}`;
  const sessionId = body.session_id || `session_${randomUUID().slice(0, 8)}`;
  const event = {
    event_id: body.event?.event_id || `event_${randomUUID().slice(0, 8)}`,
    event_name: body.event?.event_name || body.key_features?.trigger_event_name || "level_fail",
    event_time: body.event?.event_time || new Date().toISOString(),
    trace_id: traceId,
    user_id_hash: userIdHash,
    session_id: sessionId,
    payload: body.event?.payload || {},
  };
  const stages = [];
  const stage = (id, label, status, detail) => stages.push({ id, label, status, detail, completed_at: new Date().toISOString() });

  stage("frontend_event", "前端埋点", "success", `${event.event_name} 已形成标准事件`);
  const ingestion = ingestEvent(event);
  stage("backend_ingest", "Backend 监听", ingestion.duplicate ? "deduplicated" : "success", ingestion.handling);

  const assignment = assignExperiment({
    user_id_hash: userIdHash,
    experiment_id: body.experiment_id,
    force_group: body.force_group,
  });
  stage("experiment_assignment", "实验分桶", "success", `${assignment.ab_group} · ${assignment.assignment_source}`);

  const presetFeatures = body.test_case && TEST_CASES[body.test_case] ? TEST_CASES[body.test_case].features : {};
  const keyFeatures = {
    ...presetFeatures,
    ...(event.payload || {}),
    ...(body.key_features || {}),
    trigger_event_name: body.key_features?.trigger_event_name || event.payload?.trigger_event_name || presetFeatures.trigger_event_name || event.event_name,
  };
  const normalizedFeatures = normalizeFeatures(keyFeatures);
  stage("feature_build", "特征构建", "success", `构建 ${Object.keys(normalizedFeatures).length} 个标准特征`);

  let decisionResponse;
  if (assignment.ab_group === "agent") decisionResponse = runAgentRequest(normalizedFeatures, body.test_case || "pipeline_custom");
  else if (assignment.ab_group === "fixed_rule") decisionResponse = runFixedRule(normalizedFeatures);
  else decisionResponse = runHoldout(normalizedFeatures);
  stage("decision", "策略决策", decisionResponse.decision.decision_status === "fallback" ? "fallback" : "success", `${assignment.ab_group} · ${decisionResponse.decision.scene_type}`);

  const toolResults = decisionResponse.tool_results || [];
  const toolStatus = toolResults.some((item) => item.status !== "success") ? "fallback" : "success";
  stage("tool_execution", "Mock 动作执行", toolStatus, toolResults.length ? `${toolResults.filter((item) => item.status === "success").length}/${toolResults.length} 成功` : "本组不执行动作");

  const warehouseRecord = {
    pipeline_id: pipelineId,
    trace_id: traceId,
    event_id: event.event_id,
    user_id_hash: userIdHash,
    session_id: sessionId,
    experiment_id: assignment.experiment_id,
    ab_group: assignment.ab_group,
    scene_type: decisionResponse.decision.scene_type,
    decision_status: decisionResponse.decision.decision_status,
    planned_action_count: decisionResponse.decision.planned_actions.length,
    successful_action_count: toolResults.filter((item) => item.status === "success").length,
    event_time: event.event_time,
    mock_only: true,
  };
  stage("warehouse_return", "数据回流", "success", "干预与执行结果已写入临时审计记录");

  const response = {
    pipeline_id: pipelineId,
    trace_id: traceId,
    mock_only: true,
    boundary: "本地/在线 Mock 验证，不调用真实淘金币业务接口",
    assignment,
    ingestion,
    stages,
    decision: decisionResponse.decision,
    decision_trace: decisionResponse.decision_trace,
    tool_results: toolResults,
    failure_event: decisionResponse.failure_event || null,
    warehouse_record: warehouseRecord,
  };
  pushBounded(pipelineAudit, {
    pipeline_id: pipelineId,
    trace_id: traceId,
    ab_group: assignment.ab_group,
    decision_status: decisionResponse.decision.decision_status,
    stage_count: stages.length,
    created_at: new Date().toISOString(),
  });
  return response;
}

function loadJson(relativePath, fallback) {
  try {
    return JSON.parse(readFileSync(join(PACKAGE_ROOT, relativePath), "utf8"));
  } catch {
    return fallback;
  }
}

function allowedOrigin(requestOrigin) {
  const configured = (process.env.ALLOWED_ORIGINS || "*").split(",").map((item) => item.trim()).filter(Boolean);
  if (configured.includes("*")) return "*";
  return configured.includes(requestOrigin) ? requestOrigin : configured[0] || "null";
}

function sendJson(res, status, payload, origin = "*") {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
  });
  res.end(body);
}

function sendStatic(res, relativePath) {
  const allowedFiles = new Set([
    "index.html",
    "runtime-config.js",
    "dashboard_data.js",
    "agent_test_data.js",
    "synthetic_data/agent_full_replay/full_agent_replay_results.csv",
  ]);
  if (!allowedFiles.has(relativePath)) return false;
  try {
    const body = readFileSync(join(STATIC_ROOT, relativePath));
    const extension = relativePath.split(".").pop();
    const contentTypes = { html: "text/html; charset=utf-8", js: "text/javascript; charset=utf-8", csv: "text/csv; charset=utf-8" };
    res.writeHead(200, { "Content-Type": contentTypes[extension] || "application/octet-stream", "Content-Length": body.length, "X-Content-Type-Options": "nosniff" });
    res.end(body);
    return true;
  } catch {
    return false;
  }
}

function sendJavaScript(res, source) {
  const body = Buffer.from(source, "utf8");
  res.writeHead(200, { "Content-Type": "text/javascript; charset=utf-8", "Content-Length": body.length, "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store" });
  res.end(body);
}

async function readJson(req) {
  let total = 0;
  const chunks = [];
  for await (const chunk of req) {
    total += chunk.length;
    if (total > MAX_BODY_BYTES) throw new Error("request_body_too_large");
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString("utf8");
  return raw ? JSON.parse(raw) : {};
}

export const server = createServer(async (req, res) => {
  const origin = allowedOrigin(req.headers.origin || "");
  if (req.method === "OPTIONS") return sendJson(res, 204, {}, origin);
  const url = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);
  try {
    if (req.method === "GET" && (url.pathname === "/demo" || url.pathname === "/demo/")) {
      if (sendStatic(res, "index.html")) return;
    }
    if (req.method === "GET" && url.pathname === "/demo/runtime-config.js") {
      const protocol = String(req.headers["x-forwarded-proto"] || "http").split(",")[0].trim();
      const publicBaseUrl = `${protocol}://${req.headers.host}`;
      return sendJavaScript(res, `window.APP_CONFIG = ${JSON.stringify({ API_BASE_URL: publicBaseUrl })};\n`);
    }
    if (req.method === "GET" && url.pathname.startsWith("/demo/")) {
      const relativePath = decodeURIComponent(url.pathname.slice("/demo/".length));
      if (sendStatic(res, relativePath)) return;
    }
    if (req.method === "GET" && url.pathname === "/health") {
      return sendJson(res, 200, { status: "ok", service: "coin-game-agent-sandbox-api", mock_only: true, started_at: startedAt }, origin);
    }
    if (req.method === "GET" && url.pathname === "/api/v1/meta") {
      return sendJson(res, 200, { service: "coin-game-agent-sandbox-api", version: "1.0.0", mock_only: true, data_boundary: "synthetic five-table data only", supported_scenes: SCENE_ORDER }, origin);
    }
    if (req.method === "GET" && url.pathname === "/api/v1/test-cases") {
      return sendJson(res, 200, { test_cases: Object.entries(TEST_CASES).map(([id, value]) => ({ id, ...value })) }, origin);
    }
    if (req.method === "POST" && url.pathname === "/api/v1/agent/test") {
      const body = await readJson(req);
      const preset = body.test_case && TEST_CASES[body.test_case] ? TEST_CASES[body.test_case].features : {};
      const response = runAgentRequest({ ...preset, ...(body.key_features || {}) }, body.test_case || "custom");
      return sendJson(res, 200, response, origin);
    }
    if (req.method === "POST" && url.pathname === "/api/v1/pipeline/test") {
      const body = await readJson(req);
      const preset = body.test_case && TEST_CASES[body.test_case] ? TEST_CASES[body.test_case].features : {};
      return sendJson(res, 200, runPipelineRequest({ ...body, key_features: { ...preset, ...(body.key_features || {}) } }), origin);
    }
    if (req.method === "POST" && url.pathname === "/v1/experiments/assign") {
      return sendJson(res, 200, assignExperiment(await readJson(req)), origin);
    }
    if (req.method === "POST" && url.pathname === "/v1/events/ingest") {
      return sendJson(res, 202, ingestEvent(await readJson(req)), origin);
    }
    if (req.method === "POST" && url.pathname === "/v1/interventions/delivery") {
      return sendJson(res, 200, recordDelivery(await readJson(req)), origin);
    }
    if (req.method === "POST" && url.pathname === "/v1/eval/outcomes/backfill") {
      return sendJson(res, 200, recordOutcome(await readJson(req)), origin);
    }
    if (req.method === "GET" && url.pathname === "/api/v1/audit") {
      return sendJson(res, 200, { ephemeral: true, max_records: AUDIT_LIMIT, records: auditLog.slice(0, Math.min(100, number(url.searchParams.get("limit"), 20))) }, origin);
    }
    if (req.method === "GET" && url.pathname === "/api/v1/pipeline/audit") {
      return sendJson(res, 200, {
        ephemeral: true,
        max_records: AUDIT_LIMIT,
        records: pipelineAudit.slice(0, Math.min(100, number(url.searchParams.get("limit"), 20))),
        counters: {
          assignments: assignmentStore.size,
          unique_events: ingestedEventIds.size,
          deliveries: deliveryLog.length,
          outcomes: outcomeLog.length,
        },
      }, origin);
    }
    if (req.method === "GET" && url.pathname === "/api/v1/replay/summary") {
      return sendJson(res, 200, loadJson("synthetic_data/agent_full_replay/full_agent_replay_summary.json", { unavailable: true }), origin);
    }
    if (req.method === "GET" && url.pathname === "/api/v1/replay/decision-tree") {
      return sendJson(res, 200, loadJson("synthetic_data/agent_full_replay/full_agent_decision_tree.json", { unavailable: true }), origin);
    }
    return sendJson(res, 404, { error: "not_found", path: url.pathname }, origin);
  } catch (error) {
    return sendJson(res, 400, { error: "bad_request", detail: error.message }, origin);
  }
});

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  server.listen(PORT, HOST, () => {
    console.log(`Agent sandbox API listening on ${HOST}:${PORT}`);
  });
}
