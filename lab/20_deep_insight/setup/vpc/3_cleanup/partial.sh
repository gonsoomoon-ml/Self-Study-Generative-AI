#!/bin/bash
#
# Emergency cleanup for partially created VPC resources
# Use this when test_vpc_setup_new_vpc.sh fails midway
#

set +e  # Don't exit on errors

REGION="us-east-1"

echo "============================================"
echo "Emergency Cleanup - Partial VPC Resources"
echo "============================================"
echo ""
echo "This will delete all resources tagged with:"
echo "  Purpose=vpc-private-connectivity-test"
echo ""

read -p "Continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "Finding and deleting resources by tags..."
echo ""

# Find VPC
VPC_ID=$(aws ec2 describe-vpcs \
  --region $REGION \
  --filters 'Name=tag:Purpose,Values=vpc-private-connectivity-test' \
  --query 'Vpcs[0].VpcId' --output text)

if [ "$VPC_ID" = "None" ] || [ -z "$VPC_ID" ]; then
    echo "No test VPC found. Nothing to clean up."
    exit 0
fi

echo "Found test VPC: $VPC_ID"
echo ""

# 1. Delete VPC Endpoints
echo "1. Deleting VPC Endpoints..."
VPCE_IDS=$(aws ec2 describe-vpc-endpoints \
  --region $REGION \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'VpcEndpoints[*].VpcEndpointId' --output text)

if [ -n "$VPCE_IDS" ]; then
    for VPCE_ID in $VPCE_IDS; do
        echo "  Deleting: $VPCE_ID"
        aws ec2 delete-vpc-endpoints --region $REGION --vpc-endpoint-ids $VPCE_ID > /dev/null 2>&1
    done
    echo "  Waiting for VPC Endpoints to be deleted..."
    sleep 15
fi

# 2. Delete NAT Gateway
echo ""
echo "2. Deleting NAT Gateways..."
NAT_IDS=$(aws ec2 describe-nat-gateways \
  --region $REGION \
  --filter "Name=vpc-id,Values=$VPC_ID" "Name=state,Values=available,pending" \
  --query 'NatGateways[*].NatGatewayId' --output text)

if [ -n "$NAT_IDS" ]; then
    for NAT_ID in $NAT_IDS; do
        echo "  Deleting: $NAT_ID"
        aws ec2 delete-nat-gateway --region $REGION --nat-gateway-id $NAT_ID > /dev/null 2>&1
    done
    echo "  Waiting for NAT Gateways to be deleted (this may take 2-3 minutes)..."
    sleep 60
fi

# 3. Release Elastic IPs
echo ""
echo "3. Releasing Elastic IPs..."
EIP_ALLOCS=$(aws ec2 describe-addresses \
  --region $REGION \
  --filters 'Name=tag:Purpose,Values=vpc-private-connectivity-test' \
  --query 'Addresses[*].AllocationId' --output text)

if [ -n "$EIP_ALLOCS" ]; then
    for EIP_ALLOC in $EIP_ALLOCS; do
        echo "  Releasing: $EIP_ALLOC"
        aws ec2 release-address --region $REGION --allocation-id $EIP_ALLOC > /dev/null 2>&1 || echo "    Already released"
    done
fi

# 4. Detach and delete Internet Gateway
echo ""
echo "4. Detaching and deleting Internet Gateway..."
IGW_ID=$(aws ec2 describe-internet-gateways \
  --region $REGION \
  --filters "Name=attachment.vpc-id,Values=$VPC_ID" \
  --query 'InternetGateways[0].InternetGatewayId' --output text)

if [ -n "$IGW_ID" ] && [ "$IGW_ID" != "None" ]; then
    echo "  Detaching: $IGW_ID"
    aws ec2 detach-internet-gateway \
      --region $REGION \
      --internet-gateway-id $IGW_ID \
      --vpc-id $VPC_ID > /dev/null 2>&1

    echo "  Deleting: $IGW_ID"
    aws ec2 delete-internet-gateway \
      --region $REGION \
      --internet-gateway-id $IGW_ID > /dev/null 2>&1
fi

# 5. Delete Route Tables (non-main)
echo ""
echo "5. Deleting Route Tables..."
RT_IDS=$(aws ec2 describe-route-tables \
  --region $REGION \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'RouteTables[?Associations[0].Main==`false`].RouteTableId' --output text)

if [ -n "$RT_IDS" ]; then
    for RT_ID in $RT_IDS; do
        # Disassociate first
        ASSOCS=$(aws ec2 describe-route-tables \
          --region $REGION \
          --route-table-ids $RT_ID \
          --query 'RouteTables[0].Associations[?!Main].RouteTableAssociationId' --output text)

        for ASSOC in $ASSOCS; do
            echo "  Disassociating: $ASSOC"
            aws ec2 disassociate-route-table \
              --region $REGION \
              --association-id $ASSOC > /dev/null 2>&1
        done

        echo "  Deleting: $RT_ID"
        aws ec2 delete-route-table \
          --region $REGION \
          --route-table-id $RT_ID > /dev/null 2>&1
    done
fi

# 6. Delete Security Groups (wait for dependencies)
echo ""
echo "6. Deleting Security Groups..."
echo "  Waiting for ENI dependencies..."
sleep 20

SG_IDS=$(aws ec2 describe-security-groups \
  --region $REGION \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'SecurityGroups[?GroupName!=`default`].GroupId' --output text)

if [ -n "$SG_IDS" ]; then
    for SG_ID in $SG_IDS; do
        echo "  Deleting: $SG_ID"
        aws ec2 delete-security-group \
          --region $REGION \
          --group-id $SG_ID > /dev/null 2>&1 || echo "    Skipped (has dependencies)"
    done

    # Retry after additional wait
    sleep 20
    echo "  Retrying security group deletion..."
    for SG_ID in $SG_IDS; do
        aws ec2 delete-security-group \
          --region $REGION \
          --group-id $SG_ID > /dev/null 2>&1 && echo "    Deleted: $SG_ID" || true
    done
fi

# 7. Delete Subnets
echo ""
echo "7. Deleting Subnets..."
SUBNET_IDS=$(aws ec2 describe-subnets \
  --region $REGION \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[*].SubnetId' --output text)

if [ -n "$SUBNET_IDS" ]; then
    for SUBNET_ID in $SUBNET_IDS; do
        echo "  Deleting: $SUBNET_ID"
        aws ec2 delete-subnet \
          --region $REGION \
          --subnet-id $SUBNET_ID > /dev/null 2>&1 || echo "    Failed (has dependencies)"
    done
fi

# 8. Delete VPC
echo ""
echo "8. Deleting VPC..."
sleep 5
aws ec2 delete-vpc \
  --region $REGION \
  --vpc-id $VPC_ID > /dev/null 2>&1 && echo "  ✅ VPC deleted: $VPC_ID" || echo "  ⚠️  VPC still has dependencies"

echo ""
echo "============================================"
echo "Emergency Cleanup Complete!"
echo "============================================"
echo ""
echo "If you see warnings about dependencies:"
echo "  1. Wait 5 minutes for AWS to release resources"
echo "  2. Run this script again: ./cleanup_partial_vpc.sh"
echo ""
echo "Or manually check AWS Console:"
echo "  VPC ID: $VPC_ID"
echo ""
echo "Once cleanup is complete, run:"
echo "  ./test_vpc_setup_new_vpc.sh"
echo "============================================"
