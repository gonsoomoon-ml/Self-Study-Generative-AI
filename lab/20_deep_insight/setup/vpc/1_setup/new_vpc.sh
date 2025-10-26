#!/bin/bash
#
# Bedrock AgentCore VPC Private Connectivity Test Environment Setup
# WITH NEW VPC CREATION
#
# This script creates a completely isolated test VPC with all necessary resources
# All resources are tagged with "test-vpc-private"
#

set -e

# Configuration
REGION="us-east-1"
ACCOUNT_ID="057716757052"
CLUSTER_NAME="my-fargate-cluster"

# Test resource names
TEST_PREFIX="test-vpc-private"
VPC_NAME="${TEST_PREFIX}-vpc"
VPC_CIDR="10.100.0.0/16"

# Subnet CIDRs
PRIVATE_SUBNET_A_CIDR="10.100.1.0/24"
PRIVATE_SUBNET_B_CIDR="10.100.2.0/24"
PUBLIC_SUBNET_A_CIDR="10.100.11.0/24"
PUBLIC_SUBNET_B_CIDR="10.100.12.0/24"

# Resource names
SG_AGENTCORE_NAME="${TEST_PREFIX}-agentcore-sg"
SG_ALB_NAME="${TEST_PREFIX}-alb-sg"
SG_FARGATE_NAME="${TEST_PREFIX}-fargate-sg"
SG_VPCE_NAME="${TEST_PREFIX}-vpce-sg"
ALB_NAME="${TEST_PREFIX}-alb"
TARGET_GROUP_NAME="${TEST_PREFIX}-tg"
TASK_DEF_NAME="${TEST_PREFIX}-task"

echo "============================================"
echo "Bedrock AgentCore VPC Test Environment Setup"
echo "WITH NEW VPC CREATION"
echo "============================================"
echo ""
echo "Region: $REGION"
echo "VPC CIDR: $VPC_CIDR"
echo "Test Prefix: $TEST_PREFIX"
echo ""
echo "This will create:"
echo "  - New VPC with 4 subnets (2 private, 2 public)"
echo "  - Internet Gateway"
echo "  - NAT Gateway (for Fargate ECR access)"
echo "  - VPC Endpoints (Bedrock AgentCore)"
echo "  - Internal ALB"
echo "  - Security Groups"
echo ""

# Step 1: Create VPC
echo "Step 1: Creating VPC..."

VPC_ID=$(aws ec2 create-vpc \
  --region $REGION \
  --cidr-block $VPC_CIDR \
  --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=$VPC_NAME},{Key=Environment,Value=test},{Key=Purpose,Value=vpc-private-connectivity-test}]" \
  --query 'Vpc.VpcId' --output text)

echo "  VPC Created: $VPC_ID ($VPC_CIDR)"

# Enable DNS hostnames
aws ec2 modify-vpc-attribute \
  --region $REGION \
  --vpc-id $VPC_ID \
  --enable-dns-hostnames

echo "  DNS hostnames enabled"

# Step 2: Create Internet Gateway
echo ""
echo "Step 2: Creating Internet Gateway..."

IGW_ID=$(aws ec2 create-internet-gateway \
  --region $REGION \
  --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=${TEST_PREFIX}-igw},{Key=Environment,Value=test},{Key=Purpose,Value=vpc-private-connectivity-test}]" \
  --query 'InternetGateway.InternetGatewayId' --output text)

echo "  IGW Created: $IGW_ID"

# Attach IGW to VPC
aws ec2 attach-internet-gateway \
  --region $REGION \
  --vpc-id $VPC_ID \
  --internet-gateway-id $IGW_ID

echo "  IGW attached to VPC"

# Step 3: Create Subnets
echo ""
echo "Step 3: Creating Subnets..."

