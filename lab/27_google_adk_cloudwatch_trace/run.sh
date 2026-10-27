#!/usr/bin/env bash
# Runs the ADK agent under the ADOT launcher and exports traces to CloudWatch.
#
#   ./run.sh plain   -> run A: content kept on spans (no masking)
#   ./run.sh masked  -> run B: OPENINFERENCE_HIDE_INPUTS/OUTPUTS=True
#   ./run.sh redact  -> run C: run B + AWS_REDACT_SPAN_ATTRIBUTES (ADOT-level, all spans)
#   ./run.sh sid     -> run E: plain + session.id stamped on every span (token-aggregation experiment)
#   ./run.sh tok     -> run F: sid + gen_ai.usage.total_tokens / gen_ai.system on LLM spans
#   ./run.sh bedrock -> run I: tok + LLM spans relabelled as a Bedrock model (diagnostic only)
#   ./run.sh root    -> run J: tok + per-trace token sums stamped on the root invocation span
#
# Requires GOOGLE_API_KEY in ./.env (see .env.example). Never commit .env.
set -euo pipefail
cd "$(dirname "$0")"

MODE="${1:-plain}"
if [[ -f .env ]]; then set -a; source .env; set +a; fi
: "${GOOGLE_API_KEY:?GOOGLE_API_KEY is not set (put it in .env)}"

export AWS_REGION="${AWS_REGION:-us-west-2}"
export AWS_DEFAULT_REGION="$AWS_REGION"

AGENT_ID="knox-adk-trace-test"
LOG_GROUP="/aws/bedrock-agentcore/runtimes/${AGENT_ID}"
STAMP="$(date +%Y%m%d-%H%M%S)"
SESSION_ID="knox-adk-${MODE}-${STAMP}"

# --- ADOT settings for an agent hosted outside AgentCore (AWS docs) ---
export AGENT_OBSERVABILITY_ENABLED=true
export AWS_GENAI_CONTENT_EXTRACTION_OPT_OUT=true   # keep prompt/response text on spans
export OTEL_PYTHON_DISTRO=aws_distro
export OTEL_PYTHON_CONFIGURATOR=aws_configurator
export OTEL_RESOURCE_ATTRIBUTES="service.name=${AGENT_ID},deployment.environment.name=test,aws.log.group.names=${LOG_GROUP}"
export OTEL_EXPORTER_OTLP_LOGS_HEADERS="x-aws-log-group=${LOG_GROUP},x-aws-log-stream=runtime-logs,x-aws-metric-namespace=bedrock-agentcore"
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_TRACES_EXPORTER="${OTEL_TRACES_EXPORTER:-otlp}"   # set to console,otlp to also print spans
export OTEL_LOGS_EXPORTER=none
export OTEL_METRICS_EXPORTER=none
# Spans go to the shared aws/spans log group (no OTEL_EXPORTER_OTLP_TRACES_HEADERS),
# so no extra CloudWatch Logs resource policy is needed.

if [[ "$MODE" == "masked" || "$MODE" == "redact" ]]; then
  # OpenInference-level masking: affects spans created by the OpenInference instrumentor only.
  export OPENINFERENCE_HIDE_INPUTS=True
  export OPENINFERENCE_HIDE_OUTPUTS=True
fi
if [[ "$MODE" == "sid" ]]; then
  # Experiment: stamp session.id/user.id onto every span (incl. ADK-native LLM spans).
  export COPY_SESSION_ID=1
fi
if [[ "$MODE" == "root" ]]; then
  # Experiment 4: tok + per-trace token sums copied onto the root (invocation) span.
  export COPY_ROOT_TOKENS=1
fi
if [[ "$MODE" == "tok" || "$MODE" == "bedrock" || "$MODE" == "root" ]]; then
  # Experiment 2: sid + add gen_ai.usage.total_tokens and gen_ai.system on LLM spans.
  export COPY_SESSION_ID=1
  export COPY_TOKEN_TOTAL=1
fi
if [[ "$MODE" == "bedrock" ]]; then
  # Experiment 3 (diagnostic): relabel LLM spans as a Bedrock model so we can see whether
  # the console token aggregation only counts recognised providers.
  export FAKE_BEDROCK=1
fi
if [[ "$MODE" == "redact" ]]; then
  # ADOT-level redaction: applies to every span attribute, including ADK's native
  # gcp.vertex.agent LLM spans that OpenInference flags do not touch.
  export AWS_REDACT_SPAN_ATTRIBUTES='llm.input_messages.*,llm.output_messages.*,input.value,output.value,gen_ai.input.messages,gen_ai.output.messages'
fi

echo "mode=$MODE region=$AWS_REGION session_id=$SESSION_ID"
echo "$SESSION_ID" >> sessions.log
.venv/bin/opentelemetry-instrument .venv/bin/python agent.py --session-id "$SESSION_ID"
echo
echo "done. verify with: .venv/bin/python verify.py --session-id $SESSION_ID"
