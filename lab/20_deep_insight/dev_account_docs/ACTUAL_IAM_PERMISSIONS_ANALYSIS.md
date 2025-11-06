# Actual IAM Permissions Analysis - Production Account

**Account**: 738490718699 (Production)
**Date**: 2025-11-06
**Analysis**: Direct AWS IAM API inspection

---

## 🔍 CRITICAL FINDINGS

### ✅ PRODUCTION HAS ALL REQUIRED PERMISSIONS!

Production account has **ALL permissions** documented in CLAUDE.md:

1. ✅ **Task Execution Role: ObservabilityAccess** - 8 permissions for log delivery
2. ✅ **Task Execution Role: EC2NetworkAccess** - 1 permission for ENI queries
3. ✅ **Task Role: ELBAccess** - 4 permissions for ALB operations
4. ✅ **Task Role: ECSAccess** - 6 permissions for Fargate task management

**Key Finding**: Production is fully configured. If dev account has issues, it's missing these policies!

---

## 📊 TASK EXECUTION ROLE (AgentCore Runtime Container)

**Role**: `deep-insight-task-execution-role-prod`
**ARN**: `arn:aws:iam::738490718699:role/deep-insight-task-execution-role-prod`
**Created**: 2025-11-02

### Managed Policies (1)
```
✅ AmazonECSTaskExecutionRolePolicy (AWS Managed)
   - Basic ECS task execution permissions
```

### Inline Policies (9)

#### 1. CloudWatchLogsAccess ⚠️ INCOMPLETE!
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",        ✅
        "logs:CreateLogStream",       ✅
        "logs:PutLogEvents",          ✅
        "logs:DescribeLogStreams",    ✅
        "logs:DescribeLogGroups"      ✅
      ],
      "Resource": "*"
    }
  ]
}
```

**MISSING from CloudWatchLogsAccess** (documented in CLAUDE.md:124-127):
```
❌ logs:CreateDelivery
❌ logs:PutDeliverySource
❌ logs:PutDeliveryDestination
❌ logs:GetDelivery
❌ logs:DescribeDeliveries
❌ logs:DeleteDelivery
❌ logs:UpdateDeliveryConfiguration
```

**THESE ARE IN A SEPARATE POLICY!** ↓

#### 2. ObservabilityAccess ✅ (Contains Log Delivery!)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:AllowVendedLogDeliveryForResource",  ✅
        "logs:CreateDelivery",                        ✅
        "logs:PutDeliverySource",                     ✅
        "logs:PutDeliveryDestination",                ✅
        "logs:GetDelivery",                           ✅
        "logs:DescribeDeliveries",                    ✅
        "logs:DeleteDelivery",                        ✅
        "logs:UpdateDeliveryConfiguration"            ✅
      ],
      "Resource": "*"
    }
  ]
}
```

**Status**: ✅ ALL 8 permissions present (7 logs + 1 bedrock)

#### 3. BedrockAccess ⚠️ INCOMPLETE!
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",                     ✅
        "bedrock:InvokeModelWithResponseStream"    ✅
      ],
      "Resource": "*"
    }
  ]
}
```

**MISSING**:
```
❌ bedrock:AllowVendedLogDeliveryForResource
```

**BUT**: This permission IS in ObservabilityAccess policy! ✅

#### 4-9. Other Policies
```
✅ ECRAccess          - ECR image pull permissions
✅ ECSAccess          - ECS task describe permissions
✅ XRayAccess         - X-Ray tracing permissions
✅ EC2NetworkAccess   - ENI permissions
✅ ELBAccess          - Load balancer permissions
✅ CloudWatchMetricsAccess - Metrics permissions
```

---

## 📊 TASK ROLE (Fargate Container Inside Runtime)

**Role**: `deep-insight-task-role-prod`
**Purpose**: Permissions for Fargate containers launched by AgentCore Runtime

### Inline Policies (4)

#### 1. ECSAccess ✅
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:RunTask",                  ✅
        "ecs:DescribeTaskDefinition",   ✅
        "ecs:DescribeTasks",            ✅
        "ecs:StopTask",                 ✅
        "ecs:ListTasks"                 ✅
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "iam:PassRole",         ✅
      "Resource": [
        "arn:aws:iam::738490718699:role/deep-insight-task-execution-role-prod",
        "arn:aws:iam::738490718699:role/deep-insight-task-role-prod"
      ],
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": "ecs-tasks.amazonaws.com"
        }
      }
    }
  ]
}
```

