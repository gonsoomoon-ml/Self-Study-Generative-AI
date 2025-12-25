"""
Gateway 유틸리티 모듈

Amazon Bedrock AgentCore Gateway 설정 및 관리 함수를 제공합니다.
"""

import time
from typing import Dict, Any, Optional

from botocore.exceptions import ClientError


def get_gateway_details(gateway_control_client, gateway_id: str) -> Dict[str, Any]:
    """
    Gateway의 현재 상세 정보를 조회합니다.

    Args:
        gateway_control_client: bedrock-agentcore-control boto3 클라이언트
        gateway_id: Gateway ID

    Returns:
        Gateway 상세 정보 딕셔너리
    """
    return gateway_control_client.get_gateway(gatewayIdentifier=gateway_id)


def wait_for_gateway_ready(
    gateway_control_client,
    gateway_id: str,
    max_wait: int = 300,
    poll_interval: int = 5
) -> bool:
    """
    Gateway가 READY 상태가 될 때까지 대기합니다.

    Args:
        gateway_control_client: bedrock-agentcore-control boto3 클라이언트
        gateway_id: Gateway ID
        max_wait: 최대 대기 시간 (초)
        poll_interval: 상태 확인 간격 (초)

    Returns:
        READY 상태 도달 여부
    """
    terminal_states = {"READY", "FAILED", "UPDATE_UNSUCCESSFUL"}
    start_time = time.time()

    while time.time() - start_time < max_wait:
        gateway = get_gateway_details(gateway_control_client, gateway_id)
        status = gateway.get("status", "UNKNOWN")
        print(f"  Gateway 상태: {status}")

        if status == "READY":
            return True
        if status in terminal_states:
            print(f"  ✗ Gateway가 종료 상태에 도달: {status}")
            return False

        time.sleep(poll_interval)

    print("  ✗ Gateway 대기 시간 초과")
    return False


def validate_and_fix_gateway_authorizer(
    gateway_control_client,
    gateway_id: str,
    region: str,
    user_pool_id: str,
    client_id: str,
    scope: str = ""
) -> bool:
    """
    Gateway Authorizer 설정을 검증하고 필요시 수정합니다.

    Cognito Access Token에는 'aud' 클레임이 없으므로,
    allowedAudience를 설정하면 유효한 토큰도 거부됩니다.

    Args:
        gateway_control_client: bedrock-agentcore-control boto3 클라이언트
        gateway_id: Gateway ID
        region: AWS 리전
        user_pool_id: Cognito User Pool ID
        client_id: Cognito App Client ID
        scope: OAuth2 scope (선택사항)

    Returns:
        설정이 유효하거나 수정에 성공한 경우 True
    """
    print("\nGateway Authorizer 설정 검증")
    print("=" * 70)

    gw = get_gateway_details(gateway_control_client, gateway_id)
    jwt_config = gw.get("authorizerConfiguration", {}).get("customJWTAuthorizer", {})

    # 현재 설정 확인
    discovery_url = jwt_config.get("discoveryUrl")
    allowed_clients = jwt_config.get("allowedClients", [])
    allowed_audience = jwt_config.get("allowedAudience", [])
    allowed_scopes = jwt_config.get("allowedScopes", [])

    print(f"  Discovery URL: {discovery_url or '설정 안 됨'}")
    print(f"  Allowed Clients: {allowed_clients}")
    print(f"  Allowed Audience: {allowed_audience}")
    print(f"  Allowed Scopes: {allowed_scopes}")

    # 예상 Discovery URL 생성
    expected_discovery_url = (
        f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
        f"/.well-known/openid-configuration"
    )

    # 수정이 필요한지 확인
    needs_fix = False
    reasons = []

    if not discovery_url:
        needs_fix = True
        reasons.append("Discovery URL이 설정되지 않음")
    elif discovery_url != expected_discovery_url:
        needs_fix = True
        reasons.append("Discovery URL 불일치")

    if client_id not in allowed_clients:
        needs_fix = True
        reasons.append(f"Client ID {client_id}가 허용 목록에 없음")

    # Cognito Access Token에는 'aud' 클레임이 없음 - allowedAudience는 비어있어야 함
    if allowed_audience:
        needs_fix = True
        reasons.append("allowedAudience가 설정됨 (Cognito Access Token에는 'aud' 클레임 없음)")

    if not needs_fix:
        print("\n✓ Gateway Authorizer 설정이 유효합니다")
        return True

    print("\n⚠️  설정 수정 필요:")
    for reason in reasons:
        print(f"   - {reason}")

    # 설정 수정
    print("\n⏳ Gateway Authorizer 설정 업데이트 중...")

    new_auth_config = {
        "customJWTAuthorizer": {
            "discoveryUrl": expected_discovery_url,
            "allowedClients": [client_id],
            # allowedAudience는 설정하지 않음 - Cognito Access Token에는 'aud' 클레임이 없음
        }
    }

    # scope가 설정된 경우 추가
    if scope:
        new_auth_config["customJWTAuthorizer"]["allowedScopes"] = [scope]

    try:
        gateway_control_client.update_gateway(
            gatewayIdentifier=gateway_id,
            name=gw.get("name"),
            roleArn=gw.get("roleArn"),
            protocolType=gw.get("protocolType", "MCP"),
            authorizerType="CUSTOM_JWT",
            authorizerConfiguration=new_auth_config,
            policyEngineConfiguration=gw.get("policyEngineConfiguration", {}),
        )

        print("\n⏳ Gateway가 READY 상태가 될 때까지 대기 중...")
        if wait_for_gateway_ready(gateway_control_client, gateway_id):
            print("\n✓ Gateway Authorizer 설정이 성공적으로 수정되었습니다")
            return True
        else:
            print("\n✗ Gateway가 READY 상태에 도달하지 못했습니다")
            return False

    except ClientError as e:
        print(f"\n✗ Gateway 업데이트 오류: {e}")
        return False


