#!/bin/bash
# deploy_phase1_phase2.sh - Deploy Phase 1 + Phase 2 (All CloudFormation Infrastructure)
#
# This script automatically verifies AZs and deploys both CloudFormation phases:
#   - Phase 1: VPC, Security Groups, VPC Endpoints, ALB, IAM
#   - Phase 2: ECR, Docker Image, ECS Cluster, Task Definition
#
# Usage: ./deploy_phase1_phase2.sh <environment> <region>
# Example: ./deploy_phase1_phase2.sh prod us-east-1
#
# Note: This is a WRAPPER that calls phase1/deploy.sh and phase2/deploy.sh
#       You can also run those scripts individually for more control.

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Usage
if [ $# -lt 2 ]; then
    echo -e "${RED}Usage: $0 <environment> <region>${NC}"
    echo ""
    echo "Arguments:"
    echo "  environment  - Environment name (dev, staging, prod)"
    echo "  region       - AWS region (us-east-1, us-west-2, etc.)"
    echo ""
    echo "Examples:"
    echo "  $0 prod us-east-1       # Deploy to us-east-1"
    echo "  $0 staging us-west-2    # Deploy to us-west-2"
    echo ""
    exit 1
fi

ENVIRONMENT=$1
REGION=$2

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}Deep Insight - Automated Multi-Region Deployment${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""
echo -e "Environment: ${GREEN}$ENVIRONMENT${NC}"
echo -e "Region:      ${GREEN}$REGION${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Step 1: Verify AWS credentials
echo -e "${BLUE}Step 1: Verifying AWS credentials...${NC}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}❌ Error: AWS credentials not configured${NC}"
    echo "Please run: aws configure"
    exit 1
fi

AWS_REGION=$(aws configure get region 2>/dev/null || echo "")
echo -e "  ✅ AWS Account ID: ${GREEN}$AWS_ACCOUNT_ID${NC}"
echo -e "  ✅ Default Region: ${GREEN}${AWS_REGION:-not set}${NC}"
echo ""

# Step 2: Verify AZ support for the region
echo -e "${BLUE}Step 2: Verifying Availability Zone support...${NC}"
echo ""

# Define supported AZ IDs per region
declare -A SUPPORTED_AZS
SUPPORTED_AZS[us-east-1]="use1-az1 use1-az2 use1-az4"
SUPPORTED_AZS[us-east-2]="use2-az1 use2-az2 use2-az3"
SUPPORTED_AZS[us-west-2]="usw2-az1 usw2-az2 usw2-az3"
SUPPORTED_AZS[ap-south-1]="aps1-az1 aps1-az2 aps1-az3"
SUPPORTED_AZS[ap-southeast-1]="apse1-az1 apse1-az2 apse1-az3"
SUPPORTED_AZS[ap-southeast-2]="apse2-az1 apse2-az2 apse2-az3"
SUPPORTED_AZS[ap-northeast-1]="apne1-az1 apne1-az2 apne1-az4"
SUPPORTED_AZS[eu-west-1]="euw1-az1 euw1-az2 euw1-az3"
SUPPORTED_AZS[eu-central-1]="euc1-az1 euc1-az2 euc1-az3"

# Check if region is supported
if [[ -z "${SUPPORTED_AZS[$REGION]}" ]]; then
    echo -e "${RED}❌ Error: Region '$REGION' does not support AgentCore VPC mode${NC}"
    echo ""
    echo "Supported regions:"
    echo "  - us-east-1, us-east-2, us-west-2"
    echo "  - ap-south-1, ap-southeast-1, ap-southeast-2, ap-northeast-1"
    echo "  - eu-west-1, eu-central-1"
    echo ""
    exit 1
fi

echo -e "  ✅ Region '$REGION' supports AgentCore VPC mode"
echo -e "  Supported AZ IDs: ${GREEN}${SUPPORTED_AZS[$REGION]}${NC}"
echo ""

# Step 3: Get AZ mappings for this account
echo -e "${BLUE}Step 3: Finding supported AZs in your account...${NC}"
echo ""

SUPPORTED_AZ_NAMES=()
while IFS=$'\t' read -r AZ_NAME AZ_ID; do
    # Check if AZ ID is supported
    if [[ " ${SUPPORTED_AZS[$REGION]} " =~ " $AZ_ID " ]]; then
        echo -e "  ✅ $AZ_NAME → $AZ_ID (SUPPORTED)"
        SUPPORTED_AZ_NAMES+=("$AZ_NAME")
    else
        echo -e "  ${YELLOW}⚠️  $AZ_NAME → $AZ_ID (not supported)${NC}"
    fi
done < <(aws ec2 describe-availability-zones --region "$REGION" \
    --query 'AvailabilityZones[*].[ZoneName,ZoneId]' \
    --output text)

echo ""

# Verify we have at least 2 supported AZs
if [ ${#SUPPORTED_AZ_NAMES[@]} -lt 2 ]; then
    echo -e "${RED}❌ Error: Found only ${#SUPPORTED_AZ_NAMES[@]} supported AZ(s)${NC}"
    echo "   AgentCore VPC requires at least 2 AZs in different supported zones"
    echo ""
    exit 1
fi

AZ1=${SUPPORTED_AZ_NAMES[0]}
AZ2=${SUPPORTED_AZ_NAMES[1]}

echo -e "${GREEN}✅ Found ${#SUPPORTED_AZ_NAMES[@]} supported AZ(s)${NC}"
echo ""
echo -e "Will use for deployment:"
echo -e "  AvailabilityZone1: ${GREEN}$AZ1${NC}"
echo -e "  AvailabilityZone2: ${GREEN}$AZ2${NC}"
echo ""

# Step 4: Confirm deployment
echo -e "${BLUE}Step 4: Deployment confirmation${NC}"
echo ""
echo -e "${YELLOW}You are about to deploy Deep Insight infrastructure:${NC}"
echo -e "  Environment:         $ENVIRONMENT"
echo -e "  Region:              $REGION"
echo -e "  AWS Account:         $AWS_ACCOUNT_ID"
echo -e "  Availability Zone 1: $AZ1"
echo -e "  Availability Zone 2: $AZ2"
echo ""
echo -e "${YELLOW}This will deploy:${NC}"
echo -e "  ✅ Phase 1: VPC, Security Groups, VPC Endpoints, ALB, IAM (~30-40 min)"
echo -e "  ✅ Phase 2: ECR, Docker Image, ECS Cluster, Task Definition (~15-20 min)"
echo ""
read -p "Continue with deployment? (yes/no): " -r
echo ""
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo -e "${YELLOW}Deployment cancelled${NC}"
    exit 0
fi

# Step 5: Deploy Phase 1 (Infrastructure)
echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}Step 5: Deploying Phase 1 (Infrastructure)${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""

cd "$SCRIPT_DIR/phase1"

./deploy.sh "$ENVIRONMENT" \
    --region "$REGION" \
    --parameter-overrides \
        AvailabilityZone1="$AZ1" \
        AvailabilityZone2="$AZ2"

PHASE1_EXIT_CODE=$?

if [ $PHASE1_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}❌ Phase 1 deployment failed${NC}"
    exit $PHASE1_EXIT_CODE
fi

echo ""
echo -e "${GREEN}✅ Phase 1 deployment completed successfully${NC}"
echo ""

# Run verification
echo -e "${BLUE}Running Phase 1 verification...${NC}"
echo ""
./verify.sh "$ENVIRONMENT" "$REGION"
echo ""

# Step 6: Deploy Phase 2 (Fargate Runtime)
echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}Step 6: Deploying Phase 2 (Fargate Runtime)${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""

cd "$SCRIPT_DIR/phase2"

./deploy.sh "$ENVIRONMENT" --region "$REGION"

PHASE2_EXIT_CODE=$?

if [ $PHASE2_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}❌ Phase 2 deployment failed${NC}"
    exit $PHASE2_EXIT_CODE
fi

echo ""
echo -e "${GREEN}✅ Phase 2 deployment completed successfully${NC}"
echo ""

# Run verification
echo -e "${BLUE}Running Phase 2 verification...${NC}"
echo ""
./verify.sh "$ENVIRONMENT" "$REGION"
echo ""

# Step 7: Summary
echo -e "${BLUE}================================================================${NC}"
echo -e "${GREEN}✅ Deployment Complete${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""
echo "Summary:"
echo "  Environment:  $ENVIRONMENT"
echo "  Region:       $REGION"
echo "  Account:      $AWS_ACCOUNT_ID"
echo "  AZ1:          $AZ1"
echo "  AZ2:          $AZ2"
echo ""

echo "Resources Deployed:"
echo ""
echo "Phase 1 Infrastructure:"
echo "  ✅ VPC and Networking (2 private + 2 public subnets)"
echo "  ✅ Security Groups (AgentCore, ALB, Fargate, VPC Endpoint)"
echo "  ✅ VPC Endpoints (Bedrock AgentCore x2, ECR, S3, Logs)"
echo "  ✅ Internal Application Load Balancer"
echo "  ✅ IAM Roles (Task Role, Execution Role)"
echo ""
echo "Phase 2 Fargate Runtime:"
echo "  ✅ ECR Repository"
echo "  ✅ Docker Image (built and pushed)"
echo "  ✅ ECS Cluster"
echo "  ✅ ECS Task Definition"
echo ""

echo "Next Steps:"
echo "  1. Setup environment variables (Phase 3):"
echo "     cd scripts/phase3 && ./setup_env.sh"
echo ""
echo "  2. Create AgentCore Runtime (Phase 3):"
echo "     cd ../../ && uv run create_agentcore_runtime_vpc.py"
echo ""
echo "  3. Test the deployment:"
echo "     uv run invoke_agentcore_runtime_vpc.py"
echo ""
echo "For detailed logs and outputs, check CloudFormation console or:"
echo "  aws cloudformation describe-stacks --region $REGION"
echo ""
