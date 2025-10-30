"""
승인 계층 구조
관리자 레벨별 승인 프로세스를 정의합니다.
"""

from strands import Agent
from strands.models import BedrockModel
from tools.shipping_tools import force_shipping_return
from tools.payment_tools import emergency_refund


# 모델 정의
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
)


# Specialist Level (일반 상담원)
specialist_agent = Agent(
    model=model,
    system_prompt="""당신은 일반 고객 지원 상담원입니다.

권한:
- 일반적인 문의 처리
- 표준 프로세스 수행
- 50,000원 이하 환불 승인

제한:
- 고액 환불 불가 (관리자 승인 필요)
- 정책 예외 불가
- 배송 강제 중지 불가

에스컬레이션 조건:
- 환불 금액 > 50,000원
- 정책 예외 요청
- 복잡한 케이스

항상 한국어로 응답하세요."""
)


# Manager Level (관리자)
manager_agent = Agent(
    model=model,
    tools=[force_shipping_return],
    system_prompt="""당신은 고객 지원 관리자입니다.

권한:
- 고액 환불 승인 (100,000원 이하)
- 배송 강제 중지 승인
- 일부 정책 예외 승인

제한:
- 100,000원 초과 환불 불가 (디렉터 승인 필요)
- 중대한 정책 예외 불가

에스컬레이션 조건:
- 환불 금액 > 100,000원
- 중대한 정책 예외
- 법적 문제 우려

항상 한국어로 응답하세요."""
)


# Director Level (이사)
director_agent = Agent(
    model=model,
    tools=[force_shipping_return, emergency_refund],
    system_prompt="""당신은 고객 서비스 디렉터입니다.

권한:
- 모든 금액 환불 승인
- 긴급 환불 처리
- 모든 정책 예외 승인
- 최종 의사결정

책임:
- 고객 만족도와 회사 이익 균형
- 법적 리스크 관리
- 장기적 고객 관계 고려

항상 한국어로 명확하고 권위있게 응답하세요."""
)


def create_approval_hierarchy():
    """
    승인 계층 구조를 생성합니다.

    Returns:
        dict: 각 레벨의 에이전트를 포함하는 딕셔너리
    """
    return {
        "specialist": specialist_agent,
        "manager": manager_agent,
        "director": director_agent
    }


def determine_escalation_level(context: dict) -> str:
    """
    컨텍스트를 기반으로 필요한 승인 레벨을 결정합니다.

    Args:
        context: 현재 상황 컨텍스트

    Returns:
        str: "specialist", "manager", 또는 "director"
    """
    refund_amount = context.get("refund_amount", 0)
    needs_policy_exception = context.get("needs_policy_exception", False)
    shipping_force_stop = context.get("shipping_force_stop", False)

    # Director level
    if refund_amount > 100000:
        return "director"
    if needs_policy_exception and context.get("policy_severity") == "high":
        return "director"

    # Manager level
    if refund_amount > 50000:
        return "manager"
    if shipping_force_stop:
        return "manager"
    if needs_policy_exception:
        return "manager"

    # Specialist level (default)
    return "specialist"


# 예시: Hierarchical Agent 사용
def handle_with_hierarchy(query: str, context: dict) -> dict:
    """
    계층적 구조를 사용하여 문의를 처리합니다.

    Args:
        query: 고객 문의
        context: 현재 컨텍스트

    Returns:
        dict: 처리 결과
    """
    hierarchy = create_approval_hierarchy()
    required_level = determine_escalation_level(context)

    print(f"[Hierarchy] 필요한 승인 레벨: {required_level}")

    # 해당 레벨의 에이전트 선택
    agent = hierarchy[required_level]

    # 에이전트 실행 (스켈레톤)
    result = {
        "level": required_level,
        "agent": agent,
        "query": query,
        "context": context,
        "note": "실제 구현에서는 agent(query)를 호출합니다"
    }

    return result
