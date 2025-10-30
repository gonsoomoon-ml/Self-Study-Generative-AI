"""
이커머스 고객 지원 멀티 에이전트 시스템 테스트 스크립트
오케스트레이터가 적절한 서브 에이전트로 문의를 라우팅하는 것을 시연합니다
"""

from orchestrator_agent import handle_customer_query


def test_multi_agent_system():
    """샘플 문의로 멀티 에이전트 아키텍처를 테스트합니다"""

    print("\n" + "="*80)
    print("이커머스 고객 지원 - 멀티 에이전트 시스템")
    print("="*80)

    # 다양한 시나리오를 위한 테스트 문의
    test_queries = [
        # 주문 및 배송 문의
        {
            "category": "주문/배송",
            "query": "주문번호 ORD12345는 어디에 있나요? 아직 받지 못했어요."
        },
        {
            "category": "주문/배송",
            "query": "운송장번호 TRK987654로 택배 추적해주실 수 있나요?"
        },

        # 반품 및 결제 문의
        {
            "category": "반품/결제",
            "query": "주문번호 ORD67890 상품이 안 맞아서 반품하고 싶어요."
        },
        {
            "category": "반품/결제",
            "query": "주문번호 ORD11111 환불이 처리되었나요?"
        },
        {
            "category": "반품/결제",
            "query": "주문번호 ORD22222를 다른 사이즈로 교환하고 싶습니다."
        }
    ]

    # 각 테스트 문의 처리
    for i, test in enumerate(test_queries, 1):
        print(f"\n\n테스트 케이스 {i}: {test['category']}")
        print("-" * 80)
        print(f"문의: {test['query']}")

        try:
            response = handle_customer_query(test['query'])
            print(f"\n응답: {response}")
        except Exception as e:
            print(f"\n에러: {e}")

        print("\n" + "="*80)


if __name__ == "__main__":
    print("\n[시스템] 멀티 에이전트 고객 지원 시스템 시작...")
    print("[시스템] 아키텍처: 오케스트레이터 -> 서브-에이전트-01 (주문/배송) | 서브-에이전트-02 (반품/결제)")

    test_multi_agent_system()

    print("\n[시스템] 테스트 완료!")
