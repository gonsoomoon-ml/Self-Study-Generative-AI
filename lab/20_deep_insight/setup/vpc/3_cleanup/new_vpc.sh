#!/bin/bash
#
# Cleanup all test VPC resources INCLUDING the VPC itself
# This script removes everything created by test_vpc_setup_new_vpc.sh
#

set -e

REGION="us-east-1"
CONFIG_FILE="test_vpc_config.json"

echo "============================================"
echo "Cleanup Test VPC Resources (Including VPC)"
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
VPC_CIDR=$(jq -r '.vpc_cidr' $CONFIG_FILE)
PRIVATE_SUBNET_A=$(jq -r '.subnets.private[0]' $CONFIG_FILE)
PRIVATE_SUBNET_B=$(jq -r '.subnets.private[1]' $CONFIG_FILE)
PUBLIC_SUBNET_A=$(jq -r '.subnets.public[0]' $CONFIG_FILE)
PUBLIC_SUBNET_B=$(jq -r '.subnets.public[1]' $CONFIG_FILE)
IGW_ID=$(jq -r '.network.igw_id' $CONFIG_FILE)
NAT_GW=$(jq -r '.network.nat_gateway_id' $CONFIG_FILE)
EIP_ALLOC=$(jq -r '.network.eip_allocation_id' $CONFIG_FILE)
PUBLIC_RT=$(jq -r '.network.public_route_table' $CONFIG_FILE)
PRIVATE_RT=$(jq -r '.network.private_route_table' $CONFIG_FILE)
SG_AGENTCORE=$(jq -r '.security_groups.agentcore' $CONFIG_FILE)
SG_ALB=$(jq -r '.security_groups.alb' $CONFIG_FILE)
SG_FARGATE=$(jq -r '.security_groups.fargate' $CONFIG_FILE)
SG_VPCE=$(jq -r '.security_groups.vpce' $CONFIG_FILE)
VPCE_DATA=$(jq -r '.vpc_endpoints.data_plane' $CONFIG_FILE)
VPCE_GATEWAY=$(jq -r '.vpc_endpoints.gateway' $CONFIG_FILE)
ALB_ARN=$(jq -r '.alb.arn' $CONFIG_FILE)
TG_ARN=$(jq -r '.target_group.arn' $CONFIG_FILE)
LISTENER_ARN=$(jq -r '.listener_arn' $CONFIG_FILE)

echo ""
echo "Resources to be deleted:"
echo "  VPC: $VPC_ID ($VPC_CIDR)"
echo "  Subnets: 4 (2 private, 2 public)"
echo "  NAT Gateway: $NAT_GW"
echo "  Internet Gateway: $IGW_ID"
echo "  VPC Endpoints: 2"
echo "  ALB: $ALB_ARN"
echo "  Security Groups: 4"
echo "  Route Tables: 2"
echo ""
echo "⚠️  WARNING: This will delete the entire test VPC!"
echo ""

read -p "Are you sure you want to delete ALL resources? (yes/no): " CONFIRM

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

# Step 2: Deregister targets
if jq -e '.test_task.private_ip' $CONFIG_FILE > /dev/null 2>&1; then
    PRIVATE_IP=$(jq -r '.test_task.private_ip' $CONFIG_FILE)

    echo ""
    echo "Step 2: Deregistering targets..."
    aws elbv2 deregister-targets \
      --region $REGION \
      --target-group-arn $TG_ARN \
      --targets Id=$PRIVATE_IP \
      > /dev/null 2>&1 || echo "  Target already deregistered"

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
  > /dev/null 2>&1 || echo "  Listener already deleted"

# Step 4: Delete ALB
echo ""
echo "Step 4: Deleting Application Load Balancer..."
aws elbv2 delete-load-balancer \
  --region $REGION \
  --load-balancer-arn $ALB_ARN \
  > /dev/null 2>&1 || echo "  ALB already deleted"

echo "  Waiting for ALB to be deleted..."
sleep 10

# Step 5: Delete target group
echo ""
echo "Step 5: Deleting target group..."
aws elbv2 delete-target-group \
  --region $REGION \
  --target-group-arn $TG_ARN \
  > /dev/null 2>&1 || echo "  Target group already deleted"

# Step 6: Delete VPC Endpoints
echo ""
echo "Step 6: Deleting VPC Endpoints..."
echo "  Deleting data plane endpoint..."
aws ec2 delete-vpc-endpoints \
  --region $REGION \
  --vpc-endpoint-ids $VPCE_DATA \
  > /dev/null 2>&1 || echo "  Data plane endpoint already deleted"

