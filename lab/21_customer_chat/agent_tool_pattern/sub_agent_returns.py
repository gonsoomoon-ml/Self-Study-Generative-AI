"""
Sub-Agent 02: Returns and Payments Agent
Handles queries about returns, exchanges, refunds, and payment issues
"""

from strands import Agent, tool
from strands.models import BedrockModel


@tool
def process_return(order_id: str, reason: str) -> str:
    """반품 요청을 처리합니다"""
    print(f"[도구] 반품 처리 중 - 주문번호: {order_id}, 사유: {reason}")
    return f"주문번호 {order_id}의 반품 요청이 접수되었습니다. 반품 라벨은 24시간 내에 이메일로 발송됩니다."


@tool
def check_refund_status(order_id: str) -> str:
    """환불 상태를 확인합니다"""
    print(f"[도구] 환불 상태 확인 중 - 주문번호: {order_id}")
    return f"주문번호 {order_id}의 환불이 3일 전에 처리되었습니다. 환불 금액은 5-7 영업일 내에 계좌에 입금됩니다."


@tool
def process_exchange(order_id: str, new_item: str) -> str:
    """교환 요청을 처리합니다"""
    print(f"[도구] 교환 처리 중 - 주문번호: {order_id}, 새 상품: {new_item}")
    return f"교환 요청이 승인되었습니다. 반품 상품을 받은 후 새 상품 {new_item}을(를) 발송해드립니다."


# Define the model
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
)

# Define the returns agent
returns_agent = Agent(
    model=model,
    tools=[process_return, check_refund_status, process_exchange],
    system_prompt="""당신은 반품, 교환 및 결제 전문 고객 지원 상담원입니다.
    고객을 도울 수 있는 업무:
    - 반품 요청
    - 교환 절차
    - 환불 상태 조회
    - 결제 문제 처리

    고객의 입장을 이해하고 친절하게 절차를 안내하세요. 항상 한국어로 답변하세요."""
)


def handle_return_query(query: str) -> str:
    """Handle return/payment-related queries"""
    print(f"\n[Sub-Agent-02: Returns] Handling query: {query}")

    # Process with agent
    response = returns_agent(query)

    print(f"[Sub-Agent-02: Returns] Response generated")
    return response.message['content'][0]['text']
