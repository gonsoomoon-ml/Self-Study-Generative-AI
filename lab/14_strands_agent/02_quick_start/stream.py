import asyncio
from strands import Agent
from strands_tools import calculator

# Initialize our agent without a callback handler
agent = Agent(
    tools=[calculator],
    callback_handler=None  # Disable default callback handler
)

# Async function that iterates over streamed agent events
async def process_streaming_response():
    query = "What is 25 * 48 and explain the calculation"

    # Get an async iterator for the agent's response stream
    agent_stream = agent.stream_async(query)

    # Process events as they arrive
    async for event in agent_stream:
        if "data" in event:
            # Print text chunks as they're generated
            print(event["data"], end="", flush=True)
        elif "current_tool_use" in event and event["current_tool_use"].get("name"):
            # Print tool usage information
            print(f"\n[Tool use delta for: {event['current_tool_use']['name']}]")

# Run the agent with the async event processing
asyncio.run(process_streaming_response())

########################
# Callback Handler
########################
import logging
from strands import Agent
from strands_tools import shell

logger = logging.getLogger("my_agent")

# Define a simple callback handler that logs instead of printing
tool_use_ids = []
def callback_handler(**kwargs):
    if "data" in kwargs:
        # Log the streamed data chunks
        logger.info(kwargs["data"], end="")
    elif "current_tool_use" in kwargs:
        tool = kwargs["current_tool_use"]
        if tool["toolUseId"] not in tool_use_ids:
            # Log the tool use
            logger.info(f"\n[Using tool: {tool.get('name')}]")
            tool_use_ids.append(tool["toolUseId"])

# Create an agent with the callback handler
agent = Agent(
    tools=[shell],
    callback_handler=callback_handler
)

# Ask the agent a question
result = agent("What operating system am I using?")

# Print only the last response
print(result.message)