**Status**: ✅ Complete (6 permissions)

#### 2. ELBAccess (ALB Operations)
```json
PENDING - Need to retrieve
```

#### 3. S3Access
```json
PENDING - Need to retrieve
```

#### 4. BedrockAccess
```json
PENDING - Need to retrieve
```

#### 2. ELBAccess (ALB Operations) ✅
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:RegisterTargets",        ✅
        "elasticloadbalancing:DeregisterTargets",      ✅
        "elasticloadbalancing:DescribeTargetHealth",   ✅
        "elasticloadbalancing:DescribeTargetGroups"    ✅
      ],
      "Resource": "*"
    }
  ]
}
```

**Status**: ✅ Complete (4 permissions) - **This is the ALBAccess policy mentioned in CLAUDE.md!**

#### 3. S3Access ✅
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",     ✅
        "s3:GetObject",     ✅
        "s3:ListBucket"     ✅
      ],
      "Resource": [
        "arn:aws:s3:::bedrock-logs-prod-738490718699-738490718699",
        "arn:aws:s3:::bedrock-logs-prod-738490718699-738490718699/*"
      ]
    }
  ]
}
```

**Status**: ✅ Complete (3 permissions)

#### 4. BedrockAccess ✅
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",                    ✅
        "bedrock:InvokeModelWithResponseStream"   ✅
      ],
      "Resource": "*"
    }
  ]
}
```

**Status**: ✅ Complete (2 permissions)

### ⚠️ EC2 NETWORK PERMISSIONS LOCATION

#### EC2Access is in TASK EXECUTION ROLE, not Task Role!
The `ec2:DescribeNetworkInterfaces` permission documented in CLAUDE.md:151-158 is actually in the **Task Execution Role**, not the Task Role:

**Location**: Task Execution Role → EC2NetworkAccess policy
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeNetworkInterfaces"   ✅
      ],
      "Resource": "*"
    }
  ]
}
```

**Why this matters**: The AgentCore Runtime container needs this permission to query Fargate task IPs. The permission is correctly placed in the Task Execution Role (which runs the runtime), not the Task Role (which runs inside Fargate containers).

---

## 🚨 IMPLICATIONS FOR DEV ACCOUNT

### Why Dev Account Has Issues

1. **CloudWatch Logs Delivery Permissions**
   - Production: ✅ Present in "ObservabilityAccess" policy
   - Dev: ⚠️ Probably MISSING entirely
   - **Required**: 8 permissions in ObservabilityAccess

2. **EC2 Describe Network Interfaces**
   - Production: ❓ Not found in Task Role (but may be elsewhere)
   - Dev: ⚠️ Probably MISSING
   - **Impact**: Cannot get Fargate task private IP → Container launch fails

3. **ALB Target Registration**
   - Production: ❓ May be in "ELBAccess" policy
   - Dev: ⚠️ Unknown
   - **Impact**: Cannot register containers with ALB

### Why Production Still Works

Production might work because:
1. ✅ ObservabilityAccess policy contains all CloudWatch Logs Delivery permissions
2. ✅ Task Execution Role has comprehensive permissions
3. ❓ Missing Task Role permissions may not be exercised in current workflow
4. ❓ Or permissions are in ELBAccess/other policies not yet inspected

---

## ✅ DEV ACCOUNT REQUIREMENTS

### Must Have in Task Execution Role

#### CloudWatchLogsAccess (5 basic permissions)
```yaml
- logs:CreateLogGroup
- logs:CreateLogStream
- logs:PutLogEvents
- logs:DescribeLogStreams
- logs:DescribeLogGroups
```

#### ObservabilityAccess (8 permissions) ⭐ CRITICAL!
```yaml
- bedrock:AllowVendedLogDeliveryForResource
- logs:CreateDelivery
- logs:PutDeliverySource
- logs:PutDeliveryDestination
- logs:GetDelivery
- logs:DescribeDeliveries
- logs:DeleteDelivery
- logs:UpdateDeliveryConfiguration
```

**This is what enables per-invocation log streams!**

### Must Have in Task Role

#### ECSAccess (6 permissions)
```yaml
- ecs:RunTask
- ecs:DescribeTaskDefinition
- ecs:DescribeTasks
- ecs:StopTask
- ecs:ListTasks
- iam:PassRole (with conditions)
```

