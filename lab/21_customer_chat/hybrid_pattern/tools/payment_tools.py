"""
결제 관련 도구 함수
"""

from strands import tool


@tool
def process_refund(order_id: str, amount: int, reason: str = "") -> dict:
    """환불을 처리합니다"""
    print(f"[도구] 환불 처리 중 - 주문번호: {order_id}, 금액: {amount}원")

    return {
        "success": True,
        "order_id": order_id,
        "refund_amount": amount,
        "message": f"{amount}원 환불이 처리되었습니다. 5-7 영업일 내 입금 예정입니다.",
        "refund_date": "2025-10-29",
        "estimated_completion": "2025-11-05"
    }


@tool
def check_refund_status(order_id: str) -> dict:
    """환불 상태를 확인합니다"""
    print(f"[도구] 환불 상태 확인 중 - 주문번호: {order_id}")

    return {
        "order_id": order_id,
        "refund_processed": True,
        "refund_amount": 50000,
        "processed_date": "3일 전",
        "status": "처리 완료",
        "estimated_completion": "2-4 영업일 내"
    }


@tool
def emergency_refund(order_id: str, amount: int) -> dict:
    """긴급 환불을 처리합니다 (관리자 권한)"""
    print(f"[도구] 긴급 환불 처리 중 - 주문번호: {order_id}, 금액: {amount}원 (관리자 권한)")

    return {
        "success": True,
        "order_id": order_id,
        "refund_amount": amount,
        "message": f"관리자 권한으로 긴급 환불 {amount}원이 즉시 처리되었습니다.",
        "priority": "high",
        "estimated_completion": "24시간 내"
    }


@tool
def verify_payment_method(order_id: str) -> dict:
    """결제 수단을 확인합니다"""
    print(f"[도구] 결제 수단 확인 중 - 주문번호: {order_id}")

    return {
        "order_id": order_id,
        "payment_method": "신용카드",
        "card_last_4": "1234",
        "can_refund": True,
        "refund_account": "카드 자동 환불"
    }
