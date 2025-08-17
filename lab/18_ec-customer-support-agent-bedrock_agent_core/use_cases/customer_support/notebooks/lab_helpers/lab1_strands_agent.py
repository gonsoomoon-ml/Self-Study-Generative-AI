from strands.tools import tool

ECOMMERCE_MODEL_ID = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

# System prompt defining the agent's role and capabilities
ECOMMERCE_SYSTEM_PROMPT = """당신은 한국 이커머스 쇼핑몰 K-Style의 고객 지원 전문가입니다.

당신의 역할은:
- 사용 가능한 도구를 활용하여 정확한 정보 제공
- 주문, 배송, 반품, 교환 관련 고객 지원
- 고객에게 친절하고 인내심 있게 대응
- 질문에 답변한 후 항상 추가 도움 제안
- 도울 수 없는 경우 적절한 연락처로 안내

사용 가능한 도구:
1. check_return_eligibility() - 반품 자격 확인
2. process_return_request() - 반품 요청 처리  
3. get_product_recommendations() - 상품 추천

항상 정중하고 친근한 톤으로 응답하며, 고객의 문제를 해결하는 데 최선을 다해주세요."""


@tool
def check_return_eligibility(order_number: str, item_name: str) -> str:
    """
    주문 상품의 반품 가능 여부를 확인합니다.

    Args:
        order_number: 주문번호 (예: 'ORD-20240101-001')
        item_name: 상품명 (예: '플라워 패턴 원피스')

    Returns:
        반품 자격 여부와 조건에 대한 정보
    """
    # 실제 구현에서는 주문 데이터베이스를 조회
    return_policies = {
        "패션": {
            "window": "14일",
            "condition": "택배를 받은 날로부터 14일 이내, 상품 태그 보존, 착용하지 않은 상태",
            "process": "고객센터 또는 온라인 반품 신청",
            "refund_time": "상품 회수 후 3-5 영업일",
            "shipping": "무료 반품 (단순 변심 시 고객 부담)"
        },
        "뷰티": {
            "window": "7일", 
            "condition": "미개봉 상품만 가능, 개인위생상 개봉 후 반품 불가",
            "process": "고객센터 문의 필수",
            "refund_time": "상품 회수 후 3-5 영업일",
            "shipping": "무료 반품 (불량품인 경우만)"
        }
    }

    # 상품 카테고리 추정
    category = "패션"
    if any(keyword in item_name for keyword in ["립스틱", "파운데이션", "쿠션", "크림", "로션"]):
        category = "뷰티"

    policy = return_policies.get(category, return_policies["패션"])
    
    return f"반품 정책 - {item_name}:\n\n" \
           f"• 반품 기간: 배송 완료일로부터 {policy['window']}\n" \
           f"• 반품 조건: {policy['condition']}\n" \
           f"• 신청 방법: {policy['process']}\n" \
           f"• 환불 처리: {policy['refund_time']}\n" \
           f"• 배송비: {policy['shipping']}\n\n" \
           f"주문번호 {order_number}의 {item_name} 상품은 반품 가능합니다."


@tool
def process_return_request(order_number: str, reason: str) -> str:
    """
    반품 요청을 처리합니다.

    Args:
        order_number: 주문번호
        reason: 반품 사유 (예: '사이즈 불만족', '색상 차이', '불량품')

    Returns:
        반품 처리 상태 및 다음 단계 안내
    """
    # 실제 구현에서는 반품 시스템에 요청을 등록
    tracking_number = f"RET-{order_number[-6:]}"
    
    return f"반품 요청이 접수되었습니다.\n\n" \
           f"• 반품 번호: {tracking_number}\n" \
           f"• 주문번호: {order_number}\n" \
           f"• 반품 사유: {reason}\n" \
           f"• 처리 상태: 접수 완료\n\n" \
           f"다음 단계:\n" \
           f"1. 택배 회사에서 2-3일 내 상품 수거 연락\n" \
           f"2. 상품 포장 후 수거 대기\n" \
           f"3. 상품 확인 후 환불 처리 (3-5 영업일)\n\n" \
           f"문의사항이 있으시면 반품번호와 함께 고객센터로 연락주세요."


@tool
def get_product_recommendations(category: str, budget: str = "상관없음") -> str:
    """
    카테고리와 예산에 따른 상품을 추천합니다.

    Args:
        category: 상품 카테고리 (예: '패션', '뷰티', '원피스', '립스틱')
        budget: 예산 범위 (예: '5만원 이하', '10만원대')

    Returns:
        추천 상품 목록과 상세 정보
    """
    # 실제 구현에서는 상품 데이터베이스에서 조회
    recommendations = {
        "패션": [
            {"name": "플라워 패턴 원피스", "price": "89,000원", "rating": "4.8/5", "feature": "봄 신상, 무료배송"},
            {"name": "크롭 니트 가디건", "price": "65,000원", "rating": "4.7/5", "feature": "데일리 아이템"},
            {"name": "와이드 데님 팬츠", "price": "79,000원", "rating": "4.9/5", "feature": "편안한 핏"}
        ],
        "뷰티": [
            {"name": "쿠션 파운데이션", "price": "45,000원", "rating": "4.6/5", "feature": "자연스러운 커버력"},
            {"name": "매트 립스틱", "price": "28,000원", "rating": "4.8/5", "feature": "오래가는 지속력"},
            {"name": "글로우 하이라이터", "price": "32,000원", "rating": "4.7/5", "feature": "촉촉한 윤기"}
        ],
        "원피스": [
            {"name": "플라워 패턴 원피스", "price": "89,000원", "rating": "4.8/5", "feature": "봄 신상, 무료배송"},
            {"name": "체크 미니 원피스", "price": "72,000원", "rating": "4.6/5", "feature": "큐트한 디자인"},
            {"name": "블랙 롱 원피스", "price": "95,000원", "rating": "4.9/5", "feature": "포멀 룩"}
        ]
    }

    # 카테고리별 추천 상품 찾기
    products = recommendations.get(category, recommendations.get("패션", []))
    
    result = f"🛍️ {category} 카테고리 추천 상품:\n\n"
    for i, product in enumerate(products, 1):
        result += f"{i}. {product['name']}\n"
        result += f"   💰 가격: {product['price']}\n"
        result += f"   ⭐ 평점: {product['rating']}\n"
        result += f"   ✨ 특징: {product['feature']}\n\n"
    
    result += "💝 지금 주문하시면 무료배송이며, 14일 이내 무료 반품이 가능합니다.\n"
    result += "더 자세한 상품 정보나 다른 카테고리 추천이 필요하시면 말씀해 주세요!"
    
    return result