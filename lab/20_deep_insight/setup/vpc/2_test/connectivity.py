#!/usr/bin/env python3
"""
Test VPC connectivity between AgentCore Runtime and Fargate tasks
"""

import json
import boto3
import requests
import sys
import time

def load_config():
    """Load test VPC configuration"""
    try:
        with open('test_vpc_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: test_vpc_config.json not found!")
        print("Please run ./test_vpc_setup.sh first")
        sys.exit(1)

def test_alb_connectivity(config):
    """Test connectivity to Internal ALB"""

    alb_dns = config['alb']['dns']
    alb_url = f"http://{alb_dns}/health"

    print("Testing connectivity to Internal ALB...")
    print(f"  URL: {alb_url}")
    print()

    try:
        response = requests.get(alb_url, timeout=10)

        if response.status_code == 200:
            print("✅ ALB is reachable!")
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            print()
            return True
        else:
            print(f"⚠️  ALB returned status {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            print()
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot reach ALB: {e}")
        print()
        print("Note: If you're running this from outside the VPC,")
        print("      this is expected! Internal ALB is not accessible from internet.")
        print()
        return False

def check_vpc_endpoints(config):
    """Check VPC Endpoint status"""

    region = config['region']
    vpce_data = config['vpc_endpoints']['data_plane']
    vpce_gateway = config['vpc_endpoints']['gateway']

    client = boto3.client('ec2', region_name=region)

    print("Checking VPC Endpoints status...")
    print()

    try:
        response = client.describe_vpc_endpoints(
            VpcEndpointIds=[vpce_data, vpce_gateway]
        )

        for endpoint in response['VpcEndpoints']:
            endpoint_id = endpoint['VpcEndpointId']
            state = endpoint['State']
            service_name = endpoint['ServiceName']

            print(f"  {endpoint_id}")
            print(f"    Service: {service_name}")
            print(f"    State: {state}")

            if state == 'available':
                print("    Status: ✅ Available")
            else:
                print(f"    Status: ⚠️  Not yet available")

            print()

        return True

    except Exception as e:
        print(f"❌ Error checking VPC endpoints: {e}")
        return False

def check_agentcore_runtime(config):
    """Check AgentCore Runtime status"""

    if 'agentcore_runtime' not in config:
        print("⚠️  AgentCore Runtime not found in config")
        print("   Run: python3 create_test_agentcore_runtime.py")
        print()
        return False

    region = config['region']
    runtime_id = config['agentcore_runtime']['id']

    client = boto3.client('bedrock-agentcore', region_name=region)

    print("Checking AgentCore Runtime status...")
    print(f"  Runtime ID: {runtime_id}")
    print()

    try:
        response = client.get_runtime(runtimeId=runtime_id)

        status = response['status']
        print(f"  Status: {status}")

        if status == 'ACTIVE':
            print("  ✅ Runtime is active!")
        elif status == 'CREATING':
            print("  ⚠️  Runtime is still being created...")
        else:
            print(f"  ⚠️  Runtime status: {status}")

        print()
        return status == 'ACTIVE'

    except Exception as e:
        print(f"❌ Error checking runtime: {e}")
        print()
        return False

def check_fargate_task(config):
    """Check Fargate task status"""

    if 'test_task' not in config:
        print("⚠️  Test task not found in config")
        print("   Run: python3 create_test_fargate_task.py")
        print()
        return False

    region = config['region']
    cluster = 'my-fargate-cluster'
    task_arn = config['test_task']['arn']

    client = boto3.client('ecs', region_name=region)

    print("Checking Fargate task status...")
    print(f"  Task ARN: {task_arn}")
    print()

    try:
        response = client.describe_tasks(
            cluster=cluster,
            tasks=[task_arn]
        )

        if response['tasks']:
            task = response['tasks'][0]
            status = task['lastStatus']
            desired_status = task['desiredStatus']

            print(f"  Last Status: {status}")
            print(f"  Desired Status: {desired_status}")

            if status == 'RUNNING':
                print("  ✅ Task is running!")
            else:
                print(f"  ⚠️  Task status: {status}")

            print()
            return status == 'RUNNING'

        else:
            print("  ❌ Task not found")
            print()
            return False

    except Exception as e:
        print(f"❌ Error checking task: {e}")
        print()
        return False

def check_target_health(config):
    """Check ALB target health"""

    if 'test_task' not in config or 'private_ip' not in config['test_task']:
        print("⚠️  Test task IP not found in config")
        print()
        return False

    region = config['region']
    tg_arn = config['target_group']['arn']
    private_ip = config['test_task']['private_ip']

    client = boto3.client('elbv2', region_name=region)

    print("Checking ALB target health...")
    print(f"  Target IP: {private_ip}")
    print()

    try:
        response = client.describe_target_health(
            TargetGroupArn=tg_arn,
            Targets=[{'Id': private_ip}]
        )

        if response['TargetHealthDescriptions']:
            health = response['TargetHealthDescriptions'][0]['TargetHealth']
            state = health['State']
            reason = health.get('Reason', 'N/A')
            description = health.get('Description', 'N/A')

            print(f"  State: {state}")
            print(f"  Reason: {reason}")
            print(f"  Description: {description}")

            if state == 'healthy':
                print("  ✅ Target is healthy!")
            else:
                print(f"  ⚠️  Target is {state}")

            print()
            return state == 'healthy'

        else:
            print("  ❌ Target not found")
            print()
            return False

    except Exception as e:
        print(f"❌ Error checking target health: {e}")
        print()
        return False

def print_architecture_diagram(config):
    """Print architecture diagram"""

    print()
    print("=" * 60)
    print("Test Architecture")
    print("=" * 60)
    print()
    print("┌─────────────────────────────────────────────────────┐")
    print("│                    VPC (Default)                     │")
    print("│                                                       │")
    print("│  ┌─────────────────────────────────────────┐        │")
    print("│  │ VPC Endpoint (Bedrock AgentCore)        │        │")
    print(f"│  │ {config['vpc_endpoints']['data_plane']:20s}      │        │")
    print("│  └─────────────────────────────────────────┘        │")
    print("│                     │                                 │")
    print("│                     ↓ (Private)                      │")
    print("│  ┌─────────────────────────────────────────┐        │")
    print("│  │ AgentCore Runtime (VPC Mode)            │        │")
    if 'agentcore_runtime' in config:
        print(f"│  │ {config['agentcore_runtime']['id']:20s}      │        │")
    print("│  └─────────────────────────────────────────┘        │")
    print("│                     │                                 │")
    print("│                     ↓ (Private IP)                   │")
    print("│  ┌─────────────────────────────────────────┐        │")
    print("│  │ Internal ALB                            │        │")
    print(f"│  │ {config['alb']['dns'][:30]:30s}    │        │")
    print("│  └─────────────────────────────────────────┘        │")
    print("│                     │                                 │")
    print("│                     ↓ (Private IP)                   │")
    print("│  ┌─────────────────────────────────────────┐        │")
    print("│  │ Fargate Task (dynamic-executor)         │        │")
    if 'test_task' in config and 'private_ip' in config['test_task']:
        print(f"│  │ IP: {config['test_task']['private_ip']:15s}               │        │")
    print("│  └─────────────────────────────────────────┘        │")
    print("│                                                       │")
    print("└─────────────────────────────────────────────────────┘")
    print()

def main():
    print("=" * 60)
    print("Test VPC Private Connectivity")
    print("=" * 60)
    print()

    # Load configuration
    config = load_config()

    # Print architecture
    print_architecture_diagram(config)

    # Run tests
    tests = [
        ("VPC Endpoints", lambda: check_vpc_endpoints(config)),
        ("AgentCore Runtime", lambda: check_agentcore_runtime(config)),
        ("Fargate Task", lambda: check_fargate_task(config)),
        ("Target Health", lambda: check_target_health(config)),
        ("ALB Connectivity", lambda: test_alb_connectivity(config)),
    ]

    results = []
    for name, test_func in tests:
        print(f"Test: {name}")
        print("-" * 60)
        result = test_func()
        results.append((name, result))
        print()

    # Print summary
    print("=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    print()

    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name:30s}: {status}")
        if not result:
            all_passed = False

    print()

    if all_passed:
        print("✅ All tests passed!")
        print()
        print("Your VPC private connectivity is working correctly!")
        print()
        print("Next Steps:")
        print("  - Test with actual AgentCore workflow")
        print("  - Monitor CloudWatch logs")
        print("  - Check for private IP usage in logs")
    else:
        print("⚠️  Some tests failed")
        print()
        print("Common issues:")
        print("  1. VPC Endpoints not yet available (wait a few minutes)")
        print("  2. AgentCore Runtime still creating (check AWS Console)")
        print("  3. Fargate task not healthy (check target group)")
        print("  4. ALB not accessible from outside VPC (this is expected!)")

    print()
    print("To cleanup, run: ./cleanup_test_vpc.sh")
    print("=" * 60)

if __name__ == '__main__':
    main()
