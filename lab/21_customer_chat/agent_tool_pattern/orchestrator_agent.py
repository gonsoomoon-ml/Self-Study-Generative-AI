"""
Orchestrator Agent
Routes customer queries to the appropriate sub-agent based on the query type
"""

from strands import Agent, tool
from strands.models import BedrockModel
from sub_agent_orders import handle_order_query
from sub_agent_returns import handle_return_query


@tool
def route_to_orders_agent(query: str) -> str:
    """고객 문의를 주문 및 배송 상담원에게 전달합니다"""
    print(f"[오케스트레이터] 주문/배송 상담원으로 전달 중")
    return handle_order_query(query)


@tool
def route_to_returns_agent(query: str) -> str:
    """고객 문의를 반품 및 결제 상담원에게 전달합니다"""
    print(f"[오케스트레이터] 반품/결제 상담원으로 전달 중")
    return handle_return_query(query)


# Define the model
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
)

# Define the orchestrator agent
orchestrator = Agent(
    model=model,
    tools=[route_to_orders_agent, route_to_returns_agent],
    system_prompt="""당신은 메인 고객 지원 오케스트레이터입니다.
    고객의 질문을 이해하고 적절한 전문 상담원에게 전달하는 것이 당신의 역할입니다.

    - 주문, 배송, 추적, 배송 정보 관련 질문 -> route_to_orders_agent 사용
    - 반품, 교환, 환불, 결제 관련 질문 -> route_to_returns_agent 사용

    고객 문의를 분석하여 적절한 상담원에게 전달하세요. 항상 한국어로 답변하세요."""
)


def handle_customer_query(customer_query: str) -> str:
    """고객 문의를 처리하는 메인 진입점"""
    print(f"\n{'='*60}")
    print(f"[오케스트레이터] 고객 문의 접수: {customer_query}")
    print(f"{'='*60}")

    # 오케스트레이터가 문의를 분석하고 라우팅
    response = orchestrator(customer_query)

    print(f"{'='*60}")
    print(f"[오케스트레이터] 최종 응답 준비 완료")
    print(f"{'='*60}\n")

    return response.message['content'][0]['text']