# 3.1 Private Subnet A (us-east-1a)
PRIVATE_SUBNET_A=$(aws ec2 create-subnet \
  --region $REGION \
  --vpc-id $VPC_ID \
  --cidr-block $PRIVATE_SUBNET_A_CIDR \
  --availability-zone us-east-1a \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=${TEST_PREFIX}-private-a},{Key=Environment,Value=test},{Key=Purpose,Value=vpc-private-connectivity-test},{Key=Type,Value=private}]" \
  --query 'Subnet.SubnetId' --output text)

echo "  Private Subnet A: $PRIVATE_SUBNET_A (us-east-1a, $PRIVATE_SUBNET_A_CIDR)"

# 3.2 Private Subnet B (us-east-1c)
PRIVATE_SUBNET_B=$(aws ec2 create-subnet \
  --region $REGION \
  --vpc-id $VPC_ID \
  --cidr-block $PRIVATE_SUBNET_B_CIDR \
  --availability-zone us-east-1c \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=${TEST_PREFIX}-private-b},{Key=Environment,Value=test},{Key=Purpose,Value=vpc-private-connectivity-test},{Key=Type,Value=private}]" \
  --query 'Subnet.SubnetId' --output text)

echo "  Private Subnet B: $PRIVATE_SUBNET_B (us-east-1c, $PRIVATE_SUBNET_B_CIDR)"

# 3.3 Public Subnet A (us-east-1a) - for NAT Gateway
PUBLIC_SUBNET_A=$(aws ec2 create-subnet \
  --region $REGION \
  --vpc-id $VPC_ID \
  --cidr-block $PUBLIC_SUBNET_A_CIDR \
  --availability-zone us-east-1a \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=${TEST_PREFIX}-public-a},{Key=Environment,Value=test},{Key=Purpose,Value=vpc-private-connectivity-test},{Key=Type,Value=public}]" \
  --query 'Subnet.SubnetId' --output text)

echo "  Public Subnet A: $PUBLIC_SUBNET_A (us-east-1a, $PUBLIC_SUBNET_A_CIDR)"

# 3.4 Public Subnet B (us-east-1c) - for high availability
PUBLIC_SUBNET_B=$(aws ec2 create-subnet \
  --region $REGION \
  --vpc-id $VPC_ID \
  --cidr-block $PUBLIC_SUBNET_B_CIDR \
  --availability-zone us-east-1c \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=${TEST_PREFIX}-public-b},{Key=Environment,Value=test},{Key=Purpose,Value=vpc-private-connectivity-test},{Key=Type,Value=public}]" \
  --query 'Subnet.SubnetId' --output text)

echo "  Public Subnet B: $PUBLIC_SUBNET_B (us-east-1c, $PUBLIC_SUBNET_B_CIDR)"

# Step 4: Create and configure Route Tables
echo ""
echo "Step 4: Creating Route Tables..."

# 4.1 Public Route Table
PUBLIC_RT=$(aws ec2 create-route-table \
  --region $REGION \
  --vpc-id $VPC_ID \
  --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=${TEST_PREFIX}-public-rt},{Key=Environment,Value=test},{Key=Purpose,Value=vpc-private-connectivity-test}]" \
  --query 'RouteTable.RouteTableId' --output text)

echo "  Public Route Table: $PUBLIC_RT"

# Add route to Internet Gateway
aws ec2 create-route \
  --region $REGION \
  --route-table-id $PUBLIC_RT \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id $IGW_ID \
  > /dev/null

echo "  Route added: 0.0.0.0/0 → IGW"

# Associate public subnets with public route table
aws ec2 associate-route-table \
  --region $REGION \
  --subnet-id $PUBLIC_SUBNET_A \
  --route-table-id $PUBLIC_RT \
  > /dev/null

aws ec2 associate-route-table \
  --region $REGION \
  --subnet-id $PUBLIC_SUBNET_B \
  --route-table-id $PUBLIC_RT \
  > /dev/null

echo "  Public subnets associated with public route table"

# Step 5: Allocate Elastic IP and Create NAT Gateway
echo ""
echo "Step 5: Creating NAT Gateway..."

