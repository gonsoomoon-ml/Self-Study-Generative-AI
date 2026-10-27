#!/usr/bin/env bash
# Q2(b) PII-masking follow-up runs. Separate from run.sh on purpose (run.sh stays as the
# baseline plain/masked/redact harness).
#
#   ./run_q2b.sh adot-redact -> run K: AWS_REDACT_SPAN_ATTRIBUTES only (no OpenInference flags).
#                               Question: does ADOT redaction alone cover BOTH the OpenInference
#                               CHAIN/AGENT spans and the ADK-native LLM span?
#   ./run_q2b.sh adk-nocontent -> run M: ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false (ADK's own switch).
#                               Question: does ADK stop writing prompt/response text on its own LLM span?
#   ./run_q2b.sh extract     -> run L: ADOT default content-extraction path
#                               (AWS_GENAI_CONTENT_EXTRACTION_OPT_OUT unset, OTEL_LOGS_EXPORTER=otlp).
#                               Question: is prompt/response text removed from spans (incl. the ADK-native
#                               LLM span) and delivered as log events instead?
#
# Needs AWS credentials only (see run.sh).
set -euo pipefail
cd "$(dirname "$0")"

MODE="${1:?usage: ./run_q2b.sh adot-redact|extract}"
if [[ -f .env ]]; then set -a; source .env; set +a; fi

export AWS_REGION="${AWS_REGION:-us-west-2}"
export AWS_DEFAULT_REGION="$AWS_REGION"

AGENT_ID="knox-adk-trace-test"
LOG_GROUP="/aws/bedrock-agentcore/runtimes/${AGENT_ID}"
STAMP="$(date +%Y%m%d-%H%M%S)"
SESSION_ID="knox-adk-${MODE}-${STAMP}"

# Same ADOT settings as run.sh except the two variables under test.
export AGENT_OBSERVABILITY_ENABLED=true
export OTEL_PYTHON_DISTRO=aws_distro
export OTEL_PYTHON_CONFIGURATOR=aws_configurator
export OTEL_RESOURCE_ATTRIBUTES="service.name=${AGENT_ID},deployment.environment.name=test,aws.log.group.names=${LOG_GROUP}"
export OTEL_EXPORTER_OTLP_LOGS_HEADERS="x-aws-log-group=${LOG_GROUP},x-aws-log-stream=runtime-logs,x-aws-metric-namespace=bedrock-agentcore"
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_TRACES_EXPORTER="${OTEL_TRACES_EXPORTER:-otlp}"
export OTEL_METRICS_EXPORTER=none

case "$MODE" in
  adot-redact)
    export AWS_GENAI_CONTENT_EXTRACTION_OPT_OUT=true   # text stays on spans ...
    export OTEL_LOGS_EXPORTER=none
    # ... and only ADOT-level redaction is applied (no OPENINFERENCE_HIDE_*).
    export AWS_REDACT_SPAN_ATTRIBUTES='llm.input_messages.*,llm.output_messages.*,input.value,output.value,gen_ai.input.messages,gen_ai.output.messages'
    ;;
  extract)
    unset AWS_GENAI_CONTENT_EXTRACTION_OPT_OUT          # ADOT default: move text to log events
    export OTEL_LOGS_EXPORTER=otlp                      # log events go to $LOG_GROUP via OTLP
    ;;
  adk-nocontent)
    # run M: ADK's own switch. Content is NOT written onto ADK-owned (gcp.vertex.agent) spans.
    # Text on OpenInference spans is untouched; no ADOT redaction; no log export.
    export AWS_GENAI_CONTENT_EXTRACTION_OPT_OUT=true
    export OTEL_LOGS_EXPORTER=none
    export ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false
    ;;
  *) echo "unknown mode: $MODE" >&2; exit 2 ;;
esac

echo "mode=$MODE region=$AWS_REGION session_id=$SESSION_ID"
echo "$SESSION_ID" >> sessions.log
.venv/bin/opentelemetry-instrument .venv/bin/python agent.py --session-id "$SESSION_ID"
echo
echo "done. verify with: .venv/bin/python verify.py --session-id $SESSION_ID"
