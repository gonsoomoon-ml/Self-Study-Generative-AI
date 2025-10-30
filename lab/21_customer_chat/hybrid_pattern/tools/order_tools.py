"""
주문 관련 도구 함수
"""

from strands import tool


@tool
def check_order_status(order_id: str) -> dict:
    """주문 상태를 확인합니다"""
    print(f"[도구] 주문 상태 확인 중 - 주문번호: {order_id}")

    # 스켈레톤: 실제로는 데이터베이스나 API 호출
    return {
        "order_id": order_id,
        "status": "배송 중",  # "주문확인", "배송 전", "배송 중", "배송 완료"
        "has_shipping": True,
        "can_cancel": False,
        "order_date": "2025-10-25",
        "total_amount": 50000
    }


@tool
def cancel_order(order_id: str, reason: str = "고객 요청") -> dict:
    """주문을 취소합니다"""
    print(f"[도구] 주문 취소 처리 중 - 주문번호: {order_id}, 사유: {reason}")

    return {
        "success": True,
        "order_id": order_id,
        "message": f"주문번호 {order_id}가 성공적으로 취소되었습니다.",
        "refund_initiated": True
    }


@tool
def get_order_details(order_id: str) -> dict:
    """주문 상세 정보를 조회합니다"""
    print(f"[도구] 주문 상세 정보 조회 중 - 주문번호: {order_id}")

    return {
        "order_id": order_id,
        "items": [
            {"name": "상품A", "quantity": 2, "price": 25000}
        ],
        "total_amount": 50000,
        "status": "배송 중",
        "customer_name": "홍길동",
        "shipping_address": "서울시 강남구"
    }