EIP_ALLOC=$(aws ec2 allocate-address \
  --region $REGION \
  --domain vpc \
  --tag-specifications "ResourceType=elastic-ip,Tags=[{Key=Name,Value=${TEST_PREFIX}-nat-eip},{Key=Environment,Value=test},{Key=Purpose,Value=vpc-private-connectivity-test}]" \
  --query 'AllocationId' --output text)

echo "  Elastic IP allocated: $EIP_ALLOC"

NAT_GW=$(aws ec2 create-nat-gateway \
  --region $REGION \
  --subnet-id $PUBLIC_SUBNET_A \
  --allocation-id $EIP_ALLOC \
  --tag-specifications "ResourceType=natgateway,Tags=[{Key=Name,Value=${TEST_PREFIX}-nat},{Key=Environment,Value=test},{Key=Purpose,Value=vpc-private-connectivity-test}]" \
  --query 'NatGateway.NatGatewayId' --output text)

echo "  NAT Gateway created: $NAT_GW"
echo "  Waiting for NAT Gateway to become available (this may take 2-3 minutes)..."

aws ec2 wait nat-gateway-available --region $REGION --nat-gateway-ids $NAT_GW

echo "  NAT Gateway is now available!"

# 4.2 Private Route Table
PRIVATE_RT=$(aws ec2 create-route-table \
  --region $REGION \
  --vpc-id $VPC_ID \
  --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=${TEST_PREFIX}-private-rt},{Key=Environment,Value=test},{Key=Purpose,Value=vpc-private-connectivity-test}]" \
  --query 'RouteTable.RouteTableId' --output text)

echo "  Private Route Table: $PRIVATE_RT"

# Add route to NAT Gateway
aws ec2 create-route \
  --region $REGION \
  --route-table-id $PRIVATE_RT \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id $NAT_GW \
  > /dev/null

echo "  Route added: 0.0.0.0/0 → NAT Gateway"

# Associate private subnets with private route table
aws ec2 associate-route-table \
  --region $REGION \
  --subnet-id $PRIVATE_SUBNET_A \
  --route-table-id $PRIVATE_RT \
  > /dev/null

aws ec2 associate-route-table \
  --region $REGION \
  --subnet-id $PRIVATE_SUBNET_B \
  --route-table-id $PRIVATE_RT \
  > /dev/null

echo "  Private subnets associated with private route table"

# Step 6: Create Security Groups
echo ""
echo "Step 6: Creating Security Groups..."

# 6.1 VPC Endpoint Security Group (for VPC Endpoints)
SG_VPCE_ID=$(aws ec2 create-security-group \
  --region $REGION \
  --group-name $SG_VPCE_NAME \
  --description "Test: VPC Endpoints - allows HTTPS from VPC" \
  --vpc-id $VPC_ID \
  --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=$SG_VPCE_NAME},{Key=Environment,Value=test},{Key=Purpose,Value=vpc-private-connectivity-test}]" \
  --query 'GroupId' --output text)

echo "  VPC Endpoint SG: $SG_VPCE_ID"

# Allow HTTPS from VPC CIDR
aws ec2 authorize-security-group-ingress \
  --region $REGION \
  --group-id $SG_VPCE_ID \
  --protocol tcp \
  --port 443 \
  --cidr $VPC_CIDR \
  > /dev/null

echo "    Inbound: HTTPS:443 ← $VPC_CIDR"

# 6.2 AgentCore Runtime Security Group
SG_AGENTCORE_ID=$(aws ec2 create-security-group \
  --region $REGION \
  --group-name $SG_AGENTCORE_NAME \
  --description "Test: AgentCore Runtime - allows outbound to ALB" \
  --vpc-id $VPC_ID \
  --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=$SG_AGENTCORE_NAME},{Key=Environment,Value=test},{Key=Purpose,Value=vpc-private-connectivity-test}]" \
  --query 'GroupId' --output text)

echo "  AgentCore Runtime SG: $SG_AGENTCORE_ID"

