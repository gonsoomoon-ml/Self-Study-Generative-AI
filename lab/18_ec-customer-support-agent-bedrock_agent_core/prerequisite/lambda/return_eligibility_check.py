"""
반품 자격 검증 Lambda 함수
이커머스 특화: 패션/뷰티 제품의 반품 가능 여부를 자동으로 판단
"""

import json
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any


def get_tool_name(event: Dict[str, Any]) -> str:
    """이벤트에서 도구 이름을 추출합니다."""
    try:
        return event.get('tool_name', '')
    except:
        return ''


def get_named_parameter(event: Dict[str, Any], name: str) -> str:
    """이벤트에서 지정된 매개변수를 추출합니다."""
    try:
        parameters = event.get('parameters', {})
        return parameters.get(name, '')
    except:
        return ''


def check_return_eligibility(order_number: str, customer_id: str) -> Dict[str, Any]:
    """
    반품 자격을 확인합니다.
    
    Args:
        order_number: 주문번호
        customer_id: 고객 ID
        
    Returns:
        반품 가능 여부 및 세부 정보
    """
    
    # 실제 환경에서는 DynamoDB나 RDS에서 조회
    # 여기서는 모킹 데이터 사용
    mock_orders = {
        "KS-2024-001234": {
            "customer_id": "customer_ecommerce_001",
            "order_date": "2024-01-10",
            "items": [
                {
                    "name": "플라워 패턴 원피스",
                    "category": "패션",
                    "price": 59000,
                    "condition": "새 상품",
                    "tags_removed": False,
                    "worn": False
                }
            ],
            "total_amount": 59000,
            "payment_status": "완료",
            "delivery_date": "2024-01-12",
            "vip_level": "골드"
        },
        "KS-2024-001235": {
            "customer_id": "customer_ecommerce_002", 
            "order_date": "2024-01-05",
            "items": [
                {
                    "name": "쿠션 파운데이션",
                    "category": "뷰티",
                    "price": 32000,
                    "condition": "미개봉",
                    "seal_intact": True,
                    "used": False
                }
            ],
            "total_amount": 32000,
            "payment_status": "완료",
            "delivery_date": "2024-01-07",
            "vip_level": "실버"
        },
        "KS-2024-001236": {
            "customer_id": "customer_ecommerce_001",
            "order_date": "2023-12-15",  # 30일 초과
            "items": [
                {
                    "name": "니트 가디건",
                    "category": "패션", 
                    "price": 45000,
                    "condition": "새 상품",
                    "tags_removed": False,
                    "worn": False
                }
            ],
            "total_amount": 45000,
            "payment_status": "완료",
            "delivery_date": "2023-12-17",
            "vip_level": "골드"
        }
    }
    
    order = mock_orders.get(order_number)
    if not order:
        return {
            "eligible": False,
            "reason": "주문을 찾을 수 없습니다.",
            "error_code": "ORDER_NOT_FOUND"
        }
    
    # 고객 ID 확인
    if order["customer_id"] != customer_id:
        return {
            "eligible": False,
            "reason": "주문 정보와 고객 정보가 일치하지 않습니다.",
            "error_code": "CUSTOMER_MISMATCH"
        }
    
    # 배송일로부터 7일 경과 확인
    delivery_date = datetime.strptime(order["delivery_date"], "%Y-%m-%d")
    current_date = datetime.now()
    days_since_delivery = (current_date - delivery_date).days
    
    # 반품 기간 확인 (패션: 7일, 뷰티: 7일)
    return_period = 7
    
    if days_since_delivery > return_period:
        # VIP 고객에게는 추가 2일 혜택
        if order["vip_level"] in ["골드", "다이아몬드"] and days_since_delivery <= return_period + 2:
            vip_extension = True
        else:
            return {
                "eligible": False,
                "reason": f"반품 기간({return_period}일)이 지났습니다. (경과: {days_since_delivery}일)",
                "error_code": "RETURN_PERIOD_EXPIRED",
                "days_since_delivery": days_since_delivery,
                "return_period": return_period
            }
    else:
        vip_extension = False
    
    # 상품 상태 확인
    item = order["items"][0]  # 첫 번째 상품만 확인 (단순화)
    
    eligibility_result = {
        "eligible": True,
        "order_number": order_number,
        "customer_id": customer_id,
        "item_name": item["name"],
        "category": item["category"],
        "days_since_delivery": days_since_delivery,
        "return_period": return_period,
        "vip_level": order["vip_level"],
        "vip_extension": vip_extension,
        "estimated_refund": item["price"],
        "processing_time": "1-2 영업일" if order["vip_level"] in ["골드", "다이아몬드"] else "3-5 영업일"
    }
    
    # 카테고리별 추가 확인
    if item["category"] == "패션":
        if item.get("tags_removed", False):
            return {
                "eligible": False,
                "reason": "택이 제거된 상품은 반품이 불가능합니다.",
                "error_code": "TAGS_REMOVED"
            }
        
        if item.get("worn", False):
            return {
                "eligible": False,
                "reason": "착용 흔적이 있는 상품은 반품이 불가능합니다.",
                "error_code": "WORN_CONDITION"
            }
        
        eligibility_result.update({
            "conditions": [
                "택(tag)이 제거되지 않았을 것",
                "착용 흔적이나 세탁 흔적이 없을 것",
                "원래 포장 상태를 유지할 것"
            ],
            "shipping_fee": "무료" if days_since_delivery <= 7 else "3,000원"
        })
    
    elif item["category"] == "뷰티":
        if item.get("used", False):
            return {
                "eligible": False,
                "reason": "사용된 뷰티 제품은 반품이 불가능합니다.",
                "error_code": "USED_PRODUCT"
            }
        
        if not item.get("seal_intact", True):
            return {
                "eligible": False,
                "reason": "봉인이 훼손된 제품은 반품이 불가능합니다.",
                "error_code": "SEAL_DAMAGED"
            }
        
        eligibility_result.update({
            "conditions": [
                "미개봉 상태일 것",
                "봉인 스티커가 훼손되지 않았을 것",
                "사용하지 않았을 것"
            ],
            "shipping_fee": "무료"
        })
    
    return eligibility_result


