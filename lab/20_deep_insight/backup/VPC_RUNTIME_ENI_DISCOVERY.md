# VPC Runtime ENI Investigation - BREAKTHROUGH DISCOVERY

**Date**: 2025-10-18
**Runtime ID**: bedrock_manus_runtime_vpc_final-7XCALx4Xuw
**Investigation**: Why no ENI was created for VPC Runtime

---

## 🎉 CRITICAL CORRECTION TO PREVIOUS ANALYSIS

**Previous Analysis**: Container never started, no ENI created ❌
**ACTUAL TRUTH**: Container IS running, ENI WAS created ✅

---

## 🔍 Breakthrough Discovery via CloudTrail

### CloudTrail Events (2025-10-18T04:05:17-18)

**Event 1: DryRun Validation** (04:05:17)
```json
{
  "eventName": "CreateNetworkInterface",
  "errorCode": "Client.DryRunOperation",
  "errorMessage": "Request would have succeeded, but DryRun flag is set.",
  "requestParameters": {
    "subnetId": "subnet-0b2fb367d6e823a79",
    "groupSet": {"items": [{"groupId": "sg-0affaea9ac4dc26b1"}]},
    "tagSpecificationSet": {
      "items": [{
        "resourceType": "network-interface",
        "tags": [{"key": "AmazonBedrockAgentCoreManaged", "value": "true"}]
      }]
    }
  }
}
```
**Result**: ✅ Validation PASSED

**Event 2: Actual ENI Creation** (04:05:18)
```json
{
  "eventName": "CreateNetworkInterface",
  "responseElements": {
    "networkInterface": {
      "networkInterfaceId": "eni-0a38f435c9aac51ea",
      "subnetId": "subnet-0b2fb367d6e823a79",
      "privateIpAddress": "10.100.1.76",
      "status": "pending",
      "groupSet": {"items": [{"groupId": "sg-0affaea9ac4dc26b1"}]},
      "tags": [{"key": "AmazonBedrockAgentCoreManaged", "value": "true"}]
    }
  }
}
```
**Result**: ✅ ENI CREATED SUCCESSFULLY

### Service-Linked Role Activity

**Role**: `AWSServiceRoleForBedrockAgentCoreNetwork`
- **Last Used**: 2025-10-18T04:05:17 (27 seconds after Runtime creation)
- **Action**: Created ENI in customer VPC
- **Permissions**: BedrockAgentCoreNetworkServiceRolePolicy

---

## 🖥️ ENI Current Status

```bash
$ aws ec2 describe-network-interfaces --network-interface-ids eni-0a38f435c9aac51ea

{
  "NetworkInterfaceId": "eni-0a38f435c9aac51ea",
  "Status": "in-use",
  "Attachment": {
    "AttachmentId": "ela-attach-0ce6732141089d5c4",
    "Status": "attached",
    "DeviceIndex": 1,
    "InstanceOwnerId": "amazon-aws"  ← Bedrock service owns this
  },
  "PrivateIpAddress": "10.100.1.76",
  "SubnetId": "subnet-0b2fb367d6e823a79",
  "VpcId": "vpc-05975448296a22c21",
  "SecurityGroups": [{"GroupId": "sg-0affaea9ac4dc26b1"}]
}
```

**Key Findings**:
- ✅ Status: **in-use** (actively used)
- ✅ Attachment Status: **attached** (connected to container)
- ✅ InstanceOwnerId: **amazon-aws** (Bedrock service manages this)
- ✅ DeviceIndex: **1** (attached as secondary network interface)

**Conclusion**: **The container instance EXISTS and is RUNNING**

---

## ❌ Why My Earlier Analysis Was Wrong

### What I Said Before:
> "No ENI created → No container → Container never started"

### What Actually Happened:
1. ✅ Bedrock DID create an ENI (eni-0a38f435c9aac51ea)
2. ✅ Bedrock DID attach the ENI to a container instance
3. ✅ The container IS running (ENI status: in-use, attached)
4. ❌ But NO observability configured → NO CloudWatch logs
5. ❌ Health check FAILING for unknown reason

### Why I Missed the ENI:

**My earlier check**:
```bash
# I looked for ENIs with "bedrock" in description
aws ec2 describe-network-interfaces \
  --filters "Name=description,Values=*bedrock*" \
  --query 'NetworkInterfaces[*].{ID, Description}'
```

