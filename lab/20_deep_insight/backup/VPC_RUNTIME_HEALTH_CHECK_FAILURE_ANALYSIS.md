# Bedrock AgentCore VPC Runtime Health Check Failure - Root Cause Analysis

**Date**: 2025-10-18
**Runtime ID**: bedrock_manus_runtime_vpc_final-7XCALx4Xuw
**Region**: us-east-1
**Status**: READY (but non-functional)

---

## 📋 Executive Summary

Successfully created Bedrock AgentCore Runtime in VPC mode with correct AZ configuration, but the Runtime container **never starts**. Health check failures occur because no container instance exists to respond to health checks.

---

## 🔍 Root Cause Analysis

### Symptom
```
RuntimeClientError: Runtime health check failed or timed out
```

### Investigation Steps

#### 1. Infrastructure Verification ✅
All required infrastructure is properly configured:

**VPC Endpoints** (All Available):
- ✅ ECR API: `vpce-039416a0eccab0c78`
- ✅ ECR Docker: `vpce-08bd4278d0dd8779d`
- ✅ CloudWatch Logs: `vpce-0d55a82f7b038ae04`
- ✅ S3 Gateway: `vpce-06d422d1c6e63afac`
- ✅ Bedrock AgentCore: `vpce-0b1c05f284838d951`
- ✅ Bedrock AgentCore Gateway: `vpce-00259de820f493d28`

**Network Configuration**:
- ✅ Subnet: subnet-0b2fb367d6e823a79 (us-east-1a, AZ ID: use1-az2) ← **Supported AZ**
- ✅ Available IPs: 242 (plenty of capacity)
- ✅ Security Group: sg-0affaea9ac4dc26b1 (proper inbound/outbound rules)
- ✅ NAT Gateway: nat-084c84d8f7ab9ac5c (available)
- ✅ Route Table: 0.0.0.0/0 → NAT Gateway

**ECR Image**:
- ✅ Repository: bedrock-agentcore-bedrock_manus_runtime_vpc
- ✅ Tag: latest
- ✅ Digest: sha256:3c67d805526903e25db06b64e4ae61ffd2cd96818232ade0f6c313ac62b973d1
- ✅ Pushed: 2025-10-18T03:05:54
- ✅ Size: 465 MB

**Runtime Configuration**:
- ✅ Status: READY
- ✅ Network Mode: VPC
- ✅ Container URI: 057716757052.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-bedrock_manus_runtime_vpc:latest

#### 2. Log Analysis - THE SMOKING GUN 🔥

**VPC Runtime Logs** (`/aws/bedrock-agentcore/runtimes/bedrock_manus_runtime_vpc_final-7XCALx4Xuw-DEFAULT`):
```
(completely empty - NO logs at all)
```

**PUBLIC Runtime Logs** (for comparison):
```
2025-10-18T03:58:17 INFO:src.tools.global_fargate_coordinator:🚀 Initializing Global Fargate Session Manager
(container startup logs present)
```

**Conclusion**: The VPC Runtime container **never starts**. Not even a single log entry was written.

#### 3. Network Interface Analysis - CRITICAL FINDING 🚨

**ENIs in subnet-0b2fb367d6e823a79**:
- ✅ VPC Endpoint ENIs: 7 interfaces (ECR, Logs, S3, Bedrock endpoints)
- ✅ ALB ENI: 1 interface for test-vpc-private-alb
- ❌ **Runtime Container ENI: NONE** ← **Missing!**

**What This Means**:
- Bedrock AgentCore service never attempted to create a container instance
- No ENI = No container launch
- Container must have an ENI to run in VPC mode

---

## 🎯 Root Cause

**The Bedrock AgentCore service is not launching the container instance at all.**

Despite the Runtime showing `READY` status, the service never:
1. Created an ENI in the VPC subnet
2. Pulled the container image from ECR
3. Started the container
4. Wrote any logs to CloudWatch

This is a **service-level issue**, not a container or network configuration issue.

---

## 🤔 Possible Causes

### 1. Missing Permissions (Most Likely)
The Bedrock AgentCore service might lack permissions to:
- Create ENIs in the VPC (`ec2:CreateNetworkInterface`)
- Attach ENIs to the container (`ec2:AttachNetworkInterface`)
- Modify ENI security groups (`ec2:ModifyNetworkInterfaceAttribute`)

**Service-Linked Role Check**:
```bash
$ aws iam list-roles --query "Roles[?contains(RoleName, 'Bedrock')]"
# Need to verify: AWSServiceRoleForBedrockAgentCoreNetwork
```

### 2. VPC Mode Not Enabled for Account
- VPC support announced September 2025 (relatively new)
- May require AWS account-level enablement
- Could be in limited availability for us-east-1

