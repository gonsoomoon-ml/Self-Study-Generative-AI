"""
한국 패션/뷰티 이커머스 고객 지원 에이전트
반품/교환 특화 서비스

기존 전자제품 에이전트에서 전환:
- get_return_policy() → process_return()
- get_product_info() → process_exchange()  
- web_search() → web_search() (패션/뷰티 특화)
"""

from strands.tools import tool
from datetime import datetime, timedelta
import random

# 기존과 동일한 모델 ID 사용
MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"

# 패션/뷰티 전문 고객 지원 시스템 프롬프트
SYSTEM_PROMPT = """당신은 한국 패션/뷰티 전문 온라인 쇼핑몰 'K-Style'의 친절하고 전문적인 고객 상담원입니다.

🏪 K-Style 쇼핑몰 소개:
- 패션: 여성/남성 의류, 신발, 가방, 액세서리
- 뷰티: 스킨케어, 메이크업, 향수, 헤어케어
- 전문 서비스: 반품/교환 당일 처리, 스타일링 상담

👨‍💼 상담원 역할:
- 반품/교환 신청을 신속하고 정확하게 처리
- 사이즈, 색상, 스타일 관련 전문 상담 제공
- 패션 트렌드 및 뷰티 사용법 안내
- 항상 존댓말 사용, 친근하고 전문적인 응대
- 고객의 스타일과 선호도를 고려한 맞춤 서비스

🛠️ 사용 가능한 도구:
1. process_return() - 반품 신청 및 처리 (사이즈/색상/품질/변심)
2. process_exchange() - 교환 신청 및 처리 (빠른 교환 서비스)
3. web_search() - 스타일링 팁, 사용법, 트렌드 정보 검색

💡 응대 원칙:
- 반품/교환은 고객의 당연한 권리임을 인식
- 사이즈 가이드와 실제 착용감의 차이를 이해
- 온라인 쇼핑의 한계를 공감하며 최선의 해결책 제시
- 재구매 의향을 높이는 긍정적 경험 제공"""


@tool
def process_return(order_number: str, item_name: str, reason: str) -> str:
    """
    반품 신청을 처리합니다. 패션/뷰티 제품 특화.
    
    Args:
        order_number: 주문번호 (예: 'KS-2024-001234')
        item_name: 반품할 상품명
        reason: 반품 사유 ('사이즈', '색상', '품질', '변심' 등)
    
    Returns:
        반품 처리 결과 및 다음 단계 안내
    """
    
    # 패션/뷰티 반품 정책
    return_policies = {
        "패션": {
            "period": "7일",
            "conditions": [
                "택(tag) 제거하지 않았을 것",
                "착용 흔적이나 세탁 흔적이 없을 것", 
                "원래 포장 상태 유지",
                "향수나 화장품 냄새가 배지 않았을 것"
            ],
            "auto_approve": ["사이즈 불일치", "색상 차이", "품질 불량", "오배송"],
            "shipping_fee": {
                "사이즈": "무료 (판매자 부담)",
                "색상": "무료 (판매자 부담)", 
                "품질": "무료 (판매자 부담)",
                "변심": "3,000원 (고객 부담)"
            }
        },
        "뷰티": {
            "period": "7일",
            "conditions": [
                "미개봉 상태일 것",
                "봉인 스티커가 훼손되지 않았을 것",
                "사용하지 않았을 것"
            ],
            "auto_approve": ["알레르기", "색상 차이", "품질 불량", "오배송"],
            "shipping_fee": {
                "알레르기": "무료 (판매자 부담)",
                "색상": "무료 (판매자 부담)",
                "품질": "무료 (판매자 부담)", 
                "변심": "3,000원 (고객 부담)"
            }
        }
    }
    
    # 카테고리 자동 판별
    category = "뷰티" if any(keyword in item_name.lower() for keyword in 
                           ["립스틱", "파운데이션", "아이섀도", "스킨", "크림", "세럼", "향수"]) else "패션"
    
    policy = return_policies[category]
    
    # 자동 승인 여부 판단
    is_auto_approved = any(auto_reason in reason for auto_reason in policy["auto_approve"])
    
    # 접수 번호 생성
    return_id = f"RT-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    
    # 배송비 계산
    shipping_fee = "무료"
    for fee_reason, fee in policy["shipping_fee"].items():
        if fee_reason in reason:
            shipping_fee = fee
            break
    
    result = f"""✅ 반품 신청이 접수되었습니다.

📋 접수 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━
• 접수번호: {return_id}
• 주문번호: {order_number} 
• 상품명: {item_name}
• 반품사유: {reason}
• 상품 카테고리: {category}
• 접수일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}

"""
    
    if is_auto_approved:
        result += f"""✅ 반품 승인 완료 (자동 승인)
━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 다음 단계:
1. 📧 반품 접수 확인 문자가 발송됩니다
2. 📦 상품을 원래 포장재에 넣어 준비해 주세요
3. 🚚 택배기사님이 내일 오전 방문 예정입니다
4. ✅ 회수 완료 후 1-2일 내 환불 처리

💰 환불 정보:
• 배송비: {shipping_fee}
• 환불 예상일: 회수 후 1-2 영업일
• 환불 방법: 원 결제수단으로 자동 환불"""
        
        # 고객 만족도 향상 메시지
        if reason in ["사이즈 불일치", "사이즈"]:
            result += f"""

💡 다음 구매 시 도움말:
• 상품 상세페이지의 '실측 사이즈'를 확인해 주세요
• 평소 착용하시는 옷의 실측을 비교해 보세요
• 브랜드별로 사이즈가 다를 수 있습니다
• 궁금하시면 언제든 상담 문의해 주세요!"""
    else:
        result += f"""⏳ 반품 신청 검토 중
━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 검토 절차:
1. 담당자가 반품 사유를 검토합니다 (4시간 이내)
2. 승인 시 회수 일정 안내 문자 발송
3. 상품 회수 및 검수 진행
4. 최종 승인 후 환불 처리

💰 예상 비용:
• 배송비: {shipping_fee}
• 처리기간: 최대 3-5 영업일"""
    
    result += f"""

📞 문의사항:
• 고객센터: 1588-0000 (평일 9-18시)
• 카카오톡: @kstyle (24시간 상담)
• 접수번호로 진행상황 실시간 조회 가능

감사합니다. 더 나은 쇼핑 경험을 위해 노력하겠습니다! 💝"""
    
    return result


