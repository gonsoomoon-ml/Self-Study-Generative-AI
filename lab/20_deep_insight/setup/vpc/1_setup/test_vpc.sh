#!/bin/bash
#
# Bedrock AgentCore VPC Private Connectivity Test Environment Setup
#
# This script creates a test environment without affecting production
# All resources are tagged with "test-vpc-private"
#

set -e

# Configuration
REGION="us-east-1"
VPC_ID="vpc-ff5e1585"  # Default VPC
SUBNET1="subnet-926366bc"  # us-east-1a
SUBNET2="subnet-ea95adb6"  # us-east-1c
ACCOUNT_ID="057716757052"
CLUSTER_NAME="my-fargate-cluster"

# Test resource names (with -test suffix)
TEST_PREFIX="test-vpc-private"
SG_AGENTCORE_NAME="${TEST_PREFIX}-agentcore-sg"
SG_ALB_NAME="${TEST_PREFIX}-alb-sg"
SG_FARGATE_NAME="${TEST_PREFIX}-fargate-sg"
ALB_NAME="${TEST_PREFIX}-alb"
TARGET_GROUP_NAME="${TEST_PREFIX}-tg"
TASK_DEF_NAME="${TEST_PREFIX}-task"

echo "============================================"
echo "Bedrock AgentCore VPC Test Environment Setup"
echo "============================================"
echo ""
echo "Region: $REGION"
echo "VPC: $VPC_ID"
echo "Subnets: $SUBNET1, $SUBNET2"
echo "Test Prefix: $TEST_PREFIX"
echo ""

# Step 1: Create Security Groups
echo "Step 1: Creating Security Groups..."

# 1.1 AgentCore Runtime Security Group
echo "  Creating AgentCore Runtime SG..."
SG_AGENTCORE_ID=$(aws ec2 create-security-group \
  --region $REGION \
  --group-name $SG_AGENTCORE_NAME \
  --description "Test: AgentCore Runtime - allows outbound to ALB" \
  --vpc-id $VPC_ID \
  --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=$SG_AGENTCORE_NAME},{Key=Environment,Value=test},{Key=Purpose,Value=vpc-private-connectivity-test}]" \
  --query 'GroupId' --output text)

echo "  Created: $SG_AGENTCORE_ID"

# 1.2 Internal ALB Security Group
echo "  Creating Internal ALB SG..."
SG_ALB_ID=$(aws ec2 create-security-group \
  --region $REGION \
  --group-name $SG_ALB_NAME \
  --description "Test: Internal ALB - allows inbound from AgentCore" \
  --vpc-id $VPC_ID \
  --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=$SG_ALB_NAME},{Key=Environment,Value=test},{Key=Purpose,Value=vpc-private-connectivity-test}]" \
  --query 'GroupId' --output text)

echo "  Created: $SG_ALB_ID"

# 1.3 Fargate Container Security Group
echo "  Creating Fargate Container SG..."
SG_FARGATE_ID=$(aws ec2 create-security-group \
  --region $REGION \
  --group-name $SG_FARGATE_NAME \
  --description "Test: Fargate containers - allows inbound from ALB" \
  --vpc-id $VPC_ID \
  --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=$SG_FARGATE_NAME},{Key=Environment,Value=test},{Key=Purpose,Value=vpc-private-connectivity-test}]" \
  --query 'GroupId' --output text)

echo "  Created: $SG_FARGATE_ID"

# Step 2: Configure Security Group Rules
echo ""
echo "Step 2: Configuring Security Group Rules..."

# 2.1 AgentCore -> ALB (HTTP)
echo "  AgentCore -> ALB (HTTP:80)..."
aws ec2 authorize-security-group-egress \
  --region $REGION \
  --group-id $SG_AGENTCORE_ID \
  --protocol tcp \
  --port 80 \
  --source-group $SG_ALB_ID \
  > /dev/null

# 2.2 ALB <- AgentCore (HTTP)
echo "  ALB <- AgentCore (HTTP:80)..."
aws ec2 authorize-security-group-ingress \
  --region $REGION \
  --group-id $SG_ALB_ID \
  --protocol tcp \
  --port 80 \
  --source-group $SG_AGENTCORE_ID \
  > /dev/null

# 2.3 ALB -> Fargate (HTTP:8080)
echo "  ALB -> Fargate (HTTP:8080)..."
aws ec2 authorize-security-group-egress \
  --region $REGION \
  --group-id $SG_ALB_ID \
  --protocol tcp \
  --port 8080 \
  --source-group $SG_FARGATE_ID \
  > /dev/null

# 2.4 Fargate <- ALB (HTTP:8080)
echo "  Fargate <- ALB (HTTP:8080)..."
aws ec2 authorize-security-group-ingress \
  --region $REGION \
  --group-id $SG_FARGATE_ID \
  --protocol tcp \
  --port 8080 \
  --source-group $SG_ALB_ID \
  > /dev/null

