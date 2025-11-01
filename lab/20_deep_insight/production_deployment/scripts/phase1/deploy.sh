#!/bin/bash
#
# Phase 1: Infrastructure Deployment
# Deploy VPC, Subnets, Security Groups, VPC Endpoints, ALB, IAM Roles
#
# Usage: ./scripts/phase1/deploy.sh [environment]
#   environment: dev, staging, prod (default: prod)
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENVIRONMENT="${1:-prod}"

STACK_NAME="bedrock-manus-infrastructure-${ENVIRONMENT}"
TEMPLATE_FILE="$PROJECT_ROOT/cloudformation/phase1-infrastructure.yaml"
PARAMS_FILE="$PROJECT_ROOT/cloudformation/parameters/phase1-${ENVIRONMENT}-params.json"
ENV_FILE="$PROJECT_ROOT/.env"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}Phase 1: Infrastructure Deployment${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo "Environment: $ENVIRONMENT"
echo "Stack Name: $STACK_NAME"
echo "Region: ${AWS_REGION:-us-east-1}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI not found. Please install AWS CLI.${NC}"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS credentials not configured. Run 'aws configure'.${NC}"
    exit 1
fi

# Get AWS Account ID and Region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "us-east-1")

echo -e "${GREEN}✓${NC} AWS CLI configured"
echo "  Account ID: $AWS_ACCOUNT_ID"
echo "  Region: $AWS_REGION"

# Check template file
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo -e "${RED}Error: Template file not found: $TEMPLATE_FILE${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} CloudFormation template found"

# Check parameter file
if [ ! -f "$PARAMS_FILE" ]; then
    echo -e "${RED}Error: Parameter file not found: $PARAMS_FILE${NC}"
    echo "Please create: $PARAMS_FILE"
    exit 1
fi
echo -e "${GREEN}✓${NC} Parameter file found"

# Create .env file if doesn't exist
if [ ! -f "$ENV_FILE" ]; then
    echo "Creating .env file..."
    cat > "$ENV_FILE" <<EOF
# AWS Configuration
AWS_REGION=$AWS_REGION
AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID

# Project Configuration
PROJECT_NAME=bedrock-manus
ENVIRONMENT=$ENVIRONMENT

# Phase 1 Outputs (will be populated after deployment)
VPC_ID=
PRIVATE_SUBNET_ID=
PUBLIC_SUBNET_ID=
SG_AGENTCORE_ID=
SG_ALB_ID=
SG_FARGATE_ID=
SG_VPCE_ID=
ALB_ARN=
ALB_DNS=
TARGET_GROUP_ARN=
TASK_EXECUTION_ROLE_ARN=
TASK_ROLE_ARN=
EOF
    echo -e "${GREEN}✓${NC} .env file created"
else
    echo -e "${GREEN}✓${NC} .env file exists"
fi

# Update Account ID in parameter file
echo ""
echo -e "${YELLOW}Updating Account ID in parameter file...${NC}"

# Create temporary parameter file with Account ID replaced
TEMP_PARAMS_FILE="$PROJECT_ROOT/cloudformation/parameters/.phase1-${ENVIRONMENT}-params-temp.json"
sed "s/ACCOUNT_ID/${AWS_ACCOUNT_ID}/g" "$PARAMS_FILE" > "$TEMP_PARAMS_FILE"

echo -e "${GREEN}✓${NC} Parameter file updated with Account ID: $AWS_ACCOUNT_ID"

# Validate CloudFormation template
echo ""
echo -e "${YELLOW}Validating CloudFormation template...${NC}"

if aws cloudformation validate-template \
    --template-body file://"$TEMPLATE_FILE" \
    --region "$AWS_REGION" \
    > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Template validation passed"
else
    echo -e "${RED}Error: Template validation failed${NC}"
    aws cloudformation validate-template \
        --template-body file://"$TEMPLATE_FILE" \
        --region "$AWS_REGION"
    rm -f "$TEMP_PARAMS_FILE"
    exit 1
fi

# Check if stack already exists
echo ""
echo -e "${YELLOW}Checking existing stack...${NC}"

STACK_STATUS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].StackStatus' \
    --output text 2>/dev/null || echo "DOES_NOT_EXIST")

