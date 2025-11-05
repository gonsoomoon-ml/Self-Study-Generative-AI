# AWS Support Case - Bedrock AgentCore VPC Mode Failure

**Date**: 2025-10-18
**Severity**: Medium
**Category**: Service Question / Technical Issue

---

## Subject

Bedrock AgentCore Runtime VPC mode fails immediately with CREATE_FAILED / UPDATE_FAILED (no error details)

---

## Description

I am attempting to enable VPC mode for Bedrock AgentCore Runtime in us-east-1 but consistently receive CREATE_FAILED/UPDATE_FAILED status with no error messages or logs.

### What I've Tried

1. **Updated existing PUBLIC runtime to VPC** (8 attempts)
   - Result: Immediately UPDATE_FAILED
   - No CloudWatch logs

2. **Created new runtime in VPC mode** (1 attempt)
   - Result: CREATE_FAILED in 3 seconds
   - No CloudWatch logs
   - No CloudTrail error details

### Infrastructure Prepared (Following AWS Documentation)

All required infrastructure is in place:

**✅ VPC Endpoints** (all in `available` state):
- ECR API: `vpce-039416a0eccab0c78`
- ECR Docker: `vpce-08bd4278d0dd8779d`
- CloudWatch Logs: `vpce-0d55a82f7b038ae04`
- S3 Gateway: `vpce-06d422d1c6e63afac`
- Bedrock AgentCore: `vpce-0b1c05f284838d951`
- Bedrock AgentCore Gateway: `vpce-00259de820f493d28`

**✅ Network Configuration**:
- VPC ID: `vpc-05975448296a22c21`
- Private Subnets:
  - `subnet-0b2fb367d6e823a79` (us-east-1a, AZ ID: `use1-az2`) ✅ Supported
  - `subnet-0ed3a6040386768cf` (us-east-1c, AZ ID: `use1-az6`) ✅ Supported
- NAT Gateway: `nat-084c84d8f7ab9ac5c` (available)
- Route Table: 0.0.0.0/0 → NAT Gateway
- DNS Hostnames: Enabled
- DNS Support: Enabled

**✅ Security Groups**:
- AgentCore SG: `sg-0affaea9ac4dc26b1`
  - Inbound: VPC Endpoint SG + Self-referencing
  - Outbound: HTTP 80, HTTPS 443, All traffic

**✅ IAM**:
- Service-Linked Role: `AWSServiceRoleForBedrockAgentCoreNetwork` (exists)
- Execution Role: `arn:aws:iam::057716757052:role/agentcore-bedrock_manus_runtime-role`
  - Permissions: AdministratorAccess
  - Trust Policy: bedrock-agentcore.amazonaws.com

### Test Commands

**Attempt 1: Update existing runtime**
```bash
aws bedrock-agentcore-control update-agent-runtime \
  --agent-runtime-id bedrock_manus_runtime_vpc-cRZMLaFTr6 \
  --region us-east-1 \
  --role-arn "arn:aws:iam::057716757052:role/agentcore-bedrock_manus_runtime-role" \
  --agent-runtime-artifact '{
    "containerConfiguration": {
      "containerUri": "057716757052.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-bedrock_manus_runtime_vpc:latest"
    }
  }' \
  --network-configuration '{
    "networkMode": "VPC",
    "networkModeConfig": {
      "securityGroups": ["sg-0affaea9ac4dc26b1"],
      "subnets": ["subnet-0b2fb367d6e823a79", "subnet-0ed3a6040386768cf"]
    }
  }'
```
**Result**: `UPDATE_FAILED` (Version 8)

**Attempt 2: Create new runtime**
```bash
aws bedrock-agentcore-control create-agent-runtime \
  --agent-runtime-name "bedrock_manus_runtime_vpc_new" \
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
      "subnets": ["subnet-0b2fb367d6e823a79", "subnet-0ed3a6040386768cf"]
    }
  }' \
  --region us-east-1
```
**Result**: `CREATE_FAILED` in 3 seconds
**Runtime ID**: `bedrock_manus_runtime_vpc_new-r6yIW22iVV`

---

## Questions

1. **Is VPC mode enabled for my AWS account (057716757052) in us-east-1?**
   - Is there an account-level feature flag or opt-in required?

2. **Why do CREATE_FAILED/UPDATE_FAILED provide no error details?**
   - No CloudWatch logs in `/aws/bedrock-agentcore/runtimes/*`
   - No error messages in API response
   - No CloudTrail error details

3. **Is PUBLIC → VPC migration supported via update-agent-runtime?**
   - All documentation examples use `create-agent-runtime`
   - Should I delete the existing runtime and recreate?

4. **Are there any undocumented requirements for VPC mode?**
   - Service quotas
   - Region/AZ-specific limitations
   - Additional VPC Endpoints needed

5. **Can you investigate why Runtime ID `bedrock_manus_runtime_vpc_new-r6yIW22iVV` failed?**
   - Created: 2025-10-18T01:28:23
   - Failed: 2025-10-18T01:28:26 (3 seconds)

---

## Expected Behavior

Runtime should enter `CREATING` state and eventually become `READY` with VPC mode enabled.

## Actual Behavior

Runtime immediately fails with:
- Status: `CREATE_FAILED` or `UPDATE_FAILED`
- No error logs
- No error messages
- VPC configuration appears correctly applied in metadata

---

## Environment

- **Account ID**: 057716757052
- **Region**: us-east-1
- **Service**: Bedrock AgentCore
- **Failed Runtime IDs**:
  - Update attempts: `bedrock_manus_runtime_vpc-cRZMLaFTr6` (Versions 6, 7, 8)
  - Create attempt: `bedrock_manus_runtime_vpc_new-r6yIW22iVV`

---

## Additional Context

VPC support for Bedrock AgentCore was announced in September 2025. I followed the complete setup guide including all VPC Endpoints (ECR, S3, Logs, AgentCore Gateway) and verified all prerequisites.

The failure happens within seconds (before any actual resource creation), suggesting a pre-flight validation issue rather than runtime connectivity problem.

---

## Requested Actions

1. Investigate why VPC mode creation/update fails immediately
2. Enable VPC mode for my account if feature flag required
3. Provide error details for the failed runtime attempts
4. Confirm supported Availability Zones for us-east-1
5. Share any additional documentation for VPC mode setup

---

## Contact Preference

- Email notifications preferred
- Available for follow-up calls if needed

Thank you for your assistance!