def lambda_handler(event, context):
    """
    Lambda 핸들러 함수
    AgentCore Gateway에서 호출됩니다.
    """
    
    try:
        # AgentCore Gateway에서 전달된 도구 정보 확인
        tool_name = get_tool_name(event)
        
        if tool_name == "check_return_eligibility":
            order_number = get_named_parameter(event, "order_number")
            customer_id = get_named_parameter(event, "customer_id")
            
            if not order_number or not customer_id:
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": "주문번호와 고객 ID가 필요합니다.",
                        "error_code": "MISSING_PARAMETERS"
                    }, ensure_ascii=False)
                }
            
            result = check_return_eligibility(order_number, customer_id)
            
            return {
                "statusCode": 200,
                "body": json.dumps(result, ensure_ascii=False, default=str)
            }
        
        else:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": f"지원하지 않는 도구: {tool_name}",
                    "error_code": "UNSUPPORTED_TOOL"
                }, ensure_ascii=False)
            }
    
    except Exception as e:
        print(f"Lambda 실행 오류: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "내부 서버 오류가 발생했습니다.",
                "error_code": "INTERNAL_SERVER_ERROR",
                "details": str(e)
            }, ensure_ascii=False)
        }


# 로컬 테스트용
if __name__ == "__main__":
    # 테스트 이벤트
    test_events = [
        {
            "tool_name": "check_return_eligibility",
            "parameters": {
                "order_number": "KS-2024-001234",
                "customer_id": "customer_ecommerce_001"
            }
        },
        {
            "tool_name": "check_return_eligibility", 
            "parameters": {
                "order_number": "KS-2024-001235",
                "customer_id": "customer_ecommerce_002"
            }
        },
        {
            "tool_name": "check_return_eligibility",
            "parameters": {
                "order_number": "KS-2024-001236",
                "customer_id": "customer_ecommerce_001"
            }
        }
    ]
    
    print("🧪 반품 자격 검증 Lambda 테스트")
    print("=" * 50)
    
    for i, event in enumerate(test_events, 1):
        print(f"\n테스트 {i}: {event['parameters']['order_number']}")
        print("-" * 30)
        
        result = lambda_handler(event, None)
        print(f"상태 코드: {result['statusCode']}")
        
        body = json.loads(result['body'])
        if result['statusCode'] == 200:
            print(f"반품 가능: {body.get('eligible', False)}")
            if body.get('eligible'):
                print(f"상품: {body.get('item_name')}")
                print(f"VIP 레벨: {body.get('vip_level')}")
                print(f"배송 후 경과일: {body.get('days_since_delivery')}일")
                print(f"예상 환불액: {body.get('estimated_refund', 0):,}원")
            else:
                print(f"반품 불가 사유: {body.get('reason')}")
        else:
            print(f"오류: {body.get('error')}")
        
        print("=" * 50)