echo "  Deleting gateway endpoint..."
aws ec2 delete-vpc-endpoints \
  --region $REGION \
  --vpc-endpoint-ids $VPCE_GATEWAY \
  > /dev/null 2>&1 || echo "  Gateway endpoint already deleted"

echo "  Waiting for VPC endpoints to be deleted..."
sleep 15

# Step 7: Delete AgentCore Runtime
if jq -e '.agentcore_runtime' $CONFIG_FILE > /dev/null 2>&1; then
    RUNTIME_ID=$(jq -r '.agentcore_runtime.id' $CONFIG_FILE)

    echo ""
    echo "Step 7: Deleting AgentCore Runtime..."
    aws bedrock-agentcore delete-runtime \
      --region $REGION \
      --runtime-id $RUNTIME_ID \
      > /dev/null 2>&1 || echo "  Runtime already deleted"
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
  > /dev/null 2>&1 || echo "  Task definition already deregistered"

# Step 9: Delete NAT Gateway
echo ""
echo "Step 9: Deleting NAT Gateway..."
aws ec2 delete-nat-gateway \
  --region $REGION \
  --nat-gateway-id $NAT_GW \
  > /dev/null 2>&1 || echo "  NAT Gateway already deleted"

echo "  Waiting for NAT Gateway to be deleted (this may take 2-3 minutes)..."
sleep 30

# Check NAT Gateway state
NAT_STATE=$(aws ec2 describe-nat-gateways \
  --region $REGION \
  --nat-gateway-ids $NAT_GW \
  --query 'NatGateways[0].State' --output text 2>/dev/null || echo "deleted")

while [ "$NAT_STATE" != "deleted" ] && [ "$NAT_STATE" != "None" ] && [ "$NAT_STATE" != "" ]; do
    echo "  NAT Gateway state: $NAT_STATE (waiting...)"
    sleep 15
    NAT_STATE=$(aws ec2 describe-nat-gateways \
      --region $REGION \
      --nat-gateway-ids $NAT_GW \
      --query 'NatGateways[0].State' --output text 2>/dev/null || echo "deleted")
done

echo "  NAT Gateway deleted!"

# Step 10: Release Elastic IP
echo ""
echo "Step 10: Releasing Elastic IP..."
aws ec2 release-address \
  --region $REGION \
  --allocation-id $EIP_ALLOC \
  > /dev/null 2>&1 || echo "  Elastic IP already released"

# Step 11: Detach and delete Internet Gateway
echo ""
echo "Step 11: Detaching and deleting Internet Gateway..."
aws ec2 detach-internet-gateway \
  --region $REGION \
  --internet-gateway-id $IGW_ID \
  --vpc-id $VPC_ID \
  > /dev/null 2>&1 || echo "  IGW already detached"

aws ec2 delete-internet-gateway \
  --region $REGION \
  --internet-gateway-id $IGW_ID \
  > /dev/null 2>&1 || echo "  IGW already deleted"

# Step 12: Disassociate and delete route tables
echo ""
echo "Step 12: Deleting route tables..."

# Get route table associations
PUBLIC_RT_ASSOCS=$(aws ec2 describe-route-tables \
  --region $REGION \
  --route-table-ids $PUBLIC_RT \
  --query 'RouteTables[0].Associations[?!Main].RouteTableAssociationId' \
  --output text 2>/dev/null || echo "")

PRIVATE_RT_ASSOCS=$(aws ec2 describe-route-tables \
  --region $REGION \
  --route-table-ids $PRIVATE_RT \
  --query 'RouteTables[0].Associations[?!Main].RouteTableAssociationId' \
  --output text 2>/dev/null || echo "")

# Disassociate route tables
for ASSOC in $PUBLIC_RT_ASSOCS; do
    echo "  Disassociating public route table: $ASSOC"
    aws ec2 disassociate-route-table \
      --region $REGION \
      --association-id $ASSOC \
      > /dev/null 2>&1 || echo "  Already disassociated"
done

for ASSOC in $PRIVATE_RT_ASSOCS; do
    echo "  Disassociating private route table: $ASSOC"
    aws ec2 disassociate-route-table \
      --region $REGION \
      --association-id $ASSOC \
      > /dev/null 2>&1 || echo "  Already disassociated"