@tool
def process_exchange(order_number: str, item_name: str, current_option: str, desired_option: str) -> str:
    """
    교환 신청을 처리합니다. 빠른 교환 서비스 제공.
    
    Args:
        order_number: 주문번호
        item_name: 교환할 상품명
        current_option: 현재 옵션 (예: "화이트/M")
        desired_option: 원하는 옵션 (예: "블랙/L")
    
    Returns:
        교환 처리 결과 및 재고 확인
    """
    
    # 교환 접수번호 생성
    exchange_id = f"EX-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    
    # 재고 시뮬레이션
    stock_status = random.choice(["재고 있음", "재고 부족 (2-3일 소요)", "일시 품절"])
    
    result = f"""✅ 교환 신청이 접수되었습니다.

📋 교환 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━
• 접수번호: {exchange_id}
• 주문번호: {order_number}
• 상품명: {item_name}
• 현재 옵션: {current_option}
• 희망 옵션: {desired_option}
• 접수일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}

"""
    
    if stock_status == "재고 있음":
        result += f"""✅ 교환 상품 재고 확인 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 K-Style 빠른 교환 서비스:

📦 교환 프로세스:
1. 오늘 오후 5시까지 기존 상품 회수
2. 동시에 새 상품 배송 출발  
3. 내일 오전 중 새 상품 도착 예정
4. 회수와 배송이 동시에 진행됩니다!

💝 특별 혜택:
• 교환 배송비: 완전 무료
• 당일 처리: 재고 있음
• 동시 교환: 기다림 없이 바로!"""
    
    elif "부족" in stock_status:
        result += f"""⏳ 교환 상품 재고 확인 중
━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 재고 상황: {stock_status}

📅 교환 일정:
1. 오늘 회수 진행
2. 새 상품 입고 후 즉시 발송 ({stock_status.split('(')[1].split(')')[0]})
3. 회수 완료 시 임시 쿠폰 발급

🎁 기다려주셔서 감사합니다:
• 10% 할인 쿠폰 발급 (다음 구매 시)
• 무료 배송 + 포장 업그레이드"""
        
    else:  # 품절
        result += f"""😔 교환 상품 일시 품절
━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 재고 상황: {stock_status}

🔄 대안 제안:
1. 💰 전액 환불 (1-2일 내 처리)
2. 🎯 유사 상품 추천 (같은 가격대)
3. 📅 재입고 알림 신청 (우선 주문권 제공)
4. 🏷️ 다른 색상/사이즈 확인

🎁 불편을 드려 죄송합니다:
• 15% 할인 쿠폰 발급
• 다음 주문 시 무료배송 + 무료 포장"""
    
    result += f"""

🔍 교환 가능 조건:
• 택(tag) 제거하지 않았을 것
• 착용이나 사용 흔적이 없을 것
• 세탁하지 않았을 것
• 원래 포장 상태 유지

📞 추가 문의:
• 고객센터: 1588-0000
• 카카오톡: @kstyle
• 교환 진행상황 실시간 알림 제공

더 완벽한 스타일을 위해 최선을 다하겠습니다! ✨"""
    
    return result


