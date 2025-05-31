import logging
from textwrap import dedent
from src.config import TEAM_MEMBERS
from src.graph import build_graph
from src.utils.common_utils import get_message_from_string
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Default level is INFO
    # level=logging.INFO,  # Default level is INFO
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

def enable_debug_logging():
    """Enable debug level logging for more detailed execution information."""
    logging.getLogger(__name__).setLevel(logging.DEBUG)

enable_debug_logging()


# 로거 설정을 전역으로 한 번만 수행
logger = logging.getLogger(__name__)
logger.propagate = False
for handler in logger.handlers[:]:
    logger.removeHandler(handler)
handler = logging.StreamHandler()
formatter = logging.Formatter('\n%(levelname)s [%(name)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
# logger.setLevel(logging.INFO)  # 기본 레벨은 INFO로 설정
logger.setLevel(logging.DEBUG) 

from dotenv import load_dotenv
import os
from langfuse.callback import CallbackHandler
import os

########################################################
# Add by Gonsoo
########################################################
def get_langfuse_handler():
    # .env 파일에서 환경 변수 로드
    load_dotenv("../.env")


    langfuse_handler = CallbackHandler(
        public_key=os.environ.get('LANGFUSE_PUBLIC_KEY'),
        secret_key=os.environ.get('LANGFUSE_SECRET_KEY'),
        host=os.environ.get('LANGFUSE_HOST'),
    )

    # connection test
    print("## Langfuse 인증 테스트:", langfuse_handler.auth_check())    

    return langfuse_handler
########################################################


class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

# Create the graph
graph = build_graph()

def get_graph():
    return graph


from langchain_core.runnables import RunnableConfig

def run_agent_workflow(user_input: str, csv_file_path: str = None, debug: bool = False):
    """Run the agent workflow with the given user input.

    Args:
        user_input: The user's query or request
        debug: If True, enables debug level logging

    Returns:
        The final state after the workflow completes
    """
    if not user_input:
        raise ValueError("Input could not be empty")

    if debug:
        enable_debug_logging()

    logger.info(f"{Colors.GREEN}===== Starting workflow ====={Colors.END}")
    logger.info(f"{Colors.GREEN}\nuser input: {user_input}{Colors.END}")
    logger.info(f"{Colors.GREEN}\nuser file path: {csv_file_path}{Colors.END}")
    
    # csv_file_path가 주어지면 파일 경로만 user_prompts에 포함
    if csv_file_path is not None:
        user_prompts = dedent(
            '''
            Here is a user request: <user_request>{user_request}</user_request>\n
            Here is a file path: <file_path>{file_path}</file_path>
            '''
        )
        context = {"user_request": user_input, "file_path": csv_file_path}
        user_prompts = user_prompts.format(**context)
    else:
        user_prompts = dedent(
            '''
            Here is a user request: <user_request>{user_request}</user_request>
            '''
        )
        context = {"user_request": user_input}
        user_prompts = user_prompts.format(**context)
    messages = [get_message_from_string(role="user", string=user_prompts, imgs=[])]

    langfuse_handler = get_langfuse_handler()
    config = RunnableConfig(
                recursion_limit=30, 
                callbacks=[langfuse_handler]  # 여기에 Langfuse 핸들러 추가}    
    )
    result = graph.invoke(
        input={
            # Constants
            "TEAM_MEMBERS": TEAM_MEMBERS,
            # Runtime Variables
            #"messages": [{"role": "user", "content": user_input}],
            "messages": messages,
            "deep_thinking_mode": True,
            "search_before_planning": False,
            "request": user_prompts 
        },
        config=config    
    )
    # result = graph.invoke(
    #     input={
    #         # Constants
    #         "TEAM_MEMBERS": TEAM_MEMBERS,
    #         # Runtime Variables
    #         #"messages": [{"role": "user", "content": user_input}],
    #         "messages": messages,
    #         "deep_thinking_mode": True,
    #         "search_before_planning": False,
    #         "request": user_input
    #     },
    #     config=config    
    # )
    logger.debug(f"{Colors.RED}Final workflow state: {result}{Colors.END}")
    logger.info(f"{Colors.GREEN}===== Workflow completed successfully ====={Colors.END}")
    return result


if __name__ == "__main__":
    print(graph.get_graph().draw_mermaid())
