from typing import Literal, Tuple

# Define available LLM types
LLMType = Literal["basic", "reasoning", "vision"]
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

# Middle Quality
# AGENT_LLM_MAP: dict[str, LLMType] = {
#     "coordinator": "basic",
#     "planner": "basic",
#     "supervisor": "basic",
#     "researcher": "basic",
#     "coder": "basic",
#     "browser": "vision",
#     "reporter": "reasoning"
# }

# Low  Quality
AGENT_LLM_MAP: dict[str, LLMType] = {
    "coordinator": "basic",
    "planner": "basic",
    "supervisor": "basic",
    "researcher": "basic",
    "coder": "basic",
    "browser": "vision",
    "reporter": "basic"
}

AGENT_PROMPT_CACHE_MAP: dict[bool, CACHEType] = {
    "coordinator": (False, "default"),
    "planner": (False, "default"),
    "supervisor": (False, "default"),
    "researcher": (False, "default"),
    "coder": (False, "default"),
    "browser": (False, "default"),
    "reporter": (False, "default")
}

# AGENT_PROMPT_CACHE_MAP: dict[bool, CACHEType] = {
#     "coordinator": (False, "default"),
#     "planner": (True, "default"),
#     "supervisor": (True, "default"),
#     "researcher": (False, "default"),
#     "coder": (False, "default"),
#     "browser": (False, "default"),
#     "reporter": (True, "default")
# }