if [ "$STACK_STATUS" != "DOES_NOT_EXIST" ]; then
    echo -e "${YELLOW}Warning: Stack already exists with status: $STACK_STATUS${NC}"
    echo ""
    read -p "Do you want to update the existing stack? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Deployment cancelled."
        rm -f "$TEMP_PARAMS_FILE"
        exit 0
    fi
    DEPLOY_ACTION="update"
else
    echo "Stack does not exist. Will create new stack."
    DEPLOY_ACTION="create"
fi

# Deploy CloudFormation stack
echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}Deploying CloudFormation Stack...${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo "This will create the following resources:"
echo "  - VPC (10.0.0.0/16)"
echo "  - Subnets (Private, Public)"
echo "  - Internet Gateway, NAT Gateway"
echo "  - Security Groups (4)"
echo "  - VPC Endpoints (6)"
echo "  - Internal ALB"
echo "  - IAM Roles (2)"
echo ""
echo -e "${YELLOW}Expected deployment time: 30-40 minutes${NC}"
echo ""

# Confirm deployment
read -p "Continue with deployment? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Deployment cancelled."
    rm -f "$TEMP_PARAMS_FILE"
    exit 0
fi

# Deploy stack
echo ""
echo -e "${YELLOW}Starting stack deployment...${NC}"

aws cloudformation deploy \
    --template-file "$TEMPLATE_FILE" \
    --stack-name "$STACK_NAME" \
    --parameter-overrides file://"$TEMP_PARAMS_FILE" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$AWS_REGION" \
    --tags \
        Environment="$ENVIRONMENT" \
        Project=bedrock-manus \
        ManagedBy=CloudFormation \
    --no-fail-on-empty-changeset

# Clean up temp file
rm -f "$TEMP_PARAMS_FILE"

# Check deployment status
FINAL_STATUS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].StackStatus' \
    --output text 2>/dev/null)

if [[ "$FINAL_STATUS" == "CREATE_COMPLETE" || "$FINAL_STATUS" == "UPDATE_COMPLETE" ]]; then
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}✓ Stack deployment successful!${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}============================================${NC}"
    echo -e "${RED}✗ Stack deployment failed${NC}"
    echo -e "${RED}============================================${NC}"
    echo ""
    echo "Stack Status: $FINAL_STATUS"
    echo ""
    echo "To view error details, run:"
    echo "  aws cloudformation describe-stack-events --stack-name $STACK_NAME --region $AWS_REGION"
    exit 1
fi

# Extract Outputs and save to .env
echo -e "${YELLOW}Extracting stack outputs...${NC}"

# Get all outputs
VPC_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`VpcId`].OutputValue' \
    --output text)

PRIVATE_SUBNET_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`PrivateSubnetId`].OutputValue' \
    --output text)

PUBLIC_SUBNET_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`PublicSubnetId`].OutputValue' \
    --output text)

AVAILABILITY_ZONE=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`AvailabilityZone`].OutputValue' \
    --output text)

SG_AGENTCORE_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreSecurityGroupId`].OutputValue' \
    --output text)

SG_ALB_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`ALBSecurityGroupId`].OutputValue' \
    --output text)

SG_FARGATE_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`FargateSecurityGroupId`].OutputValue' \
    --output text)

SG_VPCE_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`VPCEndpointSecurityGroupId`].OutputValue' \
    --output text)

ALB_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApplicationLoadBalancerArn`].OutputValue' \
    --output text)