# 6.3 Internal ALB Security Group
SG_ALB_ID=$(aws ec2 create-security-group \
  --region $REGION \
  --group-name $SG_ALB_NAME \
  --description "Test: Internal ALB - allows inbound from AgentCore" \
  --vpc-id $VPC_ID \
  --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=$SG_ALB_NAME},{Key=Environment,Value=test},{Key=Purpose,Value=vpc-private-connectivity-test}]" \
  --query 'GroupId' --output text)

echo "  Internal ALB SG: $SG_ALB_ID"

# 6.4 Fargate Container Security Group
SG_FARGATE_ID=$(aws ec2 create-security-group \
  --region $REGION \
  --group-name $SG_FARGATE_NAME \
  --description "Test: Fargate containers - allows inbound from ALB" \
  --vpc-id $VPC_ID \
  --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=$SG_FARGATE_NAME},{Key=Environment,Value=test},{Key=Purpose,Value=vpc-private-connectivity-test}]" \
  --query 'GroupId' --output text)

echo "  Fargate Container SG: $SG_FARGATE_ID"

# Step 7: Configure Security Group Rules
echo ""
echo "Step 7: Configuring Security Group Rules..."

# AgentCore -> ALB
echo "  AgentCore → ALB (HTTP:80)..."
aws ec2 authorize-security-group-egress \
  --region $REGION \
  --group-id $SG_AGENTCORE_ID \
  --protocol tcp \
  --port 80 \
  --source-group $SG_ALB_ID \
  > /dev/null

# ALB <- AgentCore
echo "  ALB ← AgentCore (HTTP:80)..."
aws ec2 authorize-security-group-ingress \
  --region $REGION \
  --group-id $SG_ALB_ID \
  --protocol tcp \
  --port 80 \
  --source-group $SG_AGENTCORE_ID \
  > /dev/null

# ALB -> Fargate
echo "  ALB → Fargate (HTTP:8080)..."
aws ec2 authorize-security-group-egress \
  --region $REGION \
  --group-id $SG_ALB_ID \
  --protocol tcp \
  --port 8080 \
  --source-group $SG_FARGATE_ID \
  > /dev/null

# Fargate <- ALB
echo "  Fargate ← ALB (HTTP:8080)..."
aws ec2 authorize-security-group-ingress \
  --region $REGION \
  --group-id $SG_FARGATE_ID \
  --protocol tcp \
  --port 8080 \
  --source-group $SG_ALB_ID \
  > /dev/null

# Fargate -> Internet (via NAT Gateway)
echo "  Fargate → Internet (for ECR, S3, etc.)..."
aws ec2 authorize-security-group-egress \
  --region $REGION \
  --group-id $SG_FARGATE_ID \
  --protocol -1 \
  --cidr 0.0.0.0/0 \
  > /dev/null 2>&1 || echo "  (default rule already exists)"

# AgentCore -> VPC Endpoints
echo "  AgentCore → VPC Endpoints (HTTPS:443)..."
aws ec2 authorize-security-group-egress \
  --region $REGION \
  --group-id $SG_AGENTCORE_ID \
  --protocol tcp \
  --port 443 \
  --source-group $SG_VPCE_ID \
  > /dev/null

# Step 8: Create VPC Endpoints (Bedrock AgentCore)
echo ""
echo "Step 8: Creating VPC Endpoints for Bedrock AgentCore..."

# 8.1 Data Plane VPC Endpoint
echo "  Creating Data Plane VPC Endpoint..."
VPCE_DATA_ID=$(aws ec2 create-vpc-endpoint \
  --region $REGION \
  --vpc-id $VPC_ID \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.$REGION.bedrock-agentcore \
  --subnet-ids $PRIVATE_SUBNET_A $PRIVATE_SUBNET_B \
  --security-group-ids $SG_VPCE_ID \
  --private-dns-enabled \
  --tag-specifications "ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=${TEST_PREFIX}-bedrock-data},{Key=Environment,Value=test},{Key=Purpose,Value=vpc-private-connectivity-test}]" \
  --query 'VpcEndpoint.VpcEndpointId' --output text)

echo "  Created: $VPCE_DATA_ID"

