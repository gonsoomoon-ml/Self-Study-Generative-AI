from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient

def main():
    # 클라이언트 생성 - EC2 테스트를 위해 IP 주소를 명시적으로 설정
    # 로컬 테스트: "http://localhost:8000/mcp"
    # EC2 배포 시: "http://[EC2-PUBLIC-IP]:8000/mcp"
    SERVER_URL = "http://localhost:8000/mcp"  # 테스트 후 EC2 IP로 변경
    streamable_http_mcp_client = MCPClient(lambda: streamablehttp_client(SERVER_URL))
    
    try:
        print("\n=== 방법 1: with 구문과 Agent를 사용한 자연어 처리 ===")
        with streamable_http_mcp_client:
            tools = streamable_http_mcp_client.list_tools_sync()
            agent = Agent(tools=tools)
            response = agent("키 170cm와 몸무게 70kg으로 BMI를 계산해줘")
            print("Agent response:", response)

        print("\n=== 방법 2: with 구문과 agent.tool 사용 ===")
        with streamable_http_mcp_client:
            tools = streamable_http_mcp_client.list_tools_sync()
            agent = Agent(tools=tools)
            result = agent.tool.calculate_bmi(weight=70, height=170)
            print(f"Calculation result: {result['content'][0]['text']}")

        print("\n=== 방법 3: with 구문과 직접 tool 호출 ===")
        with streamable_http_mcp_client:
            result = streamable_http_mcp_client.call_tool_sync(
                tool_use_id="tool-123",
                name="calculate_bmi",
                arguments={"weight": 180, "height": 80}
            )
            print(f"Direct tool call result: {result['content'][0]['text']}")

    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    main()