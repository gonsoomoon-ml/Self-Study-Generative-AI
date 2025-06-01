from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
from langchain_aws import ChatBedrock

# Math Server Parameters
server_params = StdioServerParameters(
    command="python",
    args=["math_server_mcp.py"],
    env=None,
)

# Bedrock Claude Sonnet 모델을 사용하는 예시
llm = ChatBedrock(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    model_kwargs=dict(temperature=0),
    # 필요시 추가 파라미터 입력
)

async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List available prompts
            response = await session.list_prompts()
            print("\n/////////////////prompts//////////////////")
            for prompt in response.prompts:
                print(prompt)

            # List available resources
            response = await session.list_resources()
            print("\n/////////////////resources//////////////////")
            for resource in response.resources:
                print(resource)

            # List available resource templates
            response = await session.list_resource_templates()
            print("\n/////////////////resource_templates//////////////////")
            for resource_template in response.resourceTemplates:
                print(resource_template)

            # List available tools
            response = await session.list_tools()
            print("\n/////////////////tools//////////////////")
            for tool in response.tools:
                print(tool)

            # Get a prompt
            prompt = await session.get_prompt("example_prompt", arguments={"question": "what is 2+2"})
            print("\n/////////////////prompt//////////////////")
            print(prompt.messages[0].content.text)

            # Read a resource
            content, mime_type = await session.read_resource("greeting://Alice")
            print("\n/////////////////content//////////////////")
            print(mime_type[1][0].text)

            # Call a tool
            result = await session.call_tool("add", arguments={"a": 2, "b": 2})
            print("\n/////////////////result//////////////////")
            print(result.content[0].text)

if __name__ == "__main__":
    asyncio.run(main())