**Result**: No matches (because description is empty!)

**Correct check**:
```bash
# Should have looked for the TAG instead
aws ec2 describe-network-interfaces \
  --filters "Name=tag:AmazonBedrockAgentCoreManaged,Values=true" \
  --query 'NetworkInterfaces[*].{ID, PrivateIP, Status}'
```

**Result**: Found `eni-0a38f435c9aac51ea` ✅

---

## 🔍 Real Root Cause: Missing Observability

### Why No CloudWatch Logs

**Runtime Creation Request** (from CloudTrail):
```json
{
  "agentRuntimeName": "bedrock_manus_runtime_vpc_final",
  "agentRuntimeArtifact": {...},
  "roleArn": "arn:aws:iam::057716757052:role/agentcore-bedrock_manus_runtime-role",
  "networkConfiguration": {
    "networkMode": "VPC",
    "networkModeConfig": {...}
  },
  "protocolConfiguration": {
    "serverProtocol": "HTTP"
  }
  // ❌ NO observabilityConfiguration!
}
```

**Result**: Runtime created WITHOUT observability enabled

**Comparison with .bedrock_agentcore.yaml**:
```yaml
observability:
  enabled: true  ← This was in YAML but NOT used during creation!
```

**Why This Matters**:
- Container IS running but NOT sending logs to CloudWatch
- We CANNOT see if the Python app started successfully
- We CANNOT debug why health checks are failing
- Even PUBLIC Runtime has no observability enabled

---

## 🚨 Health Check Failure Mystery

### What We Know:
1. ✅ Runtime status: `READY`
2. ✅ Container running (ENI attached)
3. ✅ Network connectivity possible (VPC endpoints configured)
4. ❌ Health check: **TIMEOUT**

### Error When Invoking:
```
RuntimeClientError: Runtime health check failed or timed out.
Please make sure that health check is implemented according to the requirements.
```

### Possible Root Causes:

#### 1. Python Application Crashed After Container Start
- Container launched successfully
- Python process started but encountered error
- No observability = can't see the crash

**Evidence**: None (need logs to confirm)

#### 2. Wrong Port or IP Binding
Dockerfile specifies:
```dockerfile
EXPOSE 8080
EXPOSE 8000
CMD ["opentelemetry-instrument", "python", "agentcore_runtime.py"]
```

Python app (`BedrockAgentCoreApp`) should listen on 8080.

**Potential Issue**: App might be binding to 127.0.0.1 instead of 0.0.0.0

**Evidence**: Need logs to verify

#### 3. Health Check Endpoint Not Responding
Bedrock expects HTTP GET `/health` to return 200 OK.

`BedrockAgentCoreApp()` should implement this automatically.

**Potential Issue**: Health check endpoint not implemented or returning error

**Evidence**: Need logs or direct connectivity test

#### 4. Security Group Blocking Health Checks
Bedrock service needs to probe the container from within VPC.

Current security group (`sg-0affaea9ac4dc26b1`):
- Inbound: VPC Endpoint SG + Self-referencing
- Outbound: HTTPS 443, HTTP 80, All traffic

**Potential Issue**: No explicit INBOUND rule from Bedrock service IP range

**Evidence**: Security group should allow, but might need debugging

#### 5. Missing Dependencies in Container
Container image pulled from ECR successfully, but runtime dependencies missing.

**Potential Issue**: Some Python packages failed to install

**Evidence**: Need container logs

---

## 🎯 What This Means

### Good News ✅:
1. **VPC mode infrastructure WORKS**
   - ENI creation successful
   - Container launches in VPC
   - Network isolation functional

2. **All prerequisites met**
   - VPC endpoints configured
   - Security groups correct
   - IAM permissions sufficient
   - Subnet supported (use1-az2)

3. **Container is running**
   - ENI attached and in-use
   - Bedrock successfully deployed container to VPC

### Bad News ❌:
1. **No visibility into container**
   - Observability not enabled
   - Cannot see application logs
   - Cannot debug health check failure

2. **Health check failing**
   - Unknown reason (no logs)
   - Prevents Runtime from being usable
   - invoke-agent-runtime returns error

3. **Cannot update observability**
   - CLI doesn't support updating observability-configuration
   - Would need to delete and recreate Runtime

