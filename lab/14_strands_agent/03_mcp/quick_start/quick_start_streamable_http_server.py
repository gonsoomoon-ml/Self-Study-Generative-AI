########################################################
## 아래 코드는 로컬에서 실행할 때 사용
########################################################

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("BMI")

# Tools
@mcp.tool()
def calculate_bmi(weight: int, height: int) -> str:
    """Calculate BMI"""
    return "BMI: "+str(weight/(height*height))

if __name__ == "__main__":
    print("Starting MCP server on http://localhost:8000/mcp")
    mcp.run(transport="streamable-http")


########################################################
## 아래 코드는 서버(예: EC2)  실행할 때 사용
########################################################

# from mcp.server.fastmcp import FastMCP

# # host를 생성자에서 설정
# mcp = FastMCP("BMI", host="0.0.0.0", port=8000)

# # Tools
# @mcp.tool()
# def calculate_bmi(weight: int, height: int) -> str:
#     """Calculate BMI"""
#     return "BMI: "+str(weight/(height*height))

# if __name__ == "__main__":
#     print("Starting MCP server on http://0.0.0.0:8000/mcp")
#     mcp.run(transport="streamable-http")