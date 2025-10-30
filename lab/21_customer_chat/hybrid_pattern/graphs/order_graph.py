"""
주문/배송 서브 그래프 (Proof of Concept)
주문 취소, 배송 추적 등의 워크플로우를 정의합니다.
"""

from agents.orders_agent import orders_agent
from agents.shipping_agent import shipping_agent
from hierarchies.approval_hierarchy import determine_escalation_level


async def execute_order_graph(query: str, initial_context: dict = None) -> dict:
    """
    주문 그래프를 실행합니다 (간단한 PoC).

    흐름:
    1. 주문 에이전트로 상태 확인
    2. 배송이 시작되었으면 배송 에이전트 호출
    3. 필요시 계층적 승인
    """
    print(f"\n{'='*60}")
    print(f"[주문 그래프] 실행 시작")
    print(f"{'='*60}")

    context = initial_context or {}

    # Step 1: 주문 에이전트로 상태 확인
    print(f"\n[단계 1] 주문 에이전트 호출")
    order_response = orders_agent(query)
    print(f"[단계 1] 주문 에이전트 응답 완료")

    # Step 2: 배송 여부 확인 (간단한 키워드 기반)
    if "배송" in query:
        print(f"\n[단계 2] 배송 관련 문의 -> 배송 에이전트 호출")
        shipping_response = shipping_agent(query)
        print(f"[단계 2] 배송 에이전트 응답 완료")

    # Step 3: 계층적 승인 필요 여부 확인
    refund_amount = 60000  # 예시
    context["refund_amount"] = refund_amount
    required_level = determine_escalation_level(context)

    # 레벨을 한글로 변환
    level_korean = {
        "specialist": "일반 상담원",
        "manager": "관리자",
        "director": "이사"
    }

    if required_level != "specialist":
        print(f"\n[단계 3] 에스컬레이션 필요: {level_korean[required_level]} 레벨")
    else:
        print(f"\n[단계 3] 일반 처리 완료")

    print(f"\n{'='*60}")
    print(f"[주문 그래프] 처리 완료")
    print(f"{'='*60}\n")

    return {
        "그래프": "주문_처리",
        "문의": query,
        "상태": "완료",
        "승인_레벨": level_korean[required_level]
    }
