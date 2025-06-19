import asyncio
import json
import sys
import os
from mcp.client.stdio import stdio_client
from mcp.client.stdio import StdioServerParameters
from mcp.types import JSONRPCMessage
from mcp.shared.message import SessionMessage

async def main():
    # Get the directory of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    server_path = os.path.join(current_dir, "server_stdio_weather.py")
    
    # Create MCP client with stdio transport
    server_params = StdioServerParameters(
        command="python",
        args=[server_path],
        cwd=current_dir,  # Set working directory to the script's directory
        env={"PYTHONUNBUFFERED": "1"}  # Ensure Python output is not buffered
    )
    
    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            # Example 1: Get current weather forecast for Seoul
            print("\n=== Current Weather Forecast (Seoul) ===")
            request = SessionMessage(JSONRPCMessage(
                jsonrpc="2.0",
                method="get_now_forecast",
                params={"location_name": "서울"},
                id=1
            ))
            await write_stream.send(request)
            response = await read_stream.receive()
            if isinstance(response, Exception):
                raise response
            print(response.message.model_dump())
            
            # Example 2: Get past weather stats for Seoul
            print("\n=== Past Weather Stats (Seoul) ===")
            request = SessionMessage(JSONRPCMessage(
                jsonrpc="2.0",
                method="get_past_weather_stats",
                params={
                    "location_name": "서울",
                    "start_dt": "20250501",
                    "end_dt": "20250507"
                },
                id=2
            ))
            await write_stream.send(request)
            response = await read_stream.receive()
            if isinstance(response, Exception):
                raise response
            print(json.dumps(response.message.model_dump(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error during communication: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nClient terminated by user")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1) 