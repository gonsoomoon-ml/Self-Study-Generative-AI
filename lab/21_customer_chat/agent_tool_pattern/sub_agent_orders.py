"""
Sub-Agent 01: Orders and Delivery Agent
Handles queries about orders, delivery status, and shipping
"""

from strands import Agent, tool
from strands.models import BedrockModel


@tool
def check_order_status(order_id: str) -> str:
    """주문 상태를 확인합니다"""
    print(f"[도구] 주문 상태 확인 중 - 주문번호: {order_id}")
    return f"주문번호 {order_id}는 현재 배송 중입니다. 예상 도착일: 2일 후"


@tool
def track_delivery(tracking_number: str) -> str:
    """배송 위치를 추적합니다"""
    print(f"[도구] 배송 추적 중 - 운송장번호: {tracking_number}")
    return f"택배가 지역 배송센터에 도착했습니다. 마지막 업데이트: 2시간 전"


# Define the model
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
)

# Define the orders agent
orders_agent = Agent(
    model=model,
    tools=[check_order_status, track_delivery],
    system_prompt="""당신은 주문 및 배송 전문 고객 지원 상담원입니다.
    고객을 도울 수 있는 업무:
    - 주문 상태 조회
    - 배송 추적
    - 배송 정보 안내

    친절하고 명확하게 정보를 제공하세요. 항상 한국어로 답변하세요."""
)


def handle_order_query(query: str) -> str:
    """Handle order-related queries"""
    print(f"\n[Sub-Agent-01: Orders] Handling query: {query}")

    # Process with agent
    response = orders_agent(query)

    print(f"[Sub-Agent-01: Orders] Response generated")
    return response.message['content'][0]['text']
