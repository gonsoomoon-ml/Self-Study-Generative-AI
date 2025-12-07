"""
데모 4: LangGraph 세션 관리 (Checkpointer)
LangGraph가 세션을 어떻게 관리하는지 보여주고, Strands Agent와 비교합니다.

LangGraph 핵심 개념:
- Checkpointer: 그래프 상태를 각 단계마다 저장
- thread_id: 각 대화 세션의 고유 식별자
- Store: 스레드 간 장기 메모리 (선택 사항)

Strands Agent와 비교:
- Strands: session_manager + session_id
- LangGraph: checkpointer + thread_id

사전 준비:
    1. 설치: pip install langgraph langgraph-checkpoint langchain-aws
    2. AWS 자격 증명 설정 (Bedrock용)

실행 방법:
    cd /home/ubuntu/Self-Study-Generative-AI/lab/22_strands_session_manager
    uv run python code/demo4_langgraph_session.py
"""
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_aws import ChatBedrock
from utils import print_header, print_system, print_success, print_separator, print_error, Colors


# ----------------------------------------------------------------------
# 설정
# ----------------------------------------------------------------------
AWS_REGION = "us-east-1"
MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"
THREAD_ID_ALICE = "thread-alice"  # Alice의 스레드 ID
THREAD_ID_BOB = "thread-bob"      # Bob의 스레드 ID


# ----------------------------------------------------------------------
# 상태 정의
# ----------------------------------------------------------------------
class State(TypedDict):
    """메시지 히스토리를 포함하는 그래프 상태.

    Attributes:
        messages: 대화 메시지 리스트 (add_messages로 자동 누적)
    """
    messages: Annotated[list, add_messages]


# ----------------------------------------------------------------------
# 그래프 생성
# ----------------------------------------------------------------------
def create_graph(checkpointer):
    """세션 지속성을 위한 Checkpointer가 있는 LangGraph를 생성합니다.

    Args:
        checkpointer: 상태를 저장할 체크포인터 (MemorySaver, PostgresSaver 등)

    Returns:
        CompiledGraph: 컴파일된 LangGraph
    """
    # LLM 초기화
    llm = ChatBedrock(
        model_id=MODEL_ID,
        region_name=AWS_REGION,
    )

    def chatbot(state: State):
        """메시지를 처리하는 챗봇 노드.

        Args:
            state: 현재 그래프 상태

        Returns:
            dict: 응답 메시지를 포함한 상태 업데이트
        """
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    # 그래프 빌드
    builder = StateGraph(State)
    builder.add_node("chatbot", chatbot)  # 챗봇 노드 추가
    builder.add_edge(START, "chatbot")    # 시작 -> 챗봇
    builder.add_edge("chatbot", END)      # 챗봇 -> 종료

    # 지속성을 위해 체크포인터와 함께 컴파일
    return builder.compile(checkpointer=checkpointer)


# ----------------------------------------------------------------------
# 헬퍼 함수
# ----------------------------------------------------------------------
def print_user(message: str):
    """사용자 메시지를 출력합니다."""
    print(f"\n{Colors.BOLD}{Colors.USER}[사용자]{Colors.RESET} {message}")


def print_agent(message: str):
    """에이전트 응답을 출력합니다."""
    print(f"\n{Colors.BOLD}{Colors.AGENT}[에이전트]{Colors.RESET} {message}\n")


def chat(graph, thread_id: str, message: str):
    """그래프에 메시지를 보내고 대화를 출력합니다.

    Args:
        graph: LangGraph 인스턴스
        thread_id: 스레드 식별자
        message: 사용자 메시지

    Returns:
        str: 에이전트 응답
    """
    print_user(message)

    # thread_id로 세션 구분
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config
    )

    # 마지막 메시지 (에이전트 응답) 가져오기
    last_message = result["messages"][-1]
    response = last_message.content if hasattr(last_message, 'content') else str(last_message)
    print_agent(response)

    return response


def print_thread_state(graph, thread_id: str):
    """스레드의 현재 상태를 출력합니다.

    Args:
        graph: LangGraph 인스턴스
        thread_id: 스레드 식별자
    """
    config = {"configurable": {"thread_id": thread_id}}
    state = graph.get_state(config)

    print(f"\n{Colors.BOLD}[스레드 상태: {thread_id}]{Colors.RESET}")
    if state.values:
        messages = state.values.get("messages", [])
        print(f"  메시지 수: {len(messages)}")
        for i, msg in enumerate(messages[-4:]):  # 마지막 4개 메시지만 표시
            role = msg.type if hasattr(msg, 'type') else 'unknown'
            content = msg.content if hasattr(msg, 'content') else str(msg)
            print(f"  [{i}] {role}: {content[:50]}...")
    else:
        print("  (비어있음)")


