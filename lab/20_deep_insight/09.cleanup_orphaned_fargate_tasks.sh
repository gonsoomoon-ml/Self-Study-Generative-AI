#!/bin/bash
#
# Cleanup Orphaned Fargate Tasks and ALB Targets
#
# Purpose: Force cleanup of all running ECS tasks and ALB targets in the Deep Insight cluster
#          Independent of Python runtime - can be run anytime
#
# Use Cases:
#   - Container shutdown hook (ECS task stop)
#   - Periodic cleanup (cron job)
#   - Manual cleanup (ops team)
#   - Emergency cleanup (orphaned resources)
#
# Usage:
#   ./09.cleanup_orphaned_fargate_tasks.sh [cluster-name] [region]
#
# Examples:
#   ./09.cleanup_orphaned_fargate_tasks.sh                           # Use defaults from .env
#   ./09.cleanup_orphaned_fargate_tasks.sh my-cluster us-west-2     # Specify cluster and region
#

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory (absolute path)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load environment variables from .env (if exists)
ENV_FILE="${SCRIPT_DIR}/.env"
if [ -f "$ENV_FILE" ]; then
    echo -e "${BLUE}📂 Loading configuration from .env${NC}"
    set -a  # Auto-export all variables
    source "$ENV_FILE"
    set +a
    echo -e "${GREEN}✅ Loaded configuration${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  .env file not found: $ENV_FILE${NC}"
    echo -e "${YELLOW}   Using command-line arguments or defaults${NC}"
    echo ""
fi

# Configuration (can be overridden by command line arguments or environment)
CLUSTER_NAME="${1:-${ECS_CLUSTER_NAME:-my-fargate-cluster}}"
AWS_REGION="${2:-${AWS_REGION:-us-east-1}}"
ALB_TARGET_GROUP_ARN="${ALB_TARGET_GROUP_ARN}"  # From .env
AWS_CLI_TIMEOUT=30

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Fargate Task & ALB Cleanup Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Cluster: $CLUSTER_NAME"
echo "Region:  $AWS_REGION"
if [ -n "$ALB_TARGET_GROUP_ARN" ]; then
    echo -e "ALB TG:  ${GREEN}${ALB_TARGET_GROUP_ARN}${NC}"
    echo -e "         ${GREEN}✅ ALB deregistration enabled${NC}"
else
    echo -e "ALB TG:  ${YELLOW}Not configured${NC}"
    echo -e "         ${YELLOW}⚠️  ALB deregistration disabled${NC}"
fi
echo ""

