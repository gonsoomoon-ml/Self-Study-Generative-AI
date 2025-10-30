"""
반품 에이전트
반품 및 교환 요청을 처리합니다.
"""

from strands import Agent
from strands.models import BedrockModel
from strands import tool

# 반품 관련 도구
@tool
def process_return(order_id: str, reason: str) -> dict:
    """반품 요청을 처리합니다"""
    print(f"[도구] 반품 처리 중 - 주문번호: {order_id}, 사유: {reason}")
    return {
        "success": True,
        "order_id": order_id,
        "message": f"주문번호 {order_id}의 반품 요청이 접수되었습니다. 반품 라벨은 24시간 내에 이메일로 발송됩니다.",
        "return_label_sent": False,
        "estimated_label_time": "24시간 내"
    }


@tool
def process_exchange(order_id: str, new_item: str) -> dict:
    """교환 요청을 처리합니다"""
    print(f"[도구] 교환 처리 중 - 주문번호: {order_id}, 새 상품: {new_item}")
    return {
        "success": True,
        "order_id": order_id,
        "new_item": new_item,
        "message": f"교환 요청이 승인되었습니다. 반품 상품을 받은 후 새 상품 {new_item}을(를) 발송해드립니다."
    }


# 모델 정의
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
)

# 반품 에이전트
returns_agent = Agent(
    model=model,
    tools=[process_return, process_exchange],
    system_prompt="""당신은 반품 및 교환 전문 상담원입니다.

주요 업무:
- 반품 요청 처리
- 교환 요청 처리
- 반품 절차 안내

중요 규칙:
1. 반품 사유를 명확히 파악하세요
2. 교환의 경우 새 상품 정보가 필요합니다
3. 고객의 입장을 이해하고 친절하게 안내하세요

응답 형식:
{
    "action_taken": "수행한 작업",
    "return_process": "반품 절차",
    "next_steps": ["단계1", "단계2", ...],
    "estimated_time": "예상 처리 시간"
}

항상 한국어로 친절하게 응답하세요."""
)