# 8.2 Gateway VPC Endpoint
echo "  Creating Gateway VPC Endpoint..."
VPCE_GATEWAY_ID=$(aws ec2 create-vpc-endpoint \
  --region $REGION \
  --vpc-id $VPC_ID \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.$REGION.bedrock-agentcore.gateway \
  --subnet-ids $PRIVATE_SUBNET_A $PRIVATE_SUBNET_B \
  --security-group-ids $SG_VPCE_ID \
  --private-dns-enabled \
  --tag-specifications "ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=${TEST_PREFIX}-bedrock-gateway},{Key=Environment,Value=test},{Key=Purpose,Value=vpc-private-connectivity-test}]" \
  --query 'VpcEndpoint.VpcEndpointId' --output text)

echo "  Created: $VPCE_GATEWAY_ID"

# Wait for VPC Endpoints (custom wait loop - no built-in waiter exists)
echo "  Waiting for VPC Endpoints to become available..."

MAX_ATTEMPTS=60
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  STATE_DATA=$(aws ec2 describe-vpc-endpoints \
    --region $REGION \
    --vpc-endpoint-ids $VPCE_DATA_ID \
    --query 'VpcEndpoints[0].State' --output text 2>/dev/null || echo "pending")

  STATE_GATEWAY=$(aws ec2 describe-vpc-endpoints \
    --region $REGION \
    --vpc-endpoint-ids $VPCE_GATEWAY_ID \
    --query 'VpcEndpoints[0].State' --output text 2>/dev/null || echo "pending")

  if [ "$STATE_DATA" = "available" ] && [ "$STATE_GATEWAY" = "available" ]; then
    echo "  VPC Endpoints are now available!"
    break
  fi

  if [ $((ATTEMPT % 6)) -eq 0 ]; then
    echo "  Status: Data=$STATE_DATA, Gateway=$STATE_GATEWAY (attempt $((ATTEMPT + 1))/$MAX_ATTEMPTS)"
  fi

  sleep 10
  ATTEMPT=$((ATTEMPT + 1))
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
  echo "  ⚠️  Warning: VPC Endpoints did not become available within 10 minutes"
  echo "  Current states: Data=$STATE_DATA, Gateway=$STATE_GATEWAY"
  echo "  You may need to check AWS Console and wait longer before proceeding"
fi

# Step 9: Create Internal ALB
echo ""
echo "Step 9: Creating Internal Application Load Balancer..."

ALB_ARN=$(aws elbv2 create-load-balancer \
  --region $REGION \
  --name $ALB_NAME \
  --type application \
  --scheme internal \
  --subnets $PRIVATE_SUBNET_A $PRIVATE_SUBNET_B \
  --security-groups $SG_ALB_ID \
  --tags "Key=Name,Value=$ALB_NAME" "Key=Environment,Value=test" "Key=Purpose,Value=vpc-private-connectivity-test" \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text)

echo "  Created: $ALB_ARN"

# Get ALB DNS
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --region $REGION \
  --load-balancer-arns $ALB_ARN \
  --query 'LoadBalancers[0].DNSName' --output text)

echo "  ALB DNS: $ALB_DNS"

# Step 10: Create Target Group
echo ""
echo "Step 10: Creating Target Group..."