done

# Delete route tables
echo "  Deleting public route table..."
aws ec2 delete-route-table \
  --region $REGION \
  --route-table-id $PUBLIC_RT \
  > /dev/null 2>&1 || echo "  Public RT already deleted"

echo "  Deleting private route table..."
aws ec2 delete-route-table \
  --region $REGION \
  --route-table-id $PRIVATE_RT \
  > /dev/null 2>&1 || echo "  Private RT already deleted"

# Step 13: Delete Security Groups
echo ""
echo "Step 13: Deleting Security Groups..."
echo "  Waiting for all ENI dependencies to be removed..."
sleep 20

echo "  Deleting AgentCore SG..."
aws ec2 delete-security-group \
  --region $REGION \
  --group-id $SG_AGENTCORE \
  > /dev/null 2>&1 || echo "  AgentCore SG already deleted or has dependencies"

echo "  Deleting ALB SG..."
aws ec2 delete-security-group \
  --region $REGION \
  --group-id $SG_ALB \
  > /dev/null 2>&1 || echo "  ALB SG already deleted or has dependencies"

echo "  Deleting Fargate SG..."
aws ec2 delete-security-group \
  --region $REGION \
  --group-id $SG_FARGATE \
  > /dev/null 2>&1 || echo "  Fargate SG already deleted or has dependencies"

echo "  Deleting VPC Endpoint SG..."
aws ec2 delete-security-group \
  --region $REGION \
  --group-id $SG_VPCE \
  > /dev/null 2>&1 || echo "  VPC Endpoint SG already deleted or has dependencies"

# Retry security group deletion after additional wait
echo "  Retrying security group deletion after additional wait..."
sleep 20

for SG in $SG_AGENTCORE $SG_ALB $SG_FARGATE $SG_VPCE; do
    aws ec2 delete-security-group \
      --region $REGION \
      --group-id $SG \
      > /dev/null 2>&1 && echo "  Deleted: $SG" || echo "  Could not delete: $SG (may have dependencies)"
done

# Step 14: Delete Subnets
echo ""
echo "Step 14: Deleting Subnets..."

echo "  Deleting private subnet A..."
aws ec2 delete-subnet \
  --region $REGION \
  --subnet-id $PRIVATE_SUBNET_A \
  > /dev/null 2>&1 || echo "  Private subnet A already deleted"

echo "  Deleting private subnet B..."
aws ec2 delete-subnet \
  --region $REGION \
  --subnet-id $PRIVATE_SUBNET_B \
  > /dev/null 2>&1 || echo "  Private subnet B already deleted"

echo "  Deleting public subnet A..."
aws ec2 delete-subnet \
  --region $REGION \
  --subnet-id $PUBLIC_SUBNET_A \
  > /dev/null 2>&1 || echo "  Public subnet A already deleted"

echo "  Deleting public subnet B..."
aws ec2 delete-subnet \
  --region $REGION \
  --subnet-id $PUBLIC_SUBNET_B \
  > /dev/null 2>&1 || echo "  Public subnet B already deleted"

# Step 15: Delete VPC
echo ""
echo "Step 15: Deleting VPC..."
sleep 10

aws ec2 delete-vpc \
  --region $REGION \
  --vpc-id $VPC_ID \
  > /dev/null 2>&1 && echo "  VPC deleted: $VPC_ID" || echo "  Could not delete VPC (may have remaining dependencies)"

# Step 16: Clean up configuration file
echo ""
echo "Step 16: Removing configuration file..."
rm -f $CONFIG_FILE
echo "  Configuration file removed"

echo ""
echo "============================================"
echo "Cleanup Complete!"
echo "============================================"
echo ""
echo "All test resources have been deleted, including the VPC."
echo ""
echo "Note: Some resources may take a few minutes to fully delete."
echo "      If you see errors about dependencies, wait 5 minutes and run:"
echo "      ./cleanup_test_vpc_new.sh again"
echo ""
echo "Remaining resources to check manually:"
echo "  - CloudWatch Log Groups: /ecs/test-vpc-private-task"
echo ""
echo "To verify cleanup:"
echo "  aws ec2 describe-vpcs --filters 'Name=tag:Purpose,Values=vpc-private-connectivity-test'"
echo "  aws ec2 describe-security-groups --filters 'Name=tag:Purpose,Values=vpc-private-connectivity-test'"
echo "============================================"
