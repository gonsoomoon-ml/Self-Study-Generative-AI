"""
교환 처리 도구들
"""

from strands.tools import tool
from typing import Dict, Any, List
import json
from datetime import datetime, timedelta


@tool
def process_exchange(
    order_id: str,
    item_id: str,
    current_size: str,
    desired_size: str,
    customer_id: str,
    reason: str = "size_issue"
) -> Dict[str, Any]:
    """
    고객의 교환 요청을 처리합니다.
    
    Args:
        order_id: 주문 번호
        item_id: 상품 번호
        current_size: 현재 사이즈
        desired_size: 원하는 사이즈
        customer_id: 고객 ID
        reason: 교환 사유
        
    Returns:
        교환 처리 결과
    """
    
    # 재고 확인 (모의)
    stock_available = check_size_availability(item_id, desired_size)
    
    exchange_id = f"EXC{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    if stock_available:
        result = {
            "exchange_id": exchange_id,
            "status": "approved",
            "order_id": order_id,
            "item_id": item_id,
            "current_size": current_size,
            "desired_size": desired_size,
            "reason": reason,
            "estimated_delivery": (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
            "exchange_label": f"https://kstyle.com/exchange-label/{exchange_id}",
            "instructions": {
                "ko": [
                    "교환 라벨을 출력하여 기존 상품에 부착해주세요.",
                    "새 상품은 기존 상품 수거 후 5일 내 배송됩니다.",
                    "추가 비용은 발생하지 않습니다.",
                    "교환 상품 재고가 부족할 경우 연락드립니다."
                ]
            },
            "additional_cost": 0
        }
    else:
        result = {
            "exchange_id": exchange_id,
            "status": "waitlisted",
            "order_id": order_id,
            "item_id": item_id,
            "current_size": current_size,
            "desired_size": desired_size,
            "reason": reason,
            "message": "요청하신 사이즈가 현재 품절입니다. 재입고 시 우선 연락드리겠습니다.",
            "estimated_restock": (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d'),
            "alternatives": get_size_alternatives(item_id, desired_size)
        }
    
    return result


@tool
def check_size_availability(item_id: str, size: str) -> bool:
    """
    특정 상품의 사이즈 재고를 확인합니다.
    
    Args:
        item_id: 상품 번호
        size: 확인할 사이즈
        
    Returns:
        재고 여부
    """
    
    # 모의 재고 데이터
    mock_inventory = {
        "KTOP001": {"XS": 5, "S": 12, "M": 8, "L": 3, "XL": 0},
        "KJEAN002": {"26": 2, "27": 5, "28": 10, "29": 7, "30": 4},
        "KDRESS003": {"XS": 3, "S": 8, "M": 15, "L": 6, "XL": 2}
    }
    
    inventory = mock_inventory.get(item_id, {})
    return inventory.get(size, 0) > 0


@tool
def get_size_alternatives(item_id: str, desired_size: str) -> List[Dict[str, Any]]:
    """
    품절된 사이즈의 대안을 제안합니다.
    
    Args:
        item_id: 상품 번호
        desired_size: 원하는 사이즈
        
    Returns:
        대안 사이즈 리스트
    """
    
    # 사이즈 매핑
    size_alternatives = {
        "XS": ["S"],
        "S": ["XS", "M"], 
        "M": ["S", "L"],
        "L": ["M", "XL"],
        "XL": ["L"],
        "26": ["27"],
        "27": ["26", "28"],
        "28": ["27", "29"],
        "29": ["28", "30"],
        "30": ["29"]
    }
    
    alternatives = []
    for alt_size in size_alternatives.get(desired_size, []):
        if check_size_availability(item_id, alt_size):
            alternatives.append({
                "size": alt_size,
                "available": True,
                "fit_recommendation": get_fit_recommendation(desired_size, alt_size)
            })
    
    return alternatives


def get_fit_recommendation(original: str, alternative: str) -> str:
    """
    핏 추천 설명을 생성합니다.
    """
    
    recommendations = {
        ("S", "XS"): "약간 더 타이트한 핏입니다.",
        ("S", "M"): "약간 더 여유로운 핏입니다.",
        ("M", "S"): "약간 더 슬림한 핏입니다.",
        ("M", "L"): "약간 더 루즈한 핏입니다.",
        ("27", "26"): "허리가 약 1인치 작습니다.",
        ("27", "28"): "허리가 약 1인치 큽니다."
    }
    
    return recommendations.get((original, alternative), "비슷한 핏입니다.")