from typing import Dict, Any, List
from src.tools.python_repl import handle_python_repl_tool
from src.tools.bash_tool import handle_bash_tool
from src.tools.mcp_weather_tool import handle_mcp_weather_tool

tool_list = [
    {
        "toolSpec": {
            "name": "python_repl_tool",
            "description": "Use this to execute python code and do data analysis or calculation. If you want to see the output of a value, you should print it out with `print(...)`. This is visible to the user.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The python code to execute to do further analysis or calculation."
                        }
                    },
                    "required": ["code"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "bash_tool",
            "description": "Use this to execute bash command and do necessary operations.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "cmd": {
                            "type": "string",
                            "description": "The bash command to be executed."
                        }
                    },
                    "required": ["cmd"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "mcp_weather_tool",
            "description": "Use this tool to collect historical weather data for Korean cities via MCP server. This tool connects to the MCP weather server (http://34.212.60.123:8000/mcp/) and retrieves past weather statistics. IMPORTANT: Only past data (yesterday and earlier) is available, maximum 14 days range.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "location_name": {
                            "type": "string",
                            "description": "Korean city name (e.g., 서울, 부산, 대구, 인천, 대전, 광주, 울산, 수원)",
                            "default": "서울"
                        },
                        "start_dt": {
                            "type": "string",
                            "description": "Start date in YYYYMMDD format (must be yesterday or earlier)"
                        },
                        "end_dt": {
                            "type": "string",
                            "description": "End date in YYYYMMDD format (must be yesterday or earlier)"
                        },
                        "start_hh": {
                            "type": "string",
                            "description": "Start hour in 24-hour format (01-23)",
                            "default": "01"
                        },
                        "end_hh": {
                            "type": "string",
                            "description": "End hour in 24-hour format (01-23)",
                            "default": "23"
                        }
                    },
                    "required": ["start_dt", "end_dt"]
                }
            }
        }
    }
]

coder_tool_config = {
    "tools": tool_list,
    # "toolChoice": {
    #    "tool": {
    #        "name": "summarize_email"
    #    }
    # }
}

def process_coder_tool(tool) -> str:
    """Process a tool invocation
    
    Args:
        tool_name: Name of the tool to invoke
        tool_input: Input parameters for the tool
        
    Returns:
        Result of the tool invocation as a string
    """
    
    tool_name, tool_input = tool["name"], tool["input"]
    
    if tool_name == "python_repl_tool":
        # Create a new instance of the Python REPL tool
        results = handle_python_repl_tool(code=tool_input["code"])
        tool_result = {
            "toolUseId": tool['toolUseId'],
            "content": [{"json": {"text": results}}]
        }
    elif tool_name == "bash_tool":
        results = handle_bash_tool(cmd=tool_input["cmd"])
        tool_result = {
            "toolUseId": tool['toolUseId'],
            "content": [{"json": {"text": results}}]
        }
    elif tool_name == "mcp_weather_tool":
        # Handle MCP weather data collection
        results = handle_mcp_weather_tool(**tool_input)
        tool_result = {
            "toolUseId": tool['toolUseId'],
            "content": [{"json": {"text": results}}]
        }
    else:
        print(f"Unknown tool: {tool_name}")
        results = f"Error: Unknown tool '{tool_name}'"
        tool_result = {
            "toolUseId": tool['toolUseId'],
            "content": [{"json": {"text": results}}]
        }
        
    results = {"role": "user","content": [{"toolResult": tool_result}]}
    
    return results