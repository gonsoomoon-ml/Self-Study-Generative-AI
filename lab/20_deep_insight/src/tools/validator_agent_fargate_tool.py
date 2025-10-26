import os
import logging
import asyncio
from typing import Any, Annotated, Dict, List
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
    "name": "validator_agent_fargate_tool",
    "description": "Validate numerical calculations and generate citation metadata for reports using AWS Fargate containers. This tool validates calculations performed by the Coder agent, re-verifies important calculations using original data sources, and creates citation metadata for numerical accuracy and transparency.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The validation task or instruction for validating calculations and generating citations (e.g., 'Validate all calculations and create citations', 'Verify numerical accuracy and generate reference metadata')."
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
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    END = '\033[0m'

class FargateValidator:
    """
    Fargate 환경에 최적화된 경량 Validator
    캐싱 없이 우선순위 필터링만 제공
    """

    @staticmethod
    def filter_calculations_by_priority(calculations: List[Dict]) -> tuple:
        """
        Filter calculations by importance to optimize processing time
        Returns: (filtered_calculations, stats)
        """
        high_priority = [calc for calc in calculations if calc.get('importance') == 'high']
        medium_priority = [calc for calc in calculations if calc.get('importance') == 'medium']
        low_priority = [calc for calc in calculations if calc.get('importance') == 'low']

        # Performance optimization: limit processing based on total count
        total_calcs = len(calculations)

        if total_calcs > 50:
            # For large datasets, prioritize aggressively
            priority_calcs = high_priority + medium_priority[:min(10, len(medium_priority))]
            logger.info(f"🔧 Large dataset detected ({total_calcs} calculations). Using aggressive filtering.")
        elif total_calcs > 20:
            # Medium datasets, moderate filtering
            priority_calcs = high_priority + medium_priority[:min(15, len(medium_priority))]
            logger.info(f"🔧 Medium dataset detected ({total_calcs} calculations). Using moderate filtering.")
        else:
            # Small datasets, validate most calculations
            priority_calcs = high_priority + medium_priority + low_priority[:5]
            logger.info(f"🔧 Small dataset detected ({total_calcs} calculations). Validating most calculations.")

        stats = {
            'total': total_calcs,
            'high': len(high_priority),
            'medium': len(medium_priority),
            'low': len(low_priority),
            'selected': len(priority_calcs)
        }

        return priority_calcs, stats

def handle_validator_agent_fargate_tool(task: Annotated[str, "The validation task or instruction for validating calculations and generating citations."]):
    """
    Validate numerical calculations and generate citation metadata for reports using AWS Fargate containers.

    This tool provides access to a validator agent that can:
    - Validate calculations performed by the Coder agent in isolated Fargate containers
    - Re-verify important calculations using original data sources
    - Generate citation metadata for numerical accuracy
    - Create reference documentation for transparency
    - Optimize validation for large datasets using priority filtering
    - Automatically sync files between Fargate containers and local filesystem

    Args:
        task: The validation task or instruction for validating calculations and generating citations

    Returns:
        The validation results and confirmation of citation generation
    """
    tracer = trace.get_tracer(
        instrumenting_module_name=os.getenv("TRACER_MODULE_NAME", "insight_extractor_agent"),
        instrumenting_library_version=os.getenv("TRACER_LIBRARY_VERSION", "1.0.0")
    )
    with tracer.start_as_current_span("validator_agent_fargate_tool") as span:
        print()  # Add newline before log
        logger.info(f"\n{Colors.GREEN}Validator Agent Fargate Tool starting{Colors.END}")

        # Try to extract shared state from global storage
        from src.graph.nodes import _global_node_states
        shared_state = _global_node_states.get('shared', None)

        if not shared_state:
            logger.warning("No shared state found")
            return "Error: No shared state available"

        request_prompt, full_plan = shared_state.get("request_prompt", ""), shared_state.get("full_plan", "")
        clues, messages = shared_state.get("clues", ""), shared_state.get("messages", [])

        # Create validator agent with Fargate-enabled tools using consistent pattern
        logger.info(f"{Colors.BLUE}📦 Creating validator agent with Fargate tools{Colors.END}")
        validator_agent = strands_utils.get_agent(
            agent_name="validator",
            system_prompts=apply_prompt_template(
                prompt_name="validator",
                prompt_context={
                    "USER_REQUEST": request_prompt,
                    "FULL_PLAN": full_plan,
                    "EXECUTION_ENVIRONMENT": "AWS Fargate (isolated containers with automatic lifecycle management)"
                }
            ),
            agent_type="claude-sonnet-3-7", # claude-sonnet-3-5-v-2, claude-sonnet-3-7
            enable_reasoning=False,
            prompt_cache_info=(True, None), # reasoning agent uses prompt caching
            tools=[fargate_python_tool, fargate_bash_tool],
            streaming=True  # Enable streaming for consistency
        )

        # Prepare message with context if available
        message = '\n\n'.join([messages[-1]["content"][-1]["text"], clues])

        # Process streaming response and collect text in one pass
        async def process_validator_fargate_stream():
            full_text = ""
            async for event in strands_utils.process_streaming_response_yield(
                validator_agent, message, agent_name="validator", source="validator_fargate_tool"
            ):
                if event.get("event_type") == "text_chunk": full_text += event.get("data", "")
            return {"text": full_text}

        response = asyncio.run(process_validator_fargate_stream())
        result_text = response['text']

        # Update clues
        clues = '\n\n'.join([clues, CLUES_FORMAT.format("validator", response["text"])])

        # Update history
        history = shared_state.get("history", [])
        history.append({"agent":"validator", "message": response["text"]})

        # Update shared state
        shared_state['messages'] = [get_message_from_string(role="user", string=RESPONSE_FORMAT.format("validator", response["text"]), imgs=[])]
        shared_state['clues'] = clues
        shared_state['history'] = history

        logger.info(f"\n{Colors.GREEN}Validator Agent Fargate Tool completed successfully{Colors.END}")

        # Add Event
        add_span_event(span, "input_message", {"message": str(message)})
        add_span_event(span, "response", {"response": str(response["text"])})

        return result_text

# Function name must match tool name
def validator_agent_fargate_tool(tool: ToolUse, **_kwargs: Any) -> ToolResult:
    tool_use_id = tool["toolUseId"]
    task = tool["input"]["task"]

    # Use the existing handle_validator_agent_fargate_tool function
    result = handle_validator_agent_fargate_tool(task)

    # Check if execution was successful based on the result string
    if "Error" in result:
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