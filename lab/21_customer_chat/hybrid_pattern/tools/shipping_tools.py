"""
배송 관련 도구 함수
"""

from strands import tool


@tool
def track_delivery(tracking_number: str) -> dict:
    """배송 위치를 추적합니다"""
    print(f"[도구] 배송 추적 중 - 운송장번호: {tracking_number}")

    return {
        "tracking_number": tracking_number,
        "status": "지역 배송센터 도착",
        "location": "서울 강남 배송센터",
        "last_update": "2시간 전",
        "estimated_delivery": "내일",
        "delivery_attempts": 0
    }


@tool
def request_shipping_stop(order_id: str) -> dict:
    """배송 중지를 요청합니다"""
    print(f"[도구] 배송 중지 요청 중 - 주문번호: {order_id}")

    # 스켈레톤: 배송 중지가 항상 성공하는 것은 아님
    return {
        "success": False,  # 배송이 이미 시작되어 중지 불가
        "order_id": order_id,
        "message": "배송이 이미 시작되어 중지가 어렵습니다. 관리자 승인이 필요합니다.",
        "needs_escalation": True
    }


@tool
def get_shipping_status(order_id: str) -> dict:
    """주문의 배송 상태를 확인합니다"""
    print(f"[도구] 배송 상태 확인 중 - 주문번호: {order_id}")

    return {
        "order_id": order_id,
        "shipping_started": True,
        "status": "배송 중",
        "tracking_number": "TRK123456789",
        "carrier": "CJ대한통운",
        "estimated_delivery": "2025-10-30"
    }


@tool
def force_shipping_return(order_id: str) -> dict:
    """관리자 권한으로 배송을 강제 회수합니다"""
    print(f"[도구] 배송 강제 회수 처리 중 - 주문번호: {order_id} (관리자 권한)")

    return {
        "success": True,
        "order_id": order_id,
        "message": "관리자 권한으로 배송 회수가 요청되었습니다.",
        "return_initiated": True
    }
