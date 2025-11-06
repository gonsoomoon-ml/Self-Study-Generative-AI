# Development Account Documentation

This folder contains comprehensive documentation for deploying and troubleshooting the Deep Insight system in the **Development Account (057716757052)**.

---

## 📄 Documents Overview

### 1. **DEV_ACCOUNT_QUICK_CHECKLIST.md** ⭐ START HERE
**Purpose**: 30-minute quick fix guide
**When to use**: You need to fix the dev account ASAP

**Contains**:
- ⚡ Quick fix procedure (6 steps)
- ✅ Prerequisites check commands
- 🔧 One-liner fixes for HTTP scheme bug
- 🚨 Stop points and troubleshooting
- 🎯 Expected final state verification

**Estimated Time**: 30 minutes

---

### 2. **DEV_ACCOUNT_DEPLOYMENT_GUIDE.md**
**Purpose**: Comprehensive deployment guide with full context
**When to use**: You need detailed understanding and step-by-step instructions

**Contains**:
- 🚨 Critical issues analysis (environment variables + HTTP scheme)
- ✅ 20 required IAM permissions (11 + 9)
- 📋 16 required environment variables
- 🔧 7-step fix procedure with explanations
- 📊 Success criteria and debugging checklist
- 🎯 Production vs Dev comparison

**Estimated Time**: 1-2 hours (includes reading and understanding)

---

### 3. **CLOUDWATCH_IAM_PERMISSIONS_FOR_DEV.md** ⭐ IAM FOCUS
**Purpose**: CloudWatch Logs IAM permissions deep dive
**When to use**: Dev account cannot create per-invocation log streams

**Contains**:
- 🚨 ObservabilityAccess policy (8 critical permissions)
- 📋 Complete policy JSON (ready to deploy)
- 🔍 Verification commands
- 🔧 Two deployment options (CLI vs CloudFormation)
- 📊 Why each permission is needed
- ✅ Post-deployment verification

**Key Finding**: Dev account likely missing `ObservabilityAccess` policy in Task Execution Role

---

### 4. **ACTUAL_IAM_PERMISSIONS_ANALYSIS.md**
**Purpose**: Complete IAM audit of production account (738490718699)
**When to use**: You need to compare dev IAM with production IAM

**Contains**:
- 🔍 Direct AWS API inspection (not CloudFormation templates)
- ✅ All 9 Task Execution Role policies with full JSON
- ✅ All 4 Task Role policies with full JSON
- 📊 Policy-by-policy comparison tables
- 🎯 Dev account verification commands
- 📋 Complete permissions checklist

**Key Finding**: Production has ALL required permissions - use this as reference

---

## 🎯 Quick Decision Tree

### "I need to fix dev account NOW"
→ Read: **DEV_ACCOUNT_QUICK_CHECKLIST.md**
→ Time: 30 minutes

### "Log streams aren't being created"
→ Read: **CLOUDWATCH_IAM_PERMISSIONS_FOR_DEV.md**
→ Action: Add ObservabilityAccess policy
→ Time: 5 minutes

### "Environment variables are null"
→ Read: **DEV_ACCOUNT_QUICK_CHECKLIST.md** (Steps 1-5)
→ Check: Toolkit version, IAM permissions, fresh creation
→ Time: 20 minutes

### "I want to understand everything"
→ Read: **DEV_ACCOUNT_DEPLOYMENT_GUIDE.md**
→ Then: **ACTUAL_IAM_PERMISSIONS_ANALYSIS.md**
→ Time: 1-2 hours

### "I want to compare dev vs prod IAM"
→ Read: **ACTUAL_IAM_PERMISSIONS_ANALYSIS.md**
→ Use: Verification commands on dev account
→ Time: 15 minutes

---

## 🚨 Most Common Issues in Dev Account