@tool
def web_search(query: str, search_type: str = "fashion") -> str:
    """
    패션/뷰티 관련 정보를 웹에서 검색합니다.
    
    Args:
        query: 검색할 내용
        search_type: 검색 타입 ("fashion", "beauty", "trend", "care")
    
    Returns:
        검색 결과 및 전문적인 조언
    """
    
    # 패션/뷰티 특화 검색 결과 시뮬레이션
    fashion_tips = {
        "플리츠 스커트": {
            "styling": [
                "크롭 니트 + 로퍼로 프레피 룩",
                "오버핏 블라우스 + 스니커즈로 캐주얼 룩", 
                "피팅 티셔츠 + 힐로 세미 정장 룩"
            ],
            "color_match": "네이비, 베이지, 화이트가 가장 활용도 높음",
            "season": "봄/가을 시즌에 특히 인기"
        },
        "가디건": {
            "styling": [
                "슬림 진 + 화이트 티셔츠로 기본 룩",
                "플리츠 스커트 + 로퍼로 여성스러운 룩",
                "와이드 팬츠 + 스니커즈로 편안한 룩"
            ],
            "color_match": "베이지, 네이비는 어떤 색과도 잘 어울림",
            "care": "울 소재는 드라이클리닝, 아크릴은 찬물 손세탁"
        },
        "청바지": {
            "size_guide": [
                "허리 둘레를 정확히 측정해 주세요",
                "브랜드마다 사이즈가 다를 수 있습니다",
                "스키니핏은 평소보다 1사이즈 크게",
                "와이드핏은 평소 사이즈 또는 1사이즈 작게"
            ],
            "styling": "화이트 셔츠, 니트, 블라우스 등과 무난한 매치",
            "care": "뒤집어서 찬물에 세탁, 직사광선 피해 건조"
        }
    }
    
    beauty_tips = {
        "쿠션 파운데이션": {
            "usage": [
                "스킨케어 후 5분 정도 기다린 후 사용",
                "퍼프를 가볍게 눌러서 톡톡 발라주세요",
                "T존부터 시작해서 바깥쪽으로 펴발라 주세요",
                "목과 경계선이 자연스럽게 블렌딩"
            ],
            "skin_type": {
                "건성": "보습 쿠션 또는 글로우 타입 추천",
                "지성": "매트 타입이나 세바 컨트롤 기능",
                "민감성": "무향, 저자극 제품 선택"
            },
            "tip": "여름에는 한 톤 어둡게, 겨울에는 한 톤 밝게"
        },
        "립스틱": {
            "color_choice": [
                "웜톤: 코랄, 오렌지, 레드 계열",
                "쿨톤: 핑크, 베리, 자주 계열",
                "뉴트럴: 로즈, MLBB 계열"
            ],
            "application": [
                "립밤으로 보습 후 사용",
                "립라이너로 윤곽을 그린 후 채우기",
                "티슈로 한 번 눌러준 후 다시 발라주면 지속력 향상"
            ],
            "trend_2024": "생기 가득한 코랄핑크, 시크한 다크베리"
        },
        "스킨케어": {
            "routine": [
                "세안 → 토너 → 에센스 → 세럼 → 크림 → 선크림(아침)",
                "저녁에는 선크림 대신 수분크림 또는 나이트크림",
                "주 1-2회 각질제거 및 마스크팩"
            ],
            "by_age": {
                "20대": "보습과 선크림에 집중",
                "30대": "주름 예방, 안티에이징 시작",
                "40대": "탄력, 미백, 집중 관리"
            }
        }
    }
    
    # 검색 결과 생성
    result = f"""🔍 '{query}' 검색 결과

"""
    
    # 패션 관련 검색
    for item, info in fashion_tips.items():
        if item in query or any(keyword in query for keyword in ["코디", "스타일", "매치"]):
            result += f"""👗 {item} 스타일링 가이드
━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ 추천 코디:
"""
            for styling in info["styling"]:
                result += f"• {styling}\n"
            
            if "color_match" in info:
                result += f"\n🎨 컬러 매칭: {info['color_match']}"
            if "care" in info:
                result += f"\n🧼 관리 방법: {info['care']}"
            if "size_guide" in info:
                result += f"\n📏 사이즈 가이드:\n"
                for guide in info["size_guide"]:
                    result += f"• {guide}\n"
            break
    
    # 뷰티 관련 검색  
    for item, info in beauty_tips.items():
        if item in query or any(keyword in query for keyword in ["사용법", "발라", "바르", "메이크업"]):
            result += f"""💄 {item} 사용 가이드
━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 올바른 사용법:
"""
            for usage in info.get("usage", []):
                result += f"• {usage}\n"
            
            if "skin_type" in info:
                result += f"\n🧴 피부타입별 추천:\n"
                for skin, rec in info["skin_type"].items():
                    result += f"• {skin}: {rec}\n"
            
            if "color_choice" in info:
                result += f"\n🎨 컬러 선택 가이드:\n"
                for color in info["color_choice"]:
                    result += f"• {color}\n"
            
            if "trend_2024" in info:
                result += f"\n✨ 2024 트렌드: {info['trend_2024']}"
            break
    
    # 일반적인 조언이 없는 경우
    if "━━━" not in result:
        if any(keyword in query.lower() for keyword in ["트렌드", "유행", "인기"]):
            result += """🌟 2024 패션/뷰티 트렌드
━━━━━━━━━━━━━━━━━━━━━━━━━━
👗 패션 트렌드:
• 오버사이즈 블레이저
• 플리츠 스커트
• 와이드 진
• 크롭 니트
• 버킷백

💄 뷰티 트렌드:
• 생기 발랄한 코랄 메이크업
• 글래스 스킨 표현
• 그러데이션 립
• 또렷한 아이라이너
• 내추럴 브로우"""
        
        elif any(keyword in query.lower() for keyword in ["세탁", "관리", "보관"]):
            result += """🧼 의류 관리 가이드
━━━━━━━━━━━━━━━━━━━━━━━━━━
👕 소재별 관리법:
• 면: 찬물 세탁, 자연건조
• 울: 드라이클리닝 권장, 평건조
• 폴리에스터: 미지근한 물, 낮은 온도 건조
• 실크: 드라이클리닝 또는 냉수 손세탁
• 데님: 뒤집어서 찬물 세탁

💄 화장품 보관:
• 서늘하고 건조한 곳
• 직사광선 피하기
• 립스틱은 냉장고 보관 가능
• 개봉 후 사용기한 준수"""
        
        else:
            result += f"""💡 '{query}' 관련 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━
죄송합니다. 더 구체적인 검색어로 다시 검색해 주세요.

🔍 검색 팁:
• "플리츠 스커트 코디 방법"
• "쿠션 파운데이션 사용법"  
• "청바지 사이즈 가이드"
• "립스틱 색상 추천"
• "니트 세탁 방법"
"""
    
    result += f"""

💁‍♀️ 추가 도움이 필요하시면 언제든 말씀해 주세요!
스타일링 상담은 K-Style의 전문 분야입니다. ✨"""
    
    return result


