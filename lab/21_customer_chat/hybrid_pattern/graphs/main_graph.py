"""
메인 그래프 (Proof of Concept)
전체 고객 지원 시스템의 메인 워크플로우를 정의합니다.
"""

from agents.classifier_agent import classify_query
from graphs.order_graph import execute_order_graph
from graphs.return_graph import execute_return_graph


async def execute_customer_support(query: str) -> dict:
    """
    고객 지원 메인 그래프를 실행합니다 (간단한 PoC).

    흐름:
    1. 분류 에이전트로 문의 분류
    2. 분류 결과에 따라 적절한 서브그래프로 라우팅
    3. 서브그래프 실행 (주문 그래프 또는 반품 그래프)
    4. 최종 응답 생성
    """
    print(f"\n{'='*80}")
    print(f"[메인 그래프] 고객 문의 처리 시작")
    print(f"문의: {query}")
    print(f"{'='*80}\n")

    # Step 1: 분류 에이전트 호출
    print(f"[단계 1] 분류 에이전트 호출")
    classification = classify_query(query)
    category = classification.get("category", "주문")
    print(f"[단계 1] 분류 결과: {category}")

    # Step 2: 라우팅
    print(f"\n[단계 2] 서브 그래프 라우팅")
    if category in ["주문", "배송", "취소"]:
        target_graph = "주문_그래프"
        target_func = execute_order_graph
    elif category in ["반품", "환불", "교환"]:
        target_graph = "반품_그래프"
        target_func = execute_return_graph
    else:
        target_graph = "주문_그래프"  # 기본값
        target_func = execute_order_graph

    print(f"[단계 2] 라우팅 대상: {target_graph}")

    # Step 3: 서브 그래프 실행
    print(f"\n[단계 3] 서브 그래프 실행 중...")
    result = await target_func(query)

    # Step 4: 최종 응답 생성
    print(f"\n[단계 4] 최종 응답 생성")
    final_response = {
        "문의": query,
        "카테고리": category,
        "사용된_그래프": target_graph,
        "상태": "완료",
        "메시지": "고객 문의가 성공적으로 처리되었습니다."
    }

    print(f"\n{'='*80}")
    print(f"[메인 그래프] 처리 완료")
    print(f"{'='*80}\n")

    return final_response
