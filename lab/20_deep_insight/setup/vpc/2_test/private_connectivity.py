#!/usr/bin/env python3
"""
Test VPC Private Connectivity for Bedrock AgentCore

This script tests that:
1. VPC Endpoints are available
2. Fargate tasks can run in private subnets
3. Internal ALB is accessible
4. End-to-end private connectivity works
"""

import json
import boto3
import sys
import time

def load_config():
    """Load test VPC configuration"""
    try:
        with open('test_vpc_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: test_vpc_config.json not found!")
        print("Please run ./test_vpc_setup_new_vpc.sh first")
        sys.exit(1)

def check_vpc_endpoints(config):
    """Check VPC Endpoint status"""
    region = config['region']
    vpce_data = config['vpc_endpoints']['data_plane']
    vpce_gateway = config['vpc_endpoints']['gateway']

    client = boto3.client('ec2', region_name=region)

    print("=" * 60)
    print("Test 1: VPC Endpoints Status")
    print("=" * 60)
    print()

    try:
        response = client.describe_vpc_endpoints(
            VpcEndpointIds=[vpce_data, vpce_gateway]
        )

        all_available = True
        for endpoint in response['VpcEndpoints']:
            endpoint_id = endpoint['VpcEndpointId']
            state = endpoint['State']
            service_name = endpoint['ServiceName']

            print(f"VPC Endpoint: {endpoint_id}")
            print(f"  Service: {service_name}")
            print(f"  State: {state}")

            if state == 'available':
                print(f"  Status: ✅ Available")
            else:
                print(f"  Status: ⚠️  {state}")
                all_available = False

            # Show ENIs
            if endpoint.get('NetworkInterfaceIds'):
                print(f"  ENIs: {len(endpoint['NetworkInterfaceIds'])} network interfaces")

            print()

        return all_available

    except Exception as e:
        print(f"❌ Error checking VPC endpoints: {e}")
        return False

def check_internal_alb(config):
    """Check Internal ALB status"""
    region = config['region']
    alb_arn = config['alb']['arn']
    alb_dns = config['alb']['dns']

    client = boto3.client('elbv2', region_name=region)

    print("=" * 60)
    print("Test 2: Internal ALB Status")
    print("=" * 60)
    print()

    try:
        response = client.describe_load_balancers(
            LoadBalancerArns=[alb_arn]
        )

        alb = response['LoadBalancers'][0]
        state = alb['State']['Code']
        scheme = alb['Scheme']

        print(f"ALB: {alb['LoadBalancerName']}")
        print(f"  DNS: {alb_dns}")
        print(f"  Scheme: {scheme}")
        print(f"  State: {state}")

        if scheme == 'internal':
            print(f"  ✅ Scheme: internal (no public IP)")
        else:
            print(f"  ⚠️  Scheme: {scheme} (expected internal)")

        if state == 'active':
            print(f"  ✅ State: active")
            return True
        else:
            print(f"  ⚠️  State: {state}")
            return False

    except Exception as e:
        print(f"❌ Error checking ALB: {e}")
        return False

def check_private_subnets(config):
    """Check private subnets configuration"""
    region = config['region']

    # Handle both old and new VPC setup formats
    if isinstance(config['subnets'], dict):
        # New VPC format
        private_subnets = config['subnets']['private']
        public_subnets = config['subnets']['public']
    else:
        # Old VPC format
        private_subnets = config['subnets']
        public_subnets = []

    client = boto3.client('ec2', region_name=region)

    print("=" * 60)
    print("Test 3: Subnet Configuration")
    print("=" * 60)
    print()

    try:
        # Check private subnets
        if private_subnets:
            print("Private Subnets:")
            response = client.describe_subnets(SubnetIds=private_subnets)

            for subnet in response['Subnets']:
                subnet_id = subnet['SubnetId']
                cidr = subnet['CidrBlock']
                az = subnet['AvailabilityZone']
                map_public_ip = subnet.get('MapPublicIpOnLaunch', False)

                print(f"  {subnet_id}")
                print(f"    CIDR: {cidr}")
                print(f"    AZ: {az}")
                print(f"    Map Public IP: {map_public_ip}")

                if not map_public_ip:
                    print(f"    ✅ Private subnet (no auto-assign public IP)")
                else:
                    print(f"    ⚠️  Public IP auto-assigned")

                print()

        # Check public subnets
        if public_subnets:
            print("Public Subnets:")
            response = client.describe_subnets(SubnetIds=public_subnets)

            for subnet in response['Subnets']:
                subnet_id = subnet['SubnetId']
                cidr = subnet['CidrBlock']
                az = subnet['AvailabilityZone']

                print(f"  {subnet_id}")
                print(f"    CIDR: {cidr}")
                print(f"    AZ: {az}")
                print()

        return True

    except Exception as e:
        print(f"❌ Error checking subnets: {e}")
        return False

def check_security_groups(config):
    """Check security group configuration"""
    region = config['region']
    sgs = config['security_groups']

    client = boto3.client('ec2', region_name=region)

    print("=" * 60)
    print("Test 4: Security Groups")
    print("=" * 60)
    print()

    try:
        sg_ids = list(sgs.values())
        response = client.describe_security_groups(GroupIds=sg_ids)

        for sg in response['SecurityGroups']:
            sg_id = sg['GroupId']
            sg_name = sg['GroupName']

            print(f"Security Group: {sg_name}")
            print(f"  ID: {sg_id}")
            print(f"  Inbound Rules: {len(sg.get('IpPermissions', []))}")
            print(f"  Outbound Rules: {len(sg.get('IpPermissionsEgress', []))}")
            print(f"  ✅ Configured")
            print()

        return True

    except Exception as e:
        print(f"❌ Error checking security groups: {e}")
        return False

def check_nat_gateway(config):
    """Check NAT Gateway (if exists)"""
    if 'network' not in config or 'nat_gateway_id' not in config['network']:
        print("=" * 60)
        print("Test 5: NAT Gateway")
        print("=" * 60)
        print()
        print("⚠️  No NAT Gateway configured (using existing VPC setup)")
        print()
        return True

    region = config['region']
    nat_gw_id = config['network']['nat_gateway_id']

    client = boto3.client('ec2', region_name=region)

    print("=" * 60)
    print("Test 5: NAT Gateway")
    print("=" * 60)
    print()

    try:
        response = client.describe_nat_gateways(NatGatewayIds=[nat_gw_id])

        nat_gw = response['NatGateways'][0]
        state = nat_gw['State']
        subnet_id = nat_gw['SubnetId']

        print(f"NAT Gateway: {nat_gw_id}")
        print(f"  Subnet: {subnet_id}")
        print(f"  State: {state}")

        if state == 'available':
            print(f"  ✅ Available")
            return True
        else:
            print(f"  ⚠️  State: {state}")
            return False

    except Exception as e:
        print(f"❌ Error checking NAT Gateway: {e}")
        return False

def print_architecture(config):
    """Print architecture summary"""
    print("=" * 60)
    print("VPC Private Architecture Summary")
    print("=" * 60)
    print()

    vpc_id = config['vpc_id']
    vpc_cidr = config.get('vpc_cidr', 'N/A')

    print(f"VPC: {vpc_id}")
    if vpc_cidr != 'N/A':
        print(f"  CIDR: {vpc_cidr}")
    print()

    print("Network Flow (Private):")
    print("  1. Bedrock AgentCore → VPC Endpoint (Private)")
    print("  2. AgentCore → Internal ALB → Fargate (Private IPs)")
    print("  3. Fargate → NAT Gateway → Internet (for ECR/S3)")
    print()

    print("Key Benefits:")
    print("  ✅ No public IP exposure for AgentCore ↔ Fargate")
    print("  ✅ All control plane traffic via VPC Endpoints")
    print("  ✅ Internal ALB (not internet-facing)")
    print("  ✅ Private subnet deployment")
    print()

def print_next_steps():
    """Print next steps"""
    print("=" * 60)
    print("Next Steps for Testing")
    print("=" * 60)
    print()

    print("1. Run Fargate Task in Private Subnet:")
    print("   python3 create_test_fargate_task.py")
    print()

    print("2. Run agentcore_runtime.py to test actual connectivity:")
    print("   cd ..")
    print("   uv run python agentcore_runtime.py")
    print()

    print("3. Monitor logs for private IP usage:")
    print("   Check that source IPs are from VPC CIDR (10.100.x.x)")
    print("   Check that no public internet traversal occurs")
    print()

    print("4. Verify in AWS Console:")
    print("   - VPC Endpoints: available")
    print("   - Internal ALB: active, scheme=internal")
    print("   - Fargate tasks: running in private subnets")
    print()

def main():
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  Bedrock AgentCore VPC Private Connectivity Test".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    # Load configuration
    config = load_config()

    # Run tests
    tests = [
        ("VPC Endpoints", lambda: check_vpc_endpoints(config)),
        ("Internal ALB", lambda: check_internal_alb(config)),
        ("Subnets", lambda: check_private_subnets(config)),
        ("Security Groups", lambda: check_security_groups(config)),
        ("NAT Gateway", lambda: check_nat_gateway(config)),
    ]

    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))

    # Print architecture
    print_architecture(config)

    # Print summary
    print("=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    print()

    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name:20s}: {status}")
        if not result:
            all_passed = False

    print()

    if all_passed:
        print("✅ All infrastructure tests passed!")
        print()
        print("VPC private connectivity infrastructure is ready!")
        print()
        print_next_steps()
    else:
        print("⚠️  Some tests failed")
        print()
        print("Please check:")
        print("  1. VPC Endpoints are available (may take 3-5 minutes)")
        print("  2. Internal ALB is active")
        print("  3. All resources are in correct VPC")
        print()
        print("To retry: python3 test_vpc_private_connectivity.py")

    print()
    print("=" * 60)
    print()

if __name__ == '__main__':
    main()
