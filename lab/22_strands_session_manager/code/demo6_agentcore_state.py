"""
데모 6: agent.state를 사용한 커스텀 상태 저장 (AgentCore Memory)
AgentCoreMemorySessionManager와 함께 agent.state를 사용하는 방법을 보여줍니다.
demo5와 동일한 개념이지만, 저장 위치가 AWS 클라우드입니다.

FileSessionManager vs AgentCore Memory (agent.state):
- FileSessionManager: 로컬 디스크 (agent.json)
- AgentCore Memory: AWS 클라우드 (SessionAgent 이벤트)

AgentCore Memory 특징:
- 불변(immutable) 이벤트 기반 저장
- 상태 변경 히스토리 보존
- 분산/확장 가능

사전 준비:
    1. AWS 자격 증명 설정
    2. 설치: pip install 'bedrock-agentcore[strands-agents]'

실행 방법:
    cd /home/ubuntu/Self-Study-Generative-AI/lab/22_strands_session_manager
    uv run python code/demo6_agentcore_state.py
"""
import time
from strands import Agent
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from utils import print_header, print_system, print_success, print_separator, print_error, chat, Colors


# ----------------------------------------------------------------------
# 설정
# ----------------------------------------------------------------------
AWS_REGION = "us-east-1"
MEMORY_NAME = "strands_session_demo"  # demo3에서 사용한 메모리 재사용
SESSION_ID = "session-alice-state"    # 세션 ID
ACTOR_ID = "actor-alice-state"        # 액터 ID


# ----------------------------------------------------------------------
# 헬퍼 함수
# ----------------------------------------------------------------------
def print_state(agent, title: str = "현재 상태"):
    """에이전트의 커스텀 상태를 출력합니다.

    Args:
        agent: Strands Agent 인스턴스
        title: 출력 제목
    """
    print(f"\n{Colors.BOLD}[{title}]{Colors.RESET}")
    # agent.state.get() - 키 없이 호출하면 전체 데이터 dict 반환
    state_data = agent.state.get()
    if not state_data:
        print("  (비어있음)")
        return
    for key, value in state_data.items():
        print(f"  {key}: {value}")


def create_or_get_memory(client: MemoryClient, name: str) -> str:
    """메모리 리소스를 생성하거나 기존 것을 가져옵니다.

    Args:
        client: AgentCore 메모리 클라이언트
        name: 메모리 리소스 이름

    Returns:
        str: 메모리 ID
    """
    try:
        memories = client.list_memories()
        memory_list = memories if isinstance(memories, list) else memories.get("memories", [])
        for memory in memory_list:
            memory_id = memory.get("memoryId") or memory.get("memory_id") or memory.get("id")
            if memory_id and memory_id.startswith(name):
                status = memory.get("status", "UNKNOWN")
                if status == "ACTIVE":
                    print(f"기존 메모리 사용: {memory_id} (상태: {status})")
                    return memory_id
                else:
                    print(f"메모리 {memory_id} 발견, 상태: {status}, 대기 중...")
                    return wait_for_memory_active(client, memory_id)
    except Exception as e:
        print(f"참고: 메모리 목록 조회 실패: {e}")

    # 새 메모리 생성
    response = client.create_memory(
        name=name,
        description="Strands agent.state 데모용 메모리"
    )
    memory_id = response.get("memoryId") or response.get("memory_id")
    print(f"새 메모리 생성됨: {memory_id}")
    return wait_for_memory_active(client, memory_id)


def wait_for_memory_active(client: MemoryClient, memory_id: str, max_wait: int = 60) -> str:
    """메모리가 활성화될 때까지 대기합니다.

    Args:
        client: AgentCore 메모리 클라이언트
        memory_id: 메모리 ID
        max_wait: 최대 대기 시간 (초)

    Returns:
        str: 활성화된 메모리 ID
    """
    print(f"메모리 활성화 대기 중...")
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            memory = client.get_memory(memoryId=memory_id)
            status = memory.get("status", "UNKNOWN")
            print(f"  메모리 상태: {status}")

            if status == "ACTIVE":
                print(f"메모리가 활성화되었습니다!")
                return memory_id
            elif status in ["FAILED", "DELETED"]:
                raise Exception(f"메모리 실패: {status}")
        except Exception as e:
            if "ACTIVE" not in str(e):
                print(f"  상태 확인 중: {e}")

        time.sleep(3)

    raise Exception(f"메모리가 {max_wait}초 내에 활성화되지 않았습니다")