# ----------------------------------------------------------------------
# 메인 함수
# ----------------------------------------------------------------------
def main():
    print_header("데모 4: LangGraph 세션 관리")

    # ------------------------------------------------------------------
    # 초기 설정: 체크포인터 생성 (데모용 인메모리)
    # ------------------------------------------------------------------
    print_system("설정: MemorySaver 체크포인터 생성 중...")

    # MemorySaver는 상태를 메모리에 저장 (프로덕션에서는 PostgresSaver, MongoDBSaver 사용)
    checkpointer = MemorySaver()
    graph = create_graph(checkpointer)

    print(f"모델 ID: {MODEL_ID}")
    print(f"체크포인터: MemorySaver (인메모리)")
    print(f"참고: 프로덕션에서는 PostgresSaver 또는 MongoDBSaver 사용")

    # ------------------------------------------------------------------
    # 단계 1: 사용자 Alice의 대화 (thread-alice)
    # ------------------------------------------------------------------
    print_separator()
    print_system("단계 1: 사용자 Alice 접속...")
    print_separator()

    print(f"스레드 ID: {THREAD_ID_ALICE}")

    chat(graph, THREAD_ID_ALICE, "안녕하세요! 저는 김수진입니다. 다크 모드와 Python을 선호해요.")
    chat(graph, THREAD_ID_ALICE, "현재 머신러닝 프로젝트를 진행 중입니다.")

    print_thread_state(graph, THREAD_ID_ALICE)

    # ------------------------------------------------------------------
    # 단계 2: 사용자 Bob의 대화 (thread-bob)
    # ------------------------------------------------------------------
    print_separator()
    print_system("단계 2: 사용자 Bob 접속 (다른 스레드)...")
    print_separator()

    print(f"스레드 ID: {THREAD_ID_BOB}")

    chat(graph, THREAD_ID_BOB, "안녕하세요! 저는 이동현입니다. 라이트 모드와 JavaScript를 좋아해요.")
    chat(graph, THREAD_ID_BOB, "제 이름이 뭐죠?")

    print_thread_state(graph, THREAD_ID_BOB)

    # ------------------------------------------------------------------
    # 단계 3: Alice 계속 대화 (같은 스레드, 세션 유지)
    # ------------------------------------------------------------------
    print_separator()
    print_system("단계 3: Alice 대화 계속...")
    print_system("같은 thread_id 사용 - 체크포인터가 세션 상태 유지")
    print_separator()

    print(f"스레드 ID: {THREAD_ID_ALICE}")

    chat(graph, THREAD_ID_ALICE, "제 이름이 뭐고 어떤 프로젝트를 하고 있다고 했죠?")

    # ------------------------------------------------------------------
    # 단계 4: Bob 계속 대화 (같은 스레드, 세션 유지)
    # ------------------------------------------------------------------
    print_separator()
    print_system("단계 4: Bob 대화 계속...")
    print_separator()

    print(f"스레드 ID: {THREAD_ID_BOB}")

    chat(graph, THREAD_ID_BOB, "제 이름이 뭐고 무엇을 좋아한다고 했죠?")

    print_success("성공: 두 스레드 모두 별도의 대화 히스토리를 유지합니다!")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 비교: Strands vs LangGraph
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("비교: Strands Agent vs LangGraph 세션 관리")
    print("=" * 60)
    print("""
| 항목               | Strands Agent              | LangGraph                  |
|--------------------|----------------------------|----------------------------|
| 세션 식별자        | session_id                 | thread_id                  |
| 지속성 레이어      | SessionManager             | Checkpointer               |
| 기본 제공 백엔드   | File, S3, AgentCore        | Memory, Postgres, MongoDB  |
| 상태 저장          | messages + agent.state     | Graph state (TypedDict)    |
| 멀티 에이전트      | Orchestrator만             | 그래프의 각 노드           |
| 커스텀 상태        | agent.state dict           | Custom TypedDict 필드      |
| 장기 메모리        | AgentCore Memory (LTM)     | Store (크로스 스레드)      |
""")

    print("\n" + "=" * 60)
    print("핵심 개념 비교:")
    print("=" * 60)
    print("""
Strands Agent:
  session_manager = FileSessionManager(session_id="user-123")
  agent = Agent(session_manager=session_manager)

LangGraph:
  checkpointer = MemorySaver()  # 또는 PostgresSaver, MongoDBSaver
  graph = builder.compile(checkpointer=checkpointer)
  graph.invoke(input, {"configurable": {"thread_id": "user-123"}})

상태 조회:
  Strands: agent.messages, agent.state.get()
  LangGraph: graph.get_state(config), graph.get_state_history(config)
""")


# ----------------------------------------------------------------------
# 엔트리 포인트
# ----------------------------------------------------------------------
if __name__ == "__main__":
    main()
