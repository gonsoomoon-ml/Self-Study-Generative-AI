# Development Account - Quick Fix Checklist

**Account**: 057716757052 (Development)
**Problem**: Environment Variables NOT Set + HTTP Scheme Missing

---

## ⚡ QUICK FIX (30 minutes)

### 1. Prerequisites Check (5 min)

```bash
# ✅ Toolkit version
pip show bedrock-agentcore-starter-toolkit | grep Version
# Required: >= 0.1.28

# ✅ .env file exists
cat .env | grep ECS_CLUSTER_NAME
# If missing: ./production_deployment/scripts/setup_env.sh

# ✅ IAM permissions (spot check)
aws iam get-role-policy \
  --role-name deep-insight-task-execution-role-dev \
  --policy-name BedrockAgentCorePolicy \
  --query 'PolicyDocument.Statement[].Action[]' | grep logs:CreateDelivery
# Must return: "logs:CreateDelivery"
```

**Issues Found?**
- Old toolkit → `cd setup && uv sync --upgrade`
- Missing .env → `./production_deployment/scripts/setup_env.sh`
- Missing IAM → `cd production_deployment/scripts/phase1 && ./deploy.sh dev`

---

### 2. Code Fixes (2 min)

```bash
# Fix 1: Cookie acquisition
sed -i 's|f"{alb_dns}/container-info"|f"http://{alb_dns}/container-info"|' \
  src/tools/cookie_acquisition_subprocess.py

# Fix 2: Health check
sed -i 's|f"{self.alb_dns}/health"|f"http://{self.alb_dns}/health"|' \
  src/tools/fargate_container_controller.py

# Verify changes
grep -n "http://{alb_dns}" src/tools/cookie_acquisition_subprocess.py
grep -n "http://{self.alb_dns}" src/tools/fargate_container_controller.py
```

---

### 3. Delete Failed Runtime (1 min)

```bash
aws bedrock-agentcore-control delete-agent-runtime \
  --agent-runtime-id deep_insight_runtime_vpc-7CAUFPDY4l \
  --region us-east-1

# Remove from .env to force fresh creation
sed -i '/^RUNTIME_ARN=/d' .env
sed -i '/^RUNTIME_ID=/d' .env
```

---

### 4. Create Fresh Runtime (10-15 min)

```bash
# This rebuilds Docker image + creates runtime with env vars
python3 01_create_agentcore_runtime.py

# Look for this output:
# ✅ "Container에 16개 환경 변수 전달"
# ✅ "launch() 완료!"
# ✅ "Runtime이 READY 상태입니다!"
```

---

### 5. Verify Environment Variables (1 min)

```bash
# Get new runtime ID
RUNTIME_ID=$(grep RUNTIME_ID .env | cut -d= -f2)

# Check env vars count
aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-id $RUNTIME_ID \
  --region us-east-1 \
  --query 'length(keys(environmentVariables))' \
  --output text

# MUST OUTPUT: 16
# If output is 0 → STOP! Check toolkit version and IAM permissions
```

---

### 6. Test Runtime (5-10 min)

```bash
# Run end-to-end test
python3 03_invoke_agentcore_job_vpc.py

# Monitor logs (in separate terminal)
aws logs tail /aws/bedrock-agentcore/runtimes/deep_insight_runtime_vpc \
  --follow --region us-east-1
```

**Success Indicators**:
- ✅ "Session cookies obtained successfully"
- ✅ "Task started successfully"
- ✅ "Container registered with ALB"
- ✅ "Health check passed"
- ✅ "PDF report saved to S3"

---

## 🚨 STOP POINTS

### If Environment Variables = 0 After Fresh Creation

**This means toolkit version or IAM issue:**

```bash
# Check toolkit
pip show bedrock-agentcore-starter-toolkit
# If < 0.1.28:
cd setup && uv sync --upgrade && pip install --upgrade bedrock-agentcore-starter-toolkit

# Check IAM (must have ALL of these)
aws iam get-role-policy \
  --role-name deep-insight-task-execution-role-dev \
  --policy-name BedrockAgentCorePolicy \
  --query 'PolicyDocument.Statement[].Action[]' | grep -E "logs:CreateDelivery|bedrock:AllowVended"

# If missing → Update Phase 1 stack
cd production_deployment/scripts/phase1 && ./deploy.sh dev
```

---

### If "MissingSchema" Errors in Logs

**This means HTTP scheme fix didn't apply:**

```bash
# Verify fixes are in place
grep -n "http://" src/tools/cookie_acquisition_subprocess.py
grep -n "http://" src/tools/fargate_container_controller.py

# If not found, re-apply fixes (see Step 2)
# Then rebuild:
python3 01_create_agentcore_runtime.py
```

---

### If "ModuleNotFoundError: flask"

**This means Docker image is old:**

```bash
# Verify flask in requirements.txt
grep flask fargate-runtime/requirements.txt

# If missing:
echo "flask>=3.0.0" >> fargate-runtime/requirements.txt

# Rebuild:
python3 01_create_agentcore_runtime.py
```

---

## 🎯 EXPECTED FINAL STATE

### Runtime Status
```bash
aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-id <RUNTIME_ID> \
  --region us-east-1 \
  --query '{status: status, envVarsCount: length(keys(environmentVariables)), networkMode: networkConfiguration.networkMode}'
```

**Expected Output**:
```json
{
  "status": "READY",
  "envVarsCount": 16,
  "networkMode": "VPC"
}
```

### Test Job Result
```bash
# Check S3 for PDF report
aws s3 ls s3://bedrock-logs-gonsoomoon/ --recursive | grep -i "report.*pdf"

# Expected: PDF file from today's date
```

---

## 📋 16 REQUIRED ENVIRONMENT VARIABLES

**Quick verification**:
```bash
RUNTIME_ID=$(grep RUNTIME_ID .env | cut -d= -f2)
aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-id $RUNTIME_ID \
  --region us-east-1 \
  --query 'environmentVariables | keys(@)' \
  --output json
```

**Must have ALL of these**:
```
1.  ECS_CLUSTER_NAME
2.  ALB_DNS
3.  TASK_DEFINITION_ARN
4.  CONTAINER_NAME
5.  AWS_REGION
6.  AWS_ACCOUNT_ID
7.  FARGATE_SUBNET_IDS
8.  FARGATE_SECURITY_GROUP_IDS
9.  FARGATE_ASSIGN_PUBLIC_IP
10. ALB_TARGET_GROUP_ARN
11. OTEL_PYTHON_DISTRO
12. OTEL_PYTHON_CONFIGURATOR
13. OTEL_EXPORTER_OTLP_PROTOCOL
14. OTEL_EXPORTER_OTLP_LOGS_HEADERS
15. OTEL_RESOURCE_ATTRIBUTES
16. AGENT_OBSERVABILITY_ENABLED
```

---

## ✅ PRODUCTION COMPARISON

**Production account (738490718699) has:**
- ✅ Runtime with 16 environment variables
- ✅ HTTP scheme fixes applied
- ✅ All IAM permissions
- ✅ Latest toolkit version
- ✅ End-to-end tests passing

**Development account (057716757052) needs:**
- ❌ Fix environment variables (currently 0)
- ❌ Apply HTTP scheme fixes
- ⚠️ Verify IAM permissions
- ⚠️ Verify toolkit version

**Key Insight**: Same code works in production → Issue is environmental (toolkit/IAM/runtime state)

---

**Total Time**: ~30 minutes
**Last Updated**: 2025-11-06
