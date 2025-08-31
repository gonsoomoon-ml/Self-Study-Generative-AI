import os
import logging
import json
from src.prompts.template import apply_prompt_template
from src.config.agents import AGENT_LLM_MAP, AGENT_PROMPT_CACHE_MAP
from src.tools.research_tools import research_tool_config, process_search_tool
from src.tools.coder_tools import coder_tool_config, process_coder_tool
# from src.tools.browser_tools import browser_tool_config, process_browser_tool
from src.tools.reporter_tools import reporter_tool_config, process_reporter_tool
from src.tools.validator_tools import validator_tool_config, process_validator_tool

from src.agents.llm import llm_call_langfuse

llm_module = os.environ.get('LLM_MODULE', 'src.agents.llm')
if llm_module == 'src.agents.llm_st': from src.agents.llm_st import get_llm_by_type, llm_call
else: from src.agents.llm import get_llm_by_type, llm_call

# 새 핸들러와 포맷터 설정
logger = logging.getLogger(__name__)
logger.propagate = False  # 상위 로거로 메시지 전파 중지
for handler in logger.handlers[:]:
    logger.removeHandler(handler)
handler = logging.StreamHandler()
formatter = logging.Formatter('\n%(levelname)s [%(name)s] %(message)s')  # 로그 레벨이 동적으로 표시되도록 변경
handler.setFormatter(formatter)
logger.addHandler(handler)
# DEBUG와 INFO 중 원하는 레벨로 설정
logger.setLevel(logging.INFO)  # 기본 레벨은 INFO로 설정

