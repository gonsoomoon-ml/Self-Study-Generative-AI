from bedrock_agentcore.runtime import (
    BedrockAgentCoreApp,
)  #### AGENTCORE RUNTIME - LINE 1 ####
from strands import Agent
from strands.models import BedrockModel
from lab_helpers.lab1_strands_agent import (
    check_return_eligibility,
    process_return_request,
    get_product_recommendations,
    ECOMMERCE_SYSTEM_PROMPT,
    ECOMMERCE_MODEL_ID,
)

# Lab1 import: Bedrock 모델 생성
model = BedrockModel(model_id=ECOMMERCE_MODEL_ID)

# 이커머스 고객 지원 도구가 포함된 에이전트 생성 (메모리 없이)
agent = Agent(
    model=model,
    tools=[check_return_eligibility, process_return_request, get_product_recommendations],
    system_prompt=ECOMMERCE_SYSTEM_PROMPT,
)

# AgentCore Runtime App 초기화
app = BedrockAgentCoreApp()  #### AGENTCORE RUNTIME - LINE 2 ####


@app.entrypoint  #### AGENTCORE RUNTIME - LINE 3 ####
def invoke(payload):
    """AgentCore Runtime 엔트리포인트 함수"""
    user_input = payload.get("prompt", "")

    # 에이전트 호출
    response = agent(user_input)
    return response.message["content"][0]["text"]


if __name__ == "__main__":
    app.run()  #### AGENTCORE RUNTIME - LINE 4 ####
