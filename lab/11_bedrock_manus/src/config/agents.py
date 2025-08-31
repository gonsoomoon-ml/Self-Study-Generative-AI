from typing import Literal, Tuple

# Define available LLM types
LLMType = Literal["basic", "reasoning", "vision", "advanced"]
CACHEType = Tuple[bool, Literal["default", "ephemeral"]]

# Define agent-LLM mapping

# AGENT_LLM_MAP: dict[str, LLMType] = {
#     "coordinator": "basic",
#     "planner": "reasoning",
#     "supervisor": "reasoning",
#     "researcher": "basic",
#     "coder": "basic",
#     "browser": "vision",
#     "reporter": "reasoning"
# }

# High Quality
# AGENT_LLM_MAP: dict[str, LLMType] = {
#     "coordinator": "basic",
#     "planner": "reasoning",
#     "supervisor": "reasoning",
#     "researcher": "basic",
#     "coder": "reasoning",
#     "browser": "vision",
#     "reporter": "reasoning"
# }



# Low  Quality
AGENT_LLM_MAP: dict[str, LLMType] = {
    "coordinator": "reasoning",
    "planner": "advanced",
    "supervisor": "reasoning",
    "coder": "reasoning",
    "validator": "reasoning",
    "reporter": "reasoning",
    "researcher": "basic",
    "browser": "vision"
}

# AGENT_PROMPT_CACHE_MAP: dict[bool, CACHEType] = {
#     "coordinator": (False, "default"),
#     "planner": (False, "default"),
#     "supervisor": (False, "default"),
#     "researcher": (False, "default"),
#     "coder": (False, "default"),
#     "validator": (False, "default"),
#     "browser": (False, "default"),
#     "reporter": (False, "default")
# }

AGENT_PROMPT_CACHE_MAP: dict[bool, CACHEType] = {
    "coordinator": (False, "default"),
    "planner": (True, "default"),
    "supervisor": (True, "default"),
    "researcher": (False, "default"),
    "coder": (False, "default"),
    "validator": (False, "default"),
    "browser": (False, "default"),
    "reporter": (True, "default")
}

