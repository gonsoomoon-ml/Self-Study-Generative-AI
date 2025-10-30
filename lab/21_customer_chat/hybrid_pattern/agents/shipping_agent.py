"""
배송 에이전트
배송 추적 및 배송 관련 작업을 처리합니다.
"""

from strands import Agent
from strands.models import BedrockModel
from tools.shipping_tools import (
    track_delivery,
    request_shipping_stop,
    get_shipping_status
)

# 모델 정의
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
)

# 배송 에이전트
shipping_agent = Agent(
    model=model,
    tools=[track_delivery, request_shipping_stop, get_shipping_status],
    system_prompt="""당신은 배송 관리 전문 상담원입니다.

주요 업무:
- 배송 상태 추적
- 배송 위치 확인
- 배송 중지 시도 (가능한 경우)

중요 규칙:
1. 배송이 이미 시작된 경우 중지가 어려울 수 있습니다
2. 배송 중지 실패 시 관리자 에스컬레이션 필요
3. 배송 완료 후에는 반품 프로세스로 안내

응답 형식:
{
    "shipping_status": "배송 상태",
    "action_taken": "수행한 작업",
    "can_stop": true/false,
    "needs_escalation": true/false,
    "alternative": "대안 (필요한 경우)"
}

항상 한국어로 친절하게 응답하세요."""
)