TG_ARN=$(aws elbv2 create-target-group \
  --region $REGION \
  --name $TARGET_GROUP_NAME \
  --protocol HTTP \
  --port 8080 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-enabled \
  --health-check-protocol HTTP \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --tags "Key=Name,Value=$TARGET_GROUP_NAME" "Key=Environment,Value=test" "Key=Purpose,Value=vpc-private-connectivity-test" \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

echo "  Created: $TG_ARN"

# Step 11: Create ALB Listener
echo ""
echo "Step 11: Creating ALB Listener..."

LISTENER_ARN=$(aws elbv2 create-listener \
  --region $REGION \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN \
  --query 'Listeners[0].ListenerArn' --output text)

echo "  Created: $LISTENER_ARN"

# Step 12: Enable Sticky Sessions
echo ""
echo "Step 12: Configuring Sticky Sessions..."

aws elbv2 modify-target-group-attributes \
  --region $REGION \
  --target-group-arn $TG_ARN \
  --attributes \
    Key=stickiness.enabled,Value=true \
    Key=stickiness.type,Value=lb_cookie \
    Key=stickiness.lb_cookie.duration_seconds,Value=86400 \
  > /dev/null

echo "  Sticky sessions enabled (24 hours)"

# Step 13: Save configuration to file
echo ""
echo "Step 13: Saving configuration..."

cat > test_vpc_config.json <<EOF
{
  "region": "$REGION",
  "vpc_id": "$VPC_ID",
  "vpc_cidr": "$VPC_CIDR",
  "subnets": {
    "private": ["$PRIVATE_SUBNET_A", "$PRIVATE_SUBNET_B"],
    "public": ["$PUBLIC_SUBNET_A", "$PUBLIC_SUBNET_B"]
  },
  "network": {
    "igw_id": "$IGW_ID",
    "nat_gateway_id": "$NAT_GW",
    "eip_allocation_id": "$EIP_ALLOC",
    "public_route_table": "$PUBLIC_RT",
    "private_route_table": "$PRIVATE_RT"
  },
  "security_groups": {
    "agentcore": "$SG_AGENTCORE_ID",
    "alb": "$SG_ALB_ID",
    "fargate": "$SG_FARGATE_ID",
    "vpce": "$SG_VPCE_ID"
  },
  "vpc_endpoints": {
    "data_plane": "$VPCE_DATA_ID",
    "gateway": "$VPCE_GATEWAY_ID"
  },
  "alb": {
    "arn": "$ALB_ARN",
    "dns": "$ALB_DNS"
  },
  "target_group": {
    "arn": "$TG_ARN",
    "name": "$TARGET_GROUP_NAME"
  },
  "listener_arn": "$LISTENER_ARN"
}
EOF

echo "  Configuration saved to: test_vpc_config.json"

# Summary
echo ""
echo "============================================"
echo "Test Environment Setup Complete!"
echo "============================================"
echo ""
echo "Created Network Infrastructure:"
echo "  - VPC: $VPC_ID ($VPC_CIDR)"
echo "  - Private Subnets:"
echo "      $PRIVATE_SUBNET_A (us-east-1a, $PRIVATE_SUBNET_A_CIDR)"
echo "      $PRIVATE_SUBNET_B (us-east-1c, $PRIVATE_SUBNET_B_CIDR)"
echo "  - Public Subnets:"
echo "      $PUBLIC_SUBNET_A (us-east-1a, $PUBLIC_SUBNET_A_CIDR)"
echo "      $PUBLIC_SUBNET_B (us-east-1c, $PUBLIC_SUBNET_B_CIDR)"
echo "  - Internet Gateway: $IGW_ID"
echo "  - NAT Gateway: $NAT_GW"
echo ""
echo "Created Security Groups:"
echo "  - AgentCore: $SG_AGENTCORE_ID"
echo "  - ALB:       $SG_ALB_ID"
echo "  - Fargate:   $SG_FARGATE_ID"
echo "  - VPC Endpoints: $SG_VPCE_ID"
echo ""
echo "Created VPC Endpoints:"
echo "  - Data Plane: $VPCE_DATA_ID"
echo "  - Gateway:    $VPCE_GATEWAY_ID"
echo ""
echo "Created Load Balancer:"
echo "  - ALB ARN: $ALB_ARN"
echo "  - ALB DNS: $ALB_DNS"
echo "  - Target Group: $TG_ARN"
echo ""
echo "Next Steps:"
echo "  1. Run: python3 create_test_agentcore_runtime.py"
echo "  2. Run: python3 create_test_fargate_task.py"
echo "  3. Run: python3 test_vpc_connectivity.py"
echo ""
echo "To cleanup ALL resources (including VPC), run: ./cleanup_test_vpc_new.sh"
echo "============================================"
