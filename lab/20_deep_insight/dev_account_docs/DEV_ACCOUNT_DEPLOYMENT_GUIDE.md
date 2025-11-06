# Development Account Deployment Guide

**Target Account**: 057716757052 (Development)
**Date**: 2025-11-06
**Status**: Environment Variables NOT Set - Requires Investigation

---

## 🚨 CRITICAL ISSUES TO FIX

### Issue 1: Environment Variables NOT Being Set (BLOCKING)

**Problem**: Runtime `deep_insight_runtime_vpc-7CAUFPDY4l` has `environmentVariables: null`

**Verification in Production Account (738490718699)**:
- ✅ Runtime `deep_insight_runtime_vpc-3oYut44SAk` has **16 environment variables** set correctly
- ✅ Same code, same script works perfectly in production

**Root Cause**: One of the following in dev account:
1. Outdated `bedrock_agentcore_starter_toolkit` version
2. Missing IAM permissions
3. Runtime was updated (not fresh creation)
4. Environment variables not loaded from `.env` file

---

### Issue 2: Missing HTTP Scheme (WILL FAIL AFTER ISSUE 1 FIXED)

**Problem**: URLs missing `http://` scheme causing 100% failure rate

**Impact**:
- Cookie acquisition: 40/40 failures
- Health checks: 5/5 failures
- Runtime completely non-functional

**Files to Fix**:

#### 1. `src/tools/cookie_acquisition_subprocess.py:61`
```python
# ❌ BEFORE (line 61)
response = session.get(
    f"{alb_dns}/container-info",
    params={"session_id": session_id},
    timeout=5
)

# ✅ AFTER
response = session.get(
    f"http://{alb_dns}/container-info",  # Add http://
    params={"session_id": session_id},
    timeout=5
)
```

#### 2. `src/tools/fargate_container_controller.py:320`
```python
# ❌ BEFORE (line 320)
response = self.http_session.get(f"{self.alb_dns}/health", timeout=5)

# ✅ AFTER
response = self.http_session.get(f"http://{self.alb_dns}/health", timeout=5)  # Add http://
```

---

## ✅ PREREQUISITE: IAM Permissions

### Task Execution Role (Phase 1 CloudFormation)

**File**: `production_deployment/cloudformation/phase1-infrastructure.yaml`

#### 1. ECS Permissions (line 757)
```yaml
- ecs:DescribeTaskDefinition
```

#### 2. CloudWatch Logs Delivery (lines 730-738)
```yaml
- logs:CreateDelivery
- logs:PutDeliverySource
- logs:PutDeliveryDestination
- logs:GetDelivery
- logs:DescribeDeliveries
- logs:DeleteDelivery
- logs:UpdateDeliveryConfiguration
- logs:DescribeDeliverySource
- logs:DescribeDeliveryDestination
```

#### 3. Bedrock Permissions (lines 748, 823)
```yaml
- bedrock:AllowVendedLogDeliveryForResource
```

**Total**: 11 permissions required

---

### Task Role (Phase 1 CloudFormation)

**File**: `production_deployment/cloudformation/phase1-infrastructure.yaml:825-864`

#### 1. ECSAccess Policy
```yaml
- ecs:RunTask
- ecs:DescribeTasks
- ecs:StopTask
- ecs:DescribeTaskDefinition
- iam:PassRole  # For TaskExecutionRole
```

#### 2. ALBAccess Policy
```yaml
- elasticloadbalancing:RegisterTargets
- elasticloadbalancing:DeregisterTargets
- elasticloadbalancing:DescribeTargetHealth
```

#### 3. EC2Access Policy
```yaml
- ec2:DescribeNetworkInterfaces  # Critical for _wait_for_task_ip()
```

**Total**: 9 permissions required

---

## 📋 REQUIRED ENVIRONMENT VARIABLES (16 Total)

### Container Operations (4)
```bash
ECS_CLUSTER_NAME=my-fargate-cluster
ALB_DNS=internal-deep-insight-alb-dev-XXXXXXX.us-east-1.elb.amazonaws.com
TASK_DEFINITION_ARN=arn:aws:ecs:us-east-1:057716757052:task-definition/fargate-dynamic-task:6
CONTAINER_NAME=dynamic-executor
```

### AWS Configuration (2)
```bash
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=057716757052
```

### Fargate Network Configuration (4)
```bash
FARGATE_SUBNET_IDS=subnet-0b2fb367d6e823a79
FARGATE_SECURITY_GROUP_IDS=sg-0e1314a2421686c2c
FARGATE_ASSIGN_PUBLIC_IP=DISABLED
ALB_TARGET_GROUP_ARN=arn:aws:elasticloadbalancing:us-east-1:057716757052:targetgroup/...
```

