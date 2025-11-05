# Bedrock AgentCore VPC Mode UPDATE_FAILED Analysis

**Date**: 2025-10-18
**Runtime ID**: bedrock_manus_runtime_vpc-cRZMLaFTr6
**Region**: us-east-1
**Issue**: VPC mode update consistently fails with UPDATE_FAILED status

---

## 📋 Summary

Attempted to migrate Bedrock AgentCore Runtime from PUBLIC to VPC network mode. The VPC configuration was successfully applied to the runtime metadata, but the status immediately transitions to UPDATE_FAILED after each update attempt.

---

## 🔍 What We Tried

### 1. Initial Deployment Attempts

**Attempt 1**: Using `bedrock_agentcore_starter_toolkit` Python SDK
- **Method**: `runtime.launch()` with VPC configuration in `.bedrock_agentcore.yaml`
- **Result**: ❌ Toolkit removed `network_mode_config` during processing
- **Issue**: Toolkit bug - VPC configuration not properly handled

**Attempt 2**: Direct AWS CLI update
- **Method**: `aws bedrock-agentcore-control update-agent-runtime`
- **Result**: ❌ UPDATE_FAILED (Version 6)
- **VPC Config Applied**: ✅ Yes (confirmed in metadata)
- **Status**: Immediately failed

**Attempt 3**: After fixing route table
- **Method**: AWS CLI update after correcting NAT Gateway routing
- **Result**: ❌ UPDATE_FAILED (Version 7)
- **Status**: Immediately failed

### 2. Infrastructure Verification

✅ **VPC Endpoints** (Available):
```
vpce-0b1c05f284838d951  (bedrock-agentcore data plane)
vpce-00259de820f493d28  (bedrock-agentcore gateway)
```

✅ **Security Groups** (Properly Configured):
- **AgentCore SG** (sg-0affaea9ac4dc26b1):
  - Inbound: VPC Endpoint SG + Self-referencing
  - Outbound: HTTP 80 (ALB), HTTPS 443 (VPC Endpoint), All traffic (0.0.0.0/0)

✅ **Subnets** (Valid AZs):
- subnet-0b2fb367d6e823a79 (us-east-1a, 10.100.1.0/24)
- subnet-0ed3a6040386768cf (us-east-1c, 10.100.2.0/24)

✅ **Route Tables** (Fixed):
- Private route table (rtb-03f767343ef0bfe88):
  - 10.100.0.0/16 → local
  - **0.0.0.0/0 → nat-084c84d8f7ab9ac5c** (Fixed!)

✅ **NAT Gateway** (Available):
- nat-084c84d8f7ab9ac5c (State: available)

✅ **IAM Permissions**:
- Execution Role: AdministratorAccess
- Trust Policy: bedrock-agentcore.amazonaws.com

### 3. Issues Discovered

❌ **Missing Service-Linked Role**:
```bash
$ aws iam get-role --role-name AWSServiceRoleForBedrockAgentCore
NoSuchEntity: The role with name AWSServiceRoleForBedrockAgentCore cannot be found
```

❌ **Cannot Create Service-Linked Role**:
```bash
$ aws iam create-service-linked-role --aws-service-name bedrock-agentcore.amazonaws.com
AccessDenied: Cannot find Service Linked Role template for bedrock-agentcore.amazonaws.com
```

❌ **No Error Logs**:
- CloudWatch logs completely empty
- No error messages in runtime metadata
- UPDATE_FAILED status with no details

---

## 🚨 Root Cause Analysis

### Most Likely Causes

1. **Service-Linked Role Missing**
   - AWS typically auto-creates service-linked roles when needed
   - The template doesn't exist or the service can't create it
   - This prevents the service from creating ENIs in VPC

2. **VPC Mode Not Fully Available**
   - VPC support announced in September 2025
   - VPC Endpoints exist but might not be fully functional
   - Possible limited availability or beta status in us-east-1