# Function to list all running tasks
list_tasks() {
    echo -e "${BLUE}🔍 Checking for running tasks...${NC}"

    TASK_ARNS=$(aws ecs list-tasks \
        --cluster "$CLUSTER_NAME" \
        --region "$AWS_REGION" \
        --query 'taskArns[*]' \
        --output text \
        2>/dev/null || echo "")

    if [ -z "$TASK_ARNS" ]; then
        echo -e "${GREEN}✅ No running tasks found${NC}"
        return 1
    fi

    # Convert to array
    TASK_IDS=()
    for arn in $TASK_ARNS; do
        if [ -n "$arn" ]; then
            task_id=$(echo "$arn" | awk -F'/' '{print $NF}')
            TASK_IDS+=("$task_id")
        fi
    done

    if [ ${#TASK_IDS[@]} -eq 0 ]; then
        echo -e "${GREEN}✅ No running tasks found${NC}"
        return 1
    fi

    echo -e "${YELLOW}Found ${#TASK_IDS[@]} running task(s)${NC}"
    return 0
}

# Function to get task details
get_task_details() {
    local task_id=$1

    # Get task details
    TASK_INFO=$(aws ecs describe-tasks \
        --cluster "$CLUSTER_NAME" \
        --region "$AWS_REGION" \
        --tasks "$task_id" \
        --query 'tasks[0].[taskArn,lastStatus,createdAt,taskDefinitionArn]' \
        --output text 2>/dev/null)

    if [ -n "$TASK_INFO" ]; then
        local status=$(echo "$TASK_INFO" | awk '{print $2}')
        local created=$(echo "$TASK_INFO" | awk '{print $3}')
        local task_def=$(echo "$TASK_INFO" | awk -F'/' '{print $NF}')

        echo "    Status: $status, Created: $created"
        echo "    Task Definition: $task_def"
    fi
}

# Function to get container IP from task
get_task_ip() {
    local task_id=$1

    # Get task details including network attachments
    TASK_DETAILS=$(aws ecs describe-tasks \
        --cluster "$CLUSTER_NAME" \
        --region "$AWS_REGION" \
        --tasks "$task_id" \
        --query 'tasks[0].attachments[?type==`ElasticNetworkInterface`].details' \
        --output json 2>/dev/null)

    if [ -z "$TASK_DETAILS" ] || [ "$TASK_DETAILS" = "null" ] || [ "$TASK_DETAILS" = "[]" ]; then
        echo ""
        return 1
    fi

    # Extract private IP using jq (more reliable than awk for JSON)
    if command -v jq &> /dev/null; then
        PRIVATE_IP=$(echo "$TASK_DETAILS" | jq -r '.[0][] | select(.name=="privateIPv4Address") | .value' 2>/dev/null)
    else
        # Fallback: use grep if jq not available
        PRIVATE_IP=$(echo "$TASK_DETAILS" | grep -oP '"privateIPv4Address"[^"]*"value"\s*:\s*"\K[^"]+' 2>/dev/null | head -1)
    fi

    echo "$PRIVATE_IP"
}

# Function to deregister target from ALB
deregister_from_alb() {
    local container_ip=$1

    # Skip if no ALB Target Group ARN configured
    if [ -z "$ALB_TARGET_GROUP_ARN" ]; then
        echo -e "${YELLOW}    ⚠️  ALB_TARGET_GROUP_ARN not set, skipping ALB deregistration${NC}"
        return 0
    fi

    # Skip if no IP provided
    if [ -z "$container_ip" ]; then
        echo -e "${YELLOW}    ⚠️  No container IP found, skipping ALB deregistration${NC}"
        return 0
    fi

    echo "    🔗 Deregistering from ALB: $container_ip:8080"

    DEREGISTER_RESULT=$(aws elbv2 deregister-targets \
        --target-group-arn "$ALB_TARGET_GROUP_ARN" \
        --region "$AWS_REGION" \
        --targets Id="$container_ip",Port=8080 \
        2>&1)

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}    ✅ Deregistered from ALB${NC}"
        return 0
    else
        # Check if target was not registered (not an error)
        if echo "$DEREGISTER_RESULT" | grep -q "TargetNotFound\|InvalidTarget"; then
            echo -e "${YELLOW}    ℹ️  Target not registered in ALB (already removed)${NC}"
            return 0
        else
            echo -e "${YELLOW}    ⚠️  Failed to deregister from ALB: $DEREGISTER_RESULT${NC}"
            echo -e "${YELLOW}    ⚠️  Continuing with task stop anyway${NC}"
            return 1
        fi
    fi
}

# Function to stop a single task
stop_task() {
    local task_id=$1

    echo -e "${BLUE}  🛑 Stopping task: ${task_id}${NC}"

    # Get details before stopping
    get_task_details "$task_id"

    # Get container IP for ALB deregistration
    CONTAINER_IP=$(get_task_ip "$task_id")
    if [ -n "$CONTAINER_IP" ]; then
        echo "    📍 Container IP: $CONTAINER_IP"
        # Deregister from ALB first (before stopping task)
        deregister_from_alb "$CONTAINER_IP"
    else
        echo -e "${YELLOW}    ⚠️  Could not retrieve container IP${NC}"
    fi

    # Stop the task
    STOP_RESULT=$(aws ecs stop-task \
        --cluster "$CLUSTER_NAME" \
        --region "$AWS_REGION" \
        --task "$task_id" \
        --reason "Cleanup: Orphaned task cleanup script" \
        2>&1)

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}    ✅ Task stopped successfully${NC}"
        return 0
    else
        echo -e "${RED}    ❌ Failed to stop task: $STOP_RESULT${NC}"
        return 1
    fi
}