### Issue 1: Environment Variables = 0 (NULL)
**Symptoms**: Runtime created but environmentVariables is null
**Root Causes**:
1. Outdated toolkit version (< 0.1.28)
2. Missing IAM permissions
3. Runtime update instead of fresh creation

**Fix**: DEV_ACCOUNT_QUICK_CHECKLIST.md → Steps 1-6

---

### Issue 2: No Per-Invocation Log Streams
**Symptoms**: All logs in single stream, can't debug individual jobs
**Root Cause**: Missing ObservabilityAccess policy (8 permissions)

**Fix**: CLOUDWATCH_IAM_PERMISSIONS_FOR_DEV.md → Option 1 (2 minutes)

---

### Issue 3: HTTP Scheme Missing
**Symptoms**: Cookie acquisition fails, health checks fail
**Root Cause**: URLs missing `http://` prefix in 2 files

**Fix**: DEV_ACCOUNT_QUICK_CHECKLIST.md → Step 2 (2 minutes)

---

### Issue 4: Fargate Container Launch Fails
**Symptoms**: Tasks start but immediately stop, unhealthy targets
**Root Causes**:
1. Missing EC2NetworkAccess (ec2:DescribeNetworkInterfaces)
2. Missing ELBAccess (ALB registration permissions)
3. Wrong task definition or container name

**Fix**: ACTUAL_IAM_PERMISSIONS_ANALYSIS.md → Dev Account Action Items

---

## 📊 Critical Permissions Summary

### Task Execution Role (must have)
- ✅ **ObservabilityAccess** (8 perms) ← Most important!
- ✅ CloudWatchLogsAccess (5 perms)
- ✅ EC2NetworkAccess (1 perm)
- ✅ BedrockAccess (2 perms)
- ✅ ECRAccess (4 perms)
- ✅ ECSAccess (5 perms)

**Total**: 25 permissions across 6 policies

### Task Role (must have)
- ✅ ECSAccess (6 perms including iam:PassRole)
- ✅ ELBAccess (4 perms)
- ✅ S3Access (3 perms)
- ✅ BedrockAccess (2 perms)

**Total**: 15 permissions across 4 policies

---

## 🔧 Quick Verification Commands

### Check if ObservabilityAccess exists (most critical!)
```bash
aws iam get-role-policy \
  --role-name deep-insight-task-execution-role-dev \
  --policy-name ObservabilityAccess \
  --region us-east-1
```

If error → **THIS IS THE MAIN PROBLEM**

### Check environment variables count
```bash
RUNTIME_ID=$(grep RUNTIME_ID .env | cut -d= -f2)
aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-id $RUNTIME_ID \
  --region us-east-1 \
  --query 'length(keys(environmentVariables))' \
  --output text
```

Expected: 16 (not 0!)

### Check toolkit version
```bash
pip show bedrock-agentcore-starter-toolkit | grep Version
```

Required: >= 0.1.28

---

## 📚 Related Files (Outside This Folder)

**In Project Root**:
- `CLAUDE.md` - Main project documentation with all fixes
- `.env.example` - Template with all required environment variables
- `01_create_agentcore_runtime.py` - Runtime creation script
- `03_invoke_agentcore_job_vpc.py` - Runtime test script

**In CloudFormation**:
- `production_deployment/cloudformation/phase1-infrastructure.yaml` - IAM roles and policies
- `production_deployment/scripts/setup_env.sh` - Auto-generate .env from CloudFormation

---

## 🎯 Success Criteria

Your dev account is working when:

1. ✅ Environment variables count = 16 (not 0)
2. ✅ Per-invocation log streams created
3. ✅ Cookie acquisition succeeds
4. ✅ Fargate containers launch successfully
5. ✅ Health checks pass
6. ✅ PDF reports generated and saved to S3

---

**Generated**: 2025-11-06
**Target Account**: 057716757052 (Development)
**Reference Account**: 738490718699 (Production - working ✅)
**Status**: Ready for deployment