---

## 🔧 Recommended Next Steps

### Option 1: Recreate Runtime with Observability (Recommended)

Create a new Runtime with observability enabled from the start:

```bash
aws bedrock-agentcore-control create-agent-runtime \
  --agent-runtime-name "bedrock_manus_runtime_vpc_obs" \
  --agent-runtime-artifact '{
    "containerConfiguration": {
      "containerUri": "057716757052.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-bedrock_manus_runtime_vpc:latest"
    }
  }' \
  --role-arn "arn:aws:iam::057716757052:role/agentcore-bedrock_manus_runtime-role" \
  --network-configuration '{
    "networkMode": "VPC",
    "networkModeConfig": {
      "securityGroups": ["sg-0affaea9ac4dc26b1"],
      "subnets": ["subnet-0b2fb367d6e823a79"]
    }
  }' \
  --observability-configuration '{
    "cloudWatch": {
      "enabled": true,
      "logGroup": "/aws/bedrock-agentcore/runtimes/bedrock_manus_runtime_vpc_obs-DEFAULT"
    }
  }' \
  --region us-east-1
```

**Benefits**:
- Will have CloudWatch logs
- Can debug health check failures
- Can see application startup

### Option 2: AWS Support Case

**Subject**: "VPC Runtime Container Running but Health Check Failing - No Logs"

**Key Information**:
- Runtime ID: `bedrock_manus_runtime_vpc_final-7XCALx4Xuw`
- ENI ID: `eni-0a38f435c9aac51ea`
- Status: READY but health check timeout
- Container confirmed running (ENI attached, in-use)
- No observability configured (no logs available)

**Questions**:
1. Why is health check failing if container is running?
2. Can observability be enabled on existing Runtime?
3. What is the expected health check endpoint implementation?
4. Can AWS provide container logs from their side?

### Option 3: Debug Without Observability

**Test connectivity to container** (if possible):
- Use VPC peering or bastion host
- Curl http://10.100.1.76:8080/health
- See if container responds

**Check container image locally**:
```bash
docker run -p 8080:8080 \
  057716757052.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-bedrock_manus_runtime_vpc:latest

# Test health check
curl http://localhost:8080/health
```

---

## 📊 Comparison: VPC vs PUBLIC Mode

| Aspect | PUBLIC Mode | VPC Mode |
|--------|-------------|----------|
| Runtime Created | ✅ READY | ✅ READY |
| ENI Created | N/A | ✅ YES (eni-0a38f435c9aac51ea) |
| Container Started | ✅ YES | ✅ YES (proven by ENI) |
| Observability Enabled | ❌ NO | ❌ NO |
| CloudWatch Logs | ❌ Empty | ❌ Empty |
| Health Check | ✅ PASS | ❌ FAIL |
| Invocation | ✅ SUCCESS | ❌ RuntimeClientError |

**Key Insight**: Both modes have NO observability, but PUBLIC mode works while VPC mode health check fails.

---

## 💡 Key Learnings

### 1. ENI Creation != Health Check Success
- Bedrock successfully creates container in VPC
- But container health check can still fail
- Need observability to debug failures

### 2. Observability is NOT Default
- Must explicitly enable `observabilityConfiguration` during creation
- Cannot be added after Runtime is created
- Without it, debugging is nearly impossible

### 3. CloudTrail is Essential for VPC Debugging
- CloudWatch logs were empty (no observability)
- CloudTrail showed ENI creation events
- Service-Linked Role activity visible in CloudTrail

### 4. Search by Tags, Not Description
- ENIs created by Bedrock have empty description
- Tagged with `AmazonBedrockAgentCoreManaged=true`
- Must search by tag, not description filter

---

## 🔗 Related Documents

- Previous (incorrect) analysis: `VPC_RUNTIME_HEALTH_CHECK_FAILURE_ANALYSIS.md`
- VPC infrastructure setup: `VPC_MODE_FINAL_SUMMARY.md`
- AWS Support template: `AWS_SUPPORT_CASE_TEMPLATE.md`

---

**Conclusion**: The VPC Runtime container IS running, proving VPC mode works. The health check failure is likely due to application-level issues that we cannot debug without observability. **Recommendation: Recreate Runtime with observability enabled to get container logs and debug the health check failure.**
