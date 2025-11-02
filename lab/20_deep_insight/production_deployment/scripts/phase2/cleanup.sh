#!/bin/bash
#
# Cleanup Phase 2 Fargate Runtime
# Safely delete CloudFormation stack and related resources
#
# Usage:
#   ./scripts/phase2/cleanup.sh [environment]           # Interactive mode
#   ./scripts/phase2/cleanup.sh [environment] --force   # Auto mode (no confirmation)
#
# Examples:
#   ./scripts/phase2/cleanup.sh prod          # Interactive cleanup
#   ./scripts/phase2/cleanup.sh prod --force  # Force delete everything
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
ENVIRONMENT="prod"
FORCE_MODE=false

for arg in "$@"; do
    case $arg in
        --force|-f)
            FORCE_MODE=true
            shift
            ;;
        dev|staging|prod)
            ENVIRONMENT=$arg
            shift
            ;;
    esac
done

PROJECT_NAME="deep-insight"
STACK_NAME="${PROJECT_NAME}-fargate-${ENVIRONMENT}"
AWS_REGION=$(aws configure get region || echo "us-east-1")
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo -e "${RED}============================================${NC}"
echo -e "${RED}Phase 2 Fargate Runtime Cleanup${NC}"
if [ "$FORCE_MODE" = true ]; then
    echo -e "${RED}⚡ FORCE MODE - No confirmation required${NC}"
fi
echo -e "${RED}============================================${NC}"
echo ""
echo "Stack Name: $STACK_NAME"
echo "Region: $AWS_REGION"
echo ""

# Warning
echo -e "${YELLOW}⚠️  WARNING: This will delete all Phase 2 resources!${NC}"
echo ""
echo "Resources to be deleted:"
echo "  - ECR Repository and all Docker images"
echo "  - ECS Cluster (after stopping all tasks)"
echo "  - Task Definitions (deregistered)"
echo "  - CloudWatch Log Group"
echo "  - CloudFormation stack"
echo ""

# Confirmation (skip if --force)
if [ "$FORCE_MODE" = false ]; then
    read -p "Are you sure? (type 'yes' to confirm): " CONFIRM

    if [ "$CONFIRM" != "yes" ]; then
        echo "Cleanup cancelled."
        exit 0
    fi
else
    echo -e "${YELLOW}⚡ Force mode: Skipping confirmation${NC}"
    sleep 2  # Give user 2 seconds to cancel with Ctrl+C
fi

echo ""
echo -e "${YELLOW}Starting cleanup...${NC}"

# ============================================
# Step 1: Load .env to get resource names
# ============================================
echo ""
echo -e "${BLUE}Step 1: Loading environment variables...${NC}"

ENV_FILE="$(dirname "$0")/../../.env"
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
    echo -e "${GREEN}✓ Loaded .env file${NC}"
else
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo "Will attempt cleanup using default naming conventions"
fi

# Set resource names (use from .env or construct from defaults)
ECR_REPOSITORY_NAME="${ECR_REPOSITORY_NAME:-${PROJECT_NAME}-fargate-runtime-${ENVIRONMENT}}"
ECS_CLUSTER_NAME="${ECS_CLUSTER_NAME:-${PROJECT_NAME}-cluster-${ENVIRONMENT}}"
TASK_DEFINITION_FAMILY="${PROJECT_NAME}-fargate-task-${ENVIRONMENT}"
LOG_GROUP_NAME="${LOG_GROUP_NAME:-/ecs/${PROJECT_NAME}-fargate-${ENVIRONMENT}}"

echo "ECR Repository: $ECR_REPOSITORY_NAME"
echo "ECS Cluster: $ECS_CLUSTER_NAME"
echo "Task Definition: $TASK_DEFINITION_FAMILY"
echo "Log Group: $LOG_GROUP_NAME"

# ============================================
# Step 2: Stop all running ECS tasks
# ============================================
echo ""
echo -e "${BLUE}Step 2: Stopping all running ECS tasks...${NC}"

