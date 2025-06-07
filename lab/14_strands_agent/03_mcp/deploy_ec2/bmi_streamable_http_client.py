from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient

def main():
    # 클라이언트 생성 - EC2 테스트를 위해 IP 주소를 명시적으로 설정
    # SERVER_URL = "http://XX.XX.XX.XX:8000/mcp/"  # URL 끝에 슬래시(/) 추가
    # SERVER_URL = "http://35.163.60.34:8000/mcp/"  # URL 끝에 슬래시(/) 추가
    SERVER_URL = "http://35.163.60.34:9000/mcp/"  # URL 끝에 슬래시(/) 추가
    print(f"Connecting to server at {SERVER_URL}")
            
    try:
        streamable_http_mcp_client = MCPClient(lambda: streamablehttp_client(SERVER_URL))
        print("Client initialized successfully")
        
        print("\n=== 방법 1: with 구문과 Agent를 사용한 자연어 처리 ===")
        with streamable_http_mcp_client:
            print("Connected to server, listing tools...")
            tools = streamable_http_mcp_client.list_tools_sync()
            print(f"Available tools: {tools}")
            
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
        print("예상치 못한 오류가 발생했습니다.")

if __name__ == "__main__":
    main()