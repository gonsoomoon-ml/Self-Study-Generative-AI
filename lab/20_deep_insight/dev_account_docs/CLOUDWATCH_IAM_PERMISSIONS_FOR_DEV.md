# CloudWatch IAM Permissions - Development Account Fix

**Issue**: Development account cannot create per-invocation log streams
**Root Cause**: Missing IAM permissions in Task Execution Role
**Account**: 057716757052 (Development)

---

## 🚨 CRITICAL MISSING PERMISSION

### ObservabilityAccess Policy (Task Execution Role)

**Production has this ✅** | **Development needs this ❌**

This policy enables:
- Per-invocation log streams (one stream per job)
- CloudWatch Logs Delivery for AgentCore
- Bedrock vended log delivery

---

## 📋 Complete Policy JSON

### Policy Name: `ObservabilityAccess`
**Attached to**: `deep-insight-task-execution-role-dev`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:AllowVendedLogDeliveryForResource",
        "logs:CreateDelivery",
        "logs:PutDeliverySource",
        "logs:PutDeliveryDestination",
        "logs:GetDelivery",
        "logs:DescribeDeliveries",
        "logs:DeleteDelivery",
        "logs:UpdateDeliveryConfiguration"
      ],
      "Resource": "*"
    }
  ]
}
```

**Total**: 8 permissions (7 CloudWatch Logs + 1 Bedrock)

---

## 🔍 Verify if Missing in Dev Account

### Check Command
```bash
aws iam get-role-policy \
  --role-name deep-insight-task-execution-role-dev \
  --policy-name ObservabilityAccess \
  --region us-east-1
```

### Expected Results

#### If Policy EXISTS ✅
```json
{
    "RoleName": "deep-insight-task-execution-role-dev",
    "PolicyName": "ObservabilityAccess",
    "PolicyDocument": {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:AllowVendedLogDeliveryForResource",
                    "logs:CreateDelivery",
                    ...
                ]
            }
        ]
    }
}
```

#### If Policy MISSING ❌
```
An error occurred (NoSuchEntity) when calling the GetRolePolicy operation:
The role policy with name ObservabilityAccess cannot be found.
```

**If you see this error** → This is the root cause! Policy needs to be created.

---

## 🔧 How to Create Missing Policy

### Option 1: AWS CLI (Quick)

```bash
# Create policy JSON file
cat > /tmp/observability-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:AllowVendedLogDeliveryForResource",
        "logs:CreateDelivery",
        "logs:PutDeliverySource",
        "logs:PutDeliveryDestination",
        "logs:GetDelivery",
        "logs:DescribeDeliveries",
        "logs:DeleteDelivery",
        "logs:UpdateDeliveryConfiguration"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Attach policy to role
aws iam put-role-policy \
  --role-name deep-insight-task-execution-role-dev \
  --policy-name ObservabilityAccess \
  --policy-document file:///tmp/observability-policy.json \
  --region us-east-1

# Verify it was created
aws iam get-role-policy \
  --role-name deep-insight-task-execution-role-dev \
  --policy-name ObservabilityAccess \
  --region us-east-1 \
  --query 'PolicyDocument.Statement[0].Action[]' \
  --output text

# Expected: 8 lines of permissions
```

### Option 2: Update CloudFormation Stack (Recommended)

**File**: `production_deployment/cloudformation/phase1-infrastructure.yaml`

**Location**: Lines 721-739 (in TaskExecutionRole resource)

```yaml
# Add this policy to TaskExecutionRole → Policies section
- PolicyName: ObservabilityAccess
  PolicyDocument:
    Version: '2012-10-17'
    Statement:
      - Effect: Allow
        Action:
          - bedrock:AllowVendedLogDeliveryForResource
          - logs:CreateDelivery
          - logs:PutDeliverySource
          - logs:PutDeliveryDestination
          - logs:GetDelivery
          - logs:DescribeDeliveries
          - logs:DeleteDelivery
          - logs:UpdateDeliveryConfiguration
        Resource: '*'
```

Then update the stack:
```bash
cd production_deployment/scripts/phase1
./deploy.sh dev
```

---

## 📊 Why This Policy is Critical

### Without ObservabilityAccess ❌

**Symptoms**:
- ❌ Single log stream for ALL jobs (no per-invocation streams)
- ❌ Cannot debug individual job execution
- ❌ Logs mixed together, hard to trace issues
- ❌ No OTEL integration
- ❌ Runtime may fail silently on logging

**CloudWatch Logs**:
```
/aws/bedrock-agentcore/runtimes/deep_insight_runtime_vpc
└── runtime-logs (single stream for everything)
    ├── Job 1 logs
    ├── Job 2 logs
    ├── Job 3 logs  ← All mixed together!
