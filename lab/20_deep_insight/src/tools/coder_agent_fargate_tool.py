#!/usr/bin/env python3

import os
import logging
import asyncio
from typing import Any, Annotated
from strands.types.tools import ToolResult, ToolUse
from src.utils.strands_sdk_utils import strands_utils
from src.prompts.template import apply_prompt_template
from src.utils.common_utils import get_message_from_string
from src.tools import fargate_python_tool, fargate_bash_tool

# Observability
from opentelemetry import trace
from src.utils.agentcore_observability import add_span_event

# Simple logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TOOL_SPEC = {
    "name": "coder_agent_fargate_tool",
    "description": "Execute Python code and bash commands using a specialized coder agent running on AWS Fargate. This tool provides access to a coder agent that can execute Python code for data analysis and calculations, run bash commands for system operations, and handle complex programming tasks in isolated Fargate containers.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The coding task or question that needs to be executed by the coder agent."
                }
            },
            "required": ["task"]
        }
    }
}

RESPONSE_FORMAT = "Response from {}:\n\n<response>\n{}\n</response>\n\n*Please execute the next step.*"
FULL_PLAN_FORMAT = "Here is full plan :\n\n<full_plan>\n{}\n</full_plan>\n\n*Please consider this to select the next step.*"
CLUES_FORMAT = "Here is clues from {}:\n\n<clues>\n{}\n</clues>\n\n"

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def handle_coder_agent_fargate_tool(task: Annotated[str, "The coding task or question that needs to be executed by the coder agent."]):
    """
    Execute Python code and bash commands using a specialized coder agent running on AWS Fargate.

    This tool provides access to a coder agent that can:
    - Execute Python code for data analysis and calculations in Fargate containers
    - Run bash commands for system operations in isolated environments
    - Handle complex programming tasks with automatic container lifecycle management

    Args:
        task: The coding task or question that needs to be executed

    Returns:
        The result of the code execution or analysis
    """
    tracer = trace.get_tracer(
        instrumenting_module_name=os.getenv("TRACER_MODULE_NAME", "insight_extractor_agent"),
        instrumenting_library_version=os.getenv("TRACER_LIBRARY_VERSION", "1.0.0")
    )
    with tracer.start_as_current_span("coder_agent_fargate_tool") as span:
        print()  # Add newline before log
        logger.info(f"\n{Colors.GREEN}Coder Agent Fargate Tool starting task{Colors.END}")
        logger.info(f"{Colors.BLUE}🚀 Using AWS Fargate for isolated code execution{Colors.END}")

        # Try to extract shared state from global storage
        from src.graph.nodes import _global_node_states
        shared_state = _global_node_states.get('shared', None)

        if not shared_state:
            logger.warning("No shared state found")
            return "Error: No shared state available"

        request_prompt, full_plan = shared_state.get("request_prompt", ""), shared_state.get("full_plan", "")
        clues, messages = shared_state.get("clues", ""), shared_state.get("messages", [])
        csv_file_path = shared_state.get("csv_file_path")  # 동적 CSV 파일 경로

        # Fargate 세션 생성 (CSV 파일과 함께 또는 일반 세션)
        from src.tools.global_fargate_coordinator import get_global_session
        fargate_manager = get_global_session()

        if csv_file_path and os.path.exists(csv_file_path):
            logger.info(f"{Colors.BLUE}📂 Creating Fargate session with CSV data: {csv_file_path}{Colors.END}")
            if not fargate_manager.ensure_session_with_data(csv_file_path):
                return "Error: Failed to create Fargate session with CSV data"
        else:
            logger.info(f"{Colors.BLUE}📦 Creating standard Fargate session{Colors.END}")
            if not fargate_manager.ensure_session():
                return "Error: Failed to create Fargate session"

        # Create coder agent with Fargate-enabled tools using consistent pattern
        logger.info(f"{Colors.BLUE}📦 Creating coder agent with Fargate tools{Colors.END}")
        coder_agent = strands_utils.get_agent(
            agent_name="coder-fargate",
            system_prompts=apply_prompt_template(
                prompt_name="coder",
                prompt_context={
                    "USER_REQUEST": request_prompt,
                    "FULL_PLAN": full_plan,
                    "EXECUTION_ENVIRONMENT": "AWS Fargate (isolated containers with automatic lifecycle management)"
                }
            ),
            agent_type="claude-sonnet-3-7", # claude-sonnet-3-5-v-2, claude-sonnet-3-7
            enable_reasoning=False,
            tools=[fargate_python_tool, fargate_bash_tool],  # Fargate-enabled tools
            streaming=True  # Enable streaming for consistency
        )

        # Prepare message with context if available
        message = '\n\n'.join([messages[-1]["content"][-1]["text"], clues])

        # Process streaming response and collect text in one pass
        async def process_coder_stream():
            full_text = ""
            logger.info(f"{Colors.BLUE}🔄 Processing coder agent with Fargate backend{Colors.END}")
            async for event in strands_utils.process_streaming_response_yield(
                coder_agent, message, agent_name="coder-fargate", source="coder_fargate_tool"
            ):
                if event.get("event_type") == "text_chunk":
                    full_text += event.get("data", "")
            return {"text": full_text}

        response = asyncio.run(process_coder_stream())
        result_text = response['text']

        # Update clues
        clues = '\n\n'.join([clues, CLUES_FORMAT.format("coder-fargate", response["text"])])

        # Update history
        history = shared_state.get("history", [])
        history.append({"agent":"coder-fargate", "message": response["text"]})

        # Update shared state
        shared_state['messages'] = [get_message_from_string(
            role="user",
            string=RESPONSE_FORMAT.format("coder-fargate", response["text"]),
            imgs=[]
        )]
        shared_state['clues'] = clues
        shared_state['history'] = history

        logger.info(f"\n{Colors.GREEN}Coder Agent Fargate Tool completed successfully{Colors.END}")
        logger.info(f"{Colors.BLUE}✅ Code executed in isolated Fargate environment{Colors.END}")

        # Add Event
        add_span_event(span, "input_message", {"message": str(message)})
        add_span_event(span, "response", {"response": str(response["text"])})
        add_span_event(span, "execution_environment", {"environment": "AWS Fargate"})

        return result_text

# Function name must match tool name
def coder_agent_fargate_tool(tool: ToolUse, **_kwargs: Any) -> ToolResult:
    tool_use_id = tool["toolUseId"]
    task = tool["input"]["task"]

    # Use the existing handle_coder_agent_fargate_tool function
    result = handle_coder_agent_fargate_tool(task)

    # Check if execution was successful based on the result string
    if "Error in coder agent tool" in result or "Error: No shared state available" in result:
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [{"text": result}]
        }
    else:
        return {
            "toolUseId": tool_use_id,
            "status": "success",
            "content": [{"text": result}]
        }

# Alias for backward compatibility
handle_coder_agent_tool_fargate = handle_coder_agent_fargate_tool