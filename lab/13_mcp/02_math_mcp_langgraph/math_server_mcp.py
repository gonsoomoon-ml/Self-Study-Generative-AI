from mcp.server.fastmcp import FastMCP
import json
import logging

# 로깅 레벨을 WARNING으로 설정하여 INFO 레벨의 메시지를 숨깁니다
logging.getLogger("mcp").setLevel(logging.WARNING)

mcp = FastMCP("Math")

# Prompts
@mcp.prompt()
def example_prompt(question: str) -> str:
    """Example prompt description"""
    return f"""
    You are a math assistant. Answer the question.
    Question: {question}
    """

@mcp.prompt()
def system_prompt() -> str:
    """System prompt description"""
    return """
    You are an AI assistant use the tools if needed.
    """

# Resources
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"안녕하세요, {name}!"

@mcp.resource("config://app")
def get_config() -> str:
    """Static configuration data"""
    config = {
        "app": {
            "name": "Math MCP Server",
            "version": "1.0.0",
            "description": "A simple math server using MCP protocol"
        },
        "server": {
            "host": "localhost",
            "port": 8000,
            "debug": False
        },
        "features": {
            "math_operations": ["add", "multiply"],
            "prompts": ["example_prompt", "system_prompt"],
            "resources": ["greeting", "config"]
        },
        "settings": {
            "max_connections": 100,
            "timeout": 30,
            "log_level": "INFO"
        }
    }
    return json.dumps(config, indent=2)

# Tools
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a * b

if __name__ == "__main__":
    print("Math MCP server is running...")
    mcp.run()  # Run server via stdio