3. **Availability Zone Constraints**
   - AgentCore might only support specific AZs
   - us-east-1a and us-east-1c might not be supported
   - No documentation on AZ requirements

4. **Hidden Prerequisites**
   - Missing AWS Support case or feature flag
   - Account-level enablement required
   - Service quota issues

### Why It Fails Immediately

The UPDATE_FAILED happens within seconds, suggesting:
- Pre-flight validation failure (not a runtime issue)
- Service rejects the configuration before attempting deployment
- IAM/permissions check failing silently

---

## 📊 Configuration Status

**Current Runtime State**:
```json
{
  "agentRuntimeId": "bedrock_manus_runtime_vpc-cRZMLaFTr6",
  "agentRuntimeVersion": "7",
  "status": "UPDATE_FAILED",
  "networkConfiguration": {
    "networkMode": "VPC",
    "networkModeConfig": {
      "securityGroups": ["sg-0affaea9ac4dc26b1"],
      "subnets": [
        "subnet-0b2fb367d6e823a79",
        "subnet-0ed3a6040386768cf"
      ]
    }
  }
}
```

**Note**: VPC configuration IS present in metadata, but runtime failed to apply it.

---

## 🎯 Recommendations

### Immediate Actions

1. **Open AWS Support Case**
   - Subject: "Bedrock AgentCore VPC mode UPDATE_FAILED in us-east-1"
   - Include Runtime ID: `bedrock_manus_runtime_vpc-cRZMLaFTr6`
   - Request:
     - Why UPDATE_FAILED has no error details
     - Whether service-linked role is auto-created
     - VPC mode availability status in us-east-1
     - Supported Availability Zones

2. **Try Different AZs**
   - Create subnets in us-east-1b, us-east-1d
   - Some AWS services have AZ-specific limitations

3. **Check Service Quotas**
   ```bash
   aws service-quotas list-service-quotas \
     --service-code bedrock \
     --query 'Quotas[?contains(QuotaName, `VPC`)]'
   ```

### Alternative Approaches

1. **Keep PUBLIC Mode**
   - Current production deployment works fine
   - VPC mode not critical for functionality
   - Revisit when VPC support matures

2. **Use PrivateLink Without VPC Mode**
   - VPC Endpoints already created
   - May provide some private connectivity benefits
   - Test if PUBLIC mode can use VPC Endpoints

3. **Wait for General Availability**
   - VPC support is relatively new (Sep 2025)
   - May need AWS account enablement
   - Monitor AWS service announcements

---

## 📝 Lessons Learned

1. **Toolkit Limitations**
   - `bedrock_agentcore_starter_toolkit` doesn't properly handle VPC config
   - Use AWS CLI for VPC mode updates

2. **Silent Failures**
   - No error messages in CloudWatch
   - No detailed failure reasons in API responses
   - Makes debugging extremely difficult

3. **Documentation Gaps**
   - No clear prerequisites for VPC mode
   - No AZ requirements documented
   - No service-linked role documentation

---

## 🔗 References

- VPC Support Announcement: https://aws.amazon.com/about-aws/whats-new/2025/09/bedrock-agentcore-vpc-privatelink/
- Runtime ARN: `arn:aws:bedrock-agentcore:us-east-1:057716757052:runtime/bedrock_manus_runtime_vpc-cRZMLaFTr6`
- Test VPC ID: `vpc-05975448296a22c21`
- VPC Endpoint (Data): `vpce-0b1c05f284838d951`
- VPC Endpoint (Gateway): `vpce-00259de820f493d28`

---

## ✅ Next Steps

1. **Revert to PUBLIC mode** (for production stability)
2. **File AWS Support case** (to understand UPDATE_FAILED)
3. **Monitor for updates** (VPC support maturity)
4. **Document workaround** (if found)

---

**Status**: Unable to enable VPC mode
**Workaround**: Continue using PUBLIC mode with existing working deployment