class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class create_react_agent():

    def __init__(self, **kwargs):

        self.agent_name = kwargs["agent_name"]
        self.llm = get_llm_by_type(AGENT_LLM_MAP[self.agent_name])
        self.llm.stream = True
        self.llm_caller = llm_call(llm=self.llm, verbose=False, tracking=False)
        
        if AGENT_LLM_MAP[self.agent_name] in ["reasoning"]: self.enable_reasoning = True
        else: self.enable_reasoning = False
        
        if self.agent_name == "researcher": self.tool_config = research_tool_config
        elif self.agent_name == "coder": self.tool_config = coder_tool_config
        elif self.agent_name == "validator": self.tool_config = validator_tool_config
        # elif self.agent_name == "browser": self.tool_config = browser_tool_config
        elif self.agent_name == "reporter": self.tool_config = reporter_tool_config
            
        # 반복 대화 처리를 위한 설정
        self.MAX_TURNS = 30  # 무한 루프 방지용 최대 턴 수
        self.turn = 0
        self.final_response = False
        
    def invoke(self, **kwargs):

        state = kwargs.get("state", None)
        prompt_cache, cache_type = AGENT_PROMPT_CACHE_MAP[self.agent_name]
        system_prompts, messages = apply_prompt_template(self.agent_name, state, prompt_cache=prompt_cache, cache_type=cache_type)    
        
        # 도구 사용이 종료될 때까지 반복
        while not self.final_response and self.turn < self.MAX_TURNS:
            self.turn += 1
            logger.info(f"{Colors.YELLOW}🔄 --- {self.agent_name} 대화 턴 {self.turn} ---{Colors.END}")
            response, ai_message = self.llm_caller.invoke(
                agent_name=self.agent_name,
                messages=messages,
                system_prompts=system_prompts,
                tool_config=self.tool_config,
                enable_reasoning=self.enable_reasoning,
                reasoning_budget_tokens=8192
            )
            messages.append(ai_message)    

            # 도구 사용 요청 확인
            stop_reason = response.get("stop_reason") or response.get("stopReason")
            if stop_reason is None:
                # print("response에 stop_reason이 없습니다:", json.dumps(response, indent=2, ensure_ascii=False))
                pass
            if stop_reason == "tool_use":
                tool_requests_found = False

                # 응답에서 모든 도구 사용 요청 처리
                for content in ai_message['content']:
                    if 'toolUse' in content:
                        tool = content['toolUse']
                        tool_requests_found = True

                        # ReAct 단계별 행동 설명
                        tool_descriptions = {
                            "search_tool": "🔍 검색 수행 중",
                            "read_file_tool": "📖 파일 읽기 중",
                            "write_file_tool": "📝 파일 쓰기 중", 
                            "python_repl_tool": "🐍 파이썬 코드 실행 중",
                            "crawl_tool": "🌐 웹 크롤링 중",
                            "bash_tool": "⚡ 시스템 명령 실행 중"
                        }
                        
                        action_desc = tool_descriptions.get(tool['name'], f"🔧 {tool['name']} 실행 중")
                        logger.info(f"{Colors.YELLOW}🤖 ReAct Action: {action_desc}{Colors.END}")
                        logger.info(f"{Colors.BOLD}ToolUse - Tool Name: {tool['name']}, Input: {tool['input']}{Colors.END}")

                        if self.agent_name == "researcher": tool_result_message = process_search_tool(tool)
                        elif self.agent_name == "coder": tool_result_message = process_coder_tool(tool)
                        elif self.agent_name == "validator": tool_result_message = process_validator_tool(tool)
                        # elif self.agent_name == "browser": tool_result_message = process_browser_tool(tool)
                        elif self.agent_name == "reporter": tool_result_message = process_reporter_tool(tool)

                        messages.append(tool_result_message)
                        logger.info(f"{Colors.GREEN}✅ ReAct Observation: 도구 실행 완료{Colors.END}")
                        logger.info(f"{Colors.BOLD}ToolUse - 도구 실행 결과를 대화에 추가했습니다.{Colors.END}")

                # 도구 요청이 없으면 루프 종료
                if not tool_requests_found:
                    # print("도구 요청을 찾을 수 없습니다.")
                    # logger.info(f"{Colors.UNDERLINE}ToolUse - 도구 요청을 찾을 수 없습니다.{Colors.END}")
                    self.final_response = True
            else:
                # 도구 사용이 요청되지 않았으면 최종 응답으로 간주
                self.final_response = True
                # logger.info(f"{Colors.UNDERLINE}ToolUse - 최종 응답을 받았습니다.{Colors.END}")
                # print("최종 응답을 받았습니다.")

        # print("\n=== 대화 완료 ===")
        # print("최종 응답:\n", response)
        # print("메시지:\n", ai_message)
        
        return ai_message
    


