# Test: Environment Variables Delivery to AgentCore Runtime

## Hypothesis
When running `01_create_agentcore_runtime.py` on an **existing runtime**, the environment variables from `.env` may not be delivered to the running container.

## Test Procedure

### Step 1: Check Current Runtime Environment
```bash
# Current runtime in .env
grep "RUNTIME_ID\|BEDROCK_MODEL_ID" .env
```

Expected output:
```
BEDROCK_MODEL_ID=global.anthropic.claude-haiku-4-5-20251001-v1:0
RUNTIME_ID=deep_insight_runtime_vpc-Id77BBHcNl
```

### Step 2: Add Temporary Env Var Logging

Add this to `agentcore_runtime.py` at the top of the file (after imports):
```python
import os
import logging
logger = logging.getLogger(__name__)

# Log all environment variables on startup
logger.info("=" * 60)
logger.info("ENVIRONMENT VARIABLES CHECK")
logger.info("=" * 60)
logger.info(f"BEDROCK_MODEL_ID: {os.getenv('BEDROCK_MODEL_ID', 'NOT SET')}")
logger.info(f"AWS_REGION: {os.getenv('AWS_REGION', 'NOT SET')}")
logger.info(f"ECS_CLUSTER_NAME: {os.getenv('ECS_CLUSTER_NAME', 'NOT SET')}")
logger.info(f"S3_BUCKET_NAME: {os.getenv('S3_BUCKET_NAME', 'NOT SET')}")
logger.info("=" * 60)
```

### Step 3: Update Runtime
```bash
# This will update the existing runtime with new code + env vars
python3 01_create_agentcore_runtime.py
```

**What happens**:
1. Script detects existing runtime (from RUNTIME_ARN in .env)
2. Builds new Docker image with logging code
3. Pushes to ECR
4. Updates runtime configuration with env_vars

### Step 4: Run Test Job
```bash
# Run a simple job to trigger the runtime
uv run 03_invoke_agentcore_job_vpc.py
```

### Step 5: Check Logs
```bash
# Get the latest log stream
aws logs describe-log-streams \
  --log-group-name "/aws/bedrock-agentcore/runtimes/deep_insight_runtime_vpc-Id77BBHcNl-DEFAULT" \
  --order-by LastEventTime \
  --descending \
  --max-items 1 \
  --output json | jq -r '.logStreams[0].logStreamName'

# Then fetch logs from that stream
LOG_STREAM="<paste-stream-name-here>"
aws logs get-log-events \
  --log-group-name "/aws/bedrock-agentcore/runtimes/deep_insight_runtime_vpc-Id77BBHcNl-DEFAULT" \
  --log-stream-name "$LOG_STREAM" \
  --limit 100 | jq -r '.events[] | .message' | grep -A 10 "ENVIRONMENT VARIABLES"
```

## Expected Results

### If Env Vars ARE Delivered ✅
```
============================================================
ENVIRONMENT VARIABLES CHECK
============================================================
BEDROCK_MODEL_ID: global.anthropic.claude-haiku-4-5-20251001-v1:0
AWS_REGION: us-east-1
ECS_CLUSTER_NAME: deep-insight-cluster-prod
S3_BUCKET_NAME: bedrock-logs-738490718699
============================================================
```

### If Env Vars are NOT Delivered ❌
```
============================================================
ENVIRONMENT VARIABLES CHECK
============================================================
BEDROCK_MODEL_ID: NOT SET
AWS_REGION: us-east-1
ECS_CLUSTER_NAME: NOT SET
S3_BUCKET_NAME: NOT SET
============================================================
```

## Alternative: Force New Runtime

If env vars are not delivered, delete the old runtime and create fresh:

```bash
# 1. Delete existing runtime
RUNTIME_ID=$(grep "RUNTIME_ID=" .env | cut -d'=' -f2)
aws bedrock-agentcore-control delete-agent-runtime --agent-runtime-id "$RUNTIME_ID"

# 2. Remove from .env (lines 69-72)
sed -i '/^# Phase 3: AgentCore Runtime/,/^RUNTIME_ID=/d' .env

# 3. Create fresh runtime
python3 01_create_agentcore_runtime.py
```

This will create a brand new runtime with all current env vars from `.env`.

## Key Insight

**AgentCore Runtime behavior**:
- Environment variables are "baked into" the runtime at creation/update time
- When you call `launch()` on an existing runtime, it updates the runtime configuration
- **BUT**: Existing containers may not pick up new env vars until they restart
- **Solution**: Either wait for natural container recycling OR delete runtime and recreate

## Quick Test Script

Run this to quickly check if BEDROCK_MODEL_ID is visible:
```bash
python3 test_env_vars.py
```