```

### With ObservabilityAccess ✅

**Benefits**:
- ✅ Separate log stream per job execution
- ✅ Easy debugging and tracing
- ✅ OTEL integration enabled
- ✅ CloudWatch Logs Delivery works
- ✅ Bedrock vended logs delivered properly

**CloudWatch Logs**:
```
/aws/bedrock-agentcore/runtimes/deep_insight_runtime_vpc
├── 2025/11/05/[runtime-logs]abc-123-job1
├── 2025/11/05/[runtime-logs]def-456-job2
└── 2025/11/05/[runtime-logs]ghi-789-job3  ← Clean separation!
```

---

## 🎯 The 8 Permissions Explained

### Bedrock Permission (1)

**1. `bedrock:AllowVendedLogDeliveryForResource`**
- Allows Bedrock AgentCore to deliver logs to CloudWatch on your behalf
- Without this: Bedrock cannot write logs to CloudWatch Logs

### CloudWatch Logs Delivery (7)

**2. `logs:CreateDelivery`**
- Creates a delivery configuration to send logs to CloudWatch
- Required once per runtime

**3. `logs:PutDeliverySource`**
- Defines where logs come from (AgentCore runtime)
- Sets up the source endpoint

**4. `logs:PutDeliveryDestination`**
- Defines where logs go (CloudWatch Log Group)
- Sets up the destination endpoint

**5. `logs:GetDelivery`**
- Retrieves delivery configuration details
- Used for monitoring and validation

**6. `logs:DescribeDeliveries`**
- Lists all delivery configurations
- Used for debugging and management

**7. `logs:DeleteDelivery`**
- Removes delivery configuration when runtime is deleted
- Cleanup operation

**8. `logs:UpdateDeliveryConfiguration`**
- Modifies delivery settings
- Used when runtime configuration changes

---

## 🔐 Additional CloudWatch Permissions (Already Present)

### CloudWatchLogsAccess Policy (Separate)

These are basic logging permissions (already in production):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams",
        "logs:DescribeLogGroups"
      ],
      "Resource": "*"
    }
  ]
}
```

**Status**: ✅ Should already exist in dev account
**Purpose**: Basic log group/stream creation
**Note**: This is NOT enough for per-invocation log streams!

---

## ✅ Verification After Adding Policy

### 1. Check Policy Exists
```bash
aws iam get-role-policy \
  --role-name deep-insight-task-execution-role-dev \
  --policy-name ObservabilityAccess \
  --region us-east-1 \
  --query 'length(PolicyDocument.Statement[0].Action)' \
  --output text

# Expected output: 8
```

### 2. List All Permissions
```bash
aws iam get-role-policy \
  --role-name deep-insight-task-execution-role-dev \
  --policy-name ObservabilityAccess \
  --region us-east-1 \
  --query 'PolicyDocument.Statement[0].Action[]' \
  --output text

# Expected: 8 lines of permissions
```

### 3. Test Runtime Creation
```bash
# Delete old runtime (without observability)
aws bedrock-agentcore-control delete-agent-runtime \
  --agent-runtime-id <OLD_RUNTIME_ID> \
  --region us-east-1

# Create new runtime (with observability)
python3 01_create_agentcore_runtime.py

# Check environment variables set
RUNTIME_ID=$(grep RUNTIME_ID .env | cut -d= -f2)
aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-id $RUNTIME_ID \
  --region us-east-1 \
  --query 'environmentVariables.AGENT_OBSERVABILITY_ENABLED'

# Expected: "true"
```

### 4. Test Job Execution
```bash
# Run test job
python3 03_invoke_agentcore_job_vpc.py

# Check for per-invocation log stream
aws logs describe-log-streams \
  --log-group-name /aws/bedrock-agentcore/runtimes/deep_insight_runtime_vpc \
  --order-by LastEventTime \
  --descending \
  --max-items 5 \
  --region us-east-1

# Expected: Should see unique log stream names like:
# 2025/11/06/[runtime-logs]abc-123-def-456
```

---

## 📚 Reference

### Production Account Status
- ✅ ObservabilityAccess policy: **EXISTS**
- ✅ All 8 permissions: **PRESENT**
- ✅ Per-invocation log streams: **WORKING**

### Development Account Status
- ❓ ObservabilityAccess policy: **UNKNOWN** (needs verification)
- ❌ Per-invocation log streams: **NOT WORKING**
- ⚠️ Environment variables: **NOT BEING SET** (may be related)

### Related Files
- `ACTUAL_IAM_PERMISSIONS_ANALYSIS.md` - Full IAM audit
- `CLAUDE.md` - Lines 118-135 (IAM permissions documentation)
- `phase1-infrastructure.yaml:721-739` - CloudFormation template

---

## 🎯 Summary

**Single Action Required**:

Add `ObservabilityAccess` policy with 8 permissions to `deep-insight-task-execution-role-dev`

**Impact**:
- Enables per-invocation log streams ✅
- Fixes CloudWatch Logs Delivery ✅
- May also fix environment variables issue ✅ (if related to service permissions)

**Time to Fix**: 2 minutes (Option 1) or 10-15 minutes (Option 2 with CloudFormation)

---

**Generated**: 2025-11-06
**Source**: Production IAM audit via AWS CLI
**Verified**: Production account has this policy and it works