# ----------------------------------------------------------------------
# 에이전트 팩토리
# ----------------------------------------------------------------------
def create_session_manager(memory_id: str, session_id: str, actor_id: str):
    """AgentCore 메모리 세션 관리자를 생성합니다.

    Args:
        memory_id: AgentCore 메모리 리소스 ID
        session_id: 세션 식별자
        actor_id: 액터(사용자) 식별자

    Returns:
        AgentCoreMemorySessionManager: AWS 클라우드 기반 세션 관리자
    """
    config = AgentCoreMemoryConfig(
        memory_id=memory_id,
        session_id=session_id,
        actor_id=actor_id
    )
    return AgentCoreMemorySessionManager(
        agentcore_memory_config=config,
        region_name=AWS_REGION
    )


def create_agent(session_manager):
    """AgentCore Memory 세션 관리자를 사용하는 에이전트를 생성합니다.

    Args:
        session_manager: AgentCore 메모리 세션 관리자

    Returns:
        Agent: 클라우드 세션 관리 기능이 있는 에이전트
    """
    return Agent(
        system_prompt="당신은 친절한 한국어 도우미입니다. 간결하게 응답하세요.",
        # AgentCoreMemorySessionManager - agent.state를 AgentCore Memory에 저장
        session_manager=session_manager,
        callback_handler=None  # 스트리밍 출력 비활성화
    )


