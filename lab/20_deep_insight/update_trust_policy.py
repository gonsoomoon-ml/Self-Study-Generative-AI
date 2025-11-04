#!/usr/bin/env python3
import os
import json
import boto3
from dotenv import load_dotenv

# .env 로드
load_dotenv('production_deployment/.env')

# Role ARN에서 Role 이름 추출
role_arn = os.getenv('TASK_EXECUTION_ROLE_ARN')
role_name = role_arn.split('/')[-1]

print(f"Updating Trust Policy for Role: {role_name}")

# Trust Policy 정의
trust_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        },
        {
            "Sid": "BedrockAgentCoreAssumeRole",
            "Effect": "Allow",
            "Principal": {
                "Service": "bedrock-agentcore.amazonaws.com"
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": "738490718699"
                },
                "ArnLike": {
                    "aws:SourceArn": "arn:aws:bedrock-agentcore:us-east-1:738490718699:*"
                }
            }
        }
    ]
}

# IAM 클라이언트
iam = boto3.client('iam', region_name='us-east-1')

# Trust Policy 업데이트
try:
    iam.update_assume_role_policy(
        RoleName=role_name,
        PolicyDocument=json.dumps(trust_policy)
    )
    print(f"✅ Trust Policy updated successfully for {role_name}")

    # 확인
    response = iam.get_role(RoleName=role_name)
    print("\nUpdated Trust Policy:")
    print(json.dumps(response['Role']['AssumeRolePolicyDocument'], indent=2))
except Exception as e:
    print(f"❌ Error: {e}")
