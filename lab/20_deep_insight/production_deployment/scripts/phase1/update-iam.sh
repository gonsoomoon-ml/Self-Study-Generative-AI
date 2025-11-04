#!/bin/bash
# Phase 1 IAM Stack Update Script
# Purpose: Add CodeBuild Execution Role to existing IAM stack
# Usage: ./update-iam.sh prod

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Environment (prod, dev, staging)
ENVIRONMENT=${1:-prod}

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}Phase 1 IAM Stack Update - Add CodeBuild Role${NC}"
echo -e "${BLUE}Environment: ${ENVIRONMENT}${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# ============================================================
# 1. Load configuration
# ============================================================
echo -e "${YELLOW}[1/5] Loading configuration...${NC}"

# Load .env file
ENV_FILE="${PROJECT_ROOT}/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ .env file not found: $ENV_FILE${NC}"
    echo -e "${YELLOW}Please create .env from .env.example${NC}"
    exit 1
fi

source "$ENV_FILE"

# Check AWS credentials
if ! aws sts get-caller-identity &>/dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ AWS Account: $ACCOUNT_ID${NC}"
echo ""

# ============================================================
# 2. Upload updated template to S3
# ============================================================
echo -e "${YELLOW}[2/5] Uploading updated template to S3...${NC}"

TEMPLATE_BUCKET="deep-insight-templates-${ENVIRONMENT}-${ACCOUNT_ID}"
IAM_TEMPLATE="${PROJECT_ROOT}/cloudformation/nested/iam.yaml"

if [ ! -f "$IAM_TEMPLATE" ]; then
    echo -e "${RED}❌ Template not found: $IAM_TEMPLATE${NC}"
    exit 1
fi

echo "Uploading to s3://${TEMPLATE_BUCKET}/nested/iam.yaml"
aws s3 cp "$IAM_TEMPLATE" "s3://${TEMPLATE_BUCKET}/nested/iam.yaml"

echo -e "${GREEN}✓ Template uploaded${NC}"
echo ""

# ============================================================
# 3. Find IAM Stack name
# ============================================================
echo -e "${YELLOW}[3/5] Finding IAM Stack...${NC}"

PARENT_STACK_NAME="deep-insight-infrastructure-${ENVIRONMENT}"

IAM_STACK_NAME=$(aws cloudformation describe-stack-resources \
  --stack-name "$PARENT_STACK_NAME" \
  --query "StackResources[?LogicalResourceId=='IAMStack'].PhysicalResourceId" \
  --output text)

if [ -z "$IAM_STACK_NAME" ]; then
    echo -e "${RED}❌ IAM Stack not found in parent stack: $PARENT_STACK_NAME${NC}"
    exit 1
fi

echo -e "${GREEN}✓ IAM Stack: $IAM_STACK_NAME${NC}"
echo ""

# ============================================================
# 4. Update IAM Stack
# ============================================================
echo -e "${YELLOW}[4/5] Updating IAM Stack...${NC}"

echo "Stack: $IAM_STACK_NAME"
echo "Template: https://s3.amazonaws.com/${TEMPLATE_BUCKET}/nested/iam.yaml"
echo ""

# Check for changes
CHANGESET_NAME="update-codebuild-role-$(date +%s)"

echo "Creating change set..."
aws cloudformation create-change-set \
  --stack-name "$IAM_STACK_NAME" \
  --change-set-name "$CHANGESET_NAME" \
  --template-url "https://s3.amazonaws.com/${TEMPLATE_BUCKET}/nested/iam.yaml" \
  --parameters \
    ParameterKey=Environment,UsePreviousValue=true \
    ParameterKey=ProjectName,UsePreviousValue=true \
    ParameterKey=S3BucketName,UsePreviousValue=true \
  --capabilities CAPABILITY_NAMED_IAM

echo "Waiting for change set creation..."
aws cloudformation wait change-set-create-complete \
  --stack-name "$IAM_STACK_NAME" \
  --change-set-name "$CHANGESET_NAME"

# Show changes
echo ""
echo -e "${BLUE}Changes to be applied:${NC}"
aws cloudformation describe-change-set \
  --stack-name "$IAM_STACK_NAME" \
  --change-set-name "$CHANGESET_NAME" \
  --query 'Changes[].{Action:ResourceChange.Action,Resource:ResourceChange.LogicalResourceId,Type:ResourceChange.ResourceType}' \
  --output table

echo ""
read -p "Apply these changes? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⚠ Update cancelled${NC}"
    aws cloudformation delete-change-set \
      --stack-name "$IAM_STACK_NAME" \
      --change-set-name "$CHANGESET_NAME"
    exit 0
fi

# Execute change set
echo ""
echo "Executing change set..."
aws cloudformation execute-change-set \
  --stack-name "$IAM_STACK_NAME" \
  --change-set-name "$CHANGESET_NAME"

echo "Waiting for stack update to complete (2-3 minutes)..."
aws cloudformation wait stack-update-complete \
  --stack-name "$IAM_STACK_NAME"

echo -e "${GREEN}✓ IAM Stack updated successfully${NC}"
echo ""

# ============================================================
# 5. Verify and update .env
# ============================================================
echo -e "${YELLOW}[5/5] Verifying new resources...${NC}"

# Get CodeBuild Role ARN
CODEBUILD_ROLE_ARN=$(aws cloudformation describe-stacks \
  --stack-name "$IAM_STACK_NAME" \
  --query 'Stacks[0].Outputs[?OutputKey==`CodeBuildExecutionRoleArn`].OutputValue' \
  --output text)

if [ -z "$CODEBUILD_ROLE_ARN" ]; then
    echo -e "${RED}❌ CodeBuild Role not found in outputs${NC}"
    exit 1
fi

echo -e "${GREEN}✓ CodeBuild Role created: $CODEBUILD_ROLE_ARN${NC}"

# Update .env file
if ! grep -q "CODEBUILD_EXECUTION_ROLE_ARN=" "$ENV_FILE"; then
    echo "" >> "$ENV_FILE"
    echo "# CodeBuild Execution Role (Phase 1 CloudFormation에서 생성)" >> "$ENV_FILE"
    echo "CODEBUILD_EXECUTION_ROLE_ARN=$CODEBUILD_ROLE_ARN" >> "$ENV_FILE"
    echo -e "${GREEN}✓ .env file updated${NC}"
else
    echo -e "${BLUE}ℹ CODEBUILD_EXECUTION_ROLE_ARN already exists in .env${NC}"
fi

echo ""

# ============================================================
# Summary
# ============================================================
echo -e "${BLUE}============================================================${NC}"
echo -e "${GREEN}✅ IAM Stack Update Complete!${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

echo -e "${BLUE}New Resources:${NC}"
echo "  - CodeBuild Execution Role: $CODEBUILD_ROLE_ARN"
echo ""

echo -e "${BLUE}Next Steps:${NC}"
echo "  1. (Optional) Edit 01_create_agentcore_runtime.py:"
echo "     - Uncomment CODEBUILD_EXECUTION_ROLE_ARN loading"
echo "     - Uncomment code_build_execution_role parameter"
echo ""
echo "  2. Run Phase 3 deployment:"
echo "     python3 01_create_agentcore_runtime.py"
echo ""

echo -e "${YELLOW}Note: CodeBuild Role 미사용 시 toolkit이 자동으로 생성/재사용 (정상 작동)${NC}"
echo ""