def attach_policy_engine_to_gateway(
    gateway_control_client,
    gateway_id: str,
    policy_engine_arn: str,
    mode: str = "ENFORCE"
) -> bool:
    """
    Policy Engine을 Gateway에 연결합니다.

    Args:
        gateway_control_client: bedrock-agentcore-control boto3 클라이언트
        gateway_id: Gateway ID
        policy_engine_arn: Policy Engine ARN
        mode: 정책 모드 ('LOG_ONLY' 또는 'ENFORCE')

    Returns:
        연결 성공 여부
    """
    print("\nPolicy Engine을 Gateway에 연결")
    print("=" * 70)

    # 현재 Gateway 설정 조회
    gateway_config = get_gateway_details(gateway_control_client, gateway_id)

    # 이미 연결되어 있는지 확인
    existing_pe = gateway_config.get("policyEngineConfiguration", {})
    if existing_pe.get("arn"):
        print(f"✓ Policy Engine이 이미 연결됨: {existing_pe.get('arn')}")
        print(f"  모드: {existing_pe.get('mode', 'N/A')}")
        return True

    print(f"  Policy Engine ARN: {policy_engine_arn}")
    print(f"  모드: {mode}")

    try:
        gateway_control_client.update_gateway(
            gatewayIdentifier=gateway_id,
            name=gateway_config.get("name"),
            roleArn=gateway_config.get("roleArn"),
            protocolType=gateway_config.get("protocolType", "MCP"),
            authorizerType=gateway_config.get("authorizerType", "CUSTOM_JWT"),
            authorizerConfiguration=gateway_config.get("authorizerConfiguration"),
            policyEngineConfiguration={"arn": policy_engine_arn, "mode": mode},
        )

        print("✓ Gateway 업데이트 요청 완료")
        print("\n⏳ Gateway가 READY 상태가 될 때까지 대기 중...")

        if wait_for_gateway_ready(gateway_control_client, gateway_id):
            print("✓ Policy Engine이 성공적으로 연결되었습니다")
            return True
        else:
            print("✗ Gateway가 READY 상태에 도달하지 못했습니다")
            return False

    except ClientError as e:
        print(f"✗ Gateway 업데이트 오류: {e}")
        return False
