"""
Graph + Hierarchical Hybrid 패턴 테스트 스크립트
"""

import asyncio
from graphs.main_graph import execute_customer_support


async def test_hybrid_pattern():
    """
    하이브리드 패턴을 테스트합니다.
    """

    print("\n" + "="*80)
    print("Graph + Hierarchical Hybrid 패턴 테스트")
    print("="*80)

    # 테스트 케이스
    test_cases = [
        {
            "name": "주문 취소 (배송 전)",
            "query": "주문번호 ORD12345를 취소하고 환불 받고 싶어요",
            "expected_flow": "classify → order_graph → cancel_direct → refund"
        },
        {
            "name": "주문 취소 (배송 중)",
            "query": "배송 중인 주문을 취소하고 싶은데 가능한가요?",
            "expected_flow": "classify → order_graph → check_shipping → escalate → manager"
        },
        {
            "name": "반품 요청",
            "query": "주문번호 ORD67890 상품이 불량이라서 반품하고 싶어요",
            "expected_flow": "classify → return_graph → process_return → refund"
        },
        {
            "name": "고액 환불",
            "query": "15만원 주문을 환불 받고 싶어요",
            "expected_flow": "classify → return_graph → check_amount → manager_approval → refund"
        },
    ]

    # 각 테스트 케이스 실행
    for i, test in enumerate(test_cases, 1):
        print(f"\n\n{'='*80}")
        print(f"테스트 케이스 {i}: {test['name']}")
        print(f"{'='*80}")
        print(f"문의: {test['query']}")
        print(f"예상 플로우: {test['expected_flow']}")
        print(f"{'-'*80}\n")

        try:
            # 그래프 실행
            result = await execute_customer_support(test['query'])

            print(f"\n{'-'*80}")
            print(f"결과:")
            print(f"  - 카테고리: {result.get('카테고리', result.get('category'))}")
            print(f"  - 상태: {result.get('상태', result.get('status'))}")
            print(f"  - 메시지: {result.get('메시지', result.get('message'))}")
            print(f"  - 사용된 그래프: {result.get('사용된_그래프', result.get('graph_used'))}")
            print(f"{'-'*80}")

        except Exception as e:
            print(f"\n에러 발생: {e}")

    print(f"\n\n{'='*80}")
    print("모든 테스트 완료!")
    print(f"{'='*80}\n")


def show_architecture():
    """
    아키텍처 구조를 출력합니다.
    """
    print("\n" + "="*80)
    print("Graph + Hierarchical Hybrid 아키텍처")
    print("="*80)

    architecture = """
                        [Start: 고객 문의]
                                ↓
                        [Classifier Agent]
                                ↓
                    ┌───────────┴───────────┐
                    ↓                       ↓
            [Order Sub-Graph]      [Return Sub-Graph]
                    ↓                       ↓
            ┌───────┼───────┐       ┌───────┼───────┐
            ↓       ↓       ↓       ↓       ↓       ↓
        [주문]  [배송]  [재고]  [반품]  [환불]  [교환]
            ↓       ↓       ↓       ↓       ↓       ↓
            └───────┴───────┘       └───────┴───────┘
                    ↓                       ↓
            [Decision Node]      [Hierarchical Approval]
                    ↓                       ↓
                    └───────────┬───────────┘
                                ↓
                        [최종 응답]
    """

    print(architecture)

    print("\n계층적 승인 구조:")
    print("""
        Director (이사)
            ↑
            │ (환불 > 100,000원)
            │ (중대한 정책 예외)
            │
        Manager (관리자)
            ↑
            │ (환불 > 50,000원)
            │ (배송 강제 중지)
            │
        Specialist (일반 상담원)
    """)

    print("="*80 + "\n")


def show_folder_structure():
    """
    폴더 구조를 출력합니다.
    """
    print("\n" + "="*80)
    print("폴더 구조")
    print("="*80)

    structure = """
    hybrid/
    ├── graphs/                    # 그래프 정의
    │   ├── __init__.py
    │   ├── main_graph.py         # 메인 그래프
    │   ├── order_graph.py        # 주문/배송 서브그래프
    │   └── return_graph.py       # 반품/환불 서브그래프
    ├── agents/                    # 에이전트 정의
    │   ├── __init__.py
    │   ├── classifier_agent.py   # 분류 에이전트
    │   ├── orders_agent.py       # 주문 에이전트
    │   ├── shipping_agent.py     # 배송 에이전트
    │   ├── returns_agent.py      # 반품 에이전트
    │   ├── payment_agent.py      # 결제 에이전트
    │   └── decision_agent.py     # 의사결정 에이전트
    ├── tools/                     # 도구 함수
    │   ├── __init__.py
    │   ├── order_tools.py        # 주문 관련 도구
    │   ├── shipping_tools.py     # 배송 관련 도구
    │   └── payment_tools.py      # 결제 관련 도구
    ├── hierarchies/               # 계층적 구조
    │   ├── __init__.py
    │   └── approval_hierarchy.py # 승인 계층
    ├── main.py                    # 이 파일
    └── README.md
    """

    print(structure)
    print("="*80 + "\n")


if __name__ == "__main__":
    print("\n[시스템] Graph + Hierarchical Hybrid 패턴 데모")
    print("[시스템] 이것은 스켈레톤 구현입니다 - Strands SDK의 실제 Graph API가 필요합니다\n")

    # 아키텍처 보기
    show_architecture()

    # 폴더 구조 보기
    show_folder_structure()

    # 테스트 실행
    print("[시스템] 테스트 시작...\n")
    asyncio.run(test_hybrid_pattern())

    print("\n[시스템] 참고:")
    print("  - 현재 코드는 스켈레톤 구현입니다")
    print("  - TODO 주석을 참고하여 Strands SDK의 실제 Graph API로 교체하세요")
    print("  - RECOMMENDED_PATTERN.md에서 상세한 구현 가이드를 확인하세요\n")
