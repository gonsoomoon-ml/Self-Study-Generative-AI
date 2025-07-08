from strands import Agent, tool

# Level 1 - Executive Coordinator
COORDINATOR_SYSTEM_PROMPT = """You are an executive coordinator who oversees complex analyses across multiple domains.
For economic questions, use the economic_department tool.
For technical questions, use the technical_analysis tool.
For social impact questions, use the social_analysis tool.
Synthesize all analyses into comprehensive executive summaries.

Your process should be:
1. Determine which domains are relevant to the query (economic, technical, social)
2. Collect analysis from each relevant domain using the appropriate tools
3. Synthesize the information into a cohesive executive summary
4. Present findings with clear structure and organization

Always consider multiple perspectives and provide balanced, well-rounded assessments.
"""

# Create the coordinator agent with all tools
def create_coordinator():
    print("🟢 [에이전트 생성] 총괄 코디네이터 에이전트 생성")
    return Agent(
        system_prompt=COORDINATOR_SYSTEM_PROMPT,
        tools=[economic_department, technical_analysis, social_analysis],
        callback_handler=None
    )

# Process a complex task through the hierarchical agent graph
def process_complex_task(task):
    print("🟢 [실행] 계층적 에이전트 그래프 실행")
    coordinator = create_coordinator()
    return coordinator(f"Provide a comprehensive analysis of: {task}")


# Level 2 - Mid-level Manager Agent with its own specialized tools
@tool
def economic_department(query: str) -> str:
    print("📈 [호출] 경제 부서 에이전트 호출됨")
    def create_econ_manager():
        print("🟢 [에이전트 생성] 경제 부서 매니저 에이전트 생성")
        return Agent(
            system_prompt="""You are an economic department manager who coordinates specialized economic analyses.
            For market-related questions, use the market_research tool.
            For financial questions, use the financial_analysis tool.
            Synthesize the results into a cohesive economic perspective.

            Important: Make sure to use both tools for comprehensive analysis unless the query is clearly focused on just one area.
            """,
            tools=[market_research, financial_analysis],
            callback_handler=None
        )
    econ_manager = create_econ_manager()
    return str(econ_manager(query))


# Level 3 - Specialized Analysis Agents
@tool
def market_research(query: str) -> str:
    print("🔍 [호출] 마켓 리서치 전문가 에이전트 호출됨")
    print("🟢 [에이전트 생성] 마켓 리서치 전문가 에이전트 생성")
    market_agent = Agent(
        system_prompt="You are a market research specialist who analyzes consumer trends, market segments, and purchasing behaviors. Provide detailed insights on market conditions, consumer preferences, and emerging trends.",
        callback_handler=None
    )
    return str(market_agent(query))

@tool
def financial_analysis(query: str) -> str:
    print("💹 [호출] 금융 분석가 에이전트 호출됨")
    print("🟢 [에이전트 생성] 금융 분석가 에이전트 생성")
    financial_agent = Agent(
        system_prompt="You are a financial analyst who specializes in economic forecasting, cost-benefit analysis, and financial modeling. Provide insights on financial viability, economic impacts, and budgetary considerations.",
        callback_handler=None
    )
    return str(financial_agent(query))

@tool
def technical_analysis(query: str) -> str:
    print("⚙️ [호출] 기술 분석가 에이전트 호출됨")
    print("🟢 [에이전트 생성] 기술 분석가 에이전트 생성")
    tech_agent = Agent(
        system_prompt="You are a technology analyst who evaluates technical feasibility, implementation challenges, and emerging technologies. Provide detailed assessments of technical aspects, implementation requirements, and potential technological hurdles.",
        callback_handler=None
    )
    return str(tech_agent(query))

@tool
def social_analysis(query: str) -> str:
    print("👥 [호출] 사회 영향 분석가 에이전트 호출됨")
    print("🟢 [에이전트 생성] 사회 영향 분석가 에이전트 생성")
    social_agent = Agent(
        system_prompt="You are a social impact analyst who focuses on how changes affect communities, behaviors, and social structures. Provide insights on social implications, behavioral changes, and community impacts.",
        callback_handler=None
    )
    return str(social_agent(query))


from strands import Agent
from strands_tools import agent_graph

def run_agent_graph_demo():
    print("🟢 agent_graph 데모 실행 시작")
    agent = Agent(tools=[agent_graph])
    print("✅ 1. agent(에이전트) 생성 완료")
    result = agent.tool.agent_graph(
        action="create",
        graph_id="research_team",
        topology={
            "type": "star",
            "nodes": [
                {
                    "id": "coordinator",
                    "role": "team_lead",
                    "system_prompt": "You are a research team leader coordinating specialists."
                },
                {
                    "id": "data_analyst",
                    "role": "analyst",
                    "system_prompt": "You are a data analyst specializing in statistical analysis."
                },
                {
                    "id": "domain_expert",
                    "role": "expert",
                    "system_prompt": "You are a domain expert with deep subject knowledge."
                }
            ],
            "edges": [
                {"from": "coordinator", "to": "data_analyst"},
                {"from": "coordinator", "to": "domain_expert"},
                {"from": "data_analyst", "to": "coordinator"},
                {"from": "domain_expert", "to": "coordinator"}
            ]
        }
    )
    print("✅ 2. agent_graph로 연구팀 생성 완료")
    agent.tool.agent_graph(
        action="message",
        graph_id="research_team",
        message={
            "target": "coordinator",
            "content": "재택근무가 생산성에 미치는 영향에 대해 분석해줘."
        }
    )
    print("✅ 3. coordinator에게 메시지 전송 완료")

if __name__ == "__main__":
    # print("=== [MAIN] 01_graph.py 진입 ===")
    # # 예시: 계층적 에이전트 그래프 실행
    # print("\n[1] 계층적 에이전트 그래프 테스트")
    # result = process_complex_task("AI 기술이 경제, 기술, 사회에 미치는 영향")
    # print("최종 Executive Summary 결과:\n", result)

    print("\n[2] agent_graph 데모 실행")
    run_agent_graph_demo()
    print("🎉 메인 함수 종료")