#!/bin/bash
  echo "==================================================================="
  echo "AgentCore Runtime Diagnostic Report"
  echo "==================================================================="
  echo ""

  # 1. Runtime Info
  echo "1. RUNTIME INFORMATION:"
  grep -E "RUNTIME_ID|RUNTIME_ARN|RUNTIME_NAME" .env 2>/dev/null || echo "No .env file"
  echo ""

  # 2. Log Streams
  echo "2. LOG STREAMS (checking if runtime-logs exist):"
  RUNTIME_ID=$(grep "RUNTIME_ID" .env 2>/dev/null | cut -d= -f2)
  if [ ! -z "$RUNTIME_ID" ]; then
      aws logs describe-log-streams \
        --log-group-name "/aws/bedrock-agentcore/runtimes/${RUNTIME_ID}-DEFAULT" \
        --output json 2>/dev/null | jq -r '.logStreams[] | .logStreamName' | head -5
  else
      echo "Could not find RUNTIME_ID"
  fi
  echo ""

  # 3. Runtime Configuration
  echo "3. OBSERVABILITY CONFIG (.bedrock_agentcore.yaml):"
  if [ -f .bedrock_agentcore.yaml ]; then
      grep -A 5 "observability:" .bedrock_agentcore.yaml
  else
      echo "No .bedrock_agentcore.yaml file"
  fi
  echo ""

  # 4. Environment Variables (OTEL related)
  echo "4. OTEL ENVIRONMENT VARIABLES:"
  grep -E "OTEL|OBSERV" .env 2>/dev/null || echo "No OTEL variables found"
  echo ""

  # 5. IAM Role
  echo "5. IAM EXECUTION ROLE:"
  ROLE_ARN=$(grep "TASK_EXECUTION_ROLE_ARN" .env 2>/dev/null | cut -d= -f2)
  if [ ! -z "$ROLE_ARN" ]; then
      ROLE_NAME=$(echo $ROLE_ARN | awk -F'/' '{print $NF}')
      echo "Role: $ROLE_NAME"
      echo "Checking CloudWatch Logs permissions..."
      aws iam get-role-policy --role-name "$ROLE_NAME" --policy-name CloudWatchLogsAccess 2>/dev/null | jq -r '.PolicyDocument.Statement[].Action[]' | grep logs ||
  echo "Policy not found"
  else
      echo "Could not find role"
  fi
  echo ""

  # 6. Package Versions
  echo "6. PACKAGE VERSIONS:"
  pip list 2>/dev/null | grep -E "bedrock-agentcore|strands-agents" || uv pip list | grep -E "bedrock-agentcore|strands-agents"
  echo ""

  # 7. Runtime Creation Date
  echo "7. RUNTIME METADATA:"
  if [ ! -z "$RUNTIME_ID" ]; then
      aws logs describe-log-groups \
        --log-group-name-prefix "/aws/bedrock-agentcore/runtimes/${RUNTIME_ID}" \
        --output json 2>/dev/null | jq -r '.logGroups[0] | "Created: \(.creationTime/1000 | strftime("%Y-%m-%d %H:%M:%S"))"'
  fi
  echo ""

  echo "==================================================================="
  echo "End of Report"
  echo "==================================================================="