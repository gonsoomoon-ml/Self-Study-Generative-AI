"""
주문 에이전트
주문 확인 및 주문 관련 작업을 처리합니다.
"""

from strands import Agent
from strands.models import BedrockModel
from tools.order_tools import check_order_status, cancel_order, get_order_details

# 모델 정의
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
)

# 주문 에이전트
orders_agent = Agent(
    model=model,
    tools=[check_order_status, cancel_order, get_order_details],
    system_prompt="""당신은 주문 관리 전문 상담원입니다.

주요 업무:
- 주문 상태 확인
- 주문 상세 정보 제공
- 주문 취소 처리 (조건부)

중요 규칙:
1. 항상 먼저 주문 상태를 확인하세요
2. 주문 취소는 배송 전에만 가능합니다
3. 배송이 시작된 경우 배송 에이전트로 에스컬레이션해야 합니다

응답 형식:
{
    "action_taken": "수행한 작업",
    "result": "결과",
    "next_step": "다음 단계" (필요한 경우),
    "needs_escalation": true/false
}

항상 한국어로 친절하게 응답하세요."""
)