#### EC2Access ⭐ CRITICAL!
```yaml
- ec2:DescribeNetworkInterfaces
```

**Without this**: Fargate container launch fails at _wait_for_task_ip()

#### ELB/ALB Access (need to verify production)
```yaml
- elasticloadbalancing:RegisterTargets
- elasticloadbalancing:DeregisterTargets
- elasticloadbalancing:DescribeTargetHealth
```

---

## 🔧 VERIFICATION COMMANDS FOR DEV ACCOUNT

### Check Task Execution Role

```bash
# List all policies
aws iam list-role-policies \
  --role-name deep-insight-task-execution-role-dev \
  --region us-east-1

# Check for ObservabilityAccess policy (CRITICAL!)
aws iam get-role-policy \
  --role-name deep-insight-task-execution-role-dev \
  --policy-name ObservabilityAccess \
  --region us-east-1 \
  --query 'PolicyDocument.Statement[0].Action[]' \
  --output text

# Expected: 8 lines of output (7 logs:* + 1 bedrock:*)
# If error: Policy does NOT exist → THIS IS THE PROBLEM!
```

### Check Task Role

```bash
# List all policies
aws iam list-role-policies \
  --role-name deep-insight-task-role-dev \
  --region us-east-1

# Check for EC2Access (CRITICAL!)
aws iam get-role-policy \
  --role-name deep-insight-task-role-dev \
  --policy-name EC2Access \
  --region us-east-1 \
  --query 'PolicyDocument.Statement[0].Action[]' \
  --output text

# Expected: ec2:DescribeNetworkInterfaces
# If error: Policy does NOT exist → THIS IS THE PROBLEM!
```

---

## 📋 SUMMARY: Required Inline Policies

### Task Execution Role (9 policies minimum)

| Policy Name | Status in Prod | Critical? | Purpose |
|-------------|----------------|-----------|---------|
| CloudWatchLogsAccess | ✅ (5 perms) | Yes | Basic logging |
| **ObservabilityAccess** | ✅ (8 perms) | **YES!** | Log delivery + Bedrock |
| BedrockAccess | ✅ (2 perms) | Yes | Model invocation |
| ECRAccess | ✅ | Yes | Image pull |
| ECSAccess | ✅ | Yes | Task operations |
| XRayAccess | ✅ | No | Tracing |
| EC2NetworkAccess | ✅ | Yes | ENI operations |
| ELBAccess | ✅ | Yes | Load balancer |
| CloudWatchMetricsAccess | ✅ | No | Metrics |

### Task Role (4 policies minimum)

| Policy Name | Status in Prod | Critical? | Purpose |
|-------------|----------------|-----------|---------|
| ECSAccess | ✅ (6 perms) | **YES!** | Launch Fargate tasks |
| ELBAccess | ✅ (4 perms) | **YES!** | Register with ALB |
| S3Access | ✅ (3 perms) | Yes | Report storage |
| BedrockAccess | ✅ (2 perms) | Yes | Model access |

**Note**: EC2 permissions (`ec2:DescribeNetworkInterfaces`) are in **Task Execution Role**, not Task Role.

---

## 🎯 DEV ACCOUNT ACTION ITEMS

### Must Verify These Policies Exist

Run these commands in dev account (057716757052):

```bash
# 1. CRITICAL: Check ObservabilityAccess in Task Execution Role
aws iam get-role-policy \
  --role-name deep-insight-task-execution-role-dev \
  --policy-name ObservabilityAccess

# If missing → CREATE IT! (8 permissions for log streams)

# 2. CRITICAL: Check EC2NetworkAccess in Task Execution Role
aws iam get-role-policy \
  --role-name deep-insight-task-execution-role-dev \
  --policy-name EC2NetworkAccess

# If missing → CREATE IT! (ec2:DescribeNetworkInterfaces)

# 3. CRITICAL: Check ELBAccess in Task Role
aws iam get-role-policy \
  --role-name deep-insight-task-role-dev \
  --policy-name ELBAccess

# If missing → CREATE IT! (4 ALB permissions)

# 4. Check ECSAccess in Task Role
aws iam get-role-policy \
  --role-name deep-insight-task-role-dev \
  --policy-name ECSAccess

# If missing or incomplete → UPDATE IT! (6 ECS permissions)
```

---

**Key Finding**: Production has **ObservabilityAccess** policy with all 8 CloudWatch Logs Delivery permissions. This is likely MISSING in dev account, explaining the log stream issues!
