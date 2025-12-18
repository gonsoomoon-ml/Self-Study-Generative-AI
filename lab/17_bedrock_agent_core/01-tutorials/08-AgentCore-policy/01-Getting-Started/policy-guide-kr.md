# Amazon Bedrock AgentCore Policy 가이드

## 개요

AgentCore Policy는 AI 에이전트와 도구 간의 상호작용에 대한 보안 제어를 정의하고 적용하는 기능입니다. Cedar 언어를 사용하여 선언적으로 정책을 정의합니다.

## 아키텍처

```
┌─────────────┐
│   AI Agent  │
└──────┬──────┘
       │ Tool Call Request
       ▼
┌─────────────────────┐
│  AgentCore Gateway  │
└──────┬──────────────┘
       │ Policy Check
       ▼
┌─────────────────────┐
│   Policy Engine     │
│   (Cedar Policies)  │
└──────┬──────────────┘
       │ ALLOW / DENY
       ▼
┌─────────────────────┐
│   Gateway Targets   │
└─────────────────────┘
```

## 주요 단계

### 1. Policy Engine 생성

```python
from bedrock_agentcore_starter_toolkit.operations.policy.client import PolicyClient

# PolicyClient 초기화 (게이트웨이와 동일한 리전 사용)
policy_client = PolicyClient(region_name="us-east-1")

# Policy Engine 생성
engine = policy_client.create_or_get_policy_engine(
    name="InsurancePolicyEngine",
    description="보험 심사 거버넌스를 위한 정책 엔진",
)
print(f"Policy Engine ID: {engine['policyEngineId']}")
```

### 2. Gateway에 Policy Engine 연결

```python
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient

gateway_client = GatewayClient(region_name="us-east-1")

# Policy Engine을 Gateway에 연결
gateway_client.update_gateway_policy_engine(
    gateway_identifier="your-gateway-id",
    policy_engine_arn=engine["policyEngineArn"],
    mode="ENFORCE",  # "LOG_ONLY" 또는 "ENFORCE"
)
```

**모드 설명:**
- `LOG_ONLY`: 정책을 평가하지만 차단하지 않음 (테스트용)
- `ENFORCE`: 정책을 적극적으로 적용하여 비준수 요청 차단 (운영용)

### 3. Cedar 정책 생성

```python
# Gateway ARN
GATEWAY_ARN = "arn:aws:bedrock-agentcore:us-east-1:123456789012:gateway/your-gateway-id"

# Cedar 정책 정의: 100만 달러 이하의 보험 신청만 허용
cedar_statement = (
    f"permit(principal, "
    f'action == AgentCore::Action::"ApplicationToolTarget___create_application", '
    f'resource == AgentCore::Gateway::"{GATEWAY_ARN}") '
    f"when {{ context.input.coverage_amount <= 1000000 }};"
)

# 정책 생성
policy = policy_client.create_or_get_policy(
    policy_engine_id=engine["policyEngineId"],
    name="create_application_policy",
    description="100만 달러 미만 신청 허용",
    definition={"cedar": {"statement": cedar_statement}},
)
print(f"Policy ID: {policy['policyId']}")
```

## Cedar 정책 문법

### 기본 구조

```cedar
permit(
  principal,                                    // 누가
  action == AgentCore::Action::"도구_액션",      // 무엇을
  resource == AgentCore::Gateway::"게이트웨이"   // 어디서
) when {
  조건                                          // 조건
};
```

### 예제 정책들

**1. 금액 제한 정책**
```cedar
permit(principal,
  action == AgentCore::Action::"ApplicationToolTarget___create_application",
  resource == AgentCore::Gateway::"<GATEWAY_ARN>")
when { context.input.coverage_amount <= 1000000 };
```

**2. 특정 리전만 허용**
```cedar
permit(principal,
  action == AgentCore::Action::"ApplicationToolTarget___create_application",
  resource == AgentCore::Gateway::"<GATEWAY_ARN>")
when { context.input.applicant_region == "US" };
```

**3. 위험 수준 제한**
```cedar
permit(principal,
  action == AgentCore::Action::"ApprovalToolTarget___approve_claim",
  resource == AgentCore::Gateway::"<GATEWAY_ARN>")
when { context.input.risk_level != "critical" };
```

## 정책 테스트

### 테스트 1: 허용 시나리오

```python
from scripts.agent_with_tools import AgentSession

with AgentSession() as session:
    # $750,000 신청 - 정책 허용 (100만 달러 이하)
    response = session.invoke(
        "Create an application for US region with $750,000 coverage"
    )
    print(response)  # 성공
```

### 테스트 2: 거부 시나리오

```python
with AgentSession() as session:
    # $1.5M 신청 - 정책 거부 (100만 달러 초과)
    response = session.invoke(
        "Create an application for US region with $1.5M coverage"
    )
    print(response)  # 거부됨
```

## 주의사항

1. **리전 일치**: Policy Engine과 Gateway는 반드시 동일한 리전에 있어야 합니다
2. **기본 동작**: Policy Engine이 연결되면 기본적으로 모든 도구 접근이 거부됩니다
3. **정책 필수**: 도구를 사용하려면 해당 도구에 대한 permit 정책이 필요합니다

## 리소스 정리

```python
# 정책 엔진 정리
policy_client = PolicyClient(region_name="us-east-1")
policy_client.cleanup_policy_engine(policy_engine_id)

# 게이트웨이 정리
gateway_client = GatewayClient(region_name="us-east-1")
gateway_client.cleanup_gateway(gateway_id, client_info)
```

## 참고 자료

- [Cedar 언어 문서](https://www.cedarpolicy.com/)
- [AWS Bedrock AgentCore 문서](https://docs.aws.amazon.com/bedrock/)
