# Evidence — Google ADK + Claude on Bedrock → OpenInference → ADOT → CloudWatch

[한국어](DETAILS.md) · English

Verification records and documentation evidence behind the per-question answers in [README.en.md](README.en.md). Environment: Google ADK 2.13.0 + Claude Sonnet 5.5 on Amazon Bedrock (ADK `AnthropicLlm` native, no LiteLLM), openinference-instrumentation-google-adk 1.0.5, aws-opentelemetry-distro 0.21.0, 2026-10-27.

Contents: [How it works](#how-it-works) · [(a) Multi-turn tracing](#a-multi-turn-tracing) · [(b) PII masking](#b-pii-masking) · [Bedrock setup](#bedrock-setup-adk--anthropicllm--bedrock-runtime) · [(c) SSO/MFA dashboard](#c-ssomfa-dashboard) · [(d) Analytics](#d-analytics) · [Querying Omni from a coding agent](#querying-omni-from-a-coding-agent)

## How it works

```
 run.sh <mode>
   │  sets OTEL_* / AGENT_OBSERVABILITY_ENABLED and other env vars
   │  session_id = knox-adk-<mode>-<timestamp>
   ▼
 opentelemetry-instrument python agent.py --session-id ...     ← ADOT launcher
   │
   │  ┌──────────────────────────────────────────────────────────────────┐
   │  │ At process start ADOT (aws_distro) attaches auto-instrumentation │
   │  │  • openinference-instrumentation-google-adk  (CHAIN/AGENT/TOOL)   │
   │  │  • httpx instrumentation                      (POST spans)        │
   │  │  • ADK 2.x built-in OTel tracing gcp.vertex.agent (creates LLM span) │
   │  │    └ the OpenInference wrapper writes llm.input_messages.* onto this span │
   │  └──────────────────────────────────────────────────────────────────┘
   ▼
 agent.py : InMemoryRunner.run_async(user_id=, session_id=, new_message=)  ×3 turns
   │     model = ADK AnthropicLlm(client=AsyncAnthropic(base_url=https://bedrock-runtime.<region>.amazonaws.com/anthropic,
   │                                                    api_key=provide_token()))  → Claude Sonnet 5.5 on Bedrock
   │
   ▼
 OTel SDK (TracerProvider) ── OTLP http/protobuf ──▶ CloudWatch
                                                     ├─ aws/spans log group (all spans)
                                                     ├─ X-Ray index (1% sample by default)
                                                     └─ GenAI Observability console
                                                        Agents › Sessions › Traces › Spans
   ▲
   │  verify.py : two-step Logs Insights query
   │    ① @message like "<session_id>"  → collect traceIds
   │    ② all spans of those traceIds   → print scope / kind / session.id / masking state
```

What one session looks like in CloudWatch (one turn = one trace):

```
 session.id = knox-adk-plain-20261027-001352
 ├─ trace #1 (turn 1 "my name is Gildong Hong ...")
 │   └─ invocation [knox-adk-trace-test]        CHAIN  openinference  session.id ✔
 │       └─ invoke_workflow knox_trace_test_agent CHAIN  openinference  session.id ✔
 │           └─ agent_run [knox_trace_test_agent] AGENT  openinference  session.id ✔
 │               ├─ invoke_agent knox_trace_test_agent  LLM  gcp.vertex.agent
 │               │     gen_ai.usage.input/output_tokens, llm.input_messages.* (raw prompt)
 │               │     gen_ai.conversation.id ✔   session.id ✘
 │               └─ POST bedrock-runtime.<region>.amazonaws.com/anthropic/v1/messages  httpx
 ├─ trace #2 (turn 2 "weather in Seoul")  + execute_tool get_weather (TOOL)
 └─ trace #3 (turn 3 "what was my name ...")
```

## (a) Multi-turn tracing

- All three turns arrive in `aws/spans`; one turn = one trace, and the three traces are grouped under the same session. The console (GenAI Observability → Bedrock AgentCore → Agents → Sessions view) shows **Traces (3)**, and in the trace detail the ADK LLM span is recognized as `aws.genai.span_kind = LLM`, so Model / Input tokens / Output tokens are displayed.
- **Spans come from two sources.** `openinference.instrumentation.google_adk` (invocation → invoke_workflow → agent_run → execute_tool, all carrying `session.id`) and ADK 2.x built-in tracing `gcp.vertex.agent` (the `invoke_agent` LLM span, carrying tokens and the raw prompt, no `session.id`). The OpenInference attributes on the ADK LLM span (`llm.input_messages.*` etc.) are written there by OpenInference ADK 1.0.5, which patches ADK's `trace_call_llm` hook and sets attributes directly on the ADK span, bypassing the masking tracer (OITracer).
- **Two session keys**: OpenInference spans use `session.id`, the ADK LLM span uses `gen_ai.conversation.id`. Queries and aggregations must OR the two attributes or the LLM span is missed. `session.id` is only extracted from the keyword arguments of `Runner.run_async(user_id=..., session_id=...)`.
- **Version dependency**: the AWS AgentCore documentation (OpenInference ADK 0.1.x) shows a `call_llm` LLM span under the OpenInference scope, but with ADK 2.13 + OpenInference ADK 1.0.5 the LLM span only comes from the ADK built-in scope. Which masking flag is effective depends on the version pair, so re-verify with the actual versions.
- The first ingestion can lag by 10 minutes or more (not data loss).

### How Total tokens is aggregated

- **The console Agent view's Total tokens and cost are computed from Bedrock model invocation records, not from spans.** The values in the Agents table (5.7K / $0.016, 7K / $0.009) match the token sums in the Bedrock invocation logs (Sonnet 5.5: 8 calls, 5,678; Haiku 4.5: 8 calls, 6,960). Screenshot: `img/agentcore-observability.png`.
- **Span-based sums undercount turns with tool calls.** The ADK LLM span is one per turn, so the tokens of the tool-call round trip (the second model call) are missed (span sum for Sonnet 4,341 vs invocation records 5,678). Span-based paths such as Logs Insights and Omni must account for this gap.
- **CloudWatch Omni also aggregates ADK tokens.** The Agent overview showed Sessions 10, Traces 28, Total tokens 12.9k (`img/cloudwatch-omni.png`). The Tokens column of the "Top 10 agents" table showed 0, inconsistent with the summary card.
- When summing tokens per session in Logs Insights, filter on `gen_ai.conversation.id` (filtering on `session.id` misses the LLM span and returns 0/null).
```
filter attributes.gen_ai.conversation.id = "<session_id>" and attributes.aws.genai.span_kind = "LLM"
| stats sum(attributes.gen_ai.usage.input_tokens) as input_tokens,
        sum(attributes.gen_ai.usage.output_tokens) as output_tokens, count(*) as llm_spans
```

## (b) PII masking

| Mode | OpenInference spans (CHAIN/AGENT/TOOL) | ADK built-in LLM span (`gcp.vertex.agent`) |
|---|---|---|
| plain | raw content stored | raw content stored (name and phone number as is) |
| masked (`OPENINFERENCE_HIDE_*`) | `__REDACTED__` | **raw content remains** |
| redact (+ `AWS_REDACT_SPAN_ATTRIBUTES`) | `REDACTED` | `REDACTED` |
| adot-redact (`AWS_REDACT_SPAN_ATTRIBUTES` only, `run_q2b.sh`) | `REDACTED` (`input.value` of `invocation` and `execute_tool`) | `REDACTED` (`input.value`, `llm.input_messages.*`) |
| extract (ADOT default content extraction, `run_q2b.sh`) | content removed (`input.value`/`output.value` moved to log events) | **PII remains**: the nested `llm.input_messages.N.message.contents.0.message_content.text` is not extracted |
| adk-nocontent (`ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false`, `run_q2b.sh`) | raw (no change) | **PII remains** (the attributes are written by the OpenInference wrapper, not by ADK) |

- **Conclusion**: OpenInference flags alone are not enough. ADOT `AWS_REDACT_SPAN_ATTRIBUTES='llm.input_messages.*,llm.output_messages.*,input.value,output.value,gen_ai.input.messages,gen_ai.output.messages'` **on its own** masks spans from both sources (0 PII fields remaining across 17 spans). The wildcard also catches nested keys.
- **The log path must be closed separately.** With `AGENT_OBSERVABILITY_ENABLED=true`, ADOT turns on the log exporter and ADK emits `gen_ai.client.inference.operation.details` log events containing the full prompt and response. `AWS_REDACT_SPAN_ATTRIBUTES` is a span processor and does not touch these events (verified: with redaction on, 4 ADK events still reached the log group with PII). Turn it off with `OTEL_LOGS_EXPORTER=none`, or isolate the log group and apply a CloudWatch Logs data protection policy.
- **ADOT's default content extraction (extract) is not enough either.** The ADOT LLO handler only moves fixed keys such as `input.value` and `llm.input_messages.{i}.message.content` to logs; the nested key on the ADK span, `llm.input_messages.{i}.message.contents.{j}.message_content.text`, is not covered, so PII remains. Pitfall: ADOT does not create the log stream named in `x-aws-log-stream`; if it does not exist the export fails silently with `400`, so create it in advance.
- **Settings with no effect**: `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false` (ineffective because the OpenInference wrapper writes the attributes), `OPENINFERENCE_HIDE_*` (OpenInference spans only).
- **Limits**: redaction removes whole attributes, so partial masking (phone number only) needs a custom SpanProcessor or the OpenTelemetry Collector redaction processor. A CloudWatch Logs data protection policy masks only data ingested after the policy is applied, only principals with `logs:Unmask` see the original, and the managed identifiers have no Korean entries (resident registration number, mobile number), so define them as custom regular expressions. Removing content from spans also removes the input of trace-based quality evaluation (AgentCore Evaluations).

## Bedrock setup (ADK + AnthropicLlm → bedrock-runtime)

ADK Python has no Bedrock-specific model class, and the `bedrock/*` registry entries route only through LiteLLM. Because Bedrock natively serves the Anthropic Messages API (`/anthropic`) on the `bedrock-runtime` endpoint, injecting an `AsyncAnthropic(base_url=…/anthropic, api_key=<short-term Bedrock token>)` client into ADK's built-in `AnthropicLlm` calls Claude on Bedrock without LiteLLM or LangChain (an unofficial combination with no Bedrock example in the ADK docs; each part is backed by the ADK and Bedrock docs). The short-term token is produced from AWS credentials by `aws-bedrock-token-generator` (up to 12 hours).

| Run | Model | Spans | PII on OpenInference spans | PII on ADK LLM span | LLM tokens (in→out) |
|---|---|---|---|---|---|
| Haiku plain | Haiku 4.5 (`us.anthropic.claude-haiku-4-5-20251001-v1:0`) | 13 | 4/10 raw | 3/3 raw | 923→34, 863→38, 699→65 |
| Haiku redact | Haiku 4.5 | 13 | 0 (`REDACTED` 7) | 0 (`REDACTED` 3) | 938→34, 875→41, 699→77 |
| Sonnet plain | Sonnet 5.5 (`us.anthropic.claude-sonnet-5-5`) | 13 | 6/10 raw | 3/3 raw | 766→42, 692→46, 551→41 |
| Sonnet redact | Sonnet 5.5 | 13 | 0 (`REDACTED` 7) | 0 (`REDACTED` 3) | 791→38, 711→52, 551→60 |

- Span tree, session grouping and masking behave identically regardless of model (the `trace_call_llm` hook is independent of the model class).
- **Provider label error**: `gen_ai.request.model` carries the correct Bedrock model ID, but `gen_ai.provider.name=gcp.gemini` and `llm.provider=google` are hard-coded. Bedrock calls may be classified as Google in per-provider aggregation and cost attribution.
- **Bedrock Model Invocation Logging**: when enabled, the raw request and response of every call are stored in `/aws/bedrock/model-invocation-logs`, and the Input/Output columns of the console GenAI Observability → Model Invocations list show them in clear text (including redact sessions, `img/bedrock-model-invocation.png`). Span masking has no effect here, so disable text delivery or apply an account-level CloudWatch Logs data protection policy. Total tokens in Model Invocations (5,678) matches the sum of the 8 Sonnet calls.

## (c) SSO/MFA dashboard

Existing CloudWatch dashboard sharing cannot meet the requirement; CloudWatch Omni is the closest answer. The customer's region (Ireland, eu-west-1) is an Omni-supported region.

| Candidate | Sign-in | MFA | AWS console access | Trace/session views | Permission separation | Constraints |
|---|---|---|---|---|---|---|
| CloudWatch dashboard sharing (email) | Cognito user pool, password | not mentioned in the docs | not required | no (metric widgets; Logs widgets hidden by default) | per dashboard | up to 5 users; every recipient gets permission to read all metrics and EC2 tags in the account |
| CloudWatch dashboard sharing (SAML SSO) | Cognito + SAML IdP | IdP policy | not required | no | all dashboards in the account open to every SSO user | no fine-grained control; the GenAI console Sessions/Traces pages are not shareable |
| CloudWatch Omni | organization URL `https://<domain>.cloudwatch-omni.global.app.aws`, IAM Identity Center (external IdPs such as Okta, Entra) | enforced by IAM Identity Center / IdP policy | not required | yes; in a real Space the ADK agent appeared in Agent overview with 10 sessions, 28 traces, 12.9k tokens (verified); session/trace detail views and Omni dashboards per docs | Viewer/Editor/Space Admin/Custom grants + data scopes (row level) | Space = account + region; the IAM Identity Center instance must be in the domain's region (multi-region replication solves this); billed by data volume (ingest/store/scan GB), not seats |
| Amazon Managed Grafana | SAML 2.0 or IAM Identity Center | IdP policy | not required | build yourself (CloudWatch and X-Ray data sources) | per-user/team folder and dashboard permissions | no GenAI-specific session/trace view; must be built |

- Omni design: one domain (sign-in URL, IdP connection) with Spaces per team/environment; external users get a Viewer grant plus a data scope so they see only their agent's rows. Data scopes filter log and trace rows only, so also restrict dataset/export/AI actions with a Custom grant. Members who can see span content see PII, so the masking from (b) must come first.
- Supported regions (11 as of 2026-10-27): N. Virginia, Oregon, Ireland, Canada Central, Mumbai, Singapore, Sydney, Tokyo, Frankfurt, London, São Paulo. Data from unsupported regions is replicated to a supported region with CloudWatch centralization rules (requires AWS Organizations).
- To confirm: whether external users need metric dashboards or session/trace content, and whether the IdP (Okta/Entra/other) and MFA policy can be connected to IAM Identity Center.

## (d) Analytics

| Surface | Nature | What it can do | Constraints |
|---|---|---|---|
| Console GenAI Observability | pre-built views | Model Invocations (invocation count, tokens, TPM quota, latency, errors, throttling); Bedrock AgentCore (Agents → Sessions → Traces → Spans drill-down, filters, time range). Tokens and cost come from Bedrock invocation records and are the most accurate | no custom aggregation or charts; Model Invocations covers Bedrock calls only |
| Transaction Search + Logs Insights | free-form queries | 100% of spans stored in `aws/spans`. Token sums per session, tool-call frequency, turns per session, error span extraction. Metric filters → custom metrics and alarms, Contributor Insights, subscription filters | no span transformation/enrichment; trace summary indexing 1% by default (affects list views only) |
| CloudWatch Omni | AI-assisted analysis + quality evaluation | per-agent token/latency/error/session aggregation views (verified). Omni SQL (logs, traces) / PromQL (metrics); natural-language questions → queries, charts, dashboards, alerts. Quality evaluation backed by Bedrock AgentCore Evaluations (built-in and custom judges, online evaluation). Threads, Slack alerts | evaluators send trace content to the judge model, which may conflict with the masking in (b) |

Recommendation: operational metrics (tokens, cost) from the console Agent view (per agent) and Model Invocations (per model); ad-hoc analysis with Logs Insights; conversation quality with Omni's AgentCore Evaluations (the only option inside CloudWatch); sharing with external users via Omni or Managed Grafana as in (c).

## Querying Omni from a coding agent

- **Agent Toolkit for AWS**: in Claude Code, `/plugin install aws-core@claude-plugins-official` → `/reload-plugins`. The aws-core plugin installs the remote AWS MCP Server (`aws-mcp`) and skills (`aws-observability` contains `references/cloudwatch-omni/`). For Cursor/Kiro, configure MCP and run `npx skills add aws/agent-toolkit-for-aws/skills`.
- **How it works**: the public `cloudwatchomni` API (StartTelemetryQuerySession → StartTelemetryQuery(SQL) → GetTelemetryQueryResults) is called with local AWS credentials. Authorization is IAM permissions plus Space grants, not the Omni web sign-in. `omni_query.py` calls the same API directly.
```sql
SELECT `@timestamp`, name, scope['name'] AS scope, traceId,
       attributes['session.id'] AS session_id, attributes['gen_ai.conversation.id'] AS conversation_id,
       attributes['gen_ai.request.model'] AS model,
       attributes['gen_ai.usage.input_tokens'] AS in_tok, attributes['gen_ai.usage.output_tokens'] AS out_tok
FROM traces.default
WHERE `@timestamp` BETWEEN NOW() - INTERVAL '6 HOUR' AND NOW()
  AND (attributes['session.id'] = '<session>' OR attributes['gen_ai.conversation.id'] = '<session>')
ORDER BY `@timestamp`
```

```text
1) Session list
   In Omni, show a table of trace count, total tokens and average LLM latency per session
   for the knox-adk-trace-test agent over the last 6 hours (keyed by session.id or gen_ai.conversation.id).

2) Full flow of one turn (recommended)
   In session knox-adk-plain-20261027-052755, pick one LLM span (scope gcp.vertex.agent) from the turn that called a tool
   and summarize the system prompt, user input, tool call (name and arguments), tool result, final answer,
   and input/output tokens in one table.

3) PII masking check
   Compare the plain run and the redact run of the same session and show, per span,
   whether input.value / llm.input_messages.* changed to REDACTED.
```

**Result of prompt 2** (`img/omni-plugin.png`): the single ADK LLM span of the tool-calling turn contains the system prompt, full conversation history, tool call, tool result, final answer and tokens. This was a plain run so PII is visible; in a redact run the same fields show `REDACTED`.

| Item | Value | Attribute key |
|---|---|---|
| System prompt | "You are a concise travel helper. Use the get_weather tool when asked about weather. …" + agent name/description appended by ADK | `llm.input_messages.0.message.content` (role=system) |
| User input (this turn) | "What is the weather like in Seoul right now?" | `llm.input_messages.3.message.contents.0.message_content.text` |
| Conversation history (sent along) | user: "Hi, my name is Gildong Hong and my phone number is 010-1234-5678. …" → model: "Nice to meet you, Gildong! …" | `llm.input_messages.1~2.…` |
| Tool call | `get_weather`, arguments `{"city": "Seoul"}` | `llm.output_messages.0.message.tool_calls.0.tool_call.function.{name,arguments}` |
| Tool result | `{"city": "Seoul", "temp_c": 14, "condition": "clear"}` | `llm.input_messages.5.message.content` (role=tool) |
| Final answer | "It's currently clear in Seoul with a temperature of 14°C (57°F). Pack light layers for your trip next week, Gildong!" | `llm.output_messages.0.message.contents.0.message_content.text` |
| Tokens | input 692 / output 46 | `gen_ai.usage.{input,output}_tokens` |

- **Querying by traceId returns 9 spans per turn, not 4.** Two Anthropic SDK spans (`anthropic.messages.create`) and two httpx `POST` spans also appear; they carry neither `session.id` nor `gen_ai.conversation.id`, so a session filter drops them. The two Bedrock calls of a tool-calling turn are each recorded on an SDK span, which is where the gap between session-based token sums and the console (invocation-record aggregation) comes from.
- PII caution: on every path, content enters the coding agent's context unmasked. The capture-time masking from (b) must come first.
