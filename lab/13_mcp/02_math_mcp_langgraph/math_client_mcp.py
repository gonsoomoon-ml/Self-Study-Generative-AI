from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
from langchain_aws import ChatBedrock
import json

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

def format_prompt(prompt):
    return {
        "name": prompt.name,
        "description": prompt.description,
        "arguments": [{"name": arg.name, "required": arg.required} for arg in prompt.arguments]
    }

def format_resource(resource):
    return {
        "uri": str(resource.uri),
        "name": resource.name,
        "description": resource.description,
        "mimeType": resource.mimeType
    }

def format_resource_template(template):
    return {
        "uriTemplate": template.uriTemplate,
        "name": template.name,
        "description": template.description
    }

def format_tool(tool):
    return {
        "name": tool.name,
        "description": tool.description,
        "inputSchema": tool.inputSchema
    }

async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            #########################################################
            # List available prompts
            #########################################################
            response = await session.list_prompts()
            prompts = [format_prompt(prompt) for prompt in response.prompts]
            print("\n//////////////////////////////////////////")
            print("=== Available Prompts ===")
            print("//////////////////////////////////////////")
            print("===== From Server =======")
            print(json.dumps({"prompts": prompts}, indent=2, ensure_ascii=False))

            #########################################################
            # List available resources
            #########################################################
            response = await session.list_resources()
            resources = [format_resource(resource) for resource in response.resources]
            print("\n//////////////////////////////////////////")
            print("=== Available Resources ===")
            print("//////////////////////////////////////////")
            print("===== From Server =======")
            print(json.dumps({"resources": resources}, indent=2, ensure_ascii=False))

            #########################################################
            # List available resource templates
            #########################################################
            response = await session.list_resource_templates()
            templates = [format_resource_template(template) for template in response.resourceTemplates]
            print("\n//////////////////////////////////////////")
            print("=== Available Resource Templates ===")
            print("//////////////////////////////////////////")
            print("===== From Server =======")
            print(json.dumps({"resourceTemplates": templates}, indent=2, ensure_ascii=False))

            #########################################################
            # List available tools
            #########################################################
            response = await session.list_tools()
            tools = [format_tool(tool) for tool in response.tools]
            print("\n//////////////////////////////////////////")
            print("=== Available Tools ===")
            print("//////////////////////////////////////////")
            print("===== From Server =======")
            print(json.dumps({"tools": tools}, indent=2, ensure_ascii=False))

            #########################################################
            # Get a prompt
            #########################################################
            prompt = await session.get_prompt("example_prompt", arguments={"question": "what is 2+2"})
            print("\n//////////////////////////////////////////")
            print("=== Prompt Content ===")
            print("//////////////////////////////////////////")
            print("===== From Server =======")
            print(json.dumps({
                "prompt": {
                    "content": prompt.messages[0].content.text
                }
            }, indent=2, ensure_ascii=False))

            #########################################################
            # Read a resource
            #########################################################
            content, mime_type = await session.read_resource("config://app")
            print("\n//////////////////////////////////////////")
            print("=== Resource Content ===")
            print("//////////////////////////////////////////")
            print("===== From Server =======")
            try:
                # Get the text content from TextResourceContents in mime_type
                if isinstance(mime_type, tuple) and len(mime_type) > 1 and len(mime_type[1]) > 0:
                    text_content = mime_type[1][0].text
                    config = json.loads(text_content)
                    print(json.dumps(config, indent=2, ensure_ascii=False))
                else:
                    print(f"Content: {content}")
                    print(f"MIME Type: {mime_type}")
            except (json.JSONDecodeError, TypeError, IndexError, AttributeError):
                print(f"Content: {content}")
                print(f"MIME Type: {mime_type}")

            #########################################################
            # Call a tool
            #########################################################
            result = await session.call_tool("add", arguments={"a": 2, "b": 2})
            print("\n//////////////////////////////////////////")
            print("=== Tool Result ===")
            print("//////////////////////////////////////////")
            print("===== From Server =======")
            print(json.dumps({
                "result": {
                    "operation": "add",
                    "arguments": {"a": 2, "b": 2},
                    "value": result.content[0].text
                }
            }, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())