from typing import List
from typing_extensions import TypedDict
from typing import Annotated
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_aws import ChatBedrock
from langgraph.prebuilt import tools_condition, ToolNode
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio
import sys
import io
from textwrap import dedent

########################################################
# 로컬 테스트 
########################################################
# SERVER_URL = "http://localhost:8000/mcp"

########################################################
# EC2 테스트 
########################################################
# SERVER_URL = "http://XX.XX.XX.XX:8000/mcp/"  # URL 끝에 슬래시(/) 추가
SERVER_URL = "http://34.212.60.123:8000/mcp/"  # URL 끝에 슬래시(/) 추가
########################################################

sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')

client = MultiServerMCPClient(
    {
        "kr-weather": {
            "url": SERVER_URL,
            "transport": "streamable_http",
        }
    }
)

async def create_graph():
    # Bedrock Claude Sonnet 모델을 사용하는 예시
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        model_kwargs=dict(temperature=0),
        # 필요시 추가 파라미터 입력
    )
    tools = await client.get_tools()
    llm_with_tool = llm.bind_tools(tools)
    system_prompt = dedent("""
        You are a helpful weather assistant that can provide weather information for cities in Korea. 
        You can help users with:

        1. Current weather conditions for any city in Korea
        2. Historical weather statistics including:
           - Daily high/low temperatures
           - Average precipitation
           - Temperature and precipitation descriptions
           - Location information (city name, latitude, longitude)

        Important limitations and formats to remember:
        - For historical weather data, you can only query up to 14 days at a time
        - When users ask for weather information, always specify the city name clearly
        - For historical data, you must use the following date format:
          * YYYYMMDD (e.g., 20240501 for May 1, 2024)
          * When calling the weather tool, convert any date format to YYYYMMDD
          * For time-based queries, use 24-hour format (01-23)
        - If a request exceeds the 14-day limit, inform the user about this limitation

        Example queries you can handle:
        - "지금 서울 날씨 알려줘"
        - "최근 1주일의 일별 서울 날씨 알려줘"
        - "지난주 부산의 날씨 통계 알려줘"
        - "2024년 5월 1일부터 5월 14일까지 서울 날씨 알려줘"

        Please provide clear and accurate weather information based on the available data.
    """).strip()
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("messages")
    ])
    chat_llm = prompt_template | llm_with_tool

    # State Management
    class State(TypedDict):
        messages: Annotated[List[AnyMessage], add_messages]

    # Nodes
    def chat_node(state: State) -> State:
        state["messages"] = chat_llm.invoke({"messages": state["messages"]})
        return state

    # Building the graph
    graph_builder = StateGraph(State)
    graph_builder.add_node("chat_node", chat_node)
    graph_builder.add_node("tool_node", ToolNode(tools=tools))
    graph_builder.add_edge(START, "chat_node")
    graph_builder.add_conditional_edges("chat_node", tools_condition, {"tools": "tool_node", "__end__": END})
    graph_builder.add_edge("tool_node", "chat_node")
    graph = graph_builder.compile(checkpointer=MemorySaver())
    return graph

async def main():
    config = {"configurable": {"thread_id": 1234}}
    agent = await create_graph()
    while True:
        try:
            message = input("User: ").strip()
            if not message:
                continue
            response = await agent.ainvoke({"messages": message}, config=config)
            print("AI: "+response["messages"][-1].content)
        except UnicodeDecodeError:
            print("입력 오류가 발생했습니다. 다시 시도해주세요.")
            continue
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"오류가 발생했습니다: {e}")
            continue

if __name__ == "__main__":
    asyncio.run(main())