CLUSTER_EXISTS=$(aws ecs describe-clusters \
    --clusters "$ECS_CLUSTER_NAME" \
    --region "$AWS_REGION" \
    --query 'clusters[0].clusterName' \
    --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$CLUSTER_EXISTS" != "NOT_FOUND" ] && [ "$CLUSTER_EXISTS" != "None" ]; then
    RUNNING_TASKS=$(aws ecs list-tasks \
        --cluster "$ECS_CLUSTER_NAME" \
        --region "$AWS_REGION" \
        --desired-status RUNNING \
        --query 'taskArns[*]' \
        --output text)

    if [ -n "$RUNNING_TASKS" ]; then
        echo "Found running tasks. Stopping..."
        for TASK_ARN in $RUNNING_TASKS; do
            echo "  Stopping: $TASK_ARN"
            aws ecs stop-task \
                --cluster "$ECS_CLUSTER_NAME" \
                --task "$TASK_ARN" \
                --region "$AWS_REGION" \
                --output text > /dev/null
        done
        echo "Waiting for tasks to stop (30 seconds)..."
        sleep 30
        echo -e "${GREEN}✓ All tasks stopped${NC}"
    else
        echo "No running tasks found"
    fi
else
    echo "ECS Cluster not found (may have been deleted already)"
fi

# ============================================
# Step 3: Delete ECR images and repository
# ============================================
echo ""
echo -e "${BLUE}Step 3: Deleting ECR repository and images...${NC}"

REPO_EXISTS=$(aws ecr describe-repositories \
    --repository-names "$ECR_REPOSITORY_NAME" \
    --region "$AWS_REGION" \
    --query 'repositories[0].repositoryName' \
    --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$REPO_EXISTS" != "NOT_FOUND" ]; then
    # Count images
    IMAGE_COUNT=$(aws ecr list-images \
        --repository-name "$ECR_REPOSITORY_NAME" \
        --region "$AWS_REGION" \
        --query 'length(imageIds)' \
        --output text 2>/dev/null || echo "0")

    echo "Found ECR repository with $IMAGE_COUNT images"

    # Delete repository (force delete will delete all images)
    aws ecr delete-repository \
        --repository-name "$ECR_REPOSITORY_NAME" \
        --region "$AWS_REGION" \
        --force > /dev/null

    echo -e "${GREEN}✓ ECR repository and $IMAGE_COUNT images deleted${NC}"
else
    echo "ECR repository not found (may have been deleted already)"
fi

# ============================================
# Step 4: Check if stack exists
# ============================================
echo ""
echo -e "${BLUE}Step 4: Checking CloudFormation stack status...${NC}"

STACK_STATUS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].StackStatus' \
    --output text 2>/dev/null || echo "STACK_NOT_FOUND")

if [ "$STACK_STATUS" == "STACK_NOT_FOUND" ]; then
    echo -e "${YELLOW}Stack not found: $STACK_NAME${NC}"
    echo "Skipping stack deletion."
else
    echo "Current status: $STACK_STATUS"

    # ============================================
    # Step 5: Delete CloudFormation Stack
    # ============================================
    echo ""
    echo -e "${BLUE}Step 5: Deleting CloudFormation stack...${NC}"
    echo "This will take 2-5 minutes."
    echo ""

    aws cloudformation delete-stack \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION"

    echo "Delete initiated. Waiting for completion..."

    # Monitor deletion with timeout
    START_TIME=$(date +%s)
    TIMEOUT_SECONDS=$((10 * 60))  # 10 minutes timeout

    while true; do
        CURRENT_TIME=$(date +%s)
        ELAPSED=$((CURRENT_TIME - START_TIME))

        if [ $ELAPSED -gt $TIMEOUT_SECONDS ]; then
            echo ""
            echo -e "${RED}⏰ Timeout reached (10 minutes)${NC}"
            echo ""
            echo "Stack deletion is still in progress."
            echo "Check status manually:"
            echo "  aws cloudformation describe-stacks --stack-name $STACK_NAME"
            echo ""
            exit 1
        fi

        CURRENT_STATUS=$(aws cloudformation describe-stacks \
            --stack-name "$STACK_NAME" \
            --region "$AWS_REGION" \
            --query 'Stacks[0].StackStatus' \
            --output text 2>/dev/null || echo "DELETED")

        if [ "$CURRENT_STATUS" == "DELETED" ]; then
            echo -e "${GREEN}✓ Stack deleted successfully${NC}"
            break
        elif [[ "$CURRENT_STATUS" == *"FAILED"* ]]; then
            echo ""
            echo -e "${RED}✗ Stack deletion failed: $CURRENT_STATUS${NC}"
            echo ""
            echo "Fetching failed events..."
            aws cloudformation describe-stack-events \
                --stack-name "$STACK_NAME" \
                --region "$AWS_REGION" \
                --query 'StackEvents[?ResourceStatus==`DELETE_FAILED`] | [0:5].[Timestamp,LogicalResourceId,ResourceStatusReason]' \
                --output table
            echo ""
            echo "Manual cleanup may be required."
            echo "Check CloudFormation console for details."
            exit 1
        else
            echo -ne "\r  Status: $CURRENT_STATUS (${ELAPSED}s elapsed)"
            sleep 10
        fi
    done
fi

# ============================================
# Step 6: Clean up .env file Phase 2 section
# ============================================
echo ""
echo -e "${BLUE}Step 6: Cleaning up .env file...${NC}"

if [ -f "$ENV_FILE" ]; then
    if [ "$FORCE_MODE" = false ]; then
        read -p "Remove Phase 2 variables from .env file? (y/N): " DELETE_ENV_SECTION
        if [ "$DELETE_ENV_SECTION" == "y" ] || [ "$DELETE_ENV_SECTION" == "Y" ]; then
            # Remove Phase 2 section from .env (lines between "# Phase 2" and next "# Phase" or EOF)
            sed -i '/^# Phase 2 Outputs/,/^# Phase [3-9]/d' "$ENV_FILE" 2>/dev/null || true
            echo -e "${GREEN}✓ Phase 2 section removed from .env${NC}"
        else
            echo -e "${YELLOW}.env file kept unchanged${NC}"
        fi
    else
        echo -e "${YELLOW}⚡ Force mode: Auto-removing Phase 2 section from .env${NC}"
        sed -i '/^# Phase 2 Outputs/,/^# Phase [3-9]/d' "$ENV_FILE" 2>/dev/null || true
        echo -e "${GREEN}✓ Phase 2 section removed from .env${NC}"
    fi
else
    echo ".env file not found"
fi

# ============================================
# Step 7: Deregister Task Definitions (optional)
# ============================================
echo ""
echo -e "${BLUE}Step 7: Deregistering task definitions...${NC}"

TASK_DEFINITIONS=$(aws ecs list-task-definitions \
    --family-prefix "$TASK_DEFINITION_FAMILY" \
    --region "$AWS_REGION" \
    --query 'taskDefinitionArns[*]' \
    --output text 2>/dev/null || echo "")

if [ -n "$TASK_DEFINITIONS" ]; then
    TD_COUNT=$(echo "$TASK_DEFINITIONS" | wc -w)
    echo "Found $TD_COUNT task definition(s) to deregister"

    if [ "$FORCE_MODE" = false ]; then
        read -p "Deregister all task definitions? (y/N): " DEREGISTER_TDS
        if [ "$DEREGISTER_TDS" == "y" ] || [ "$DEREGISTER_TDS" == "Y" ]; then
            for TD_ARN in $TASK_DEFINITIONS; do
                echo "  Deregistering: $TD_ARN"
                aws ecs deregister-task-definition \
                    --task-definition "$TD_ARN" \
                    --region "$AWS_REGION" \
                    --output text > /dev/null
            done
            echo -e "${GREEN}✓ $TD_COUNT task definition(s) deregistered${NC}"
        else
            echo -e "${YELLOW}Task definitions kept (INACTIVE)${NC}"
        fi
    else
        echo -e "${YELLOW}⚡ Force mode: Auto-deregistering task definitions${NC}"
        for TD_ARN in $TASK_DEFINITIONS; do
            echo "  Deregistering: $TD_ARN"
            aws ecs deregister-task-definition \
                --task-definition "$TD_ARN" \
                --region "$AWS_REGION" \
                --output text > /dev/null
        done
        echo -e "${GREEN}✓ $TD_COUNT task definition(s) deregistered${NC}"
    fi
else
    echo "No task definitions found"
fi

# ============================================
# Summary
# ============================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}✓ Phase 2 Cleanup Complete!${NC}"
if [ "$FORCE_MODE" = true ]; then
    echo -e "${GREEN}⚡ Force Mode - All resources deleted${NC}"
fi
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Cleaned up:"
echo "  ✓ CloudFormation stack: $STACK_NAME"
echo "  ✓ ECR repository and Docker images"
echo "  ✓ ECS Cluster (tasks stopped)"
if [ "$FORCE_MODE" = true ]; then
    echo "  ✓ Task definitions deregistered (auto)"
    echo "  ✓ .env Phase 2 section removed (auto)"
else
    echo "  ✓ Task definitions (if you selected 'y')"
    echo "  ✓ .env Phase 2 section (if you selected 'y')"
fi
echo ""
echo "Note: Phase 1 infrastructure (VPC, ALB, etc.) remains intact"
echo ""
echo "You can now redeploy Phase 2:"
echo "  ./scripts/phase2/deploy.sh $ENVIRONMENT"
echo ""
