"""
반품/환불 서브 그래프 (Proof of Concept)
반품, 교환, 환불 워크플로우를 정의합니다.
"""

from agents.returns_agent import returns_agent
from agents.payment_agent import payment_agent
from hierarchies.approval_hierarchy import determine_escalation_level


async def execute_return_graph(query: str, initial_context: dict = None) -> dict:
    """
    반품 그래프를 실행합니다 (간단한 PoC).

    흐름:
    1. 반품 에이전트로 반품 처리
    2. 결제 에이전트로 환불 처리
    3. 고액 환불시 계층적 승인
    """
    print(f"\n{'='*60}")
    print(f"[반품 그래프] 실행 시작")
    print(f"{'='*60}")

    context = initial_context or {}

    # 레벨을 한글로 변환
    level_korean = {
        "specialist": "일반 상담원",
        "manager": "관리자",
        "director": "이사"
    }

    # Step 1: 반품 에이전트 호출
    print(f"\n[단계 1] 반품 에이전트 호출")
    return_response = returns_agent(query)
    print(f"[단계 1] 반품 에이전트 응답 완료")

    # Step 2: 환불 처리 (환불이 필요한 경우)
    if "환불" in query:
        print(f"\n[단계 2] 환불 관련 문의 -> 결제 에이전트 호출")
        payment_response = payment_agent(query)
        print(f"[단계 2] 결제 에이전트 응답 완료")

        # Step 3: 고액 환불 승인 체크
        refund_amount = 120000  # 예시
        context["refund_amount"] = refund_amount
        required_level = determine_escalation_level(context)

        if required_level != "specialist":
            print(f"\n[단계 3] 고액 환불 -> 에스컬레이션: {level_korean[required_level]} 레벨")
        else:
            print(f"\n[단계 3] 일반 환불 처리 완료")

        escalation_level = level_korean[required_level]
    else:
        print(f"\n[단계 2-3] 환불 없는 반품/교환 처리")
        escalation_level = "일반 상담원"

    print(f"\n{'='*60}")
    print(f"[반품 그래프] 처리 완료")
    print(f"{'='*60}\n")

    return {
        "그래프": "반품_처리",
        "문의": query,
        "상태": "완료",
        "승인_레벨": escalation_level
    }