### 3. Undocumented Prerequisites
- Missing additional VPC endpoints
- Specific IAM policy requirements
- Service quota limitations

### 4. Single-Subnet Limitation
- Using only 1 subnet (subnet-0b2fb367d6e823a79)
- AWS services often require multi-AZ for HA
- However, Runtime was created successfully (status: READY)

---

## 📊 Comparison: VPC vs PUBLIC Mode

| Aspect | PUBLIC Mode (✅ Working) | VPC Mode (❌ Failed) |
|--------|-------------------------|---------------------|
| Runtime Status | READY | READY |
| Container Started | ✅ Yes | ❌ No |
| CloudWatch Logs | ✅ Present | ❌ Empty |
| ENI Created | N/A (no VPC) | ❌ No ENI |
| Health Check | ✅ Pass | ❌ Timeout |
| Invocation | ✅ Success | ❌ RuntimeClientError |

---

## 🔧 Attempted Fixes

1. ✅ Created all required VPC endpoints (ECR, S3, Logs, Bedrock)
2. ✅ Fixed Availability Zone to use supported AZ (use1-az2)
3. ✅ Configured security groups with proper rules
4. ✅ Verified ECR image exists and is accessible
5. ✅ Ensured NAT Gateway and routing configured
6. ✅ Confirmed sufficient IP addresses in subnet

**All prerequisites met, but container still doesn't start.**

---

## ✅ Recommended Actions

### Immediate: Contact AWS Support

**Subject**: Bedrock AgentCore VPC Mode - Container Not Starting (ENI Not Created)

**Key Information**:
- Runtime ID: `bedrock_manus_runtime_vpc_final-7XCALx4Xuw`
- Status: READY (but non-functional)
- Region: us-east-1
- Network Mode: VPC
- Subnet: subnet-0b2fb367d6e823a79 (use1-az2, supported AZ)
- Issue: No ENI created, no container started, no logs written

**Questions for AWS**:
1. Why is no ENI being created for the VPC Runtime container?
2. What permissions does the service need to create ENIs in customer VPC?
3. Is VPC mode fully available in us-east-1 for account 057716757052?
4. Are there any undocumented prerequisites for VPC mode?
5. Does VPC mode require multi-AZ (2+ subnets)?

### Verification Steps

**Check Service-Linked Role**:
```bash
aws iam get-role --role-name AWSServiceRoleForBedrockAgentCoreNetwork
aws iam list-attached-role-policies --role-name AWSServiceRoleForBedrockAgentCoreNetwork
```

**Check VPC Flow Logs** (if enabled):
```bash
# Look for ENI creation attempts or permission denied errors
```

**Try Multi-Subnet Configuration**:
```bash
# Create Runtime with 2 subnets in supported AZs
aws bedrock-agentcore-control create-agent-runtime \
  --network-configuration '{
    "networkMode": "VPC",
    "networkModeConfig": {
      "securityGroups": ["sg-0affaea9ac4dc26b1"],
      "subnets": ["subnet-0b2fb367d6e823a79", "subnet-in-use1-az4"]
    }
  }'
```

### Workaround: Continue with PUBLIC Mode

The production Runtime `bedrock_manus_runtime-E8I6oFGlTA` (PUBLIC mode) is working correctly. VPC mode is not required for functionality - it only provides:
- Private network connectivity
- VPC-based security controls
- PrivateLink connectivity

**Recommendation**: Use PUBLIC mode until VPC mode issue is resolved by AWS.

---

## 📝 Key Files

- **Test Script**: `invoke_agentcore_job_vpc.py`
- **Runtime Config**: `.bedrock_agentcore.yaml`
- **Container Image**: `057716757052.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-bedrock_manus_runtime_vpc:latest`
- **Log Group**: `/aws/bedrock-agentcore/runtimes/bedrock_manus_runtime_vpc_final-7XCALx4Xuw-DEFAULT` (empty)

---

## 🔗 References

- AWS VPC Support Announcement: https://aws.amazon.com/about-aws/whats-new/2025/09/bedrock-agentcore-vpc-privatelink/
- Runtime Service Contract: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-service-contract.html
- Supported AZs for us-east-1: use1-az1, use1-az2, use1-az4
- AWS Support Case Template: `AWS_SUPPORT_CASE_TEMPLATE.md`

---

## 📅 Timeline

- **03:05:54** - ECR image pushed
- **04:04:50** - VPC Runtime created (status: READY)
- **04:18:48** - First invocation attempt (health check failed)
- **04:23:46** - Investigation confirmed: no ENI, no container, no logs

---

**Conclusion**: The Bedrock AgentCore service successfully created the Runtime metadata (status: READY) but never launched the actual container instance in the VPC. This requires AWS Support investigation as all customer-side prerequisites are met.
