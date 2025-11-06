#!/usr/bin/env python3
"""
Test script to verify global CRI model access
Tests: global.anthropic.claude-sonnet-4-5-20250929-v1:0
"""

import boto3
import json
from datetime import datetime

def test_global_cri_model():
    """Test if global CRI model is accessible"""

    # Model to test
    model_id = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
    region = "us-east-1"

    print("="*70)
    print(f"Testing Global CRI Model Access")
    print("="*70)
    print(f"Model ID: {model_id}")
    print(f"Region: {region}")
    print(f"Time: {datetime.now().isoformat()}")
    print("="*70)

    # Create Bedrock Runtime client
    bedrock_runtime = boto3.client(
        service_name='bedrock-runtime',
        region_name=region
    )

    # Test payload
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 100,
        "messages": [
            {
                "role": "user",
                "content": "Say 'Hello from global CRI model!' in one sentence."
            }
        ]
    }

    try:
        print("\n[1/2] Attempting to invoke model...")

        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )

        print("✅ Model invocation successful!")

        # Parse response
        response_body = json.loads(response['body'].read())

        print("\n[2/2] Response details:")
        print(f"  Stop Reason: {response_body.get('stop_reason', 'N/A')}")
        print(f"  Input Tokens: {response_body.get('usage', {}).get('input_tokens', 'N/A')}")
        print(f"  Output Tokens: {response_body.get('usage', {}).get('output_tokens', 'N/A')}")

        # Extract message content
        content = response_body.get('content', [])
        if content:
            message = content[0].get('text', '')
            print(f"\n📝 Model Response:\n{message}")

        print("\n" + "="*70)
        print("✅ TEST PASSED - Global CRI model is accessible!")
        print("="*70)
        return True

    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ Model invocation failed!")
        print(f"\nError Type: {type(e).__name__}")
        print(f"Error Message: {error_msg}")

        # Check specific error types
        if "ValidationException" in error_msg:
            print("\n💡 Issue: Model ID format validation failed")
            print("   Possible causes:")
            print("   - Model ID doesn't exist")
            print("   - Incorrect format")
        elif "AccessDeniedException" in error_msg:
            print("\n💡 Issue: No access to this model")
            print("   Possible causes:")
            print("   - Model access not granted in this account")
            print("   - Cross-region inference not enabled")
        elif "serviceUnavailableException" in error_msg:
            print("\n💡 Issue: Service unavailable")
            print("   Possible causes:")
            print("   - Model doesn't exist with this ID")
            print("   - Region doesn't support this model")
            print("   - VPC endpoint routing issue")

        print("\n" + "="*70)
        print("❌ TEST FAILED - Global CRI model not accessible")
        print("="*70)
        return False

if __name__ == "__main__":
    test_global_cri_model()