class create_react_agent_langfuse():

    def __init__(self, **kwargs):

        self.agent_name = kwargs["agent_name"]
        self.llm = get_llm_by_type(AGENT_LLM_MAP[self.agent_name])
        # print("## Agent Name: ", self.agent_name, " , ", AGENT_LLM_MAP[self.agent_name])
        self.llm.stream = True
        # self.llm_caller = llm_call(llm=self.llm, verbose=False, tracking=False)
        self.llm_caller = llm_call_langfuse(llm=self.llm, verbose=False, tracking=False)
        
        if AGENT_LLM_MAP[self.agent_name] in ["reasoning"]: 
            self.enable_reasoning = True
            # self.enable_reasoning = False
        else: self.enable_reasoning = False
        
        if self.agent_name == "researcher": self.tool_config = research_tool_config
        elif self.agent_name == "coder": self.tool_config = coder_tool_config
        elif self.agent_name == "validator": self.tool_config = validator_tool_config
        # elif self.agent_name == "browser": self.tool_config = browser_tool_config
        elif self.agent_name == "reporter": self.tool_config = reporter_tool_config
            
        # 반복 대화 처리를 위한 설정
        self.MAX_TURNS = 20  # 무한 루프 방지용 최대 턴 수
        # self.MAX_TURNS = 12  # 무한 루프 방지용 최대 턴 수
        self.turn = 0
        self.final_response = False
        
    def invoke(self, **kwargs):

        state = kwargs.get("state", None)
        prompt_cache, cache_type = AGENT_PROMPT_CACHE_MAP[self.agent_name]
        system_prompts, messages = apply_prompt_template(self.agent_name, state, prompt_cache=prompt_cache, cache_type=cache_type)    
        
        # 도구 사용이 종료될 때까지 반복
        while not self.final_response and self.turn < self.MAX_TURNS:
            self.turn += 1
            logger.info(f"{Colors.YELLOW}🔄 --- {self.agent_name} 대화 턴 {self.turn} ---{Colors.END}")
            response, ai_message = self.llm_caller.invoke(
                agent_name=self.agent_name,
                messages=messages,
                system_prompts=system_prompts,
                tool_config=self.tool_config,
                enable_reasoning=self.enable_reasoning,
                reasoning_budget_tokens=8192
            )
            messages.append(ai_message)    

            # print("## response in agent: \n", json.dumps(response, indent=2, ensure_ascii=False))
            
            # 도구 사용 요청 확인
            stop_reason = response.get("stop_reason") or response.get("stopReason")
            if stop_reason is None:
                # print("response에 stop_reason이 없습니다:", json.dumps(response, indent=2, ensure_ascii=False))
                pass
            if stop_reason == "tool_use":
                tool_requests_found = False

                # 응답에서 모든 도구 사용 요청 처리
                for content in ai_message['content']:
                    if 'toolUse' in content:
                        tool = content['toolUse']
                        tool_requests_found = True

                        # ReAct 단계별 행동 설명
                        tool_descriptions = {
                            "search_tool": "🔍 검색 수행 중",
                            "read_file_tool": "📖 파일 읽기 중",
                            "write_file_tool": "📝 파일 쓰기 중", 
                            "python_repl_tool": "🐍 파이썬 코드 실행 중",
                            "crawl_tool": "🌐 웹 크롤링 중",
                            "bash_tool": "⚡ 시스템 명령 실행 중"
                        }
                        
                        action_desc = tool_descriptions.get(tool['name'], f"🔧 {tool['name']} 실행 중")
                        logger.info(f"{Colors.YELLOW}🤖 ReAct Action: {action_desc}{Colors.END}")
                        logger.info(f"{Colors.BOLD}ToolUse - Tool Name: {tool['name']}, Input: {tool['input']}{Colors.END}")

                        if self.agent_name == "researcher": tool_result_message = process_search_tool(tool)
                        elif self.agent_name == "coder": tool_result_message = process_coder_tool(tool)
                        elif self.agent_name == "validator": tool_result_message = process_validator_tool(tool)
                        # elif self.agent_name == "browser": tool_result_message = process_browser_tool(tool)
                        elif self.agent_name == "reporter": tool_result_message = process_reporter_tool(tool)

                        messages.append(tool_result_message)
                        logger.info(f"{Colors.GREEN}✅ ReAct Observation: 도구 실행 완료{Colors.END}")
                        logger.info(f"{Colors.BOLD}ToolUse - 도구 실행 결과를 대화에 추가했습니다.{Colors.END}")

                # 도구 요청이 없으면 루프 종료
                if not tool_requests_found:
                    # print("도구 요청을 찾을 수 없습니다.")
                    # logger.info(f"{Colors.UNDERLINE}ToolUse - 도구 요청을 찾을 수 없습니다.{Colors.END}")
                    self.final_response = True
            else:
                # 도구 사용이 요청되지 않았으면 최종 응답으로 간주
                self.final_response = True
                # logger.info(f"{Colors.UNDERLINE}ToolUse - 최종 응답을 받았습니다.{Colors.END}")
                # print("최종 응답을 받았습니다.")

        # print("\n=== 대화 완료 ===")
        # print("최종 응답:\n", response)
        # print("메시지:\n", ai_message)
        
        return ai_message


research_agent = None
coder_agent = None
browser_agent = None
