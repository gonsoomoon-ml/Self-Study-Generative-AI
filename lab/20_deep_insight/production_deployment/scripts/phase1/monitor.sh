#!/bin/bash
#
# Monitor CloudFormation Stack Progress
# Usage: ./scripts/phase1/monitor.sh [environment] [timeout_minutes]
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ENVIRONMENT="${1:-prod}"
TIMEOUT_MINUTES="${2:-60}"
STACK_NAME="deep-insight-infrastructure-${ENVIRONMENT}"
AWS_REGION=$(aws configure get region || echo "us-east-1")

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}CloudFormation Stack Monitor${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo "Stack Name: $STACK_NAME"
echo "Region: $AWS_REGION"
echo "Timeout: ${TIMEOUT_MINUTES} minutes"
echo ""

START_TIME=$(date +%s)
TIMEOUT_SECONDS=$((TIMEOUT_MINUTES * 60))

echo -e "${YELLOW}Monitoring stack progress...${NC}"
echo "Press Ctrl+C to stop monitoring (stack will continue)"
echo ""

while true; do
    # Get current time
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    ELAPSED_MIN=$((ELAPSED / 60))

    # Check timeout
    if [ $ELAPSED -gt $TIMEOUT_SECONDS ]; then
        echo ""
        echo -e "${RED}⏰ Timeout reached (${TIMEOUT_MINUTES} minutes)${NC}"
        echo ""
        echo "Stack is still running. Options:"
        echo "  1. Wait more: ./scripts/phase1/monitor.sh $ENVIRONMENT <new_timeout>"
        echo "  2. Cancel deployment: aws cloudformation cancel-update-stack --stack-name $STACK_NAME"
        echo "  3. Delete stack: aws cloudformation delete-stack --stack-name $STACK_NAME"
        echo ""
        exit 1
    fi

    # Get stack status
    STACK_STATUS=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].StackStatus' \
        --output text 2>/dev/null || echo "STACK_NOT_FOUND")

    if [ "$STACK_STATUS" == "STACK_NOT_FOUND" ]; then
        echo -e "${RED}✗ Stack not found: $STACK_NAME${NC}"
        exit 1
    fi

    # Get nested stacks status
    NESTED_STACKS=$(aws cloudformation list-stack-resources \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION" \
        --query 'StackResourceSummaries[?ResourceType==`AWS::CloudFormation::Stack`].[LogicalResourceId,ResourceStatus]' \
        --output text 2>/dev/null || echo "")

    # Clear screen and display status
    clear
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}CloudFormation Stack Monitor${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo ""
    echo "Stack: $STACK_NAME"
    echo "Status: $STACK_STATUS"
    echo "Elapsed: ${ELAPSED_MIN} minutes / ${TIMEOUT_MINUTES} minutes"
    echo ""

    # Display nested stacks
    if [ ! -z "$NESTED_STACKS" ]; then
        echo -e "${YELLOW}Nested Stacks:${NC}"
        echo "$NESTED_STACKS" | while IFS=$'\t' read -r name status; do
            case $status in
                *COMPLETE*)
                    echo -e "  ${GREEN}✓${NC} $name: $status"
                    ;;
                *FAILED*)
                    echo -e "  ${RED}✗${NC} $name: $status"
                    ;;
                *IN_PROGRESS*)
                    echo -e "  ${YELLOW}⧗${NC} $name: $status"
                    ;;
                *)
                    echo -e "    $name: $status"
                    ;;
            esac
        done
        echo ""
    fi

    # Check if complete or failed
    case $STACK_STATUS in
        CREATE_COMPLETE|UPDATE_COMPLETE)
            echo -e "${GREEN}============================================${NC}"
            echo -e "${GREEN}✓ Stack deployment successful!${NC}"
            echo -e "${GREEN}============================================${NC}"
            echo ""
            echo "Total time: ${ELAPSED_MIN} minutes"
            exit 0
            ;;
        *FAILED*|ROLLBACK_COMPLETE|UPDATE_ROLLBACK_COMPLETE)
            echo -e "${RED}============================================${NC}"
            echo -e "${RED}✗ Stack deployment failed${NC}"
            echo -e "${RED}============================================${NC}"
            echo ""
            echo "Fetching last 10 failed events..."
            aws cloudformation describe-stack-events \
                --stack-name "$STACK_NAME" \
                --region "$AWS_REGION" \
                --query 'StackEvents[?ResourceStatus==`CREATE_FAILED` || ResourceStatus==`UPDATE_FAILED`] | [0:10].[Timestamp,ResourceType,LogicalResourceId,ResourceStatusReason]' \
                --output table
            echo ""
            echo "View full events in CloudFormation console:"
            echo "  https://console.aws.amazon.com/cloudformation"
            exit 1
            ;;
        *IN_PROGRESS*|*PENDING*)
            # Continue monitoring
            ;;
        *)
            echo -e "${YELLOW}Unknown status: $STACK_STATUS${NC}"
            ;;
    esac

    # Wait before next check
    sleep 10
done
