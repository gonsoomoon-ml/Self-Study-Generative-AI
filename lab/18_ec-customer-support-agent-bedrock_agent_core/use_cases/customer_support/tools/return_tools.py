"""
반품 처리 도구들
"""

from strands.tools import tool
from typing import Dict, Any
import json
from datetime import datetime, timedelta


@tool
def process_return(
    order_id: str,
    item_id: str, 
    reason: str,
    customer_id: str,
    return_type: str = "refund"
) -> Dict[str, Any]:
    """
    고객의 반품 요청을 처리합니다.
    
    Args:
        order_id: 주문 번호
        item_id: 상품 번호  
        reason: 반품 사유
        customer_id: 고객 ID
        return_type: 반품 유형 (refund/exchange)
    
    Returns:
        반품 처리 결과
    """
    
    # 반품 정책 확인
    return_window = 14  # 14일 반품 가능
    
    # 모의 반품 처리
    return_id = f"RET{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    result = {
        "return_id": return_id,
        "status": "approved",
        "order_id": order_id,
        "item_id": item_id,
        "reason": reason,
        "return_type": return_type,
        "estimated_refund_date": (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'),
        "return_label": f"https://kstyle.com/return-label/{return_id}",
        "instructions": {
            "ko": [
                "반품 라벨을 출력하여 상품에 부착해주세요.",
                "원래 포장 상태로 반품해주세요.",
                "영수증이나 주문 확인서를 함께 동봉해주세요.",
                "픽업 서비스를 원하시면 고객센터로 연락주세요."
            ]
        }
    }
    
    return result


@tool  
def check_return_policy(product_category: str) -> Dict[str, Any]:
    """
    상품 카테고리별 반품 정책을 확인합니다.
    
    Args:
        product_category: 상품 카테고리
        
    Returns:
        반품 정책 정보
    """
    
    policies = {
        "clothing": {
            "return_window": 14,
            "conditions": ["새 상품 상태", "택 부착", "세탁하지 않은 상태"],
            "refund_method": "원결제수단",
            "shipping_cost": "고객 부담"
        },
        "beauty": {
            "return_window": 7,
            "conditions": ["미개봉 상태", "위생상 문제없는 상태"],
            "refund_method": "원결제수단", 
            "shipping_cost": "고객 부담",
            "restrictions": ["개봉된 화장품은 반품 불가"]
        },
        "accessories": {
            "return_window": 14,
            "conditions": ["새 상품 상태", "포장재 포함"],
            "refund_method": "원결제수단",
            "shipping_cost": "고객 부담"
        }
    }
    
    return policies.get(product_category, policies["clothing"])