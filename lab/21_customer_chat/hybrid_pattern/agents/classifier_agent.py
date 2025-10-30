"""
분류 에이전트
고객 문의를 분석하여 적절한 카테고리로 분류합니다.
"""

from strands import Agent
from strands.models import BedrockModel

# 모델 정의
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
)

# 분류 에이전트
classifier_agent = Agent(
    model=model,
    system_prompt="""당신은 고객 지원 문의를 분류하는 전문가입니다.

고객의 문의를 분석하여 다음 카테고리 중 하나로 분류하세요:

1. "주문" - 주문 확인, 주문 변경, 주문 내역 관련
2. "배송" - 배송 추적, 배송 지연, 배송 주소 변경
3. "취소" - 주문 취소 요청
4. "반품" - 반품 요청, 반품 절차 문의
5. "환불" - 환불 상태 확인, 환불 요청
6. "교환" - 상품 교환 요청

응답은 반드시 다음 형식의 JSON으로 제공하세요:
{
    "category": "카테고리명",
    "confidence": 0.95,
    "reasoning": "분류 이유"
}

예시:
고객: "주문 취소하고 싶어요"
응답: {"category": "취소", "confidence": 0.98, "reasoning": "명확한 취소 요청"}

항상 한국어로 응답하세요."""
)


def classify_query(query: str) -> dict:
    """
    고객 문의를 분류합니다.

    Args:
        query: 고객 문의

    Returns:
        dict: 분류 결과 {"category": str, "confidence": float, "reasoning": str}
    """
    print(f"[분류 에이전트] 문의 분석 중...")

    # 에이전트 실행
    response = classifier_agent(f"다음 고객 문의를 분류해주세요: {query}")

    # 응답 파싱
    result_text = response.message['content'][0]['text']

    # JSON 파싱 시도
    import json
    try:
        # JSON 추출 (```json ... ``` 형식 처리)
        if "```json" in result_text:
            json_str = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            json_str = result_text.split("```")[1].split("```")[0].strip()
        else:
            json_str = result_text.strip()

        result = json.loads(json_str)
        category = result.get("category", "주문")
    except:
        # JSON 파싱 실패시 키워드 기반 폴백
        query_lower = query.lower()
        if any(word in query_lower for word in ["반품", "불량", "하자"]):
            category = "반품"
        elif any(word in query_lower for word in ["환불", "돈"]):
            category = "환불"
        elif any(word in query_lower for word in ["취소", "안받"]):
            category = "취소"
        elif any(word in query_lower for word in ["배송", "추적", "택배"]):
            category = "배송"
        else:
            category = "주문"
        result = {"category": category, "confidence": 0.8, "reasoning": "키워드 기반 분류"}

    print(f"[분류 에이전트] 분류 결과: {category}")
    return result
