"""
결제 에이전트
환불 및 결제 관련 작업을 처리합니다.
"""

from strands import Agent
from strands.models import BedrockModel
from tools.payment_tools import (
    process_refund,
    check_refund_status,
    verify_payment_method
)

# 모델 정의
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
)

# 결제 에이전트
payment_agent = Agent(
    model=model,
    tools=[process_refund, check_refund_status, verify_payment_method],
    system_prompt="""당신은 결제 및 환불 전문 상담원입니다.

주요 업무:
- 환불 처리
- 환불 상태 확인
- 결제 수단 확인

중요 규칙:
1. 환불 전에 결제 수단을 확인하세요
2. 환불 금액이 100,000원을 초과하면 관리자 승인이 필요합니다
3. 환불 처리 시간을 명확히 안내하세요

응답 형식:
{
    "action_taken": "수행한 작업",
    "refund_amount": 금액,
    "refund_status": "상태",
    "estimated_completion": "예상 완료 시간",
    "needs_approval": true/false
}

항상 한국어로 친절하게 응답하세요."""
)
