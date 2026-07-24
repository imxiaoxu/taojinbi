import assert from "node:assert/strict";
import { TEST_CASES, runAgentRequest, runDecision, runPipelineRequest } from "./app.mjs";

for (const [caseId, testCase] of Object.entries(TEST_CASES)) {
  const response = runAgentRequest(testCase.features, caseId);
  assert.equal(response.mock_only, true, `${caseId}: mock boundary missing`);
  assert.equal(response.decision.scene_type, testCase.expected_scene, `${caseId}: scene mismatch`);
  assert.equal(response.tool_results.every((item) => item.mock_only), true, `${caseId}: non-mock tool result`);
}

const level2 = runDecision(TEST_CASES.level2_first_fail.features, "level2_first_fail");
assert.deepEqual(level2.decision.actions.map((item) => item.action_type), ["show_tutorial", "switch_guided_mode", "reduce_difficulty"]);

const guardrail = runDecision(TEST_CASES.guardrail_block.features, "guardrail_block");
assert.equal(guardrail.decision.decision_status, "no_action");
assert.equal(guardrail.guardrail.reason, "session_frequency_limit");

const timeout = runDecision(TEST_CASES.tool_timeout.features, "tool_timeout");
assert.equal(timeout.decision.decision_status, "fallback");
assert.equal(timeout.decision.fallback_action, "show_static_hint");

const runtimeError = runAgentRequest(TEST_CASES.agent_runtime_error.features, "agent_runtime_error");
assert.equal(runtimeError.system_status, "degraded");
assert.equal(runtimeError.decision.decision_status, "fallback");
assert.equal(runtimeError.failure_event.detected, true);
assert.equal(runtimeError.failure_event.service_process_alive, true);

const agentPipeline = runPipelineRequest({
  user_id_hash: "synthetic_agent_test",
  session_id: "session_agent",
  force_group: "agent",
  test_case: "level2_first_fail",
});
assert.equal(agentPipeline.assignment.ab_group, "agent");
assert.equal(agentPipeline.stages.length, 7);
assert.equal(agentPipeline.decision.scene_type, "level_2_block");

const fixedRulePipeline = runPipelineRequest({
  user_id_hash: "synthetic_rule_test",
  session_id: "session_rule",
  force_group: "fixed_rule",
  test_case: "continuous_failure",
});
assert.equal(fixedRulePipeline.assignment.ab_group, "fixed_rule");
assert.equal(fixedRulePipeline.tool_results.length, 2);

const crashedAgentPipeline = runPipelineRequest({
  user_id_hash: "synthetic_crash_test",
  session_id: "session_crash",
  force_group: "agent",
  test_case: "agent_runtime_error",
});
assert.equal(crashedAgentPipeline.decision.decision_status, "fallback");
assert.equal(crashedAgentPipeline.failure_event.component, "agent_decision_engine");
assert.equal(crashedAgentPipeline.failure_event.detected, true);

const holdoutPipeline = runPipelineRequest({
  user_id_hash: "synthetic_holdout_test",
  session_id: "session_holdout",
  force_group: "holdout",
  test_case: "level2_first_fail",
});
assert.equal(holdoutPipeline.assignment.ab_group, "holdout");
assert.equal(holdoutPipeline.decision.decision_status, "no_action");
assert.equal(holdoutPipeline.tool_results.length, 0);

console.log(`Sandbox smoke tests: ${Object.keys(TEST_CASES).length + 14}/${Object.keys(TEST_CASES).length + 14} passed`);
