#!/bin/bash
#
# Cleanup all test VPC resources
# This script safely removes all resources created by test_vpc_setup.sh
#

set -e

REGION="us-east-1"
CONFIG_FILE="test_vpc_config.json"

echo "============================================"
echo "Cleanup Test VPC Resources"
echo "============================================"
echo ""

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: $CONFIG_FILE not found!"
    echo "Nothing to cleanup."
    exit 1
fi

# Load configuration
echo "Loading configuration from $CONFIG_FILE..."
VPC_ID=$(jq -r '.vpc_id' $CONFIG_FILE)
SG_AGENTCORE=$(jq -r '.security_groups.agentcore' $CONFIG_FILE)
SG_ALB=$(jq -r '.security_groups.alb' $CONFIG_FILE)
SG_FARGATE=$(jq -r '.security_groups.fargate' $CONFIG_FILE)
VPCE_DATA=$(jq -r '.vpc_endpoints.data_plane' $CONFIG_FILE)
VPCE_GATEWAY=$(jq -r '.vpc_endpoints.gateway' $CONFIG_FILE)
ALB_ARN=$(jq -r '.alb.arn' $CONFIG_FILE)
TG_ARN=$(jq -r '.target_group.arn' $CONFIG_FILE)
LISTENER_ARN=$(jq -r '.listener_arn' $CONFIG_FILE)

echo ""
echo "Resources to be deleted:"
echo "  VPC Endpoints: $VPCE_DATA, $VPCE_GATEWAY"
echo "  ALB: $ALB_ARN"
echo "  Target Group: $TG_ARN"
echo "  Security Groups: $SG_AGENTCORE, $SG_ALB, $SG_FARGATE"
echo ""

read -p "Are you sure you want to delete these resources? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "Starting cleanup..."
echo ""

# Step 1: Stop and delete Fargate task
if jq -e '.test_task' $CONFIG_FILE > /dev/null 2>&1; then
    TASK_ARN=$(jq -r '.test_task.arn' $CONFIG_FILE)
    TASK_ID=$(echo $TASK_ARN | rev | cut -d'/' -f1 | rev)

    echo "Step 1: Stopping Fargate task..."
    aws ecs stop-task \
      --region $REGION \
      --cluster my-fargate-cluster \
      --task $TASK_ID \
      --reason "Test cleanup" \
      > /dev/null 2>&1 || echo "  Task already stopped or not found"

    echo "  Waiting for task to stop..."
    sleep 5
else
    echo "Step 1: No Fargate task to stop"
fi

# Step 2: Deregister targets from target group
if jq -e '.test_task.private_ip' $CONFIG_FILE > /dev/null 2>&1; then
    PRIVATE_IP=$(jq -r '.test_task.private_ip' $CONFIG_FILE)

    echo ""
    echo "Step 2: Deregistering targets from target group..."
    aws elbv2 deregister-targets \
      --region $REGION \
      --target-group-arn $TG_ARN \
      --targets Id=$PRIVATE_IP \
      > /dev/null 2>&1 || echo "  Target already deregistered or not found"

    echo "  Waiting for deregistration..."
    sleep 5
else
    echo ""
    echo "Step 2: No targets to deregister"
fi

# Step 3: Delete ALB listener
echo ""
echo "Step 3: Deleting ALB listener..."
aws elbv2 delete-listener \
  --region $REGION \
  --listener-arn $LISTENER_ARN \
  > /dev/null 2>&1 || echo "  Listener already deleted or not found"

# Step 4: Delete ALB
echo ""
echo "Step 4: Deleting Application Load Balancer..."
aws elbv2 delete-load-balancer \
  --region $REGION \
  --load-balancer-arn $ALB_ARN \
  > /dev/null 2>&1 || echo "  ALB already deleted or not found"

echo "  Waiting for ALB to be deleted..."
sleep 10

# Step 5: Delete target group
echo ""
echo "Step 5: Deleting target group..."
aws elbv2 delete-target-group \
  --region $REGION \
  --target-group-arn $TG_ARN \
  > /dev/null 2>&1 || echo "  Target group already deleted or not found"

# Step 6: Delete VPC Endpoints
echo ""
echo "Step 6: Deleting VPC Endpoints..."
echo "  Deleting data plane endpoint..."
aws ec2 delete-vpc-endpoints \
  --region $REGION \
  --vpc-endpoint-ids $VPCE_DATA \
  > /dev/null 2>&1 || echo "  Data plane endpoint already deleted or not found"

echo "  Deleting gateway endpoint..."
aws ec2 delete-vpc-endpoints \
  --region $REGION \
  --vpc-endpoint-ids $VPCE_GATEWAY \
  > /dev/null 2>&1 || echo "  Gateway endpoint already deleted or not found"

echo "  Waiting for VPC endpoints to be deleted..."
sleep 10

# Step 7: Delete AgentCore Runtime
if jq -e '.agentcore_runtime' $CONFIG_FILE > /dev/null 2>&1; then
    RUNTIME_ID=$(jq -r '.agentcore_runtime.id' $CONFIG_FILE)

    echo ""
    echo "Step 7: Deleting AgentCore Runtime..."
    aws bedrock-agentcore delete-runtime \
      --region $REGION \
      --runtime-id $RUNTIME_ID \
      > /dev/null 2>&1 || echo "  Runtime already deleted or not found"
else
    echo ""
    echo "Step 7: No AgentCore Runtime to delete"
fi

# Step 8: Delete task definition
echo ""
echo "Step 8: Deregistering task definition..."
aws ecs deregister-task-definition \
  --region $REGION \
  --task-definition test-vpc-private-task:1 \
  > /dev/null 2>&1 || echo "  Task definition already deregistered or not found"

# Step 9: Delete Security Groups (must be last, after all dependencies)
echo ""
echo "Step 9: Deleting Security Groups..."
echo "  Waiting for all dependencies to be removed..."
sleep 15

echo "  Deleting AgentCore SG..."
aws ec2 delete-security-group \
  --region $REGION \
  --group-id $SG_AGENTCORE \
  > /dev/null 2>&1 || echo "  AgentCore SG already deleted or not found"

echo "  Deleting ALB SG..."
aws ec2 delete-security-group \
  --region $REGION \
  --group-id $SG_ALB \
  > /dev/null 2>&1 || echo "  ALB SG already deleted or not found"

echo "  Deleting Fargate SG..."
aws ec2 delete-security-group \
  --region $REGION \
  --group-id $SG_FARGATE \
  > /dev/null 2>&1 || echo "  Fargate SG already deleted or not found"

# Step 10: Clean up configuration file
echo ""
echo "Step 10: Removing configuration file..."
rm -f $CONFIG_FILE
echo "  Configuration file removed"

echo ""
echo "============================================"
echo "Cleanup Complete!"
echo "============================================"
echo ""
echo "All test resources have been deleted."
echo ""
echo "Note: Some resources may take a few minutes to fully delete."
echo "      If you see errors, wait a few minutes and run this script again."
echo ""
echo "Remaining resources to check manually:"
echo "  - CloudWatch Log Groups: /ecs/test-vpc-private-task"
echo "  - ECR Images (if any test images were created)"
echo ""
echo "To verify cleanup:"
echo "  aws ec2 describe-security-groups --filters 'Name=tag:Purpose,Values=vpc-private-connectivity-test'"
echo "  aws ec2 describe-vpc-endpoints --filters 'Name=tag:Purpose,Values=vpc-private-connectivity-test'"
echo "============================================"