# Function to stop all tasks
stop_all_tasks() {
    echo ""
    echo -e "${BLUE}🛑 Stopping all running tasks...${NC}"
    echo ""

    local stopped_count=0
    local failed_count=0

    for task_id in "${TASK_IDS[@]}"; do
        if stop_task "$task_id"; then
            ((stopped_count++))
        else
            ((failed_count++))
        fi
        echo ""
    done

    echo -e "${BLUE}========================================${NC}"
    echo -e "${GREEN}✅ Stopped: $stopped_count${NC}"
    if [ $failed_count -gt 0 ]; then
        echo -e "${RED}❌ Failed:  $failed_count${NC}"
    fi
    echo -e "${BLUE}========================================${NC}"

    return $failed_count
}

# Function to verify cleanup
verify_cleanup() {
    echo ""
    echo -e "${BLUE}🔍 Verifying cleanup...${NC}"

    sleep 5  # Wait for tasks to stop

    REMAINING_TASKS=$(aws ecs list-tasks \
        --cluster "$CLUSTER_NAME" \
        --region "$AWS_REGION" \
        --query 'taskArns[*]' \
        --output text \
        2>/dev/null || echo "")

    if [ -z "$REMAINING_TASKS" ]; then
        echo -e "${GREEN}✅ All tasks cleaned up successfully${NC}"
        return 0
    else
        local count=$(echo "$REMAINING_TASKS" | wc -w)
        echo -e "${YELLOW}⚠️  $count task(s) still running (may be stopping)${NC}"
        return 1
    fi
}

# Function to get cluster statistics
show_cluster_stats() {
    echo ""
    echo -e "${BLUE}📊 Cluster Statistics:${NC}"

    STATS=$(aws ecs describe-clusters \
        --clusters "$CLUSTER_NAME" \
        --region "$AWS_REGION" \
        --query 'clusters[0].[runningTasksCount,pendingTasksCount,activeServicesCount]' \
        --output text 2>/dev/null)

    if [ -n "$STATS" ]; then
        running=$(echo "$STATS" | awk '{print $1}')
        pending=$(echo "$STATS" | awk '{print $2}')
        services=$(echo "$STATS" | awk '{print $3}')

        echo "  Running tasks: $running"
        echo "  Pending tasks: $pending"
        echo "  Active services: $services"
    else
        echo -e "${RED}  ❌ Could not retrieve cluster statistics${NC}"
    fi
}

# Main execution
main() {
    # Check prerequisites
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}❌ Error: AWS CLI not found${NC}"
        echo "Please install AWS CLI: https://aws.amazon.com/cli/"
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity --region "$AWS_REGION" &> /dev/null; then
        echo -e "${RED}❌ Error: AWS credentials not configured or invalid${NC}"
        echo "Please run: aws configure"
        exit 1
    fi

    # Show initial cluster stats
    show_cluster_stats

    echo ""

    # List tasks
    if ! list_tasks; then
        # No tasks to clean up
        exit 0
    fi

    echo ""

    # Ask for confirmation (can be skipped with --force flag)
    if [ "$3" != "--force" ]; then
        echo -e "${YELLOW}⚠️  WARNING: This will perform the following actions:${NC}"
        echo -e "${YELLOW}   • Deregister all targets from ALB (if configured)${NC}"
        echo -e "${YELLOW}   • Stop all running tasks in the cluster${NC}"
        echo ""
        read -p "Continue? (yes/no): " -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            echo -e "${YELLOW}Cleanup cancelled${NC}"
            exit 0
        fi
    fi

    # Stop all tasks
    stop_all_tasks
    exit_code=$?

    # Verify cleanup
    verify_cleanup

    # Show final cluster stats
    show_cluster_stats

    echo ""
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ Cleanup completed successfully${NC}"
    else
        echo -e "${YELLOW}⚠️  Cleanup completed with some failures${NC}"
    fi

    exit $exit_code
}

# Run main function
main "$@"