# ----------------------------------------------------------------------
# 메인 함수
# ----------------------------------------------------------------------
def main():
    print_header("데모 6: agent.state with AgentCore Memory")

    # ------------------------------------------------------------------
    # 초기 설정: AgentCore Memory 리소스 연결
    # ------------------------------------------------------------------
    print_system("설정: Bedrock AgentCore Memory 연결 중...")

    try:
        client = MemoryClient(region_name=AWS_REGION)
        memory_id = create_or_get_memory(client, MEMORY_NAME)
        print(f"메모리 ID: {memory_id}")
        print(f"리전: {AWS_REGION}")
    except Exception as e:
        print_error(f"AgentCore Memory 연결 실패: {e}")
        print("\n다음 사항을 확인하세요:")
        print("  1. AWS 자격 증명이 설정되어 있는지")
        print("  2. pip install 'bedrock-agentcore[strands-agents]' 설치 여부")
        print("  3. AWS 계정에서 Bedrock AgentCore 접근 권한")
        return

    # ------------------------------------------------------------------
    # 단계 1: 에이전트 생성 및 커스텀 상태 저장
    # ------------------------------------------------------------------
    print_separator()
    print_system("단계 1: 에이전트 생성 및 커스텀 상태 저장...")
    print_separator()

    session_manager = create_session_manager(memory_id, SESSION_ID, ACTOR_ID)
    agent = create_agent(session_manager)

    print(f"모델 ID: {agent.model.config.get('model_id', 'unknown')}")
    print(f"세션 ID: {SESSION_ID}")
    print(f"액터 ID: {ACTOR_ID}")

    # 커스텀 상태 저장 - set() 메서드 사용
    agent.state.set("user_preferences", {
        "theme": "dark",        # 테마 설정
        "language": "ko",       # 언어 설정
        "notifications": True   # 알림 설정
    })
    agent.state.set("visit_count", 1)  # 방문 횟수
    agent.state.set("last_topic", "AgentCore Memory")  # 마지막 주제
    agent.state.set("favorite_languages", ["Python", "TypeScript"])  # 선호 언어

    print_state(agent, "저장된 상태")

    # 에이전트 호출 시 AgentCore Memory에 저장됨
    chat(agent, "안녕하세요! 저는 다크 모드와 한국어를 선호합니다.")

    # ------------------------------------------------------------------
    # 단계 2: 앱 재시작 시뮬레이션 및 상태 복원 확인
    # ------------------------------------------------------------------
    print_separator()
    print_system("단계 2: 앱 재시작 시뮬레이션...")
    print_system("AgentCore Memory에서 커스텀 상태가 복원되는지 확인...")
    print_separator()

    restored_session_manager = create_session_manager(memory_id, SESSION_ID, ACTOR_ID)
    restored_agent = create_agent(restored_session_manager)

    print(f"세션 ID: {SESSION_ID} (복원됨)")
    print_state(restored_agent, "복원된 상태")

    # 상태 값 검증
    prefs = restored_agent.state.get("user_preferences") or {}
    print(f"\n검증 결과:")
    print(f"  테마: {prefs.get('theme')} {'✓' if prefs.get('theme') == 'dark' else '✗'}")
    print(f"  언어: {prefs.get('language')} {'✓' if prefs.get('language') == 'ko' else '✗'}")
    print(f"  방문 횟수: {restored_agent.state.get('visit_count')} {'✓' if restored_agent.state.get('visit_count') == 1 else '✗'}")

    # ------------------------------------------------------------------
    # 단계 3: 상태 업데이트 (방문 횟수 증가)
    # ------------------------------------------------------------------
    print_separator()
    print_system("단계 3: 상태 업데이트 (방문 횟수 증가)...")
    print_separator()

    old_count = restored_agent.state.get("visit_count") or 0
    restored_agent.state.set("visit_count", old_count + 1)
    restored_agent.state.set("last_topic", "agent.state with AgentCore")

    print(f"visit_count: {old_count} -> {restored_agent.state.get('visit_count')}")
    print(f"last_topic: 'AgentCore Memory' -> '{restored_agent.state.get('last_topic')}'")

    # 저장 트리거
    chat(restored_agent, "제가 선호하는 언어가 뭐라고 했죠?")

    # ------------------------------------------------------------------
    # 단계 4: 다시 재시작하여 업데이트된 상태 확인
    # ------------------------------------------------------------------
    print_separator()
    print_system("단계 4: 다시 재시작하여 업데이트된 상태 확인...")
    print_separator()

    final_session_manager = create_session_manager(memory_id, SESSION_ID, ACTOR_ID)
    final_agent = create_agent(final_session_manager)

    print_state(final_agent, "최종 복원 상태")

    # 업데이트된 값 검증
    print(f"\n검증 결과:")
    print(f"  visit_count: {final_agent.state.get('visit_count')} {'✓' if final_agent.state.get('visit_count') == 2 else '✗'}")
    print(f"  last_topic: {final_agent.state.get('last_topic')} {'✓' if final_agent.state.get('last_topic') == 'agent.state with AgentCore' else '✗'}")

    print_success("성공: 커스텀 상태가 AgentCore Memory에서 유지됩니다!")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 요약: agent.state 저장 위치 비교
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("요약: agent.state 저장 위치 비교")
    print("=" * 60)
    print("""
| 항목             | FileSessionManager       | AgentCore Memory          |
|------------------|--------------------------|---------------------------|
| 저장 위치        | 로컬 디스크 (agent.json) | AWS 클라우드              |
| 저장 방식        | JSON 파일 덮어쓰기       | 불변 이벤트 추가          |
| 상태 히스토리    | 없음                     | 있음 (이벤트 히스토리)    |
| 확장성           | 단일 서버                | 분산, 확장 가능           |
| 비용             | 무료                     | AWS 요금                  |
| 자동 선호도 추출 | 없음                     | LTM 전략으로 가능         |

참고:
- agent.state는 수동으로 저장하는 커스텀 데이터
- AgentCore LTM은 대화에서 자동으로 선호도/팩트 추출
- 두 기능은 독립적으로 사용 가능
""")


# ----------------------------------------------------------------------
# 엔트리 포인트
# ----------------------------------------------------------------------
if __name__ == "__main__":
    main()