ALB_DNS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApplicationLoadBalancerDNS`].OutputValue' \
    --output text)

TARGET_GROUP_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`TargetGroupArn`].OutputValue' \
    --output text)

TASK_EXECUTION_ROLE_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`TaskExecutionRoleArn`].OutputValue' \
    --output text)

TASK_ROLE_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`TaskRoleArn`].OutputValue' \
    --output text)

# Update .env file
echo ""
echo -e "${YELLOW}Updating .env file with stack outputs...${NC}"

# Update values in .env file
sed -i "s|^VPC_ID=.*|VPC_ID=$VPC_ID|" "$ENV_FILE"
sed -i "s|^PRIVATE_SUBNET_ID=.*|PRIVATE_SUBNET_ID=$PRIVATE_SUBNET_ID|" "$ENV_FILE"
sed -i "s|^PUBLIC_SUBNET_ID=.*|PUBLIC_SUBNET_ID=$PUBLIC_SUBNET_ID|" "$ENV_FILE"
sed -i "s|^SG_AGENTCORE_ID=.*|SG_AGENTCORE_ID=$SG_AGENTCORE_ID|" "$ENV_FILE"
sed -i "s|^SG_ALB_ID=.*|SG_ALB_ID=$SG_ALB_ID|" "$ENV_FILE"
sed -i "s|^SG_FARGATE_ID=.*|SG_FARGATE_ID=$SG_FARGATE_ID|" "$ENV_FILE"
sed -i "s|^SG_VPCE_ID=.*|SG_VPCE_ID=$SG_VPCE_ID|" "$ENV_FILE"
sed -i "s|^ALB_ARN=.*|ALB_ARN=$ALB_ARN|" "$ENV_FILE"
sed -i "s|^ALB_DNS=.*|ALB_DNS=$ALB_DNS|" "$ENV_FILE"
sed -i "s|^TARGET_GROUP_ARN=.*|TARGET_GROUP_ARN=$TARGET_GROUP_ARN|" "$ENV_FILE"
sed -i "s|^TASK_EXECUTION_ROLE_ARN=.*|TASK_EXECUTION_ROLE_ARN=$TASK_EXECUTION_ROLE_ARN|" "$ENV_FILE"
sed -i "s|^TASK_ROLE_ARN=.*|TASK_ROLE_ARN=$TASK_ROLE_ARN|" "$ENV_FILE"

# Add Availability Zone if not exists
if ! grep -q "^AVAILABILITY_ZONE=" "$ENV_FILE"; then
    echo "AVAILABILITY_ZONE=$AVAILABILITY_ZONE" >> "$ENV_FILE"
else
    sed -i "s|^AVAILABILITY_ZONE=.*|AVAILABILITY_ZONE=$AVAILABILITY_ZONE|" "$ENV_FILE"
fi

echo -e "${GREEN}✓${NC} .env file updated"

# Summary
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Phase 1 Deployment Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Created Resources:"
echo ""
echo -e "${BLUE}Network:${NC}"
echo "  VPC ID:            $VPC_ID"
echo "  Private Subnet:    $PRIVATE_SUBNET_ID ($AVAILABILITY_ZONE)"
echo "  Public Subnet:     $PUBLIC_SUBNET_ID ($AVAILABILITY_ZONE)"
echo ""
echo -e "${BLUE}Security Groups:${NC}"
echo "  AgentCore SG:      $SG_AGENTCORE_ID"
echo "  ALB SG:            $SG_ALB_ID"
echo "  Fargate SG:        $SG_FARGATE_ID"
echo "  VPC Endpoint SG:   $SG_VPCE_ID"
echo ""
echo -e "${BLUE}Load Balancer:${NC}"
echo "  ALB ARN:           ${ALB_ARN:0:50}..."
echo "  ALB DNS:           $ALB_DNS"
echo "  Target Group:      ${TARGET_GROUP_ARN:0:50}..."
echo ""
echo -e "${BLUE}IAM Roles:${NC}"
echo "  Task Execution:    ${TASK_EXECUTION_ROLE_ARN:0:50}..."
echo "  Task Role:         ${TASK_ROLE_ARN:0:50}..."
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Run verification: ./scripts/phase1/verify.sh"
echo "  2. Proceed to Phase 2: ./scripts/phase2/1-deploy-infrastructure.sh"
echo ""
echo -e "${GREEN}============================================${NC}"
