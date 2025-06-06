from mcp.server.fastmcp import FastMCP

mcp = FastMCP("BMI")

# Tools
@mcp.tool()
def calculate_bmi(weight: int, height: int) -> str:
    """Calculate BMI"""
    return "BMI: "+str(weight/(height*height))

if __name__ == "__main__":
    print("Starting MCP server on http://0.0.0.0:8000/mcp")
    mcp.run(transport="streamable-http")