### OpenTelemetry Configuration (6)
```bash
OTEL_PYTHON_DISTRO=aws_distro
OTEL_PYTHON_CONFIGURATOR=aws_configurator
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_EXPORTER_OTLP_LOGS_HEADERS=x-aws-log-group=bedrock-agentcore-observability,x-aws-log-stream=custom-spans,x-aws-metric-namespace=AgentCore
OTEL_RESOURCE_ATTRIBUTES=service.name=deep-insight-runtime
AGENT_OBSERVABILITY_ENABLED=true
```

---

## 🔧 STEP-BY-STEP FIX PROCEDURE

### Step 1: Code Fixes (HTTP Scheme)

```bash
# In development account environment
cd /path/to/project

# Fix cookie acquisition
vim src/tools/cookie_acquisition_subprocess.py
# Line 61: Add http:// to URL (see Issue 2 above)

# Fix health check
vim src/tools/fargate_container_controller.py
# Line 320: Add http:// to URL (see Issue 2 above)

# Commit changes
git add src/tools/cookie_acquisition_subprocess.py src/tools/fargate_container_controller.py
git commit -m "fix: Add http:// scheme to ALB URLs"
```

### Step 2: Verify Prerequisites

```bash
# 1. Check toolkit version (must be >= 0.1.28)
pip show bedrock-agentcore-starter-toolkit

# If version is old:
cd setup
uv sync --upgrade
pip install --upgrade bedrock-agentcore-starter-toolkit boto3

# 2. Verify .env file exists and has required variables
cat .env | grep -E "ECS_CLUSTER_NAME|ALB_DNS|TASK_DEFINITION_ARN|CONTAINER_NAME"

# If .env is missing or incomplete:
./production_deployment/scripts/setup_env.sh

# 3. Verify Phase 1 stack has latest IAM permissions
aws cloudformation describe-stacks \
  --stack-name deep-insight-infrastructure-dev \
  --region us-east-1 \
  --query 'Stacks[0].LastUpdatedTime'

# If stack is old (before 2025-11-05), update it:
cd production_deployment/scripts/phase1
./deploy.sh dev
```

### Step 3: Delete Failed Runtime

```bash
# Delete the runtime with null environment variables
aws bedrock-agentcore-control delete-agent-runtime \
  --agent-runtime-id deep_insight_runtime_vpc-7CAUFPDY4l \
  --region us-east-1

# Wait for deletion to complete (check status)
aws bedrock-agentcore-control list-agent-runtimes \
  --region us-east-1 \
  --query 'agentRuntimes[?agentRuntimeName==`deep_insight_runtime_vpc`]'
```

### Step 4: Rebuild Docker Image

```bash
# Important: Rebuild with HTTP scheme fixes
cd fargate-runtime

# Build new image
docker build -t dynamic-executor:v20-http-fix .

# Tag for ECR
ECR_REPO=$(aws ecr describe-repositories --repository-names deep-insight-fargate-runtime-dev --region us-east-1 --query 'repositories[0].repositoryUri' --output text)
docker tag dynamic-executor:v20-http-fix $ECR_REPO:v20-http-fix
docker tag dynamic-executor:v20-http-fix $ECR_REPO:latest

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_REPO
docker push $ECR_REPO:v20-http-fix
docker push $ECR_REPO:latest

# Update Task Definition to use new image (Phase 2)
# (Or update manually via AWS Console)
```

### Step 5: Create New Runtime (Fresh)

```bash
# IMPORTANT: Fresh creation, NOT update
# Remove existing RUNTIME_ARN from .env to force fresh creation
sed -i '/^RUNTIME_ARN=/d' .env

# Run creation script
python3 01_create_agentcore_runtime.py

# This will:
# 1. Build new Docker image with HTTP fixes
# 2. Push to ECR
# 3. Create NEW runtime (not update)
# 4. Set all 16 environment variables
```

### Step 6: Verify Environment Variables Set

```bash
# Get new runtime ID from script output or .env
RUNTIME_ID=$(grep RUNTIME_ID .env | cut -d= -f2)

# Verify all 16 environment variables are set
aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-id $RUNTIME_ID \
  --region us-east-1 \
  --query 'environmentVariables' \
  --output json

# Expected: JSON object with 16 key-value pairs
# If null: STOP and investigate toolkit version / IAM permissions
```

### Step 7: Test Runtime

```bash
# Run end-to-end test
python3 03_invoke_agentcore_job_vpc.py

# Monitor logs
aws logs tail /aws/bedrock-agentcore/runtimes/deep_insight_runtime_vpc --follow --region us-east-1
```

---

## 🎯 SUCCESS CRITERIA

