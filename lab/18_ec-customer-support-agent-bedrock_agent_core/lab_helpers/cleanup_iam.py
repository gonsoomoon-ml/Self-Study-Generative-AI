"""
IAM Role과 Policy 정리 유틸리티
기존 이커머스 에이전트 관련 IAM 리소스를 삭제합니다.
"""

import boto3
from boto3 import Session
from utils import get_aws_account_id


def cleanup_ecommerce_iam_resources():
    """이커머스 에이전트 관련 IAM 리소스를 정리합니다."""
    iam = boto3.client("iam")
    boto_session = Session()
    region = boto_session.region_name
    account_id = get_aws_account_id()
    
    role_name = f"EcommerceCustomerSupportBedrockAgentCoreRole-{region}"
    policy_name = f"EcommerceCustomerSupportBedrockAgentCorePolicy-{region}"
    policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
    
    print("🧹 이커머스 에이전트 IAM 리소스 정리 중...")
    
    # 1. 정책과 역할 분리
    try:
        iam.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
        print(f"✅ 정책 분리 완료: {policy_name}")
    except Exception as e:
        print(f"⚠️ 정책 분리 실패 (이미 분리됨): {e}")
    
    # 2. 정책 삭제
    try:
        iam.delete_policy(PolicyArn=policy_arn)
        print(f"✅ 정책 삭제 완료: {policy_name}")
    except Exception as e:
        print(f"⚠️ 정책 삭제 실패 (존재하지 않음): {e}")
    
    # 3. 역할 삭제
    try:
        iam.delete_role(RoleName=role_name)
        print(f"✅ 역할 삭제 완료: {role_name}")
    except Exception as e:
        print(f"⚠️ 역할 삭제 실패 (존재하지 않음): {e}")
    
    print("🎉 IAM 리소스 정리 완료!")


if __name__ == "__main__":
    cleanup_ecommerce_iam_resources()