from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient

def main():
    ########################################################
    # 로컬 테스트 
    ########################################################
    SERVER_URL = "http://localhost:8000/mcp"

    ########################################################
    # EC2 테스트 
    ########################################################
    # SERVER_URL = "http://XX.XX.XX.XX:8000/mcp/"  # URL 끝에 슬래시(/) 추가
    # SERVER_URL = "http://35.163.60.34:8000/mcp/"  # URL 끝에 슬래시(/) 추가
    ########################################################


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
            response = agent("지금 서울 날씨 알려줘")
            print("Agent response:", response)

            response = agent("최근 1주일의 일별 서울 날씨 알려줘")
            print("Agent response:", response)


    except Exception as e:
        print(f"\nError: {e}")
        print("예상치 못한 오류가 발생했습니다.")

if __name__ == "__main__":
    main()