### ✅ Phase 1: Environment Variables
```bash
# Run this command:
aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-id <RUNTIME_ID> \
  --region us-east-1 \
  --query 'length(keys(environmentVariables))' \
  --output text

# Expected output: 16
# Actual (current): 0 ❌
```

### ✅ Phase 2: Cookie Acquisition
```bash
# Check CloudWatch Logs for:
# ✅ "Session cookies obtained successfully"
# ❌ NO "MissingSchema: Invalid URL"
```

### ✅ Phase 3: Fargate Container Launch
```bash
# Check CloudWatch Logs for:
# ✅ "Task started successfully"
# ✅ "Container registered with ALB"
# ✅ "Health check passed"
```

### ✅ Phase 4: Job Completion
```bash
# Check for PDF report generation:
# ✅ "PDF report saved to S3"
# ✅ Job status: COMPLETED
```

---

## 📊 COMPARISON: Production vs Development

| Aspect | Production (738490718699) | Development (057716757052) |
|--------|---------------------------|----------------------------|
| **Runtime ID** | deep_insight_runtime_vpc-3oYut44SAk | deep_insight_runtime_vpc-7CAUFPDY4l |
| **Status** | READY ✅ | READY (but broken) ⚠️ |
| **Env Vars** | 16 variables ✅ | 0 (null) ❌ |
| **HTTP Scheme** | Fixed ✅ | Missing ❌ |
| **IAM Permissions** | Complete ✅ | Unknown (verify) ⚠️ |
| **Toolkit Version** | Latest ✅ | Unknown (verify) ⚠️ |
| **Last Test** | 2025-11-05 SUCCESS ✅ | 2025-11-05 FAILED ❌ |

---

## 🔍 DEBUGGING CHECKLIST

If environment variables are still null after fresh creation:

### 1. Toolkit Version
```bash
pip show bedrock-agentcore-starter-toolkit | grep Version
# Must be >= 0.1.28
```

### 2. IAM Permissions (Task Execution Role)
```bash
ROLE_NAME="deep-insight-task-execution-role-dev"
aws iam get-role-policy \
  --role-name $ROLE_NAME \
  --policy-name BedrockAgentCorePolicy \
  --query 'PolicyDocument.Statement[].Action' \
  --output json

# Must include all 11 permissions listed above
```

### 3. Environment Variables Loaded
```bash
# Add debug logging to 01_create_agentcore_runtime.py line 320:
import json
print(f"DEBUG: container_env_vars = {json.dumps(container_env_vars, indent=2)}")

# Re-run script and verify output shows 16 variables
```

### 4. Launch API Call
```bash
# Check if launch() is being called with env_vars parameter
# Add debug in 01_create_agentcore_runtime.py line 321:
print(f"DEBUG: launch_kwargs = {launch_kwargs}")

# Expected: {'env_vars': {16 variables}}
```

### 5. AWS API Response
```bash
# Enable boto3 debug logging
export AWS_DEBUG=true
python3 01_create_agentcore_runtime.py 2>&1 | grep -A 50 "CreateAgentRuntime"

# Check if environmentVariables is in the request payload
```

---

## 📚 REFERENCE FILES

### Configuration Files
- `.env` - Environment variables (auto-generated)
- `.env.example` - Template with all required variables
- `.bedrock_agentcore.yaml` - Runtime configuration (VPC settings)

### Scripts
- `01_create_agentcore_runtime.py` - Runtime creation (lines 273-321: env_vars)
- `production_deployment/scripts/setup_env.sh` - Auto-generate .env from CloudFormation

### CloudFormation
- `production_deployment/cloudformation/phase1-infrastructure.yaml` - IAM roles and permissions
- `production_deployment/cloudformation/phase2-fargate.yaml` - ECS task definition

### Application Code (Needs HTTP Fixes)
- `src/tools/cookie_acquisition_subprocess.py:61` - Add http:// scheme
- `src/tools/fargate_container_controller.py:320` - Add http:// scheme

---

## 📞 SUPPORT

If issues persist after following this guide:

1. **Compare with Production**: Both accounts use identical code - production works, dev doesn't
2. **Check Toolkit Version**: Production likely has newer toolkit (>= 0.1.28)
3. **Verify IAM Permissions**: Production has all 20 required permissions (11 + 9)
4. **Fresh Creation**: Delete runtime and create fresh (don't update)
5. **Review Logs**: CloudWatch Logs show detailed error messages

**Key Insight**: Since production works with the same code, the issue is environmental (toolkit version, IAM, or stale runtime state).

---

**Generated**: 2025-11-06
**Author**: Claude Code
**Reference**: CLAUDE.md (lines 40-276)
