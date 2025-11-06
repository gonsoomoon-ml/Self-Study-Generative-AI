#!/usr/bin/env python3
"""
Test if environment variables are delivered to AgentCore runtime container

This creates a simple job that prints all environment variables to check
if BEDROCK_MODEL_ID is available in the runtime container.
"""

import os
import json
import time
from dotenv import load_dotenv
import boto3

# Load environment
load_dotenv('.env')

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
RUNTIME_ARN = os.getenv("RUNTIME_ARN")
RUNTIME_ID = os.getenv("RUNTIME_ID")

if not RUNTIME_ARN or not RUNTIME_ID:
    print("❌ RUNTIME_ARN or RUNTIME_ID not found in .env")
    exit(1)

print(f"Testing runtime: {RUNTIME_ID}")
print(f"Expected BEDROCK_MODEL_ID: {os.getenv('BEDROCK_MODEL_ID')}")
print()

# Create a simple job to check environment variables
agentcore = boto3.client('bedrock-agentcore', region_name=AWS_REGION)

# Job input with Python code to print env vars
job_input = {
    "query": "Print the value of BEDROCK_MODEL_ID environment variable"
}

try:
    print("🚀 Creating job to check environment variables...")
    response = agentcore.create_agent_job(
        agentRuntimeId=RUNTIME_ID,
        inputText=json.dumps(job_input),
        sessionId=f"env-test-{int(time.time())}"
    )

    job_id = response['jobId']
    print(f"✅ Job created: {job_id}")
    print()
    print("📝 To see the results, run:")
    print(f"   aws logs tail /aws/bedrock-agentcore/runtimes/{RUNTIME_ID.rsplit('-', 1)[0]}-DEFAULT --follow")
    print()
    print("🔍 Look for:")
    print("   - 'BEDROCK_MODEL_ID' in the logs")
    print("   - Model ID being used by the runtime")

except Exception as e:
    print(f"❌ Error creating job: {e}")
    exit(1)