# 기존 전자제품 프로젝트와 동일한 구조로 에이전트 생성 함수 제공
def create_ecommerce_agent():
    """패션/뷰티 이커머스 고객 지원 에이전트를 생성합니다."""
    from strands import Agent
    from strands.models import BedrockModel
    import boto3
    
    region = boto3.session.Session().region_name
    
    model = BedrockModel(
        model_id=MODEL_ID,
        temperature=0.3,
        region_name=region
    )
    
    agent = Agent(
        model=model,
        tools=[
            process_return,
            process_exchange, 
            web_search
        ],
        system_prompt=SYSTEM_PROMPT
    )
    
    return agent


if __name__ == "__main__":
    # 에이전트 테스트
    agent = create_ecommerce_agent()
    
    # 테스트 시나리오 (패션/뷰티 특화)
    test_queries = [
        "지난주 산 원피스 사이즈가 작아요. 반품하고 싶어요",
        "이 청바지를 M에서 L로 교환할 수 있나요?",
        "플리츠 스커트에 어떤 상의가 어울려요?",
        "쿠션 파운데이션 올바른 사용법 알려주세요"
    ]
    
    print("🛍️ K-Style 패션/뷰티 고객 지원 에이전트 테스트")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\n고객: {query}")
        print("-" * 40)
        try:
            response = agent(query)
            print(f"상담원: {response}")
        except Exception as e:
            print(f"오류: {e}")
        print("=" * 60)