# 2.5 Fargate -> Internet (for downloads, S3, etc.)
echo "  Fargate -> Internet (for S3, ECR, etc.)..."
aws ec2 authorize-security-group-egress \
  --region $REGION \
  --group-id $SG_FARGATE_ID \
  --protocol -1 \
  --cidr 0.0.0.0/0 \
  > /dev/null 2>&1 || echo "  (default rule already exists)"

# Step 3: Create VPC Endpoints (Bedrock AgentCore)
echo ""
echo "Step 3: Creating VPC Endpoints for Bedrock AgentCore..."

# 3.1 Data Plane VPC Endpoint
echo "  Creating Data Plane VPC Endpoint..."
VPCE_DATA_ID=$(aws ec2 create-vpc-endpoint \
  --region $REGION \
  --vpc-id $VPC_ID \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.$REGION.bedrock-agentcore \
  --subnet-ids $SUBNET1 $SUBNET2 \
  --security-group-ids $SG_AGENTCORE_ID \
  --private-dns-enabled \
  --tag-specifications "ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=${TEST_PREFIX}-bedrock-data},{Key=Environment,Value=test},{Key=Purpose,Value=vpc-private-connectivity-test}]" \
  --query 'VpcEndpoint.VpcEndpointId' --output text)

echo "  Created: $VPCE_DATA_ID"

# 3.2 Gateway VPC Endpoint
echo "  Creating Gateway VPC Endpoint..."
VPCE_GATEWAY_ID=$(aws ec2 create-vpc-endpoint \
  --region $REGION \
  --vpc-id $VPC_ID \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.$REGION.bedrock-agentcore.gateway \
  --subnet-ids $SUBNET1 $SUBNET2 \
  --security-group-ids $SG_AGENTCORE_ID \
  --private-dns-enabled \
  --tag-specifications "ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=${TEST_PREFIX}-bedrock-gateway},{Key=Environment,Value=test},{Key=Purpose,Value=vpc-private-connectivity-test}]" \
  --query 'VpcEndpoint.VpcEndpointId' --output text)

echo "  Created: $VPCE_GATEWAY_ID"

# Wait for VPC Endpoints to become available
echo "  Waiting for VPC Endpoints to become available..."
aws ec2 wait vpc-endpoint-available --region $REGION --vpc-endpoint-ids $VPCE_DATA_ID $VPCE_GATEWAY_ID
echo "  VPC Endpoints are now available!"

# Step 4: Create Internal ALB
echo ""
echo "Step 4: Creating Internal Application Load Balancer..."

ALB_ARN=$(aws elbv2 create-load-balancer \
  --region $REGION \
  --name $ALB_NAME \
  --type application \
  --scheme internal \
  --subnets $SUBNET1 $SUBNET2 \
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

# Step 5: Create Target Group
echo ""
echo "Step 5: Creating Target Group..."

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

# Step 6: Create ALB Listener
echo ""
echo "Step 6: Creating ALB Listener..."

LISTENER_ARN=$(aws elbv2 create-listener \
  --region $REGION \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN \
  --query 'Listeners[0].ListenerArn' --output text)

echo "  Created: $LISTENER_ARN"

# Step 7: Enable Sticky Sessions
echo ""
echo "Step 7: Configuring Sticky Sessions..."

aws elbv2 modify-target-group-attributes \
  --region $REGION \
  --target-group-arn $TG_ARN \
  --attributes \
    Key=stickiness.enabled,Value=true \
    Key=stickiness.type,Value=lb_cookie \
    Key=stickiness.lb_cookie.duration_seconds,Value=86400 \
  > /dev/null

echo "  Sticky sessions enabled (24 hours)"

# Step 8: Save configuration to file
echo ""
echo "Step 8: Saving configuration..."

cat > test_vpc_config.json <<EOF
{
  "region": "$REGION",
  "vpc_id": "$VPC_ID",
  "subnets": ["$SUBNET1", "$SUBNET2"],
  "security_groups": {
    "agentcore": "$SG_AGENTCORE_ID",
    "alb": "$SG_ALB_ID",
    "fargate": "$SG_FARGATE_ID"
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
echo "Created Resources:"
echo "  - Security Groups:"
echo "      AgentCore: $SG_AGENTCORE_ID"
echo "      ALB:       $SG_ALB_ID"
echo "      Fargate:   $SG_FARGATE_ID"
echo ""
echo "  - VPC Endpoints:"
echo "      Data Plane: $VPCE_DATA_ID"
echo "      Gateway:    $VPCE_GATEWAY_ID"
echo ""
echo "  - Internal ALB:"
echo "      ARN: $ALB_ARN"
echo "      DNS: $ALB_DNS"
echo ""
echo "  - Target Group:"
echo "      ARN: $TG_ARN"
echo "      Name: $TARGET_GROUP_NAME"
echo ""
echo "Next Steps:"
echo "  1. Run: python3 create_test_agentcore_runtime.py"
echo "  2. Run: python3 create_test_fargate_task.py"
echo "  3. Run: python3 test_vpc_connectivity.py"
echo ""
echo "To cleanup, run: ./cleanup_test_vpc.sh"
echo "============================================"
